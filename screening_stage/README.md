# Screening stage

The screening stage evaluated every arm of the framework at rank 8 on four datasets and three frozen speech foundation models. Its results decided which methods were carried to the extension stage: AdaLoRA, IA3 and HiRA did not exceed LoRA and were not carried forward.

| | |
|---|---|
| Runs | 828 |
| Arms | 23 |
| Datasets | 4 (4 independent corpus units) |
| Models | 3 (HuBERT Base, wav2vec 2.0 Base, Whisper Base (encoder)) |
| Blocks (corpus unit × model) | 12 |
| Speaker-disjoint partitions per cell | 3 |
| Ranks | 8 |
| Source package (internal identifier) | `paquete_etapa2_final_20260906_2331`, generated 2026-09-06 23:31:32 |

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

Column definitions are in [`DATA_DICTIONARY.md`](../DATA_DICTIONARY.md). [`MANIFEST.json`](MANIFEST.json) gives the SHA-256 of every file and where it comes from: the eight package files are byte-identical to the frozen analysis package, renamed to English; the protocol and search extracts are the rows of this stage taken from extracts that cover both stages.

## Arms

| Id in the data | Name in the article | Role |
|---|---|---|
| `adalora_peft` | AdaLoRA | established method |
| `cov_readout` | cov-readout | last-layer covariance features with a gradient-trained head (readout control) |
| `dfa` | dfa | closed-form depth-fusion readout of the frozen encoder (proposed) |
| `dfa_last` | dfa-last | dfa reading only the last layer (depth control) |
| `dfa_lora_anchor` | dfa-lora-anchor | hybrid; the readout competes on validation as anchor, spherical input |
| `dfa_lora_ns` | dfa-lora-ns | hybrid; the readout competes on validation as anchor, input as is |
| `dora` | DoRA | established method |
| `ens_lora` | ens_lora | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `hira` | HiRA | established method |
| `ia3` | IA3 | established method |
| `lora` | LoRA | established method |
| `lora_ln` | lora-ln | LoRA with a non-affine LayerNorm before the head projector |
| `lora_recipe` | lora-recipe | lora-ln-dw with test-time averaging of four checkpoints (readout control) |
| `modlora` | modlora | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `oft` | oft | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `pa_lora` | pa_lora | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `proto_class` | proto_class | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `proto_kernel` | proto_kernel | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `radial_lora` | radial_lora | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `radial_lora_v3` | radial-lora | input-side variant of LoRA with a fixed, rank-dependent exponent |
| `sglora_v12` | sglora_v12 | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `tda` | tda | further in-house adapter variant, reported in Supplementary Table S3 and outside the article's claims |
| `wls_readout` | wls-readout | learned weighted layer sum with a gradient-trained head (readout control) |

## Datasets

| Id in the data | Name in the article | Condition | Material |
|---|---|---|---|
| `adress_dementia` | ADReSS | Alzheimer's dementia | picture description (English) |
| `coperia_cough` | COPERIA cough | persistent post-COVID-19 symptoms | voluntary cough (Spanish) |
| `neurovoz_vowels` | NeuroVoz | Parkinson's disease | sustained vowels (Spanish) |
| `visia` | VISIA | adolescent suicidal ideation | clinical interview (Spanish) |
