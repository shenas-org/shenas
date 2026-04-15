.PHONY: app-clean app-dev app-install db-flush hooks-setup js-deps js-format-check js-lint js-test js-typecheck python-format-check python-lint python-test python-typecheck tests-coverage

app-clean:
	rm -rf .ruff_cache/ .pytest_cache/ dist/ packages/ htmlcov/ .coverage coverage/ coverage.json

app-dev:
	@fuser -k 7280/tcp 5173/tcp 2>/dev/null; sleep 0.3; \
	uv sync --quiet; \
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

app-install:
	uv tool install --editable app/ --force
	@echo "Installed shenas and shenasctl to ~/.local/bin/"
	@echo "Run 'shenasctl --install-completion' for tab completion"

db-flush:
	rm -f data/shenas.duckdb data/shenas.duckdb.wal
	rm -rf data/users/
	@echo "Flushed registry DB and all user DBs."

hooks-setup:
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

js-deps:
	@for pkg in app/vendor plugins/dashboards/*/package.json plugins/frontends/*/package.json; do \
		dir=$$([ -d "$$pkg" ] && echo "$$pkg" || dirname "$$pkg"); \
		if [ -f "$$dir/package.json" ]; then \
			(cd "$$dir" && npm ci --silent); \
		fi; \
	done

js-format-check:
	npm run format:check

js-lint:
	npm run lint

js-test:
	@for pkg in app/vendor plugins/dashboards/*/package.json plugins/frontends/*/package.json; do \
		dir=$$([ -d "$$pkg" ] && echo "$$pkg" || dirname "$$pkg"); \
		if grep -q '"test"' "$$dir/package.json" 2>/dev/null; then \
			echo "Testing $$dir"; \
			(cd "$$dir" && npm test) || exit 1; \
		fi; \
	done

js-typecheck:
	@for pkg in app/vendor plugins/dashboards/*/package.json plugins/frontends/*/package.json; do \
		dir=$$([ -d "$$pkg" ] && echo "$$pkg" || dirname "$$pkg"); \
		if [ -f "$$dir/tsconfig.json" ]; then \
			echo "Type checking $$dir"; \
			(cd "$$dir" && npx --no-install tsc --noEmit) || exit 1; \
		fi; \
	done

python-format-check:
	uv run ruff format --check .

python-lint:
	uv run ruff check .

python-test:
	uv run --no-sync pytest

python-typecheck:
	uv run ty check app/ --exclude "**/vendor/**" --exclude "**/fl/**" --exclude "**/telemetry/**" --exclude "**/graphql/**" --exclude "**/tests/**"

tests-coverage:
	uv run --no-sync pytest --cov=app \
		--cov-report=term-missing --cov-report=html:htmlcov --cov-report=json:coverage.json
