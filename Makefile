.PHONY: install repo-server setup-hooks coverage clean logos release-desktop release-repo-server release-fl-server release-shenas-net setup-android android-emulator android-dev infra-init infra-import infra-plan infra-apply infra-output infra-destroy infra-gh-vars k8s-apply k8s-status k8s-logs

# Set up Android SDK, NDK, and Rust targets for mobile development
ANDROID_SDK_ROOT = $(HOME)/Android/Sdk
NDK_VERSION = 27.2.12479018
NDK_ZIP = android-ndk-r27d-linux.zip

install:
	uv tool install --editable app/ --force
	uv tool install --editable server/repository/ --force
	@echo "Installed shenas, shenasctl, shenasrepoctl to ~/.local/bin/"
	@echo "Run 'shenasctl --install-completion' for tab completion"

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
	rsvg-convert -w 192 -h 192 $$SVG -o app/static/images/shenas.png; \
	rsvg-convert -w 192 -h 192 $$SVG -o app/static/images/shenas-192.png; \
	for s in 32 128 256 512; do \
		rsvg-convert -w $$s -h $$s $$SVG -o app/desktop/src-tauri/icons/$${s}x$${s}.png; \
		rsvg-convert -w $$s -h $$s $$SVG -o app/mobile/src-tauri/icons/$${s}x$${s}.png; \
	done; \
	rsvg-convert -w 512 -h 512 $$SVG -o app/desktop/src-tauri/icons/icon.png; \
	rsvg-convert -w 512 -h 512 $$SVG -o app/mobile/src-tauri/icons/icon.png; \
	rsvg-convert -w 512 -h 512 $$SVG -o server/shenas.net/public/logo.png; \
	rsvg-convert -w 192 -h 192 $$SVG -o server/shenas.net/public/logo-192.png; \
	cp $$SVG server/shenas.net/public/favicon.svg; \
	echo "Regenerated all logos from $$SVG"

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
	$(ANDROID_SDK_ROOT)/emulator/emulator -avd shenas &

android-dev:
	cd app/mobile && \
	if [ ! -d src-tauri/gen/android ]; then npx tauri android init; fi && \
	bash build-ui.sh && cd src-tauri && cargo clean && cd .. && npx tauri android dev

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
# Usage: make release-repo-server / release-fl-server / release-shenas-net
release-repo-server:
	@output=$$(bash scripts/bump-tag.sh repo-server server/repository/); \
	if [ -z "$$output" ]; then echo "No repo-server changes to release."; exit 0; fi; \
	eval "$$output"; \
	echo "$$TAG ($$BUMP bump from $$PREV, $$COMMIT_COUNT commits)"; \
	echo ""; \
	git log "$$PREV"..HEAD --pretty=format:"  %s" -- server/repository/ | head -20; \
	echo ""; echo ""; \
	read -p "Create tag $$TAG and push? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		git tag "$$TAG" && git push origin "$$TAG"; \
		echo "Tagged and pushed $$TAG"; \
	else \
		echo "Aborted"; \
	fi

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
	@echo "=== repo-server ===" && kubectl logs -n shenas -l app=repo-server --tail=20 2>/dev/null || true
	@echo "=== fl-server ===" && kubectl logs -n shenas -l app=fl-server --tail=20 2>/dev/null || true
	@echo "=== shenas-net ===" && kubectl logs -n shenas -l app=shenas-net --tail=20 2>/dev/null || true
