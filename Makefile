PACKAGES_DIR := $(CURDIR)/packages
SIGN = uv run shenas registry sign
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

# Build component wheels into packages/ and sign them
# Usage: make build-components                    (all)
#        make build-components COMPONENT=dashboard (one)
build-components:
	@for comp in $(or $(COMPONENT),$(patsubst frontend_components/%/pyproject.build.toml,%,$(wildcard frontend_components/*/pyproject.build.toml))); do \
		version=$$($(BUMP) frontend_components/$$comp/VERSION); \
		echo "Building component: $$comp v$$version"; \
		cd frontend_components/$$comp && node -e "let p=JSON.parse(require('fs').readFileSync('package.json')); p.version='$$version'; require('fs').writeFileSync('package.json', JSON.stringify(p,null,2)+'\n')" && cd $(CURDIR); \
		cd frontend_components/$$comp && npm run build && cd $(CURDIR); \
		cp frontend_components/$$comp/$$comp.html frontend_components/$$comp/shenas_components/$$comp/static/$$comp.html; \
		cp frontend_components/$$comp/pyproject.build.toml frontend_components/$$comp/pyproject.toml; \
		cd frontend_components/$$comp && uv build --out-dir $(PACKAGES_DIR) && cd $(CURDIR); \
		rm frontend_components/$$comp/pyproject.toml; \
		$(SIGN) $(PACKAGES_DIR)/shenas_component_$${comp}-$$version-*.whl; \
	done

# Download a pipe wheel + all its transitive deps into packages/
# Usage: make vendor PIPE=garmin
vendor:
	@test -n "$(PIPE)" || (echo "Usage: make vendor PIPE=<name>" && exit 1)
	uv run pip download shenas-pipe-$(PIPE) --dest $(PACKAGES_DIR) --find-links $(PACKAGES_DIR)
	@echo "Vendored shenas-pipe-$(PIPE) and dependencies into $(PACKAGES_DIR)"

# Sign all unsigned wheels in packages/
sign-all:
	@for whl in $(PACKAGES_DIR)/*.whl; do \
		if [ ! -f "$$whl.sig" ]; then \
			$(SIGN) "$$whl"; \
		fi; \
	done
