# Data dictionary

The analysis packages were produced by the research group's analysis engine, which names its columns in Spanish. The files are published byte-identical, so their columns keep those names; this dictionary gives the meaning of each one. Two levels of aggregation coexist and must not be mixed: a **run** is one training of one arm on one dataset, model and partition; a **block** is one independent corpus unit read through one model, and every test statistic (p, q, minimum detectable effect, interval of a difference) is computed over blocks.

## Identifiers shared by several files

| Column | Meaning |
|---|---|
| `dataset` | dataset identifier; the stage READMEs map it to the name used in the article |
| `model` | frozen speech foundation model: `hubert_base`, `wav2vec2_base`, `whisper_base` |
| `adapter`, `brazo` | arm identifier; the stage READMEs map it to the name used in the article |
| `display` | the arm's display label in the engine's own reports |
| `rank` | rank of the low-rank update (8 unless stated; the analytic readouts have no rank and carry 8 as a label) |
| `seed` | optimisation seed (fixed at 54 for every run) |
| `split_seed` | seed of the speaker-disjoint partition (7, 8 or 9) |
| `replica` | partition replicate, written `seed\|split_seed` |
| `bloque` | block, written `corpus_unit/model`; `coperia` joins the cough and sustained /a/ datasets, which share participants |
| `metrica` | endpoint: `speaker_auroc` or `speaker_macro_f1` |
| `rival` | arm the contrast is taken against |
| `familia_cerrada` | `True` when the arm's method family had been closed to further development by the research programme when the package was produced; metadata only, it does not exclude the arm from any analysis |

## runs.csv

| Column | Meaning |
|---|---|
| `run_id` | run identifier: model, rank, seed, partition and launch time |
| `aggregation_level` | level at which the endpoint is computed (`speaker`) |
| `speaker_aggregation` | how processed inputs are aggregated to the speaker (`mean_logits`) |
| `gate_fail` | 1 when the run failed a validity gate of the engine; such runs are dropped in every analysis |
| `above_floor`, `speaker_above_floor` | 1 when the run's macro-F1 exceeds that of always predicting the majority class (recording and speaker level) |
| `learning_rate` | learning rate selected by the search |
| `speaker_auroc`, `speaker_macro_f1` | speaker-level endpoints on the held-out test speakers |

## contrasts.csv

| Column | Meaning |
|---|---|
| `familia` | `confirmatoria`: pre-specified contrast; `suplementaria`: exploratory contrast between candidates, with its own false-discovery correction |
| `lectura` | how the contrast is read: `superioridad` (signed test) or `equivalencia` (two one-sided tests against a declared margin) |
| `delta` | median over blocks of the paired difference, arm minus rival |
| `ci_low`, `ci_high` | 95 % interval of `delta` over blocks |
| `p`, `q` | exact two-sided Wilcoxon signed-rank p over blocks; Benjamini–Hochberg q within the family |
| `mde_abs` | minimum detectable effect at α = 0.05 two-sided and power 0.80, `(z_0.975 + z_0.80) · sd(delta[delta != 0]) / sqrt(n_efectivo)`; infinite when no test is possible |
| `n_bloques` | blocks in the contrast |
| `n_efectivo` | blocks with a non-zero difference, the n the Wilcoxon test uses |
| `n_pares` | paired run differences behind the block means |
| `bloques_a_favor` | blocks in which the arm is ahead of the rival |
| `significativo` | `True` when `q < 0.05` |
| `clase_nulo` | `no_informativo` for a non-significant contrast, which is not evidence of no difference; `no_aplica` for a significant one |
| `ciego_mde` | `True` when the absolute `delta` is below `mde_abs`, so the design could not resolve an effect of the observed size |
| `familia_m` | number of contrasts in the false-discovery family |
| `q_floor` | smallest q the family can reach with this number of blocks |

## block_deltas.csv

`delta` is the paired difference, arm minus rival, in one block (`bloque`) on one endpoint (`metrica`), after averaging runs within the block.

## negative_control.csv

Each arm is tested against itself across replicates; a significant result would mean the engine is broken. `testable` says whether the test exists with the available blocks, `certifica` whether the control passed, and `nota` restates the expected outcome (not significant).

## below_floor_rates.csv

`tasa_bajo_suelo` is the share of the arm's `n` runs whose speaker-level macro-F1 does not exceed that of always predicting the majority class.

## analysis_policies.csv

| Column | Meaning |
|---|---|
| `politica` | `floor=OFF` keeps runs at or below the majority-class floor, `floor=ON` drops them; `rivales=1` sets each arm against LoRA, `rivales=2` against LoRA and DoRA |
| `estatus` | `CONFIRMATORIA` for the pre-specified policy, `sensibilidad` for the others |
| `drop_below_floor` | the floor filter as a boolean |
| `n_runs_usados` | runs entering the analysis under the policy |
| `significativo_a_favor` | significant with the arm ahead |

The remaining columns are as in `contrasts.csv`.

## arm_summary.csv

| Column | Meaning |
|---|---|
| `locus` | where the arm acts: `encoder`, `readout`, `hybrid` or `full_ft` |
| `familia` | method family label of the engine (Spanish), descriptive only |
| `es_control` | `True` for the control arms |
| `<endpoint>__run_mediana`, `__run_ic_low`, `__run_ic_high` | median over runs and its bootstrap 95 % interval (5,000 resamples, fixed seed) |
| `<endpoint>__bloque_mediana`, `__bloque_ic_low`, `__bloque_ic_high` | the same over blocks, the level used with the tests |
| `<endpoint>__n_runs`, `<endpoint>__n_bloques` | runs and blocks behind the medians |
| `train_runtime_s`, `vram_peak_gb`, `infer_samples_per_s` | median training time per run, peak GPU memory and inference throughput |
| `trainable_params` | trainable parameters (empty means unknown, never zero) |
| `n_runs_coste` | runs behind the cost columns, which can differ from the runs behind the endpoints |

## coverage.csv

`bloques_presentes` and `bloques_esperados` count the arm's blocks, `completo` is `True` when none is missing, `rangos` lists its ranks and `bloques_ausentes` names the missing blocks.

## protocol_runs.csv and protocol_logs.csv

Extracted from the campaign logs, one row per run and per log. They record the partition sizes (`n_speakers`, `pool_speakers`, `test_speakers`, `final_train_val_speakers`), the nested learning-rate search (`n_outer_splits`, `n_inner_splits`, `n_trials`, `trial_records`, `trials_completed`, `first_trial_selected`, `lr_from_fold`, `sampler_pruner`) and the training settings of each arm (`num_train_epochs`, `batch_size`, `patience`, `adapter_*`, `trainer_overrides`, `use_class_weights`, `balance_loss_by_unit`). Multi-valued fields are separated by `|`, one value per outer fold.

## hpo_trials.csv

One row per arm: `cells` searched, `trial_files` written, `trials_per_file`, `complete_trials_median` after pruning, `val_score_range_max` the largest spread of the validation score within one search, and `files_with_nonzero_range` the searches in which the trials did not all return the same score.

## bundle_runs.csv (extension stage)

The campaign's own per-run table, with every metric it recorded: recording-level (`auroc`, `macro_f1`, `accuracy`, `balanced_accuracy`, `sensitivity`, `specificity`, `ppv`, `sens_at_spec90`, `worst_class_recall`) and speaker-level (`speaker_*`) metrics, test sizes (`n_test`, `n_positive`, `speaker_n_test`, `speaker_n_positive`, `n_classes`), the majority-class floor (`majority_f1`, `speaker_majority_f1`), diagnostic detectors (`dead_detector`, `alarmist_detector`, `recall_confounder`, `g1_vs_g2_*`), and cost (`train_runtime_s`, `vram_peak_gb`, `infer_samples_per_s`, `trainable_params`). `sens_at_spec90` is a curve summary whose threshold is chosen on the test set; it is not an operating point.

## cell_wall_clock.csv (extension stage)

One row per cell: `wall_s` is the end-to-end wall clock in seconds, learning-rate search included, `hpo` the search configuration label, `gpu` the device index and `status` the cell's final state (`OK`, or `SIN_DIR` when the cell left no output directory).

## sensitivity_readout.json (extension stage)

Sensitivity analyses of the closed-form readout run on the processed partitions held on disk, under the keys of `analyses`: `dfa_speaker_balanced` (training inputs replicated so that every speaker carries the same total weight), `dfa_speaker_weighted` (one averaged input per speaker) and `dfa_no_mask` (Whisper frames pooled over the whole window instead of the recorded audio). The paired per-block differences are the result; the `note` field states the scope.


## Inputs for the reconstructed presentation

`metadata/*_macros.csv` contains `macro`, `value`, and `provenance`; the value is a released aggregate or model descriptor, not an individual measurement. The three other metadata CSVs contain the displayed cohort, split and demographic fields. `metadata/templates/` contains table structure only. The scientific descriptors are in CSV, not copied from reference TeX at execution.

`paper/figs/fig_blocks_data.csv` holds paired mean differences and minima/maxima across partitions (percentage points). `fig_rank_curve_data.csv` holds medians and `q25`/`q75` across blocks; these are interquartile ranges, not confidence intervals. Both are immutable references; scripts regenerate their counterparts in `outputs/figs/`.

The paper bootstrap uses 5,000 resamples and `numpy.random.default_rng(0)`. Regenerating `sensitivity_macros.tex` starts from the published sensitivity aggregate JSON, not from new sensitivity training. Archived engine contrasts and article contrasts can use different rank groupings/test conventions; see `docs/KNOWN_LIMITS.md`.


## Current paper analysis exports

The default `current` profile does not consume historical q values. The historical all-arm tables are commented out in the manuscript. `paper/current_artifacts.json` defines its active artifact snapshot.

- `outputs/current/data/paired_contrasts.csv`: one row per endpoint/contrast/family (58). `delta` and `mde` are in the endpoint's original units, not percentage points; `p` and `q` are unrounded. `family_m` includes both endpoints as in the paper.
- `block_differences.csv`: the paired mean difference in each corpus/backbone block and number of paired observations.
- `all_arms_by_rank.csv`: per-stage arm/rank inventory, run count, block count, median block AUROC/macro-F1 and below-floor run count (42 rows, 2,025 runs). It is descriptive and includes methods outside the paper's primary comparison.

These are freshly calculated from the run-level CSVs. Descriptor CSVs remain aggregate metadata inputs. The reported mask/padding dose-response correlation lacks its original six x/y pairs and is rendered as a reported JSON aggregate; it is not an independently recalculated statistic in this package.
