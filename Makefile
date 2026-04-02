.PHONY: install repo-server setup-hooks coverage clean release-desktop infra-init infra-import infra-plan infra-apply infra-output infra-destroy

# Install CLI tools globally (~/.local/bin/)
install:
	uv tool install --editable app/ --force
	uv tool install --editable repo-server/ --force
	@echo "Installed shenas, shenasctl, shenasrepoctl to ~/.local/bin/"
	@echo "Run 'shenasctl --install-completion' for tab completion"

repo-server:
	uv run python -m repository.main $(CURDIR)/packages

# Install git pre-commit hook
setup-hooks:
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

coverage:
	uv run --no-sync pytest --cov=repo_server --cov=app \
		--cov=shenas_pipes --cov=shenas_schemas \
		--cov-report=term-missing --cov-report=html:htmlcov --cov-report=json:coverage.json

clean:
	moon run :clean
	rm -rf .moon/cache/ packages/ .ruff_cache/ .pytest_cache/

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

# Infrastructure (OpenTofu)
infra-init:
	cd deploy/tofu && tofu init

# One-time: import resources created before OpenTofu
infra-import:
	cd deploy/tofu && \
	tofu import google_container_cluster.shenas projects/shenas-491609/locations/us-east4/clusters/shenas && \
	tofu import google_compute_global_address.ingress_ip projects/shenas-491609/global/addresses/shenas-ip && \
	tofu import google_artifact_registry_repository.shenas projects/shenas-491609/locations/us-east4/repositories/shenas && \
	tofu import google_service_account.github_deploy projects/shenas-491609/serviceAccounts/github-deploy@shenas-491609.iam.gserviceaccount.com && \
	tofu import google_iam_workload_identity_pool.github projects/shenas-491609/locations/global/workloadIdentityPools/github-pool && \
	tofu import google_iam_workload_identity_pool_provider.github projects/shenas-491609/locations/global/workloadIdentityPools/github-pool/providers/github-provider && \
	echo "Import complete. Run: make infra-plan"

infra-plan:
	cd deploy/tofu && tofu plan

infra-apply:
	cd deploy/tofu && tofu apply

infra-output:
	cd deploy/tofu && tofu output

infra-destroy:
	cd deploy/tofu && tofu destroy
