UV ?= uv
RUN := $(UV) run --locked
.DEFAULT_GOAL := help
.PHONY: help install browser verify-data test reproduce package verify-package
help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  make %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
install: ## Install the exact locked environment
	$(UV) sync --locked
browser: ## Install Chromium; Linux system dependencies may be needed
	$(RUN) playwright install chromium
verify-data: ## Verify all stage manifests and additional scientific inputs
	$(RUN) python tools/verify_data.py
test: ## Run integrity and scientific regression tests
	$(RUN) pytest -q
reproduce: ## Reconstruct everything in fresh staging and compare references
	$(RUN) python tools/reproduce.py
package: ## Build a local release archive from a passing reconstruction
	$(RUN) python tools/package_release.py
verify-package: ## Verify the local release archive
	$(RUN) python tools/package_release.py --verify dist/phd-paper-method-1.1.0rc2-current.zip
