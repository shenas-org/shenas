.PHONY: android-clean android-dev android-emulator android-setup api-dev app-clean app-dev app-install ci-runner-build coverage db-flush desktop-build desktop-dev desktop-release discord-apply discord-destroy discord-init discord-output discord-plan github-apply github-destroy github-init github-output github-plan headless-build headless-deploy hooks-setup lint infra-apply infra-destroy infra-gh-vars infra-import infra-init infra-output infra-plan k8s-apply k8s-logs k8s-secrets-set k8s-status logos-generate oss-init oss-sync packages-publish plugins-build postgres-dev pyinstaller shenas-net-release shenas-org-release test shenas-net-api-release shenas-net-dev

ANDROID_SDK_ROOT = $(HOME)/Android/Sdk
NDK_VERSION = 27.2.12479018
NDK_ZIP = android-ndk-r27d-linux.zip

# ---------------------------------------------------------------------------
# Android
# ---------------------------------------------------------------------------

android-clean:
	rm -rf app/mobile/mobile-dist
	cd app/mobile/src-tauri && cargo clean
	$(MAKE) android-dev

android-dev:
	@$(ANDROID_SDK_ROOT)/platform-tools/adb shell pm clear com.shenas.mobile
	@cd app/mobile && if [ ! -d src-tauri/gen/android ]; then npx tauri android init; fi
	moon run mobile:build-frontend
	@$(ANDROID_SDK_ROOT)/platform-tools/adb reverse tcp:7280 tcp:7280 2>/dev/null || true
	cd app/mobile && npx tauri android dev

android-emulator:
	@ANDROID_AVD_HOME=$(HOME)/.config/.android/avd \
	$(ANDROID_SDK_ROOT)/emulator/emulator -avd shenas >/tmp/emu.log 2>&1 &

android-setup:
	@echo "Setting up Android development environment..."
	@if [ ! -d "$(ANDROID_SDK_ROOT)/cmdline-tools/latest" ]; then \
		mkdir -p $(ANDROID_SDK_ROOT)/cmdline-tools; \
		curl -sL -o /tmp/cmdline-tools.zip \
			https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip; \
		unzip -qo /tmp/cmdline-tools.zip -d $(ANDROID_SDK_ROOT)/cmdline-tools; \
		mv $(ANDROID_SDK_ROOT)/cmdline-tools/cmdline-tools $(ANDROID_SDK_ROOT)/cmdline-tools/latest; \
		rm /tmp/cmdline-tools.zip; \
	fi
	@yes | $(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/sdkmanager --licenses --sdk_root=$(ANDROID_SDK_ROOT) > /dev/null 2>&1 || true
	@$(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/sdkmanager \
		"platform-tools" "platforms;android-35" --sdk_root=$(ANDROID_SDK_ROOT) | tail -1
	@if [ ! -d "$(ANDROID_SDK_ROOT)/ndk/$(NDK_VERSION)" ]; then \
		curl -sL -o /tmp/$(NDK_ZIP) https://dl.google.com/android/repository/$(NDK_ZIP); \
		mkdir -p $(ANDROID_SDK_ROOT)/ndk; \
		unzip -qo /tmp/$(NDK_ZIP) -d $(ANDROID_SDK_ROOT)/ndk; \
		mv $(ANDROID_SDK_ROOT)/ndk/android-ndk-r27d $(ANDROID_SDK_ROOT)/ndk/$(NDK_VERSION); \
		rm /tmp/$(NDK_ZIP); \
	fi
	@if command -v rustup > /dev/null 2>&1; then \
		rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android; \
	fi
	@$(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/sdkmanager \
		"emulator" "system-images;android-35;google_apis;x86_64" --sdk_root=$(ANDROID_SDK_ROOT) | tail -1
	@if ! $(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/avdmanager list avd 2>/dev/null | grep -q "shenas"; then \
		$(ANDROID_SDK_ROOT)/cmdline-tools/latest/bin/avdmanager create avd \
			-n shenas -k "system-images;android-35;google_apis;x86_64" --force --device "pixel_6"; \
	fi
	@cd app/mobile && npm install

# ---------------------------------------------------------------------------
# API / App / DB
# ---------------------------------------------------------------------------

api-dev:
	cd server/api && uv pip install -e . --quiet && \
		DATABASE_URL=postgres://postgres@localhost:5432/shenas_net \
		LOCAL_PACKAGES_DIR=$(CURDIR)/packages \
		uv run uvicorn shenas_net_api.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log

plugins-build:
	moon run :build --query "tag=plugin"

app-clean:
	moon run :clean
	rm -rf dist/ build/_pyinstaller_work/ htmlcov/ .coverage coverage.json packages/ .ruff_cache/ .pytest_cache/

app-dev:
	@fuser -k 7280/tcp 5173/tcp 2>/dev/null; sleep 0.3; \
	uv sync --group fl --quiet; \
	(cd app/vendor && npm install --silent && npm run build --silent); \
	moon run frontend*:build dashboard*:build; \
	trap 'kill 0' EXIT; \
	uv run shenas --reload --no-tls & \
	while ! curl -s http://127.0.0.1:7280/api/health > /dev/null 2>&1; do sleep 0.2; done; \
	cd plugins/frontends/default && npx vite & \
	wait

ci-runner-build:
	gcloud builds submit --config server/deploy/docker/cloudbuild.yaml \
		--substitutions=_TAG="us-east4-docker.pkg.dev/shenas-491609/shenas/ci-runner:latest",_TAG_LATEST="us-east4-docker.pkg.dev/shenas-491609/shenas/ci-runner:latest",_VERSION="latest",_DOCKERFILE="server/deploy/docker/Dockerfile.ci-runner" .

app-install:
	uv tool install --editable app/ --force
	uv tool install --editable shenasctl/ --force --with-editable app/
	@echo "Installed shenas and shenasctl to ~/.local/bin/"
	@echo "Run 'shenasctl --install-completion' for tab completion"

db-flush:
	rm -f data/shenas.duckdb data/shenas.duckdb.wal
	rm -rf data/users/
	@echo "Flushed registry DB and all user DBs."

# ---------------------------------------------------------------------------
# Desktop
# ---------------------------------------------------------------------------

desktop-build:
	uv run python build/pyinstaller_build.py --onefile
	cp dist/pyinstaller/shenas-x86_64-unknown-linux-gnu app/desktop/src-tauri/binaries/
	cp dist/pyinstaller/shenas-scheduler-x86_64-unknown-linux-gnu app/desktop/src-tauri/binaries/
	cp dist/pyinstaller/shenasctl-x86_64-unknown-linux-gnu app/desktop/src-tauri/binaries/
	cd app/desktop/src-tauri && cargo run --release

desktop-dev:
	cd app/desktop && npx tauri dev

desktop-release:
	@output=$$(bash scripts/bump-tag.sh desktop app/ app/desktop/ build/ scheduler/); \
	if [ -z "$$output" ]; then echo "No desktop changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- app/ app/desktop/ build/ scheduler/ | head -20; \
	echo ""; read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
	fi

# ---------------------------------------------------------------------------
# Discord (OpenTofu)
# ---------------------------------------------------------------------------

discord-apply:
	cd server/deploy/tofu-discord && tofu apply

discord-destroy:
	cd server/deploy/tofu-discord && tofu destroy

discord-init:
	cd server/deploy/tofu-discord && tofu init

discord-output:
	cd server/deploy/tofu-discord && tofu output

discord-plan:
	cd server/deploy/tofu-discord && tofu plan

# ---------------------------------------------------------------------------
# GitHub (OpenTofu)
# ---------------------------------------------------------------------------

github-apply:
	cd server/deploy/tofu-github && tofu apply

github-destroy:
	cd server/deploy/tofu-github && tofu destroy

github-init:
	cd server/deploy/tofu-github && tofu init

github-output:
	cd server/deploy/tofu-github && tofu output

github-plan:
	cd server/deploy/tofu-github && tofu plan

# ---------------------------------------------------------------------------
# Hooks / Tests
# ---------------------------------------------------------------------------

hooks-setup:
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

lint:
	moon run :python-lint :python-format-check :python-type-check :js-lint :js-format-check :js-type-check

test:
	moon run :python-test :js-test

coverage:
	uv run --no-sync pytest --cov=app \
		--cov=shenas_sources --cov=shenas_datasets \
		--cov-report=term-missing --cov-report=html:htmlcov --cov-report=json:coverage.json \
		--ignore=server/fl --ignore=server/api

pyinstaller:
	uv run python build/pyinstaller_build.py

# ---------------------------------------------------------------------------
# Infrastructure (OpenTofu - GCP)
# ---------------------------------------------------------------------------

infra-apply:
	cd server/deploy/tofu && tofu apply

infra-destroy:
	cd server/deploy/tofu && tofu destroy

infra-gh-vars:
	@WIF=$$(cd server/deploy/tofu && tofu output -raw wif_provider) && \
	SA=$$(cd server/deploy/tofu && tofu output -raw service_account) && \
	gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$$WIF" && \
	gh variable set GCP_SERVICE_ACCOUNT --body "$$SA"

infra-import:
	@cd server/deploy/tofu; \
	_import() { echo "Importing $$1..."; tofu import "$$1" "$$2" 2>&1 | grep -v "already managed" || true; }; \
	_import google_container_cluster.shenas projects/shenas-491609/locations/us-east4/clusters/shenas; \
	_import google_compute_global_address.ingress_ip projects/shenas-491609/global/addresses/shenas-ip; \
	_import google_artifact_registry_repository.shenas projects/shenas-491609/locations/us-east4/repositories/shenas; \
	_import google_service_account.github_deploy projects/shenas-491609/serviceAccounts/github-deploy@shenas-491609.iam.gserviceaccount.com; \
	_import google_iam_workload_identity_pool.github projects/shenas-491609/locations/global/workloadIdentityPools/github-pool; \
	_import google_iam_workload_identity_pool_provider.github projects/shenas-491609/locations/global/workloadIdentityPools/github-pool/providers/github-provider

infra-init:
	cd server/deploy/tofu && tofu init

infra-output:
	cd server/deploy/tofu && tofu output

infra-plan:
	cd server/deploy/tofu && tofu plan

# ---------------------------------------------------------------------------
# Kubernetes
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Headless worker (cloud deployment)
# ---------------------------------------------------------------------------

headless-build:
	docker build -f server/deploy/docker/Dockerfile.headless -t shenas-headless .

headless-deploy: headless-build
	@kubectl create namespace shenas-workers 2>/dev/null || true
	@if ! kubectl -n shenas-workers get secret headless-db-key >/dev/null 2>&1; then \
		echo "Creating DB encryption key..."; \
		kubectl -n shenas-workers create secret generic headless-db-key \
			--from-literal=key=$$(openssl rand -hex 32); \
	fi
	@if [ -f data/dev_credentials.json ]; then \
		echo "Uploading credentials..."; \
		kubectl -n shenas-workers create secret generic headless-credentials \
			--from-file=dev_credentials.json=data/dev_credentials.json \
			--dry-run=client -o yaml | kubectl apply -f -; \
	else \
		echo "Warning: data/dev_credentials.json not found. Export via Ctrl+P first."; \
	fi
	@TOKEN=$$(uv run python -c "\
		from app.database import shenas_db; db = shenas_db(); \
		r = db.cursor().__enter__().execute('SELECT remote_token FROM shenas_system.local_users WHERE id = 0').fetchone(); \
		print(r[0] if r and r[0] else '')" 2>/dev/null); \
	if [ -n "$$TOKEN" ]; then \
		echo "Uploading mesh token for user 0..."; \
		kubectl -n shenas-workers create secret generic headless-mesh-token \
			--from-literal=token=$$TOKEN \
			--dry-run=client -o yaml | kubectl apply -f -; \
	else \
		echo "Warning: no remote token for user 0. Sign in to shenas.net first."; \
	fi
	kubectl -n shenas-workers apply -f server/deploy/k8s/headless-worker.yaml

k8s-apply:
	kubectl apply -f server/deploy/k8s/namespace.yaml
	@for f in server/deploy/k8s/*.yaml; do \
		sed "s|REGION|us-east4|g; s|PROJECT_ID|shenas-491609|g" "$$f" | kubectl apply -f -; \
	done

k8s-logs:
	@echo "=== fl-server ===" && kubectl logs -n shenas -l app=fl-server --tail=20 2>/dev/null || true
	@echo "=== shenas-net ===" && kubectl logs -n shenas -l app=shenas-net --tail=20 2>/dev/null || true

k8s-secrets-set:
	@DB_IP=$$(cd server/deploy/tofu && tofu output -raw database_ip 2>/dev/null); \
	DB_PASS=$$(grep db_password server/deploy/tofu/terraform.tfvars 2>/dev/null | sed 's/.*= *"//;s/".*//'); \
	DBURL="postgres://shenas:$$DB_PASS@$$DB_IP:5432/shenas_net"; \
	read -p "GOOGLE_CLIENT_ID: " GID; \
	read -p "GOOGLE_CLIENT_SECRET: " GSEC; \
	kubectl create secret generic shenas-net-api-secrets \
		--namespace shenas \
		--from-literal=SESSION_SECRET=$$(openssl rand -hex 32) \
		--from-literal=BASE_URL=https://shenas.net \
		--from-literal=FRONTEND_URL=https://shenas.net \
		--from-literal=DATABASE_URL=$$DBURL \
		--from-literal=GOOGLE_CLIENT_ID=$$GID \
		--from-literal=GOOGLE_CLIENT_SECRET=$$GSEC \
		--dry-run=client -o yaml | kubectl apply -f -

k8s-status:
	@kubectl get deployments,services,ingress,managedcertificate -n shenas

# ---------------------------------------------------------------------------
# Logos
# ---------------------------------------------------------------------------

logos-generate:
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
	convert app/desktop/src-tauri/icons/256x256.png -define icon:auto-resize=256,128,64,48,32,16 app/desktop/src-tauri/icons/icon.ico; \
	rsvg-convert -w 512 -h 512 $$MARK -o app/mobile/src-tauri/icons/icon.png; \
	rsvg-convert -w 512 -h 512 $$SVG -o server/shenas.net/public/logo.png; \
	rsvg-convert -w 192 -h 192 $$SVG -o server/shenas.net/public/logo-192.png; \
	cp $$MARK server/shenas.net/public/favicon.svg

# ---------------------------------------------------------------------------
# OSS (Copybara)
# ---------------------------------------------------------------------------

oss-init:
	@echo "Generating deploy key for OSS sync..."
	@rm -f /tmp/oss_deploy_key /tmp/oss_deploy_key.pub
	@ssh-keygen -t ed25519 -f /tmp/oss_deploy_key -N "" -C "copybara-oss-sync" -q
	@echo "Adding deploy key to shenas-org/shenas (write access)..."
	@gh repo deploy-key add /tmp/oss_deploy_key.pub --repo shenas-org/shenas --title "Copybara OSS Sync" --allow-write
	@echo "Adding private key as secret OSS_DEPLOY_KEY on shenas-net/shenas..."
	@gh secret set OSS_DEPLOY_KEY --repo shenas-net/shenas < /tmp/oss_deploy_key
	@rm -f /tmp/oss_deploy_key /tmp/oss_deploy_key.pub

oss-sync:
	@gh workflow run "OSS Release" --repo shenas-net/shenas
	@echo "OSS Release triggered. Monitor at: https://github.com/shenas-net/shenas/actions/workflows/oss-release.yml"

# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------

packages-publish:
	@if [ ! -d packages ] || [ -z "$$(ls packages/*.whl 2>/dev/null)" ]; then \
		echo "No packages found in packages/. Build with: moon run :build"; exit 1; \
	fi
	gcloud storage cp packages/*.whl gs://shenas-packages/
	@if ls packages/*.sig >/dev/null 2>&1; then gcloud storage cp packages/*.sig gs://shenas-packages/; fi

# ---------------------------------------------------------------------------
# Postgres
# ---------------------------------------------------------------------------

postgres-dev:
	@createdb -U postgres shenas_net 2>/dev/null && echo "Created database shenas_net" || echo "Database shenas_net already exists"
	@echo "DATABASE_URL=postgres://postgres@localhost:5432/shenas_net"

# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------

shenas-net-release:
	@output=$$(bash scripts/bump-tag.sh shenas-net server/shenas.net/); \
	if [ -z "$$output" ]; then echo "No shenas-net changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- server/shenas.net/ | head -20; \
	echo ""; read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
	fi

shenas-org-release:
	@output=$$(bash scripts/bump-tag.sh shenas-org server/shenas.org/); \
	if [ -z "$$output" ]; then echo "No shenas-org changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- server/shenas.org/ | head -20; \
	echo ""; read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
	fi

shenas-net-api-release:
	@output=$$(bash scripts/bump-tag.sh shenas-net-api server/api/); \
	if [ -z "$$output" ]; then echo "No shenas-net-api changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- server/api/ | head -20; \
	echo ""; read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
	fi

# ---------------------------------------------------------------------------
# Website
# ---------------------------------------------------------------------------

shenas-net-dev:
	cd server/shenas.net && npm install --silent && npx astro dev --host 127.0.0.1
