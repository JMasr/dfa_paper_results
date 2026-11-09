# Extension stage

The extension stage carried the closed-form readout, LoRA, DoRA and radial-lora to seven datasets under the same protocol, added full fine-tuning, the readout controls and the hybrids, ran LoRA and DoRA at ranks 256 and 512, and recorded the cost of every cell.

| | |
|---|---|
| Runs | 1197 |
| Arms | 13 |
| Datasets | 7 (6 independent corpus units) |
| Models | 3 (HuBERT Base, wav2vec 2.0 Base, Whisper Base (encoder)) |
| Blocks (corpus unit × model) | 18 |
| Speaker-disjoint partitions per cell | 3 |
| Ranks | 8, 256, 512 |
| Source package (internal identifier) | `paquete_campana2_20260908_1651`, generated 2026-09-08 16:51:10 |

## Files

| File | One row is | Level |
|---|---|---|
| [`runs.csv`](runs.csv) | one training run (dataset × model × arm × rank × partition) | run |
| [`contrasts.csv`](contrasts.csv) | one contrast (arm against a rival, on one endpoint) with its test | block |
| [`block_deltas.csv`](block_deltas.csv) | one paired difference of one contrast in one block | block |
| [`negative_control.csv`](negative_control.csv) | one arm tested against itself across replicates (must not be significant) | block |
| [`below_floor_rates.csv`](below_floor_rates.csv) | one arm: share of runs at or below the majority-class floor | run |
| [`analysis_policies.csv`](analysis_policies.csv) | one contrast under one of the four analysis policies (floor filter × rivals) | block |
| [`arm_summary.csv`](arm_summary.csv) | one arm: medians and bootstrap intervals at run and block level, cost | run and block |
| [`coverage.csv`](coverage.csv) | one arm: blocks present and missing | block |
| [`protocol_runs.csv`](protocol_runs.csv) | one run: partition sizes, search trials completed, training settings, extracted from the campaign logs | run |
| [`protocol_logs.csv`](protocol_logs.csv) | one log: sampler and pruner, final train/validation and test speakers | log |
| [`hpo_trials.csv`](hpo_trials.csv) | one arm: learning-rate trials per search and within-search spread of the validation score | arm |
| [`bundle_runs.csv`](bundle_runs.csv) | one training run with every metric the campaign recorded, including ranks 256 and 512 | run |
| [`cell_wall_clock.csv`](cell_wall_clock.csv) | one cell: end-to-end wall clock, search included | cell |
| [`sensitivity_readout.json`](sensitivity_readout.json) | sensitivity analyses of the closed-form readout (Supplementary Table S13) | block |

Column definitions are in [`DATA_DICTIONARY.md`](../DATA_DICTIONARY.md). [`MANIFEST.json`](MANIFEST.json) gives the SHA-256 of every file and where it comes from: the eight package files are byte-identical to the frozen analysis package, renamed to English; the protocol and search extracts are the rows of this stage taken from extracts that cover both stages.

## Arms

| Id in the data | Name in the article | Role |
|---|---|---|
| `dfa` | dfa | closed-form depth-fusion readout of the frozen encoder (proposed) |
| `dfa_last` | dfa-last | dfa reading only the last layer (depth control) |
| `dfa_lora` | dfa-lora | LoRA branches trained beneath the closed-form readout (hybrid) |
| `dfa_lora_anchor` | dfa-lora-anchor | hybrid; the readout competes on validation as anchor, spherical input |
| `dfa_lora_ns` | dfa-lora-ns | hybrid; the readout competes on validation as anchor, input as is |
| `dfa_sph` | dfa-sph | dfa with a spherical projection of the standardised embedding |
| `dora` | DoRA | established method |
| `full_ft` | Full fine-tuning | all encoder weights trained (capacity reference) |
| `lora` | LoRA | established method |
| `lora_ln` | lora-ln | LoRA with a non-affine LayerNorm before the head projector |
| `lora_ln_dw` | lora-ln-dw | lora-ln with a frozen uniform read of all layers (readout control) |
| `lora_recipe` | lora-recipe | lora-ln-dw with test-time averaging of four checkpoints (readout control) |
| `radial_lora_v3` | radial-lora | input-side variant of LoRA with a fixed, rank-dependent exponent |

## Datasets

| Id in the data | Name in the article | Condition | Material |
|---|---|---|---|
| `adress_dementia` | ADReSS | Alzheimer's dementia | picture description (English) |
| `coperia_a` | COPERIA /a/ | persistent post-COVID-19 symptoms | sustained /a/ (Spanish) |
| `coperia_cough` | COPERIA cough | persistent post-COVID-19 symptoms | voluntary cough (Spanish) |
| `coswara` | Coswara | COVID-19 (self-reported test) | sustained /a/ (crowd-sourced) |
| `neurovoz_vowels` | NeuroVoz | Parkinson's disease | sustained vowels (Spanish) |
| `parcz_vowels` | PARCZ | Parkinson's disease | sustained vowels (Czech) |
| `visia` | VISIA | adolescent suicidal ideation | clinical interview (Spanish) |
