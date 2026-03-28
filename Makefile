PACKAGES_DIR := $(CURDIR)/packages
SIGN = uv run --no-sync shenasrepoctl sign

.PHONY: repository build build-pipes build-schemas build-components dev-install dev-uninstall setup-hooks coverage

repository:
	uv run python -m repository.main $(PACKAGES_DIR)

build: build-schemas build-pipes build-components

# Build pipe wheels into packages/ and sign them
# Usage: make build-pipes              (all)
#        make build-pipes PIPE=garmin  (one)
build-pipes:
	@for pipe in $(or $(PIPE),$(patsubst pipes/%/pyproject.toml,%,$(wildcard pipes/*/pyproject.toml))); do \
		echo "Building pipe: $$pipe"; \
		cd pipes/$$pipe && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
		for whl in $(PACKAGES_DIR)/shenas_pipe_$$(echo $$pipe | tr '-' '_')-*.whl; do \
			if [ ! -f "$$whl.sig" ]; then $(SIGN) "$$whl"; fi; \
		done; \
	done

# Build schema wheels into packages/ and sign them
# Usage: make build-schemas                        (all)
#        make build-schemas SCHEMA=fitness         (one)
build-schemas:
	@for schema in $(or $(SCHEMA),$(patsubst schemas/%/pyproject.build.toml,%,$(wildcard schemas/*/pyproject.build.toml)) $(patsubst schemas/%/pyproject.toml,%,$(filter-out schemas/core/pyproject.toml,$(wildcard schemas/*/pyproject.toml)))); do \
		echo "Building schema: $$schema"; \
		if [ -f schemas/$$schema/pyproject.build.toml ] && [ ! -f schemas/$$schema/pyproject.toml ]; then \
			cp schemas/$$schema/pyproject.build.toml schemas/$$schema/pyproject.toml; \
			cd schemas/$$schema && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
			rm schemas/$$schema/pyproject.toml; \
		else \
			cd schemas/$$schema && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
		fi; \
		pkg=$$(echo $$schema | tr '-' '_'); \
		for whl in $(PACKAGES_DIR)/shenas_schema_$${pkg}-*.whl; do \
			if [ ! -f "$$whl.sig" ]; then $(SIGN) "$$whl"; fi; \
		done; \
	done

# Build component wheels into packages/ and sign them
# Usage: make build-components                          (all)
#        make build-components COMPONENT=data-table     (one)
build-components:
	@for comp in $(or $(COMPONENT),$(patsubst components/%/pyproject.build.toml,%,$(wildcard components/*/pyproject.build.toml))); do \
		pkg=$$(echo $$comp | tr '-' '_'); \
		echo "Building component: $$comp"; \
		cd components/$$comp && npm run build && cd $(CURDIR); \
		cp components/$$comp/$$comp.html components/$$comp/shenas_components/$$pkg/static/$$comp.html; \
		cp components/$$comp/pyproject.build.toml components/$$comp/pyproject.toml; \
		cd components/$$comp && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
		rm components/$$comp/pyproject.toml; \
		for whl in $(PACKAGES_DIR)/shenas_component_$${pkg}-*.whl; do \
			if [ ! -f "$$whl.sig" ]; then $(SIGN) "$$whl"; fi; \
		done; \
	done

# Editable install of all local packages (source changes take effect immediately)
dev-install:
	@echo "Installing schemas..."
	@for schema in $(patsubst schemas/%/pyproject.build.toml,%,$(wildcard schemas/*/pyproject.build.toml)); do \
		if [ ! -f schemas/$$schema/pyproject.toml ]; then \
			cp schemas/$$schema/pyproject.build.toml schemas/$$schema/pyproject.toml; \
			uv pip install -e schemas/$$schema; \
			rm schemas/$$schema/pyproject.toml; \
		else \
			uv pip install -e schemas/$$schema; \
		fi; \
	done
	@echo "Installing pipes..."
	@for pipe in $(patsubst pipes/%/pyproject.toml,%,$(wildcard pipes/*/pyproject.toml)); do \
		uv pip install -e pipes/$$pipe; \
	done
	@echo "Installing components..."
	@for comp in $(patsubst components/%/pyproject.build.toml,%,$(wildcard components/*/pyproject.build.toml)); do \
		if [ ! -f components/$$comp/pyproject.toml ]; then \
			cp components/$$comp/pyproject.build.toml components/$$comp/pyproject.toml; \
			uv pip install -e components/$$comp; \
			rm components/$$comp/pyproject.toml; \
		else \
			uv pip install -e components/$$comp; \
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

# Install git pre-commit hook
setup-hooks:
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

coverage:
	uv run --no-sync pytest --cov=cli --cov=repository --cov=app \
		--cov=shenas_pipes --cov=shenas_schemas \
		--cov-report=term-missing --cov-report=html:htmlcov --cov-report=json:coverage.json
