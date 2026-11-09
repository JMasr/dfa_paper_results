# Released aggregate descriptors

These CSVs make cohort and model descriptors explicit inputs rather than retaining them only in LaTeX tables and macros. They originate from aggregates measured and reported by the authors; provenance is recorded in the release manifest. They contain no individual participant records, audio or participant identifiers.

`build_metadata.py` reconstructs the two macro collections and the cohort, partition and demographic tables from these CSVs. This transformation reproduces the descriptive artifacts; it does not recalculate ages or cohort composition from private records. `check_splits.py` additionally checks speaker counts against protocol logs.

Text fields retain LaTeX formatting where needed for ranges, units and notes; column headers identify their meaning. Missing information remains missing and is never converted to zero.
