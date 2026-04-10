.PHONY: install dev setup-hooks coverage clean logos dev-desktop dev-website dev-postgres dev-api k8s-secrets-web-api release-desktop release-fl-server release-shenas-net release-web-api setup-android android-emulator android-dev infra-init infra-import infra-plan infra-apply infra-output infra-destroy infra-gh-vars k8s-apply k8s-status k8s-logs flush-db github-init github-plan github-apply github-output github-destroy oss-init oss-sync

# Set up Android SDK, NDK, and Rust targets for mobile development
ANDROID_SDK_ROOT = $(HOME)/Android/Sdk
NDK_VERSION = 27.2.12479018
NDK_ZIP = android-ndk-r27d-linux.zip

install:
	uv tool install --editable app/ --force
	@echo "Installed shenas and shenasctl to ~/.local/bin/"
	@echo "Run 'shenasctl --install-completion' for tab completion"

dev:
	@fuser -k 7280/tcp 5173/tcp 2>/dev/null; sleep 0.3; \
	uv sync --group fl --quiet; \
	(cd app/vendor && npm install --silent && npm run build --silent); \
	for pkg in plugins/frontends/* plugins/dashboards/*; do \
		[ -f "$$pkg/package.json" ] || continue; \
		[ -f "$$pkg/vite.config.js" ] || continue; \
		static=$$(find "$$pkg" -path '*/static' -type d 2>/dev/null | head -1); \
		if [ -z "$$static" ] || [ -z "$$(ls -A $$static 2>/dev/null)" ]; then \
			echo "Building $$pkg (missing static/)..."; \
			(cd "$$pkg" && npm install --silent && npm run build); \
		fi; \
	done; \
	trap 'kill 0' EXIT; \
	uv run shenas --reload --no-tls & \
	while ! curl -s http://127.0.0.1:7280/api/health > /dev/null 2>&1; do sleep 0.2; done; \
	cd plugins/frontends/default && npx vite & \
	wait

# Install git pre-commit hook
setup-hooks:
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

coverage:
	uv run --no-sync pytest --cov=repo_server --cov=app \
		--cov=shenas_pipes --cov=shenas_schemas \
		--cov-report=term-missing --cov-report=html:htmlcov --cov-report=json:coverage.json

# Regenerate all PNG logos from the source SVG (requires rsvg-convert)
logos:
	@SVG=app/static/images/shenas.svg; \
	MARK=app/static/images/shenas-mark.svg; \
	rsvg-convert -w 192 -h 192 $$SVG -o app/static/images/shenas.png; \
	rsvg-convert -w 192 -h 192 $$SVG -o app/static/images/shenas-192.png; \
	rsvg-convert -w 192 -h 192 $$MARK -o app/static/images/shenas-mark-192.png; \
	for s in 32 128 256 512; do \
		rsvg-convert -w $$s -h $$s $$MARK -o app/desktop/src-tauri/icons/$${s}x$${s}.png; \
		rsvg-convert -w $$s -h $$s $$MARK -o app/mobile/src-tauri/icons/$${s}x$${s}.png; \
	done; \
	rsvg-convert -w 512 -h 512 $$MARK -o app/desktop/src-tauri/icons/icon.png; \
	rsvg-convert -w 512 -h 512 $$MARK -o app/mobile/src-tauri/icons/icon.png; \
	rsvg-convert -w 512 -h 512 $$SVG -o server/shenas.net/public/logo.png; \
	rsvg-convert -w 192 -h 192 $$SVG -o server/shenas.net/public/logo-192.png; \
	cp $$MARK server/shenas.net/public/favicon.svg; \
	echo "Regenerated all logos from $$SVG and $$MARK"

dev-website:
	cd server/shenas.net && npm install --silent && npm run dev

dev-desktop:
	cd app/desktop && npx tauri dev

# Build sidecars + Tauri desktop app and run
build-desktop:
	uv run python build/pyinstaller_build.py --onefile
	cp dist/pyinstaller/shenas-x86_64-unknown-linux-gnu app/desktop/src-tauri/binaries/
	cp dist/pyinstaller/shenas-scheduler-x86_64-unknown-linux-gnu app/desktop/src-tauri/binaries/
	cp dist/pyinstaller/shenasctl-x86_64-unknown-linux-gnu app/desktop/src-tauri/binaries/
	cd app/desktop/src-tauri && cargo run --release

# Create the shenas_net database for the web API
dev-postgres:
	@createdb -U postgres shenas_net 2>/dev/null && echo "Created database shenas_net" || echo "Database shenas_net already exists"
	@echo "DATABASE_URL=postgres://postgres@localhost:5432/shenas_net"

# Start the web API dev server (auth + future vault endpoints)
dev-api:
	cd server/api && uv pip install -e . --quiet && \
		DATABASE_URL=postgres://postgres@localhost:5432/shenas_net \
		uv run uvicorn shenas_web_api.main:app --reload --port 8000

# Create/update K8s secret for web-api (production)
k8s-secrets-web-api:
	@DB_IP=$$(cd server/deploy/tofu && tofu output -raw database_ip 2>/dev/null); \
	DB_PASS=$$(grep db_password server/deploy/tofu/terraform.tfvars 2>/dev/null | sed 's/.*= *"//;s/".*//'); \
	DBURL="postgres://shenas:$$DB_PASS@$$DB_IP:5432/shenas_net"; \
	read -p "GOOGLE_CLIENT_ID: " GID; \
	read -p "GOOGLE_CLIENT_SECRET: " GSEC; \
	echo "DATABASE_URL=$$DBURL"; \
	kubectl create secret generic web-api-secrets \
		--namespace shenas \
		--from-literal=SESSION_SECRET=$$(openssl rand -hex 32) \
		--from-literal=BASE_URL=https://shenas.net \
		--from-literal=FRONTEND_URL=https://shenas.net \
		--from-literal=DATABASE_URL=$$DBURL \
		--from-literal=GOOGLE_CLIENT_ID=$$GID \
		--from-literal=GOOGLE_CLIENT_SECRET=$$GSEC \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "Secret web-api-secrets created/updated in namespace shenas"

flush-db:
	rm -f data/shenas.duckdb data/shenas.duckdb.wal
	rm -rf data/users/
	@echo "Flushed registry DB and all user DBs."

clean:
	moon run :clean
	rm -rf .moon/cache/ packages/ .ruff_cache/ .pytest_cache/

setup-android:
	@echo "Setting up Android development environment..."
	@# Command line tools
	@if [ ! -d "$(ANDROID_SDK_ROOT)/cmdline-tools/latest" ]; then \
		mkdir -p $(ANDROID_SDK_ROOT)/cmdline-tools; \
		curl -sL -o /tmp/cmdline-tools.zip \
			https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip; \
		unzip -qo /tmp/cmdline-tools.zip -d $(ANDROID_SDK_ROOT)/cmdline-tools; \
		mv $(ANDROID_SDK_ROOT)/cmdline-tools/cmdline-tools $(ANDROID_SDK_ROOT)/cmdline-tools/latest; \
		rm /tmp/cmdline-tools.zip; \
		echo "Installed command line tools"; \
	else \
		echo "Command line tools already installed"; \
	fi
	@# Accept licenses
	@yes | $(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/sdkmanager --licenses --sdk_root=$(ANDROID_SDK_ROOT) > /dev/null 2>&1 || true
	@# Platform tools + SDK
	@$(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/sdkmanager \
		"platform-tools" "platforms;android-35" --sdk_root=$(ANDROID_SDK_ROOT) | tail -1
	@# NDK (download directly -- sdkmanager can silently fail)
	@if [ ! -d "$(ANDROID_SDK_ROOT)/ndk/$(NDK_VERSION)" ]; then \
		echo "Downloading Android NDK..."; \
		curl -sL -o /tmp/$(NDK_ZIP) \
			https://dl.google.com/android/repository/$(NDK_ZIP); \
		mkdir -p $(ANDROID_SDK_ROOT)/ndk; \
		unzip -qo /tmp/$(NDK_ZIP) -d $(ANDROID_SDK_ROOT)/ndk; \
		mv $(ANDROID_SDK_ROOT)/ndk/android-ndk-r27d $(ANDROID_SDK_ROOT)/ndk/$(NDK_VERSION); \
		rm /tmp/$(NDK_ZIP); \
		echo "Installed NDK $(NDK_VERSION)"; \
	else \
		echo "NDK $(NDK_VERSION) already installed"; \
	fi
	@# Rust Android targets (skip if rustup not available)
	@if command -v rustup > /dev/null 2>&1; then \
		rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android; \
	else \
		echo "rustup not found -- install Android Rust targets manually if needed"; \
	fi
	@# Emulator + system image
	@$(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/sdkmanager \
		"emulator" "system-images;android-35;google_apis;x86_64" --sdk_root=$(ANDROID_SDK_ROOT) | tail -1
	@if ! $(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/avdmanager list avd 2>/dev/null | grep -q "shenas"; then \
		$(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/avdmanager create avd \
			-n shenas -k "system-images;android-35;google_apis;x86_64" --force --device "pixel_6"; \
		echo "Created AVD: shenas"; \
	else \
		echo "AVD 'shenas' already exists"; \
	fi
	@# Mobile npm deps
	@cd app/mobile && npm install
	@echo ""
	@echo "Android environment ready. Add to your shell profile:"
	@echo "  export ANDROID_HOME=$(ANDROID_SDK_ROOT)"
	@echo "  export NDK_HOME=$(ANDROID_SDK_ROOT)/ndk/$(NDK_VERSION)"
	@echo ""
	@echo "Then run:"
	@echo "  make android-emulator"
	@echo "  cd app/mobile && npx tauri android init"
	@echo "  npx tauri android dev"

android-emulator:
	@ANDROID_AVD_HOME=$(HOME)/.config/.android/avd \
	$(ANDROID_SDK_ROOT)/emulator/emulator -avd shenas >/tmp/emu.log 2>&1 &
	@if command -v hyprctl >/dev/null; then \
		for i in $$(seq 1 30); do sleep 1; \
			if hyprctl clients | grep -q "Android Emulator - shenas"; then \
				hyprctl dispatch focuswindow "title:Android Emulator - shenas:5554" >/dev/null; \
				hyprctl dispatch togglefloating active >/dev/null; \
				hyprctl dispatch resizeactive exact 1100 1900 >/dev/null; \
				break; \
			fi; \
		done; \
	fi

android-dev:
	 @$(ANDROID_SDK_ROOT)/platform-tools/adb shell pm clear com.shenas.mobile

	@cd app/mobile && if [ ! -d src-tauri/gen/android ]; then npx tauri android init; fi
	moon run mobile:build-frontend
	@# Reverse-forward the host's shenas API into the device so vite's /api proxy
	@# (which targets 127.0.0.1:7280 on the host) is reachable. Tauri itself
	@# already auto-reverses 5173 (the devUrl). The mobile Rust API server
	@# silently steps aside when this port is taken (see src-tauri/src/lib.rs).
	@$(ANDROID_SDK_ROOT)/platform-tools/adb reverse tcp:7280 tcp:7280 2>/dev/null || true
	cd app/mobile && npx tauri android dev

# Force a clean rebuild of mobile frontend + Rust
android-dev-clean:
	rm -rf app/mobile/mobile-dist
	cd app/mobile/src-tauri && cargo clean
	$(MAKE) android-dev

# Tag a desktop release (version auto-computed from conventional commits)
release-desktop:
	@output=$$(bash scripts/bump-tag.sh desktop app/ app/desktop/ build/ scheduler/); \
	if [ -z "$$output" ]; then echo "No desktop changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	echo ""; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- app/ app/desktop/ build/ scheduler/ | head -20; \
	echo ""; echo ""; \
	read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
		echo "Tagged and pushed $$TAG"; \
	else \
		echo "Aborted"; \
	fi

# Tag a server release (version auto-computed from conventional commits)
release-fl-server:
	@output=$$(bash scripts/bump-tag.sh fl-server server/fl/); \
	if [ -z "$$output" ]; then echo "No fl-server changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	echo ""; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- server/fl/ | head -20; \
	echo ""; echo ""; \
	read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
		echo "Tagged and pushed $$TAG"; \
	else \
		echo "Aborted"; \
	fi

release-shenas-net:
	@output=$$(bash scripts/bump-tag.sh shenas-net server/shenas.net/); \
	if [ -z "$$output" ]; then echo "No shenas-net changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	echo ""; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- server/shenas.net/ | head -20; \
	echo ""; echo ""; \
	read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
		echo "Tagged and pushed $$TAG"; \
	else \
		echo "Aborted"; \
	fi

release-web-api:
	@output=$$(bash scripts/bump-tag.sh web-api server/api/); \
	if [ -z "$$output" ]; then echo "No web-api changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	echo ""; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- server/api/ | head -20; \
	echo ""; echo ""; \
	read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
		echo "Tagged and pushed $$TAG"; \
	else \
		echo "Aborted"; \
	fi

# Upload built packages to GCS for the repo server
publish-packages:
	@if [ ! -d packages ] || [ -z "$$(ls packages/*.whl 2>/dev/null)" ]; then \
		echo "No packages found in packages/. Build with: moon run :build"; exit 1; \
	fi
	gsutil -m cp packages/*.whl packages/*.sig gs://shenas-packages/
	@echo "Uploaded $$(ls packages/*.whl | wc -l) packages to gs://shenas-packages/"

# Infrastructure (OpenTofu)
infra-init:
	cd server/deploy/tofu && tofu init

# One-time: import resources created before OpenTofu (skips already-imported)
infra-import:
	@cd server/deploy/tofu; \
	_import() { echo "Importing $$1..."; tofu import "$$1" "$$2" 2>&1 | grep -v "already managed" || true; }; \
	_import google_container_cluster.shenas projects/shenas-491609/locations/us-east4/clusters/shenas; \
	_import google_compute_global_address.ingress_ip projects/shenas-491609/global/addresses/shenas-ip; \
	_import google_artifact_registry_repository.shenas projects/shenas-491609/locations/us-east4/repositories/shenas; \
	_import google_service_account.github_deploy projects/shenas-491609/serviceAccounts/github-deploy@shenas-491609.iam.gserviceaccount.com; \
	_import google_iam_workload_identity_pool.github projects/shenas-491609/locations/global/workloadIdentityPools/github-pool; \
	_import google_iam_workload_identity_pool_provider.github projects/shenas-491609/locations/global/workloadIdentityPools/github-pool/providers/github-provider; \
	echo "Import complete. Run: make infra-plan"

infra-plan:
	cd server/deploy/tofu && tofu plan

infra-apply:
	cd server/deploy/tofu && tofu apply

infra-output:
	cd server/deploy/tofu && tofu output

infra-destroy:
	cd server/deploy/tofu && tofu destroy

# Discord (OpenTofu)
discord-init:
	cd server/deploy/tofu-discord && tofu init

discord-plan:
	cd server/deploy/tofu-discord && tofu plan

discord-apply:
	cd server/deploy/tofu-discord && tofu apply

discord-output:
	cd server/deploy/tofu-discord && tofu output

discord-destroy:
	cd server/deploy/tofu-discord && tofu destroy

# GitHub (OpenTofu)
github-init:
	cd server/deploy/tofu-github && tofu init

github-plan:
	cd server/deploy/tofu-github && tofu plan

github-apply:
	cd server/deploy/tofu-github && tofu apply

github-output:
	cd server/deploy/tofu-github && tofu output

github-destroy:
	cd server/deploy/tofu-github && tofu destroy

# Copybara (OSS release sync)
oss-init:
	@echo "Generating deploy key for OSS sync..."
	@rm -f /tmp/oss_deploy_key /tmp/oss_deploy_key.pub
	@ssh-keygen -t ed25519 -f /tmp/oss_deploy_key -N "" -C "copybara-oss-sync" -q
	@echo "Adding deploy key to shenas-org/shenas (write access)..."
	@gh repo deploy-key add /tmp/oss_deploy_key.pub --repo shenas-org/shenas --title "Copybara OSS Sync" --allow-write
	@echo "Adding private key as secret OSS_DEPLOY_KEY on shenas-net/shenas..."
	@gh secret set OSS_DEPLOY_KEY --repo shenas-net/shenas < /tmp/oss_deploy_key
	@rm -f /tmp/oss_deploy_key /tmp/oss_deploy_key.pub
	@echo "Triggering OSS Release workflow..."
	@gh workflow run "OSS Release" --repo shenas-net/shenas
	@echo "Done. Monitor at: https://github.com/shenas-net/shenas/actions/workflows/oss-release.yml"

oss-sync:
	@gh workflow run "OSS Release" --repo shenas-net/shenas
	@echo "OSS Release triggered. Monitor at: https://github.com/shenas-net/shenas/actions/workflows/oss-release.yml"

# Set GitHub repo variables from tofu outputs (requires gh CLI)
infra-gh-vars:
	@WIF=$$(cd server/deploy/tofu && tofu output -raw wif_provider) && \
	SA=$$(cd server/deploy/tofu && tofu output -raw service_account) && \
	gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$$WIF" && \
	gh variable set GCP_SERVICE_ACCOUNT --body "$$SA" && \
	echo "GitHub variables set:" && \
	echo "  GCP_WORKLOAD_IDENTITY_PROVIDER: $$WIF" && \
	echo "  GCP_SERVICE_ACCOUNT: $$SA"

# Kubernetes
k8s-apply:
	kubectl apply -f server/deploy/k8s/namespace.yaml
	@for f in server/deploy/k8s/*.yaml; do \
		sed "s|REGION|us-east4|g; s|PROJECT_ID|shenas-491609|g" "$$f" | kubectl apply -f -; \
	done

k8s-status:
	@kubectl get deployments,services,ingress,managedcertificate -n shenas

k8s-logs:
	@echo "=== fl-server ===" && kubectl logs -n shenas -l app=fl-server --tail=20 2>/dev/null || true
	@echo "=== shenas-net ===" && kubectl logs -n shenas -l app=shenas-net --tail=20 2>/dev/null || true
