# Contributing to the reproduction package

This repository reconstructs the article's analysis from exported results. Repeating model training requires the original experimental code and authorized source data.

- Work on `feature/`, `fix/` or `docs/` branches, not directly on `main`.
- Use `uv sync --locked` and keep `uv.lock` under version control.
- Preserve scientific inputs and record their provenance and versions. Do not modify data to match a reference.
- Keep inputs, regenerated outputs and comparison references separate. Never copy references into the output directory to make a comparison pass.
- Link reported values to their CSV inputs, configuration and code. Record discrepancies and missing evidence explicitly.
- Do not include audio, participant identifiers, credentials or `.env` files.
- Run integrity, reproduction and comparison checks before proposing a release.
- Use English for documentation, identifiers and technical comments. Follow the maintainer's commit conventions and do not append automated attribution trailers.
- Review changes and metadata before publication. Reproduction commands must not publish files, create tags or modify external services.
