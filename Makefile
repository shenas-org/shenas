PACKAGES_DIR := $(CURDIR)/packages
SIGN = uv run --no-sync shenas registry sign
BUMP = python scripts/bump-version.py

repository_server:
	uv run python -m repository_server.main $(PACKAGES_DIR)

# Build pipe wheels into packages/ and sign them
# Usage: make build-pipes              (all)
#        make build-pipes PIPE=garmin  (one)
build-pipes:
	@for pipe in $(or $(PIPE),$(patsubst pipes/%/pyproject.toml,%,$(wildcard pipes/*/pyproject.toml))); do \
		version=$$($(BUMP) pipes/$$pipe/VERSION); \
		echo "Building pipe: $$pipe v$$version"; \
		cd pipes/$$pipe && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
		$(SIGN) $(PACKAGES_DIR)/shenas_pipe_$${pipe}-$$version-*.whl; \
	done

# Build schema wheels into packages/ and sign them
# Usage: make build-schemas                             (all)
#        make build-schemas SCHEMA=fitness_tracker      (one)
build-schemas:
	@for schema in $(or $(SCHEMA),$(patsubst schemas/%/VERSION,%,$(wildcard schemas/*/VERSION))); do \
		version=$$($(BUMP) schemas/$$schema/VERSION); \
		echo "Building schema: $$schema v$$version"; \
		if [ -f schemas/$$schema/pyproject.build.toml ] && [ ! -f schemas/$$schema/pyproject.toml ]; then \
			cp schemas/$$schema/pyproject.build.toml schemas/$$schema/pyproject.toml; \
			cd schemas/$$schema && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
			rm schemas/$$schema/pyproject.toml; \
		else \
			cd schemas/$$schema && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
		fi; \
		pkg=$$(echo $$schema | tr '-' '_'); \
		$(SIGN) $(PACKAGES_DIR)/shenas_schema_$${pkg}-$$version-*.whl; \
	done

# Build component wheels into packages/ and sign them
# Usage: make build-components                    (all)
#        make build-components COMPONENT=dashboard (one)
build-components:
	@for comp in $(or $(COMPONENT),$(patsubst frontend_components/%/pyproject.build.toml,%,$(wildcard frontend_components/*/pyproject.build.toml))); do \
		pkg=$$(echo $$comp | tr '-' '_'); \
		version=$$($(BUMP) frontend_components/$$comp/VERSION); \
		echo "Building component: $$comp v$$version"; \
		cd frontend_components/$$comp && node -e "let p=JSON.parse(require('fs').readFileSync('package.json')); p.version='$$version'; require('fs').writeFileSync('package.json', JSON.stringify(p,null,2)+'\n')" && cd $(CURDIR); \
		cd frontend_components/$$comp && npm run build && cd $(CURDIR); \
		cp frontend_components/$$comp/$$comp.html frontend_components/$$comp/shenas_components/$$pkg/static/$$comp.html; \
		cp frontend_components/$$comp/pyproject.build.toml frontend_components/$$comp/pyproject.toml; \
		cd frontend_components/$$comp && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
		rm frontend_components/$$comp/pyproject.toml; \
		$(SIGN) $(PACKAGES_DIR)/shenas_component_$${pkg}-$$version-*.whl; \
	done

# Download a pipe wheel + all its transitive deps into packages/
# Usage: make vendor PIPE=garmin
vendor:
	@test -n "$(PIPE)" || (echo "Usage: make vendor PIPE=<name>" && exit 1)
	uv run pip download shenas-pipe-$(PIPE) --dest $(PACKAGES_DIR) --find-links $(PACKAGES_DIR)
	@echo "Vendored shenas-pipe-$(PIPE) and dependencies into $(PACKAGES_DIR)"

# Editable install of all local packages (source changes take effect immediately)
dev-install:
	@echo "Installing schemas..."
	@for schema in $(patsubst schemas/%/VERSION,%,$(wildcard schemas/*/VERSION)); do \
		if [ -f schemas/$$schema/pyproject.build.toml ] && [ ! -f schemas/$$schema/pyproject.toml ]; then \
			cp schemas/$$schema/pyproject.build.toml schemas/$$schema/pyproject.toml; \
			uv pip install -e schemas/$$schema; \
			rm schemas/$$schema/pyproject.toml; \
		else \
			uv pip install -e schemas/$$schema; \
		fi; \
	done
	@echo "Installing pipes..."
	@for pipe in $(patsubst pipes/%/VERSION,%,$(wildcard pipes/*/VERSION)); do \
		uv pip install -e pipes/$$pipe; \
	done
	@echo "Installing components..."
	@for comp in $(patsubst frontend_components/%/VERSION,%,$(wildcard frontend_components/*/VERSION)); do \
		if [ -f frontend_components/$$comp/pyproject.build.toml ] && [ ! -f frontend_components/$$comp/pyproject.toml ]; then \
			cp frontend_components/$$comp/pyproject.build.toml frontend_components/$$comp/pyproject.toml; \
			uv pip install -e frontend_components/$$comp; \
			rm frontend_components/$$comp/pyproject.toml; \
		else \
			uv pip install -e frontend_components/$$comp; \
		fi; \
	done
	@echo "Dev install complete."

# Uninstall all dev-installed shenas packages
dev-uninstall:
	@pkgs=$$(uv pip list --format json 2>/dev/null | python -c "import sys,json; print(' '.join(p['name'] for p in json.load(sys.stdin) if p['name'].startswith('shenas-')))" 2>/dev/null); \
	if [ -z "$$pkgs" ]; then \
		echo "No shenas packages installed."; \
	else \
		uv pip uninstall $$pkgs; \
	fi

# Sign all unsigned wheels in packages/
sign-all:
	@for whl in $(PACKAGES_DIR)/*.whl; do \
		if [ ! -f "$$whl.sig" ]; then \
			$(SIGN) "$$whl"; \
		fi; \
	done
