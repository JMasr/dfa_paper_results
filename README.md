# DFA: results and reproducible analysis

Analysis code and exported results for *Closed-Form Depth-Fusion Readout versus Parameter-Efficient Adaptation of Speech Foundation Models for Low-Resource Clinical Screening from Voice*.

Authors: José Manuel Ramírez Sánchez, Laura Docío-Fernández, Alejandro A. García-Caballero and Carmen García-Mateo.

## Run the analysis

```bash
uv sync --locked
uv run --locked playwright install chromium
uv run --locked pytest -q
uv run --locked python tools/reproduce.py
```

The environment uses Python 3.11.12 and dependencies pinned in `uv.lock`. On Linux, Chromium also requires system libraries: use `playwright install --with-deps chromium` if they are missing. An installed browser can be selected through `CHROME_BIN`. After installation, processing requires only a CPU and local files.

The analysis starts from 2,025 completed runs: 828 in `screening_stage/` and 1,197 in `extension_stage/`. It calculates 58 contrasts and regenerates the current tables and figures in `outputs/current/`. The reproduction report records hashes and comparisons against reference artifacts. The cohort and model CSVs in `metadata/` contain declared aggregates; they are not inferred from training metrics. This package does not train models or recalculate AUROC/F1 from individual predictions. It contains no audio or participant-identifying records.

`paper/` contains numerical references used to check the reconstruction. The generators calculate new outputs from the bundles rather than copying these references. Original campaign files retain their SHA-256 manifests. Historical tables that are inactive in the manuscript are excluded from the default profile. See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) and [docs/KNOWN_LIMITS.md](docs/KNOWN_LIMITS.md) for provenance and scope.

The original exports use some Spanish column names and categorical values. They are preserved byte-for-byte for data integrity and documented in English in the data dictionary.

## Audit text

```bash
uv run --locked python tools/audit_text.py . --git
```

The auditor checks for automated attribution, tool markers, invisible characters, bidirectional controls, damaged encoding and Unicode normalization differences. Legitimate typography is classified separately. It neither determines whether a person or a model wrote a text nor modifies files. Use `--json /path/report.json` to save findings, `--strict` to fail on warnings, and `--pdf` to inspect PDF text and metadata with pypdf. Editorial disclosures of tool use are identified separately from authorship signatures.

## Check the accompanying LaTeX project

With the delivery's `repo_latex/` directory beside this repository:

```bash
uv run --locked python tools/reproduce.py --manuscript-dir ../repo_latex
```

After a successful reconstruction, create a self-contained archive with `uv run --locked python tools/package_release.py`. This command does not publish files or create tags. Code is licensed under MIT and aggregate data under CC BY 4.0; see [LICENSE](LICENSE) and [LICENSE-DATA](LICENSE-DATA).
