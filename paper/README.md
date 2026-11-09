# Article reference artifacts

`current_artifacts.json` records the literal inputs of the Elsevier article and supplement wrappers, excluding comments: 19 TeX artifacts and four figures. It also records source hashes and commented inputs without distributing the manuscript text. `used_macros.json` lists the 188 scientific macros used by the manuscript.

`generated/` and `layout/` contain comparison references. Scripts write fresh outputs to `outputs/current/`; they do not copy these reference TeX files into the results. The default profile excludes `supps_tab_all_one.tex` and `supps_tab_all_two.tex`, which are inactive in the manuscript. Other inactive artifacts that can be recalculated from runs are retained as additional detail, distinguished by the coverage map.

| Active artifact group | Generation |
|---|---|
| Performance, contrasts, controls, corpus and cost tables | `build_paper_sota.py --from-runs`, using run-level results and the cost bundle |
| Complete statistics, additional arms and cross-stage relaunch comparisons | The same generator; new p/q families calculated from the original rows |
| Three presentation views | `build_editorial_views.py`, using newly calculated tables |
| Protocol macros | `build_protocol_macros.py`, using exported configuration and logs |
| Sensitivity results | `build_sensitivity_macros.py`, using block differences and reported aggregates in JSON; checked at published precision |
| Five descriptor files | `build_metadata.py`, using aggregate metadata CSVs; partition counts checked against logs |
| Paired-difference and rank figures | Regenerated CSVs, `build_readable_figures.py`, HTML, PDF/PNG |
| Method schematic | Editable HTML, rendered by the same pipeline |

The old exhaustive tables and four block matrices remain as historical references. Their old table names and numbers are not the numbering of the current supplement. See [scope and limitations](../docs/KNOWN_LIMITS.md).
