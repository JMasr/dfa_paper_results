#!/usr/bin/env python3
"""Partition and learning-rate search as executed -> LaTeX macros.

Reads the protocol_runs.csv and protocol_logs.csv of both stages (extracted once from what every run
of the two campaigns recorded about itself) and the code constants in tools/protocol_constants.json, and
writes outputs/generated/protocol_macros.tex, so that the Methods describe the protocol that ran and no
figure of it is typed by hand. The build stops if the protocol was not one and the same in every run.

Macros (prefix \\prot):
  \\protRunsOne / \\protRunsTwo          completed runs read, per stage (must equal the packages' rows)
  \\protOuterFolds / \\protInnerFolds    folds of the development pool / folds inside each of them
  \\protSearchesPerCell                  learning-rate searches per cell (= outer folds)
  \\protValPoolPct                       share of the development pool held out to stop the final model
  \\protTrainPctMin..Max, \\protValPctMin..Max, \\protTestPctMin..Max
                                         speakers of the final model's three subsets, range over corpora
  \\protPrunerStartupOne/Two, \\protPrunerWarmupOne/Two   median-pruning rule of each stage (…Word: spelled out)
  \\protDoneOneMin..Max / \\protDoneTwoMin..Max   median completed trials per search, range over the
                                         gradient-trained methods of the primary comparison at rank 8
  \\protFirstTrialPctOne / \\protFirstTrialPctTwo  searches of those methods won by their first trial (%)
  \\protMaxEpochs, \\protBatchSize, \\protPatience, \\protDivergenceGapFactor   recorded by every run (effective_config.json)
  \\protRank, \\protRankMid, \\protRankHigh, \\protAlphaOverR, \\protDropout   the adapter constants every gradient run recorded
  \\protAdalora{TargetRatio,Tinit,Tfinal,Orth}, \\protIaThreeInit, \\protRadial{LambdaRef,RankRef,LambdaMax,Beta}
                                         method constants as the runs of that method recorded them
  \\protWeightDecay, \\protGradClip, \\protWarmupPct, \\protEsThreshold, \\protDivergencePatience, \\protLrLow, \\protLrHigh
                                         trainer and search constants from the configuration the runs resolved
                                         to, with the extract's proof that no run overrode them
  \\statBootResamples, \\statPowerZ     the bootstrap and power constants of the results generator

    python3 tools/build_protocol_macros.py
"""
from __future__ import annotations
import csv, hashlib, json, math, re, statistics, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_data  # noqa: E402

OUT = repo_data.ROOT / "outputs" / "generated" / "protocol_macros.tex"
GRADIENT = {1: ("lora", "dora", "adalora_peft", "ia3", "hira", "radial_lora_v3"),   # primary comparison, screening
            2: ("lora", "dora", "radial_lora_v3")}                                  # carried into the extension
BUDGET = {1: {"6"}, 2: {"12", "1"}}


def die(m: str):
    sys.stderr.write("ERROR: " + m + "\n"); sys.exit(1)


def one(values, what):
    s = set(values)
    if len(s) != 1: die(f"{what} is not unique across runs: {sorted(s)}")
    return s.pop()


def consts_(arm, R):
    c = set(r["adapter_constants"] for r in R if r["adapter_type"] == arm)
    if len(c) != 1: die(f"{arm}: constants differ across runs: {sorted(c)}")
    return dict(kv.split("=", 1) for kv in c.pop().split(";") if kv)


def g_(x): return f"{float(x):g}"


def main():
    global OUT
    if "--out" in sys.argv:                                # --out <folder> writes the macros elsewhere
        OUT = Path(sys.argv[sys.argv.index("--out") + 1]).expanduser().resolve() / OUT.name
    man = json.loads((Path(__file__).resolve().parent / "protocol_constants.json").read_text())
    R = repo_data.both_stages("protocol_runs.csv")
    L = repo_data.both_stages("protocol_logs.csv")
    code = man["code"]

    # ---- one protocol in every run -----------------------------------------------------------------
    outer = int(one((r["n_outer_splits"] for r in R), "n_outer_splits"))
    inner = int(one((r["n_inner_splits"] for r in R), "n_inner_splits"))
    one((r["num_runs"] for r in R), "num_runs"); one((r["seed"] for r in R), "optimisation seed")
    if {r["split_seed"] for r in R} != {"7", "8", "9"}: die("partition seeds are not exactly 7, 8, 9")
    for k in ("test_out_fraction_override", "outer_val_fraction_override", "pruner_overrides"):
        if one((r[k] for r in R), k) != "": die(f"{k} was overridden in the campaigns")
    if one((r["outer_folds"] for r in R), "fold directories per run") != str(outer): die("fold directories != n_outer_splits")
    n_runs = {}
    declared = {st: repo_data.manifest(st)["bundle"]["runs"] for st in (1, 2)}
    for st in (1, 2):
        rs = [r for r in R if r["stage"] == str(st)]
        n_runs[st] = len(rs)
        if n_runs[st] != man["completed_runs"][f"stage{st}"]: die(f"stage {st}: rows differ from MANIFEST.json")
        if n_runs[st] != declared[st]:
            die(f"stage {st}: {n_runs[st]} runs read, the package declares {declared[st]}")
        if {r["n_trials"] for r in rs} != BUDGET[st]: die(f"stage {st}: trial budgets {sorted({r['n_trials'] for r in rs})}")
        for r in rs:                                    # every search holds exactly its budget of trial records
            if set(r["trial_records"].split("|")) != {r["n_trials"]}: die(f"trial records != budget in {r}")

    # ---- the three subsets of the final model --------------------------------------------------------
    vfrac, tfrac = code["FINAL_MODEL_VAL_FRACTION"], code["DEFAULT_TEST_OUT_FRACTION"]
    split = {}
    for r in R:
        n, pool, test = int(r["n_speakers"]), int(r["pool_speakers"]), int(r["test_speakers"])
        if pool + test != n: die(f"pool + test != speakers in {r}")
        val = math.ceil(vfrac * pool)                   # sklearn train_test_split(test_size=float)
        split.setdefault(r["corpus"], set()).add((pool - val, val, test))
    for c, s in split.items():
        if len(s) != 1: die(f"{c}: subset sizes differ across runs: {sorted(s)}")
    logged = defaultdict(set)
    for l in L:                                         # the sizes the runs logged must be the ones derived
        if not l["final_train_val_speakers"]: continue
        for tv in l["final_train_val_speakers"].split(" / "):
            a, b = tv.split("|"); logged[l["corpus"]].add((int(a), int(b)))
    for c, s in logged.items():
        tr, va, _ = next(iter(split[c]))
        if s != {(tr, va)}: die(f"{c}: logs give train/val {sorted(s)}, derived {(tr, va)}")
    if set(logged) != set(split): die("a corpus has no logged final split")
    pct = {k: [100 * next(iter(s))[i] / sum(next(iter(s))) for s in split.values()] for i, k in enumerate(("Train", "Val", "Test"))}

    # ---- pruning rule ------------------------------------------------------------------------------
    lines2 = {l["sampler_pruner"] for l in L if l["stage"] == "2" and l["sampler_pruner"]}
    want = {"TPE(startup=3) + MedianPruner(startup=4, warmup=5)", "TPE(startup=1) + NopPruner"}
    if lines2 != want: die(f"stage-2 sampler/pruner lines: {sorted(lines2)}")
    for l in L:
        if l["stage"] == "2" and ("MedianPruner" in l["sampler_pruner"]) != (l["adapter"] not in ("dfa", "dfa_last", "dfa_sph")):
            die(f"stage 2: pruner line does not match the arm type in {l}")

    # ---- what the search completed -----------------------------------------------------------------
    done, first = {}, {}
    for st in (1, 2):
        meds, f, n = [], 0, 0
        for arm in GRADIENT[st]:
            rs = [r for r in R if r["stage"] == str(st) and r["adapter"] == arm and r["rank"] == "8"]
            if not rs: die(f"stage {st}: no rank-8 runs of {arm}")
            d = [int(x) for r in rs for x in r["trials_completed"].split("|")]
            if min(d) < 1: die(f"stage {st} {arm}: a search completed no trial")
            meds.append(statistics.median(d))
            w = [int(x) for r in rs for x in r["first_trial_selected"].split("|")]
            f += sum(w); n += len(w)
        done[st] = (min(meds), max(meds)); first[st] = 100 * f / n

    # ---- trainer and adapter constants recorded by the runs ------------------------------------------
    LOWRANK = ("lora", "dora", "hira", "radial_lora_v3", "lora_ln", "lora_ln_dw", "lora_recipe")   # the reported arms that carry a scaled low-rank branch
    grad = [r for r in R if r["adapter_type"] in LOWRANK]
    if any(r["adapter_scaling"] == "" for r in grad): die("a low-rank run did not record its adapter scaling")
    epochs = one((r["num_train_epochs"] for r in R), "num_train_epochs"); batch = one((r["batch_size"] for r in R), "batch_size")
    patience = one((r["patience"] for r in R), "patience")
    gap = one((r["divergence_gap"] for r in R if r["divergence_gap"] != ""), "divergence_gap (runs that recorded it)")
    if one((r["trainer_overrides"] for r in R), "trainer overrides") != "": die("a run overrode a trainer constant")
    alpha_r = one((r["adapter_scaling"] for r in grad), "adapter_scaling")
    # the screening-stage code did not write the branch dropout into effective_config.json; the value is the one every
    # low-rank run of the extension stage recorded, and the AdaLoRA runs of the screening stage recorded the same figure
    drop = one((r["adapter_dropout"] for r in grad if r["adapter_dropout"] != ""), "adapter_dropout (runs that recorded it)")
    if g_(consts_("adalora_peft", R)["adalora_dropout"]) != g_(drop): die("AdaLoRA dropout differs from the low-rank branch dropout")
    ranks = sorted({int(r["rank"]) for r in R if r["rank"].isdigit()})
    if ranks != [8, 256, 512]: die(f"ranks run: {ranks}")
    consts = lambda arm: consts_(arm, R)
    ada, ia3, rad = consts("adalora_peft"), consts("ia3"), consts("radial_lora_v3")
    tc, ls = man["code"]["trainer_config"], man["code"]["lr_search_space"]
    sota = (Path(__file__).resolve().parent / "build_paper_sota.py").read_text()   # bootstrap and power constants
    from build_paper_sota import BOOTSTRAP_RESAMPLES
    boot = str(BOOTSTRAP_RESAMPLES)
    z = re.search(r"^Z = ([\d.]+) \+ ([\d.]+)", sota, re.M)

    def g(x): return f"{float(x):g}"
    M = [("protRunsOne", n_runs[1]), ("protRunsTwo", n_runs[2]),
         ("protOuterFolds", outer), ("protInnerFolds", inner), ("protSearchesPerCell", outer),
         ("protValPoolPct", g(100 * vfrac)), ("protTestPoolPct", g(100 * tfrac))]
    for k, v in pct.items():
        M += [(f"prot{k}PctMin", f"{min(v):.0f}"), (f"prot{k}PctMax", f"{max(v):.0f}")]
    M += [("protPrunerStartupOne", code["stage1_pruner"]["n_startup_trials"]), ("protPrunerWarmupOne", code["stage1_pruner"]["n_warmup_steps"]),
          ("protPrunerStartupTwo", 4), ("protPrunerWarmupTwo", 5),
          ("protDoneOneMin", g(done[1][0])), ("protDoneOneMax", g(done[1][1])),
          ("protDoneTwoMin", g(done[2][0])), ("protDoneTwoMax", g(done[2][1])),
          ("protFirstTrialPctOne", f"{first[1]:.0f}"), ("protFirstTrialPctTwo", f"{first[2]:.0f}")]
    words = "zero one two three four five six seven eight nine ten eleven twelve".split()
    M += [(k + "Word", words[int(v)]) for k, v in M
          if k in ("protOuterFolds", "protInnerFolds", "protPrunerStartupOne", "protPrunerWarmupOne",
                   "protPrunerStartupTwo", "protPrunerWarmupTwo")]
    M += [("protMaxEpochs", epochs), ("protBatchSize", batch), ("protPatience", patience), ("protDivergenceGapFactor", g(1 + float(gap))),
          ("protRank", 8), ("protRankMid", 256), ("protRankHigh", 512), ("protAlphaOverR", g(alpha_r)), ("protDropout", g(drop)),
          ("protAdaloraTargetRatio", g(ada["adalora_peft_target_r_ratio"])), ("protAdaloraTinitPct", g(100 * float(ada["adalora_peft_tinit_ratio"]))),
          ("protAdaloraTfinalPct", g(100 * float(ada["adalora_peft_tfinal_ratio"]))), ("protAdaloraOrth", g(ada["adalora_peft_orth_reg_weight"])),
          ("protIaThreeInit", g(ia3["ia3_init_value"])),
          ("protRadialLambdaRef", g(rad["rlv3_lambda_ref"])), ("protRadialRankRef", g(rad["rlv3_rank_ref"])), ("protRadialLambdaMax", g(rad["rlv3_lambda_max"])), ("protRadialBeta", g(rad["rlv3_beta"])),
          ("protWeightDecay", g(tc["weight_decay"])), ("protGradClip", g(tc["max_grad_norm"])), ("protWarmupPct", g(100 * float(tc["warmup_ratio"]))),
          ("protEsThreshold", "10^{-4}" if float(tc["early_stopping_threshold"]) == 1e-4 else g(tc["early_stopping_threshold"])),
          ("protDivergencePatience", tc["early_stopping_divergence_patience"]),
          ("protLrLow", "10^{-5}" if float(ls["low"]) == 1e-5 else g(ls["low"])), ("protLrHigh", "5\\times10^{-2}" if float(ls["high"]) == 5e-2 else g(ls["high"])),
          ("protAdaloraMidPct", g(100 * (1 - float(ada["adalora_peft_tinit_ratio"]) - float(ada["adalora_peft_tfinal_ratio"])))),
          ("statBootResamples", boot), ("statPowerPct", f"{100 * __import__('statistics').NormalDist().cdf(float(z.group(2))):.0f}"), ("statPowerZ", f"{float(z.group(1)) + float(z.group(2)):.2f}")]
    words = "zero one two three four five six seven eight nine ten eleven twelve".split()
    M += [(k + "Word", words[int(v)]) for k, v in M if k in ("protPatience", "protDivergencePatience")]
    OUT.write_text("%% GENERATED by tools/build_protocol_macros.py -- do not edit.\n"
                   f"%% Source: {{screening,extension}}_stage/protocol_runs.csv and protocol_logs.csv; code constants at {code['repo_head'][:7]}\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in M))
    for k, v in M: print(f"  \\{k} = {v}")
    for c, s in sorted(split.items()):
        tr, va, te = next(iter(s)); print(f"  {c}: {tr}/{va}/{te} speakers")


if __name__ == "__main__":
    main()
