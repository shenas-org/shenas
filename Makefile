.PHONY: install repository setup-hooks coverage clean release-desktop setup-android android-emulator

# Install CLI tools globally (~/.local/bin/)
install:
	uv tool install --editable app/ --force
	uv tool install --editable repository/ --force
	@echo "Installed shenas, shenasctl, shenasrepoctl to ~/.local/bin/"
	@echo "Run 'shenasctl --install-completion' for tab completion"

repository:
	uv run python -m repository.main $(CURDIR)/packages

# Install git pre-commit hook
setup-hooks:
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

coverage:
	uv run --no-sync pytest --cov=repository --cov=app \
		--cov=shenas_pipes --cov=shenas_schemas \
		--cov-report=term-missing --cov-report=html:htmlcov --cov-report=json:coverage.json

clean:
	moon run :clean
	rm -rf .moon/cache/ packages/ .ruff_cache/ .pytest_cache/

# Set up Android SDK, NDK, and Rust targets for mobile development
ANDROID_SDK_ROOT = $(HOME)/Android/Sdk
NDK_VERSION = 27.2.12479018
NDK_ZIP = android-ndk-r27d-linux.zip

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
