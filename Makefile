.PHONY: install repository setup-hooks coverage

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
