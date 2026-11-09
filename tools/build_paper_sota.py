#!/usr/bin/env python3
"""Results tables, macros and figures of the article, from the released data of both stages.

  screening_stage/   4 datasets x 3 models = 12 blocks; every arm at rank 8, including AdaLoRA, IA3 and
                     HiRA, which did not exceed LoRA and were not carried forward.
  extension_stage/   7 datasets x 3 models = 18 blocks; the readout, LoRA, DoRA, radial-lora, full
                     fine-tuning, the readout controls and the hybrids, with per-run cost.

With --from-runs, current performance tables and figures are recalculated from run-level
CSV exports. Pair by partition within block, average within block, median over blocks,
Wilcoxon on nonzero block differences, separate BH families and percentile bootstrap.
Participant counts and selected-run costs come from extension_stage/bundle_runs.csv,
whose hash is pinned below. Analytic trainable-parameter counts are cross-checked there.

Without --from-runs, the legacy inventory tables additionally render archived arm
summaries and policy q values for forensic comparison. Those tables are not active in
the current manuscript and must not be mistaken for independently recalculated q.

    python3 tools/build_paper_sota.py --from-runs

"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, statistics, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_data  # noqa: E402

Z = 1.959963984540054 + 0.8416212335729143
BOOTSTRAP_RESAMPLES = 5000
BOOTSTRAP_SEED = 0
MET = {"speaker_auroc": "Auroc", "speaker_macro_f1": "MacroF"}
METLAB = {"Auroc": "AUROC", "MacroF": "macro-F1"}
BUNDLE_SHA16 = "a5c77c16c5ea6486"

NAME = {"dfa": r"\textsc{dfa}", "dfa_last": r"\textsc{dfa-last}", "lora": "LoRA", "dora": "DoRA",
        "adalora_peft": "AdaLoRA", "ia3": r"IA$^3$", "hira": "HiRA", "radial_lora_v3": r"\textsc{radial-lora}",
        "full_ft": "Full fine-tuning", "dfa_lora_anchor": r"\textsc{dfa-lora-anchor}", "dfa_lora_ns": r"\textsc{dfa-lora-ns}",
        "dfa_lora": r"\textsc{dfa-lora}", "dfa_sph": r"\textsc{dfa-sph}", "lora_ln": r"\textsc{lora-ln}",
        "lora_ln_dw": r"\textsc{lora-ln-dw}", "lora_recipe": r"\textsc{lora-recipe}", "wls_readout": r"\textsc{wls-readout}",
        "cov_readout": r"\textsc{cov-readout}"}
STEM = {"dfa": "Dfa", "dfa_last": "DfaLast", "lora": "Lora", "dora": "Dora", "adalora_peft": "Adalora", "ia3": "IaThree",
        "hira": "Hira", "radial_lora_v3": "Radial", "full_ft": "FullFt", "dfa_lora_anchor": "Anchor", "dfa_lora_ns": "Ns",
        "dfa_lora": "DfaLora", "dfa_sph": "DfaSph", "lora_ln": "LoraLn", "lora_ln_dw": "LoraLnDw", "lora_recipe": "LoraRecipe",
        "wls_readout": "Wls", "cov_readout": "Cov"}
SITE = {"lora": "low-rank branch", "dora": "low-rank branch + magnitude", "adalora_peft": "low-rank branch, rank re-allocated",
        "ia3": "per-channel output gate", "hira": "low-rank branch, Hadamard with $W_0$", "radial_lora_v3": "norm-tempered input + low-rank branch",
        "dfa": "readout, closed form", "dfa_last": "readout, closed form", "full_ft": "whole model",
        "dfa_lora_anchor": "encoder + closed-form readout", "dfa_lora_ns": "encoder + closed-form readout", "dfa_lora": "encoder + closed-form readout",
        "dfa_sph": "readout, closed form", "lora_ln": "low-rank branch + LN head", "lora_ln_dw": "low-rank branch + uniform depth read",
        "lora_recipe": "low-rank branch + depth read + averaging", "wls_readout": "readout, learned layer weights, gradient head",
        "cov_readout": "readout, covariance features, gradient head"}
LABEL = {"dfa": r"\textsc{dfa} (proposed readout)", "dfa_last": r"\textsc{dfa-last} (depth control)", "lora": "LoRA", "dora": "DoRA",
         "radial_lora_v3": r"\textsc{radial-lora}", "adalora_peft": "AdaLoRA", "ia3": r"IA$^3$", "hira": "HiRA"}
PUBLISHED = ["lora", "dora", "adalora_peft", "ia3", "hira"]
EXT = ["lora", "dora", "radial_lora_v3"]                       # carried into the extension stage
STAGE_OF = {"lora": 2, "dora": 2, "radial_lora_v3": 2, "adalora_peft": 1, "ia3": 1, "hira": 1, "dfa": 2, "dfa_last": 2,
            "lora_ln_dw": 2, "lora_recipe": 2, "wls_readout": 1}
CORPUS = {"adress_dementia": "ADReSS", "coperia": "COPERIA", "coswara": "Coswara", "neurovoz_vowels": "NeuroVoz",
          "parcz_vowels": "PARCZ", "visia": "VISIA"}
DSNAME = {"adress_dementia": "ADReSS", "coperia_a": "COPERIA /a/", "coperia_cough": "COPERIA cough", "coswara": "Coswara",
          "neurovoz_vowels": "NeuroVoz", "parcz_vowels": "PARCZ", "visia": "VISIA"}
BACK = {"hubert_base": "HuBERT", "wav2vec2_base": "wav2vec~2.0", "whisper_base": "Whisper"}
PAL = {"adress_dementia": "#315f9e", "coperia": "#c2410c", "neurovoz_vowels": "#1f8a5f", "visia": "#7c3aed",
       "coswara": "#9a6500", "parcz_vowels": "#b0326a"}
KIND = {"adress_dementia": "spontaneous speech", "visia": "interview speech", "neurovoz_vowels": "sustained vowels",
        "parcz_vowels": "sustained vowels", "coperia": "voluntary cough and sustained /a/", "coswara": "sustained /a/, crowd-sourced"}
REGIME = [("speech", "connected and interview speech (ADReSS, VISIA)", ["adress_dementia", "visia"]),
          ("vowels", "sustained vowels (NeuroVoz, PARCZ, Coswara)", ["neurovoz_vowels", "parcz_vowels", "coswara"]),
          ("cough", "voluntary cough and /a/ (COPERIA)", ["coperia"])]
RSTEM = {"speech": "Speech", "vowels": "Vowels", "cough": "Cough"}

# Analytic trainable-parameter counts for the 768-dimensional, 12-layer encoders at rank 8 on the
# query and value projections of every layer (24 injection sites). Cross-checked against telemetry.
D, L, R, SITES = 768, 12, 8, 24
HEAD_PARAMS = D * 256 + 256 + 256 * 2 + 2                       # HF audio-classification head, C=2
PARAMS = {"lora": 2 * D * R * SITES, "dora": 2 * D * R * SITES + D * SITES, "adalora_peft": 2 * D * R * SITES + R * SITES,
          "ia3": D * SITES, "hira": 2 * D * R * SITES, "radial_lora_v3": 2 * D * R * SITES, "dfa": 0, "dfa_last": 0}


def die(m): sys.stderr.write("ERROR: " + m + "\n"); sys.exit(1)
def sha16(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
def load(p):
    with open(p, newline="", encoding="utf-8") as fh: return list(csv.DictReader(fh))
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def pp(x, signed=True): return "n/a" if x is None or math.isinf(x) or math.isnan(x) else (f"{100*x:+.2f}" if signed else f"{100*x:.2f}")
def q3(x): return "n/a" if x is None or math.isnan(x) else f"{x:.3f}"
def m3(x): return "n/a" if x is None else f"{x:.3f}"
def thousands(n): return f"{n:,}".replace(",", "{,}")
def rk(arm, rank="8"): return NAME[arm] + ("" if rank == "8" else f" ($r{{=}}{rank}$)")
def stem(arm, rank="8"): return STEM[arm] + ("" if rank == "8" else {"256": "Rmid", "512": "Rhigh"}[rank])


def bh(ps):
    m = len(ps); order = sorted(range(m), key=lambda i: ps[i]); q = [0.0] * m; prev = 1.0
    for r in range(m, 0, -1):
        i = order[r - 1]; prev = min(prev, ps[i] * m / r); q[i] = prev
    return q


def contrast(runs, cand, rc, rival, rr, met, corpora=None):
    cell = defaultdict(dict)
    for r in runs:
        if corpora is not None and r["bloque"].split("/")[0] not in corpora: continue
        key = (r["bloque"], r["dataset"], r["split_seed"])
        for method, rank, side in [(cand, rc, "c"), (rival, rr, "r")]:
            if (r["adapter"], r["rank"]) == (method, rank):
                if side in cell[key]: raise ValueError(f"Duplicate paired observation: {key} / {method} / {rank}")
                value = f(r.get(met))
                if value is None or not math.isfinite(value): raise ValueError(f"Missing/nonfinite {met}: {key} / {method}")
                cell[key][side] = value
    if not cell: raise ValueError("Empty contrast")
    incomplete = [key for key, value in cell.items() if set(value) != {"c", "r"}]
    if incomplete: raise ValueError(f"Unpaired observations: {incomplete[:3]}")
    per = defaultdict(list)
    for (blk, _, _), d in cell.items():
        if "c" in d and "r" in d: per[blk].append(d["c"] - d["r"])
    blocks = sorted(per); d = np.array([statistics.mean(per[b]) for b in blocks]); nz = d[d != 0]
    p = float(stats.wilcoxon(nz, zero_method="wilcox", alternative="two-sided", mode="exact").pvalue) if len(nz) >= 2 else float("nan")
    mde = (Z * float(np.std(nz, ddof=1)) / math.sqrt(len(nz))) if len(nz) >= 2 else float("inf")
    if len(nz) and 2.0 ** (1 - len(nz)) > 0.05: mde = float("inf")
    return dict(blocks=blocks, deltas=d, cells=dict(per), delta=float(np.median(d)), p=p, n=len(d), fav=int((d > 0).sum()), mde=mde)


def block_values(runs, arm, rank, met):
    per = defaultdict(list)
    for r in runs:
        if (r["adapter"], r["rank"]) == (arm, rank) and r[met]: per[r["bloque"]].append(float(r[met]))
    return {b: (statistics.mean(v), statistics.stdev(v) if len(v) > 1 else 0.0) for b, v in per.items()}


def boot_ci(vals, seed=BOOTSTRAP_SEED):
    rng = np.random.default_rng(seed); v = np.array(vals)
    # Same RNG draws and percentile convention as the original loop, vectorised.
    b = np.median(rng.choice(v, size=(BOOTSTRAP_RESAMPLES, len(v)), replace=True), axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def sig(d, q):
    ds = f"${pp(d)}$"; qs = q3(q)
    if q is not None and not math.isnan(q) and q < 0.05: ds = "$\\mathbf{" + pp(d) + "}$"; qs = r"\textbf{" + qs + "}"
    return ds, qs


STAGE_DIR = {1: "screening_stage", 2: "extension_stage"}


def write_csv(path: Path, rows: list):
    with path.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)


def open_stage(n: int, verify_engine: bool = True):
    """Stage n of the release: manifest and per-run rows, after checking the procedure against the engine."""
    pkg = repo_data.stage(n); man = repo_data.manifest(n)
    R = load(pkg / "runs.csv")
    if len(R) != man["bundle"]["runs"]: die(f"run count mismatch in {pkg.name}")
    if not verify_engine:
        print(f"validation: {len(R)} run-level records ({pkg.name}); archived summaries not used")
        return man, R
    eng = {(r["metrica"], r["brazo"], r["rival"]): r for r in load(pkg / "contrasts.csv")}
    for met in MET:
        mine = contrast(R, "dfa", "8", "lora", "8", met); e = eng[(met, "dfa", "lora")]
        if abs(mine["delta"] - float(e["delta"])) > 1e-9 or abs(mine["p"] - float(e["p"])) > 1e-9 or mine["fav"] != int(e["bloques_a_favor"]):
            die(f"procedure does not reproduce the engine on {met} in {pkg.name}")
    print(f"validation: reproduces the engine's dfa - lora on both endpoints ({pkg.name})")
    return man, R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="folder for the generated .tex (default: <repo>/outputs/generated)")
    ap.add_argument("--figs", default=None, help="folder for the generated figures (default: <repo>/outputs/figs)")
    ap.add_argument("--from-runs", action="store_true", help="Recompute current analyses without archived contrasts, policies or arm summaries")
    ap.add_argument("--data", help="Directory for unrounded analysis CSVs")
    a = ap.parse_args()
    out = Path(a.out).expanduser().resolve() if a.out else repo_data.ROOT / "outputs" / "generated"
    figs = Path(a.figs).expanduser().resolve() if a.figs else repo_data.ROOT / "outputs" / "figs"
    out.mkdir(parents=True, exist_ok=True); figs.mkdir(parents=True, exist_ok=True)
    man2, R2 = open_stage(2, not a.from_runs); man1, R1 = open_stage(1, not a.from_runs)
    p2 = repo_data.stage(2); p1 = repo_data.stage(1)
    pkg2, pkg1 = man2["analysis_package"], man1["analysis_package"]
    RUNS = {2: R2, 1: R1}
    bpath = p2 / "bundle_runs.csv"
    if sha16(bpath) != BUNDLE_SHA16: die("extension_stage/bundle_runs.csv does not carry the pinned hash")
    brun = load(bpath)

    banner = (f"%% GENERATED by tools/build_paper_sota.py -- DO NOT EDIT BY HAND.\n"
              f"%% Stage 2: {pkg2}; stage 1: {pkg1}; bundle runs.csv sha256[:16]={BUNDLE_SHA16}\n")
    M = [banner]
    def emit(n, v): M.append(f"\\newcommand{{\\{n}}}{{{v}}}")
    def tt(s): return r"\texttt{" + str(s).replace("_", r"\_") + "}"
    emit("paqTwoName", tt(pkg2)); emit("paqTwoBundle", tt(man2["bundle"]["name"])); emit("paqTwoRuns", str(man2["bundle"]["runs"]))
    emit("paqOneName", tt(pkg1)); emit("paqOneBundle", tt(man1["bundle"]["name"])); emit("paqOneRuns", str(man1["bundle"]["runs"]))
    emit("paqRunsTotal", str(man1["bundle"]["runs"] + man2["bundle"]["runs"]))
    blocks2 = sorted({r["bloque"] for r in R2}, key=lambda b: (list(CORPUS).index(b.split("/")[0]), list(BACK).index(b.split("/")[1])))
    blocks1 = sorted({r["bloque"] for r in R1}, key=lambda b: (list(CORPUS).index(b.split("/")[0]), list(BACK).index(b.split("/")[1])))
    BLK = {2: blocks2, 1: blocks1}
    emit("nBlocks", str(len(blocks2))); emit("nBlocksOne", str(len(blocks1)))
    emit("nArmsTwo", str(len({r["adapter"] for r in R2}))); emit("nArmsOne", str(len({r["adapter"] for r in R1})))
    emit("nCorpora", str(len({b.split("/")[0] for b in blocks2}))); emit("nCorporaOne", str(len({b.split("/")[0] for b in blocks1})))
    emit("nPartitions", str(len({r["split_seed"] for r in R2})))
    emit("nDatasets", str(len({r["dataset"] for r in R2}))); emit("nDatasetsOne", str(len({r["dataset"] for r in R1})))
    emit("nCellsOne", str(len({(r["bloque"], r["dataset"], r["split_seed"]) for r in R1 if r["adapter"] == "dfa"})))

    # ---- participants (stage-2 bundle, pinned) --------------------------------------------------
    per = {}; pos_all = []
    for r in brun:
        if r["rank"] == "8": per.setdefault(r["dataset"], {})[r["split_seed"]] = (int(r["n_classes"]), int(r["speaker_n_test"]), int(r["speaker_n_positive"]), int(r["n_test"]))
    for ds, d in per.items():
        key = ds.split("_")[0].capitalize() + ("A" if ds == "coperia_a" else "Cough" if ds == "coperia_cough" else "")
        nsp = sorted({v[1] for v in d.values()}); npos = sorted({v[2] for v in d.values()}); nrec = sorted({v[3] for v in d.values()})
        emit(f"{key}TestSpk", "/".join(map(str, nsp))); emit(f"{key}TestPos", "/".join(map(str, npos)))
        emit(f"{key}TestRec", str(nrec[0]) if len(nrec) == 1 else f"{nrec[0]}--{nrec[-1]}"); pos_all += npos
    emit("TestPosMin", str(min(pos_all))); emit("TestPosMax", str(max(pos_all)))

    # ---- analytic parameter counts, cross-checked against telemetry -----------------------------
    def tele(arm, col, rank="8"):
        v = [f(r[col]) for r in brun if r["adapter"] == arm and r["rank"] == rank and f(r[col]) is not None]
        return statistics.median(v) if v else None
    for arm in ("lora", "dora", "radial_lora_v3"):
        t = tele(arm, "trainable_params")
        if t is None or int(round(t)) - HEAD_PARAMS != PARAMS[arm]: die(f"analytic parameter count for {arm} ({PARAMS[arm]}) != telemetry {t} - head {HEAD_PARAMS}")
    print("validation: analytic parameter counts match the bundle telemetry (lora, dora, radial-lora)")
    for arm, n in PARAMS.items(): emit(f"{STEM[arm]}Params", thousands(n) if n else "0")
    emit("HeadParams", thousands(HEAD_PARAMS)); emit("LoraParamsWhisper", thousands(2 * 512 * R * 12)); emit("LdaCoefs", thousands((D + 1) * 2))

    # ---- per-arm statistics ---------------------------------------------------------------------
    def floor_rate(runs, arm, rank="8"):
        sel = [r for r in runs if (r["adapter"], r["rank"]) == (arm, rank)]
        k = sum(1 for r in sel if r["speaker_above_floor"] == "0"); return (k / len(sel) if sel else None), k, len(sel)
    def arm_stats(runs, arm, rank="8"):
        o = {}
        for met, ms in MET.items():
            bv = block_values(runs, arm, rank, met)
            if not bv: return None
            vals = [v[0] for v in bv.values()]; lo, hi = boot_ci(vals)
            o[ms] = (statistics.median(vals), lo, hi, statistics.median(v[1] for v in bv.values()), len(vals))
        return o
    S1ARMS = ["dfa", "dfa_last", "lora", "dora", "adalora_peft", "ia3", "hira", "radial_lora_v3", "wls_readout"]
    S2ARMS = ["dfa", "dfa_last", "lora", "dora", "radial_lora_v3", "lora_ln_dw", "lora_recipe"]
    STATS = {}; FLOOR = {}
    for arm in S1ARMS: STATS[(arm, 1)] = arm_stats(R1, arm); FLOOR[(arm, 1)] = floor_rate(R1, arm)
    for arm in S2ARMS: STATS[(arm, 2)] = arm_stats(R2, arm); FLOOR[(arm, 2)] = floor_rate(R2, arm)
    def S(arm): return STATS[(arm, STAGE_OF[arm])]
    def FL(arm): return FLOOR[(arm, STAGE_OF[arm])]
    for arm in sorted(set(S1ARMS) | set(S2ARMS)):
        s = S(arm)
        for ms in MET.values():
            med, lo, hi, sd, n = s[ms]
            emit(f"{STEM[arm]}{ms}Med", m3(med)); emit(f"{STEM[arm]}{ms}Lo", m3(lo)); emit(f"{STEM[arm]}{ms}Hi", m3(hi)); emit(f"{STEM[arm]}{ms}PartSd", f"{100*sd:.1f}")
        fr, k, n = FL(arm); emit(f"{STEM[arm]}Floor", f"{100*fr:.1f}"); emit(f"{STEM[arm]}FloorK", str(k)); emit(f"{STEM[arm]}FloorN", str(n))
        emit(f"{STEM[arm]}Blocks", str(s["Auroc"][4]))
    for arm in ("dfa", "dfa_last", "lora", "dora", "radial_lora_v3"):        # stage-1 values of the arms that ran in both
        s = STATS[(arm, 1)]
        for ms in MET.values(): emit(f"{STEM[arm]}One{ms}Med", m3(s[ms][0])); emit(f"{STEM[arm]}One{ms}Lo", m3(s[ms][1])); emit(f"{STEM[arm]}One{ms}Hi", m3(s[ms][2]))
        emit(f"{STEM[arm]}OneFloor", f"{100*FLOOR[(arm, 1)][0]:.1f}")
    dl = [r for r in R2 if r["adapter"] == "dfa" and r["speaker_above_floor"] == "0"]
    emit("DfaFloorWhere", ", ".join(sorted({DSNAME.get(r["dataset"], r["dataset"]) for r in dl})) or "none")
    pub_floor = {arm: FL(arm)[0] for arm in PUBLISHED}
    lo_arm = min(pub_floor, key=pub_floor.get); hi_arm = max(pub_floor, key=pub_floor.get)
    emit("PubFloorMin", f"{100*pub_floor[lo_arm]:.1f}"); emit("PubFloorMinArm", NAME[lo_arm]); emit("PubFloorMax", f"{100*pub_floor[hi_arm]:.1f}"); emit("PubFloorMaxArm", NAME[hi_arm])
    pub_sd = {arm: S(arm)["Auroc"][3] for arm in PUBLISHED}
    emit("PubPartSdMin", f"{100*min(pub_sd.values()):.1f}"); emit("PubPartSdMax", f"{100*max(pub_sd.values()):.1f}")
    ext_floor = {arm: FLOOR[(arm, 2)][0] for arm in ("lora", "dora", "radial_lora_v3")}
    emit("ExtFloorMin", f"{100*min(ext_floor.values()):.1f}"); emit("ExtFloorMax", f"{100*max(ext_floor.values()):.1f}")
    ext_sd = {arm: STATS[(arm, 2)]["Auroc"][3] for arm in ("lora", "dora", "radial_lora_v3")}
    emit("ExtPartSdMin", f"{100*min(ext_sd.values()):.1f}"); emit("ExtPartSdMax", f"{100*max(ext_sd.values()):.1f}")

    # ---- families -------------------------------------------------------------------------------
    def family(specs, tag):
        res = []
        for c, rv, st in specs:
            for met in MET:
                r = contrast(RUNS[st], c, "8", rv, "8", met); r.update(cand=c, rival=rv, met=met, stage=st); res.append(r)
        for r, q in zip(res, bh([r["p"] for r in res])):
            r["q"] = q; s = f"{tag}{STEM[r['cand']]}Vs{STEM[r['rival']]}{MET[r['met']]}"
            emit(s + "D", pp(r["delta"])); emit(s + "Q", q3(q)); emit(s + "P", q3(r["p"])); emit(s + "Fav", str(r["fav"])); emit(s + "N", str(r["n"])); emit(s + "Mde", pp(r["mde"], signed=False))
        emit(f"{tag}FamilyM", str(len(res))); emit(f"{tag}NSig", str(sum(1 for r in res if r["q"] < 0.05 and r["delta"] > 0)))
        emit(f"{tag}NSigAgainst", str(sum(1 for r in res if r["q"] < 0.05 and r["delta"] < 0)))
        return res
    def get(fam, c, rv, met): return next(x for x in fam if (x["cand"], x["rival"], x["met"]) == (c, rv, met))
    def dq(r): d, q = sig(r["delta"], r["q"]); return f"{d} ({q})"
    S1F = family([("dfa", rv, 1) for rv in PUBLISHED + ["radial_lora_v3"]], "s")                 # screening: dfa vs every method
    K1F = family([(rv, "lora", 1) for rv in PUBLISHED + ["radial_lora_v3"] if rv != "lora"], "k")  # screening: method vs LoRA
    A = family([("dfa", rv, 2) for rv in EXT], "a")                                              # extension: dfa vs survivors
    E = family([(rv, "lora", 2) for rv in EXT if rv != "lora"], "e")                            # extension: survivors vs LoRA
    C = family([("dfa", "dfa_last", 2)], "c")                                                    # depth ablation
    Rf = family([("lora_ln_dw", "lora", 2), ("lora_recipe", "lora", 2), ("dfa", "lora_ln_dw", 2), ("dfa", "lora_recipe", 2),
                 ("wls_readout", "lora", 1), ("dfa", "wls_readout", 1)], "r")                      # readout-factor controls
    Dc = family([("dfa_last", "lora", 2), ("dfa_last", "dora", 2)], "d")
    P = family([("dfa_lora_anchor", "dfa", 2), ("dfa_lora_ns", "dfa", 2), ("dfa", "full_ft", 2), ("lora", "full_ft", 2)], "p")
    ALLFAM = [("Screening stage: \\textsc{dfa} $-$ method", S1F), ("Screening stage: method $-$ LoRA", K1F),
              ("Extension stage: \\textsc{dfa} $-$ method", A), ("Extension stage: method $-$ LoRA", E),
              ("Depth ablation", C), ("Readout-factor controls", Rf), ("Depth control against published methods", Dc),
              ("Additional arms", P)]
    # Export the unrounded evidence behind the paper, independently of its TeX views.
    data = Path(a.data).resolve() if a.data else out.parent / "data"
    data.mkdir(parents=True, exist_ok=True)
    contrast_rows = [["family", "family_m", "stage", "candidate", "rival", "endpoint", "delta", "p", "q", "blocks", "favourable", "mde"]]
    delta_rows = [["family", "stage", "candidate", "rival", "endpoint", "block", "mean_paired_difference", "paired_observations"]]
    for title, members in ALLFAM:
        for result in members:
            contrast_rows.append([title, len(members), result["stage"], result["cand"], result["rival"], result["met"], result["delta"], result["p"], result["q"], result["n"], result["fav"], result["mde"]])
            for block, value in zip(result["blocks"], result["deltas"]):
                delta_rows.append([title, result["stage"], result["cand"], result["rival"], result["met"], block, value, len(result["cells"][block])])
    write_csv(data / "paired_contrasts.csv", contrast_rows)
    write_csv(data / "block_differences.csv", delta_rows)
    inventory = [["stage", "adapter", "rank", "runs", "blocks", "median_block_auroc", "median_block_macro_f1", "below_floor_runs"]]
    for stage, runs in sorted(RUNS.items()):
        for arm, rank in sorted({(row["adapter"], row["rank"]) for row in runs}):
            selected = [row for row in runs if (row["adapter"], row["rank"]) == (arm, rank)]
            values = [block_values(runs, arm, rank, metric) for metric in MET]
            inventory.append([stage, arm, rank, len(selected), len(values[0]), *[statistics.median(v[0] for v in by_block.values()) for by_block in values], sum(row["speaker_above_floor"] == "0" for row in selected)])
    write_csv(data / "all_arms_by_rank.csv", inventory)

    for arm in ("lora", "dora"):
        for met, ms in MET.items():
            r = contrast(R2, arm, "512", arm, "8", met)
            emit(f"{STEM[arm]}RankGain{ms}D", pp(r["delta"])); emit(f"{STEM[arm]}RankGain{ms}P", q3(r["p"])); emit(f"{STEM[arm]}RankGain{ms}Fav", str(r["fav"])); emit(f"{STEM[arm]}RankGain{ms}Mde", pp(r["mde"], signed=False))
    for rv in ("lora", "dora"):
        for met, ms in MET.items():
            r = contrast(R2, "dfa", "8", rv, "512", met)
            emit(f"xDfaVs{STEM[rv]}Rhigh{ms}D", pp(r["delta"])); emit(f"xDfaVs{STEM[rv]}Rhigh{ms}P", q3(r["p"])); emit(f"xDfaVs{STEM[rv]}Rhigh{ms}Fav", str(r["fav"])); emit(f"xDfaVs{STEM[rv]}Rhigh{ms}Mde", pp(r["mde"], signed=False))

    # ---- Table: screening stage, performance ----------------------------------------------------
    def perf_table(arms, stage, fname, label, caption):
        best = {ms: max(STATS[(a, stage)][ms][0] for a in arms) for ms in MET.values()}
        rows = []
        for arm in arms:
            st_ = STATS[(arm, stage)]; cells = []
            for ms in ("Auroc", "MacroF"):
                med, lo, hi, sd, n = st_[ms]; txt = (r"\textbf{" + f"{med:.3f}" + "}") if abs(med - best[ms]) < 1e-9 else f"{med:.3f}"
                cells.append(f"{txt} [{lo:.3f}, {hi:.3f}]")
            fr = FLOOR[(arm, stage)][0]; cells.append("\\textbf{0.0\\%}" if fr == 0 else f"{100*fr:.1f}\\%")
            rows.append(f"{LABEL.get(arm, NAME[arm])} & " + " & ".join(cells) + r" \\")
        (out / fname).write_text(banner + r"""
\begin{table}[!t]
\centering
\caption{""" + caption + r"""}
\label{""" + label + r"""}
\footnotesize
\setlength{\tabcolsep}{4pt}
\fitwidth{\begin{tabular}{lccc}
\toprule
Arm & Speaker AUROC [95\% CI] & Speaker macro-F1 [95\% CI] & Below floor \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}}
\end{table}
""")
    perf_table(["dfa", "dfa_last", "lora", "dora", "adalora_peft", "ia3", "hira", "radial_lora_v3"], 1, "sota_tab_screen_perf.tex", "tab:screen_perf",
               r"Screening stage (four corpora, $B{=}$\nBlocksOne{} blocks): speaker-level performance at rank~8, median over blocks with descriptive bootstrap 95\% intervals, and share of runs below the majority-class floor. Bold: best of the column.")
    perf_table(["dfa", "dfa_last", "lora", "dora", "radial_lora_v3"], 2, "sota_tab_perarm.tex", "tab:sota_perarm",
               r"Extension stage (seven corpora, $B{=}$\nBlocks{} blocks): speaker-level performance at rank~8, median over blocks with descriptive bootstrap 95\% intervals, and share of runs below the majority-class floor. Bold: best of the column.")

    # ---- Table: screening stage, contrasts ------------------------------------------------------
    rows = []
    for rv in ["lora", "dora", "adalora_peft", "ia3", "hira", "radial_lora_v3"]:
        k = ["--", "--"] if rv == "lora" else [dq(get(K1F, rv, "lora", met)) for met in MET]
        d_ = [dq(get(S1F, "dfa", rv, met)) for met in MET]
        rows.append(f"{rk(rv)} & {k[0]} & {k[1]} & {d_[0]} & {d_[1]} \\\\")
    (out / "sota_tab_screen.tex").write_text(banner + r"""
\begin{table}[!t]
\centering
\caption{Screening stage: paired contrasts on the \nBlocksOne{} blocks, in percentage points with Benjamini--Hochberg $q$ in parentheses (families of $m{=}$\kFamilyM{} and \sFamilyM{}). Bold: $q<0.05$.}
\label{tab:screen}
\footnotesize
\setlength{\tabcolsep}{4pt}
\fitwidth{\begin{tabular}{lcccc}
\toprule
 & \multicolumn{2}{c}{Method $-$ LoRA} & \multicolumn{2}{c}{\textsc{dfa} $-$ method} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}
Method & AUROC & macro-F1 & AUROC & macro-F1 \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}}
\end{table}
""")

    # ---- Table: extension stage, contrasts -------------------------------------------------------
    rows = [r"\addlinespace[2pt]\multicolumn{7}{l}{\emph{\textsc{dfa} $-$ method}}\\[1pt]"]
    for rv in EXT:
        cells = []
        for met in MET:
            r = get(A, "dfa", rv, met); d, q = sig(r["delta"], r["q"]); cells.append(f"{d} & {q} & {r['fav']}/{r['n']}")
        rows.append(f"\\quad {rk(rv)} & " + " & ".join(cells) + r" \\")
    rows.append(r"\addlinespace[2pt]\multicolumn{7}{l}{\emph{Method $-$ LoRA}}\\[1pt]")
    for rv in EXT[1:]:
        cells = []
        for met in MET:
            r = get(E, rv, "lora", met); d, q = sig(r["delta"], r["q"]); cells.append(f"{d} & {q} & {r['fav']}/{r['n']}")
        rows.append(f"\\quad {rk(rv)} & " + " & ".join(cells) + r" \\")
    (out / "sota_tab_contrasts.tex").write_text(banner + r"""
\begin{table}[!t]
\centering
\caption{Extension stage: pre-specified paired contrasts on the \nBlocks{} corpus-unit $\times$ backbone blocks, in percentage points with Benjamini--Hochberg $q$ within each family ($m{=}$\aFamilyM{} and \eFamilyM{}) and the number of blocks in which the first arm is better. Bold: $q<0.05$. Minimum detectable effects: Supplementary Table~S9.}
\label{tab:sota_contrasts}
\footnotesize
\setlength{\tabcolsep}{4pt}
\fitwidth{\begin{tabular}{lrrcrrc}
\toprule
 & \multicolumn{3}{c}{AUROC} & \multicolumn{3}{c}{macro-F1} \\
\cmidrule(lr){2-4}\cmidrule(lr){5-7}
Contrast & $\Delta$ & $q$ & Blocks & $\Delta$ & $q$ & Blocks \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}}
\end{table}
""")

    # ---- Table: readout-factor controls ---------------------------------------------------------
    lines = []
    for arm in ("lora_ln_dw", "lora_recipe", "wls_readout"):
        st = STAGE_OF[arm]; s_ = STATS[(arm, st)]; fr = FLOOR[(arm, st)][0]
        med, lo, hi, sd, n = s_["Auroc"]; medf = s_["MacroF"][0]
        cells = [str(st), f"{med:.3f} [{lo:.3f}, {hi:.3f}]", f"{medf:.3f}", ("\\textbf{0.0\\%}" if fr == 0 else f"{100*fr:.1f}\\%"),
                 dq(get(Rf, arm, "lora", "speaker_auroc")), dq(get(Rf, "dfa", arm, "speaker_auroc"))]
        lines.append(f"{NAME[arm]} & " + " & ".join(cells) + r" \\")
    (out / "sota_tab_controls.tex").write_text(banner + r"""
\begin{table*}[!t]
\centering
\caption{Readout controls at rank~8: speaker AUROC (median over blocks with descriptive bootstrap 95\% intervals), median macro-F1, below-floor rate, and paired AUROC contrasts against LoRA and against \textsc{dfa} (percentage points, $q$ over the family of $m{=}$\rFamilyM{}). Bold: $q<0.05$.}
\label{tab:sota_controls}
\footnotesize
\setlength{\tabcolsep}{4pt}
\fitwidth{\begin{tabular}{lcccccc}
\toprule
Control & Stage & AUROC [95\% CI] & macro-F1 & Below floor & Control $-$ LoRA & \textsc{dfa} $-$ control \\
\midrule
""" + "\n".join(lines) + r"""
\bottomrule
\end{tabular}}
\end{table*}
""")

    # ---- Table: material regimes (exploratory) -------------------------------------------------
    lines = []
    for key, label, corpora in REGIME:
        rivals = [("lora", 2), ("dora", 2), ("radial_lora_v3", 2)] + ([("adalora_peft", 1), ("ia3", 1), ("hira", 1)] if key == "speech" else [])
        first = True
        for rv, st in rivals:
            cells = []
            for met, ms in MET.items():
                r = contrast(RUNS[st], "dfa", "8", rv, "8", met, corpora=corpora)
                emit(f"g{RSTEM[key]}{STEM[rv]}{ms}D", pp(r["delta"])); emit(f"g{RSTEM[key]}{STEM[rv]}{ms}P", q3(r["p"])); emit(f"g{RSTEM[key]}{STEM[rv]}{ms}Fav", str(r["fav"])); emit(f"g{RSTEM[key]}{STEM[rv]}{ms}N", str(r["n"]))
                testable = (not math.isnan(r["p"])) and 2.0 ** (1 - r["n"]) <= 0.05
                ptxt = "--" if not testable else q3(r["p"])
                dtxt = ("$\\mathbf{" + pp(r["delta"]) + "}$") if (testable and r["p"] < 0.05) else f"${pp(r['delta'])}$"
                cells.append(f"{dtxt} ({ptxt}) & {r['fav']}/{r['n']}")
            reg = label if first else ""; first = False
            lines.append(f"{reg} & {rk(rv)} & " + " & ".join(cells) + r" \\")
        lines.append(r"\addlinespace[2pt]")
    (out / "sota_tab_regime.tex").write_text(banner + r"""
\begin{table}[!t]
\centering
\caption{Exploratory breakdown by elicited material: \textsc{dfa} $-$ method in percentage points, with the unadjusted exact Wilcoxon $p$ in parentheses (shown only where six or more blocks make a test possible) and blocks in favour. Bold: $p<0.05$.}
\label{tab:sota_regime}
\footnotesize
\setlength{\tabcolsep}{4pt}
\fitwidth{\begin{tabular}{llcccc}
\toprule
 & & \multicolumn{2}{c}{AUROC} & \multicolumn{2}{c}{macro-F1} \\
\cmidrule(lr){3-4}\cmidrule(lr){5-6}
Material & \textsc{dfa} versus & $\Delta$ ($p$) & Blocks & $\Delta$ ($p$) & Blocks \\
\midrule
""" + "\n".join(lines) + r"""
\bottomrule
\end{tabular}}
\end{table}
""")

    # ---- cross-stage determinism ----------------------------------------------------------------
    def cells_of(runs, arm):
        return {(r["dataset"], r["model"], r["split_seed"]): (r["speaker_auroc"], r["speaker_macro_f1"]) for r in runs if r["adapter"] == arm and r["rank"] == "8"}
    xrows = []
    for arm in ("dfa", "dfa_last", "lora", "dora", "radial_lora_v3"):
        a1, a2 = cells_of(R1, arm), cells_of(R2, arm); shared = sorted(set(a1) & set(a2))
        same = sum(1 for k in shared if a1[k] == a2[k]); diffs = [abs(float(a1[k][0]) - float(a2[k][0])) * 100 for k in shared]
        emit(f"x{STEM[arm]}Shared", str(len(shared))); emit(f"x{STEM[arm]}Ident", str(same))
        emit(f"x{STEM[arm]}MedAbs", f"{statistics.median(diffs):.1f}"); emit(f"x{STEM[arm]}MaxAbs", f"{max(diffs):.1f}")
        xrows.append(f"{NAME[arm]} & {len(shared)} & {same} & {statistics.median(diffs):.1f} & {max(diffs):.1f} \\\\")
    (out / "supps_tab_stages.tex").write_text(banner + r"""
\begin{table}[!t]
\centering
\caption{Reproducibility of the full pipeline across the two stages. Each arm was run in both stages on the same 36 cells (four corpora $\times$ three backbones $\times$ three partitions, identical partition and optimisation seeds); the gradient arms were relaunched with a fresh learning-rate search (6 trials per cell in stage 1, 12 in stage 2). Identical: cells whose speaker AUROC and macro-F1 agree to every printed digit; $|\Delta|$: absolute per-cell difference in speaker AUROC, percentage points.}
\label{tab:supps_stages}
\footnotesize
\begin{tabular}{lrrrr}
\toprule
Arm & Shared cells & Identical & Median $|\Delta|$ & Max $|\Delta|$ \\
\midrule
""" + "\n".join(xrows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")

    # ---- cost at rank 8 (stage-2 bundle telemetry) ----------------------------------------------
    COST = {}
    for arm in ("dfa", "dfa_last", "lora", "dora", "radial_lora_v3", "full_ft", "dfa_lora_anchor", "dfa_lora_ns"):
        t, v, i = tele(arm, "train_runtime_s"), tele(arm, "vram_peak_gb"), tele(arm, "infer_samples_per_s"); COST[arm] = (t, v, i)
        emit(f"{STEM[arm]}TrainS", "--" if t is None else f"{t:.0f}"); emit(f"{STEM[arm]}Vram", "--" if v is None else f"{v:.2f}")
        emit(f"{STEM[arm]}InferSps", "--" if i is None else f"{i:.0f}")
    grad = {arm: COST[arm][0] for arm in ("lora", "dora", "radial_lora_v3")}
    emit("DfaTrainSavingMin", f"{100*(1 - COST['dfa'][0]/min(grad.values())):.0f}")
    emit("DfaTrainSavingMax", f"{100*(1 - COST['dfa'][0]/max(grad.values())):.0f}")
    emit("GradFastestArm", NAME[min(grad, key=grad.get)]); emit("GradSlowestArm", NAME[max(grad, key=grad.get)])
    emit("VramMin", f"{min(COST[a][1] for a in ('dfa','lora','dora','radial_lora_v3')):.1f}"); emit("VramMax", f"{max(COST[a][1] for a in ('dfa','lora','dora','radial_lora_v3')):.1f}")
    lines = []
    for arm in ("dfa", "lora", "dora", "radial_lora_v3"):
        t, v, _ = COST[arm]; fr = FL(arm)[0]; sd = S(arm)["Auroc"][3]
        params = thousands(PARAMS[arm]) if PARAMS[arm] else "0$^{a}$"
        lines.append(f"{rk(arm)} & {params} & {t:.0f} & {'0.0' if fr == 0 else f'{100*fr:.1f}'}\\% & {100*sd:.1f} \\\\")
    (out / "sota_tab_cost.tex").write_text(banner + r"""
\begin{table}[!t]
\centering
\caption{Cost and reliability at rank~8 on the seven corpora: the method's own trainable parameters (768-dimensional encoders), median training time of the selected run (the learning-rate search that precedes every gradient run is not included), share of runs below the majority-class floor, and median within-block standard deviation of speaker AUROC across the three data partitions.}
\label{tab:sota_cost}
\footnotesize
\setlength{\tabcolsep}{5pt}
\fitwidth{\begin{tabular}{lrrrr}
\toprule
Arm & Trainable params & Training (s) & Below floor & Partition SD (pp) \\
\midrule
""" + "\n".join(lines) + r"""
\bottomrule
\end{tabular}}

\vspace{2pt}
{\footnotesize $^{a}$ No gradient-trained parameter; the discriminant's \LdaCoefs{} coefficients are fitted in closed form. Every gradient-trained arm also trains the classification head (\HeadParams{} parameters).}
\end{table}
""")

    # ---- per-corpus breakdown (stage 2) ---------------------------------------------------------
    d = contrast(R2, "dfa", "8", "lora", "8", "speaker_auroc"); perc = defaultdict(list)
    for b, v in zip(d["blocks"], d["deltas"]): perc[b.split("/")[0]].append(100 * v)
    absv = {arm: block_values(R2, arm, "8", "speaker_auroc") for arm in ("dfa", "lora")}
    lines = []
    for c in sorted(perc, key=lambda c: -statistics.median(perc[c])):
        med = lambda Dd: statistics.median(v[0] for k, v in Dd.items() if k.split("/")[0] == c)
        dm = statistics.median(perc[c]); fav = sum(1 for v in perc[c] if v > 0)
        rng = f"{min(perc[c]):+.1f} to {max(perc[c]):+.1f}"
        lines.append(f"{CORPUS[c]} & {KIND[c]} & {med(absv['dfa']):.3f} & {med(absv['lora']):.3f} & ${dm:+.1f}$ ({rng}) & {fav}/{len(perc[c])} \\\\")
        emit(f"corp{c.split('_')[0].capitalize()}DfaMinusLora", f"{dm:+.1f}"); emit(f"corp{c.split('_')[0].capitalize()}Fav", str(fav))
    (out / "sota_tab_corpus.tex").write_text(banner + r"""
\begin{table}[!t]
\centering
\caption{The \textsc{dfa}--LoRA difference by corpus units (speaker AUROC, rank~8): block medians over the three backbones, and the median paired difference with its range across backbones. $\Delta$ is a median of paired differences, not the difference of the two medians.}
\label{tab:sota_corpus}
\footnotesize
\setlength{\tabcolsep}{4pt}
\fitwidth{\begin{tabular}{llcccc}
\toprule
Corpus & Material & \textsc{dfa} & LoRA & $\Delta$ (range), pp & Backbones for \\
\midrule
""" + "\n".join(lines) + r"""
\bottomrule
\end{tabular}}
\end{table}
""")

    # ---- figures --------------------------------------------------------------------------------
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.linewidth": 0.6, "pdf.fonttype": 42})

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 7.6), gridspec_kw={"height_ratios": [18, 12.5]})
    fig_data = [["stage", "block", "method", "endpoint", "delta_pp", "partition_min_pp", "partition_max_pp"]]   # what the figure draws
    ROWS = [(2, [("lora", "o", True), ("dora", "o", False)]), (1, [("adalora_peft", "s", True), ("ia3", "^", True), ("hira", "D", True)])]
    for (st, rivals), axrow in zip(ROWS, axes):
        blocks = BLK[st]; y = np.arange(len(blocks))[::-1]
        res = {(rv, met): contrast(RUNS[st], "dfa", "8", rv, "8", met) for rv, _, _ in rivals for met in MET}
        allv = [100 * v for r in res.values() for cells in r["cells"].values() for v in cells]
        lo, hi = min(allv) - 2, max(allv) + 2
        for ax, met, title in zip(axrow, MET, ("Speaker AUROC", "Speaker macro-F1")):
            ax.axvspan(0, hi + 5, color="#315f9e", alpha=0.05, lw=0, zorder=0); ax.axvline(0, color="#5b6577", lw=0.8)
            for yi, b in zip(y, blocks):
                c = PAL[b.split("/")[0]]
                for j, (rv, mk, filled) in enumerate(rivals):
                    r = res[(rv, met)]; cells = [100 * v for v in r["cells"][b]]; dd = 100 * dict(zip(r["blocks"], r["deltas"]))[b]
                    yy = yi + (j - (len(rivals) - 1) / 2) * 0.22
                    fig_data.append([STAGE_DIR[st], b, rv, met, f"{dd:.6f}", f"{min(cells):.6f}", f"{max(cells):.6f}"])
                    ax.plot([min(cells), max(cells)], [yy, yy], color=c, lw=0.9, alpha=0.6, zorder=2, solid_capstyle="butt")
                    if filled: ax.plot(dd, yy, mk, ms=4.6, color=c, mec="white", mew=0.6, zorder=3)
                    else: ax.plot(dd, yy, mk, ms=4.6, mfc="white", mec=c, mew=1.2, zorder=3)
            stage_name = "extension stage" if st == 2 else "screening stage"
            ax.set_xlim(lo, hi); ax.set_title(f"{title}, {stage_name} ($B$={len(blocks)})", fontsize=9.0, loc="left")
            ax.set_xlabel(r"$\Delta$ = dfa $-$ method (pp); shaded: $\Delta>0$")
            ax.grid(axis="x", color="#e3e7ee", lw=0.5); ax.set_axisbelow(True)
            for sp in ("top", "right"): ax.spines[sp].set_visible(False)
            if st == 2: emit(f"DfaVsLora{MET[met]}BlocksFor", str(res[("lora", met)]["fav"])); emit(f"DfaVsDora{MET[met]}BlocksFor", str(res[("dora", met)]["fav"]))
        axrow[0].set_yticks(y); axrow[0].set_yticklabels([f"{CORPUS[b.split('/')[0]]} / {BACK[b.split('/')[1]].replace('~', ' ')}" for b in blocks], fontsize=7.3)
        axrow[1].set_yticks(y); axrow[1].set_yticklabels([])
    handles = [Line2D([], [], marker="o", ls="", color="#5b6577", mec="white", ms=4.6, label="top row: dfa $-$ LoRA"),
               Line2D([], [], marker="o", ls="", mfc="white", mec="#5b6577", mew=1.2, ms=4.6, label="top row: dfa $-$ DoRA"),
               Line2D([], [], marker="s", ls="", color="#5b6577", mec="white", ms=4.6, label="bottom row: dfa $-$ AdaLoRA"),
               Line2D([], [], marker="^", ls="", color="#5b6577", mec="white", ms=4.6, label="bottom row: dfa $-$ IA$^3$"),
               Line2D([], [], marker="D", ls="", color="#5b6577", mec="white", ms=4.6, label="bottom row: dfa $-$ HiRA"),
               Line2D([], [], ls="-", color="#5b6577", lw=0.9, label="range over the block's partitions")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(w_pad=1.2, h_pad=1.6, rect=(0, 0.055, 1, 1)); fig.savefig(figs / "fig_blocks.pdf", metadata={"CreationDate": None, "ModDate": None}); plt.close(fig)
    write_csv(figs / "fig_blocks_data.csv", fig_data)

    curve = {}
    for arm in ("lora", "dora"):
        for rank in ("8", "256", "512"):
            for met, ms in MET.items():
                vals = [v[0] for v in block_values(R2, arm, rank, met).values()]
                curve[(arm, rank, ms)] = (statistics.median(vals), float(np.percentile(vals, 25)), float(np.percentile(vals, 75)))
                emit(f"{stem(arm, rank)}{ms}MedR", m3(curve[(arm, rank, ms)][0]))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    fig_data = [["series", "rank", "endpoint", "median", "q25", "q75"]]
    for (arm, rank, ms), (md, lo_q, hi_q) in sorted(curve.items()):
        fig_data.append([arm, rank, ms, f"{md:.6f}", f"{lo_q:.6f}", f"{hi_q:.6f}"])
    COL = {"lora": "#c2410c", "dora": "#7c3aed"}; ranks = ["8", "256", "512"]
    for ax, (met, ms), lab in zip(axes, MET.items(), ("Speaker AUROC", "Speaker macro-F1")):
        for j, arm in enumerate(("lora", "dora")):
            xs = [i + (j - 0.5) * 0.18 for i in range(3)]
            med = [curve[(arm, r, ms)][0] for r in ranks]
            lo = [curve[(arm, r, ms)][0] - curve[(arm, r, ms)][1] for r in ranks]; hi = [curve[(arm, r, ms)][2] - curve[(arm, r, ms)][0] for r in ranks]
            ax.errorbar(xs, med, yerr=[lo, hi], fmt="o", color=COL[arm], ms=5, capsize=2.5, lw=1.0, label=NAME[arm])
        dmed = statistics.median(v[0] for v in block_values(R2, "dfa", "8", met).values())
        ftm = statistics.median(v[0] for v in block_values(R2, "full_ft", "8", met).values())
        fig_data += [["dfa", "", ms, f"{dmed:.6f}", "", ""], ["full_ft", "", ms, f"{ftm:.6f}", "", ""]]
        ax.axhline(dmed, color="#315f9e", lw=1.5, label="dfa (closed form, no rank)")
        ax.axhline(ftm, color="#5b6577", lw=1.0, ls=(0, (3, 2)), label="full fine-tuning")
        ax.set_xticks(range(3)); ax.set_xticklabels(ranks); ax.set_xlim(-0.5, 2.5)
        ax.set_xlabel("adapter rank $r$"); ax.set_title(lab, fontsize=9.5, loc="left")
        ax.grid(axis="y", color="#e3e7ee", lw=0.5); ax.set_axisbelow(True)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(w_pad=1.5, rect=(0, 0.1, 1, 1)); fig.savefig(figs / "fig_rank_curve.pdf", metadata={"CreationDate": None, "ModDate": None}); plt.close(fig)
    write_csv(figs / "fig_rank_curve_data.csv", fig_data)

    # ---- supplement: every arm of each stage, with the package's own confirmatory contrasts ----
    def all_arms_table(pkg, runs, label, capnote):
        res7 = {r["brazo"]: r for r in load(pkg / "arm_summary.csv")}
        pol = [r for r in load(pkg / "analysis_policies.csv") if r["estatus"] == "CONFIRMATORIA"]
        by = {(r["brazo"], r["rival"], r["metrica"]): r for r in pol}; fam = pol[0]["familia_m"] if pol else "?"
        emit(f"pkgFamily{'Two' if label == 'two' else 'One'}", str(fam))
        lines = []
        for arm in sorted(res7, key=lambda b: -(f(res7[b]["speaker_auroc__bloque_mediana"]) or 0)):
            r = res7[arm]
            sel = [x for x in runs if x["adapter"] == arm]; frall = sum(1 for x in sel if x["speaker_above_floor"] == "0") / len(sel)
            cells = [f"{f(r['speaker_auroc__bloque_mediana']):.3f}", f"{f(r['speaker_macro_f1__bloque_mediana']):.3f}", f"{100*frall:.1f}\\%"]
            for rv in ("lora", "dora"):
                for met in MET:
                    x = by.get((arm, rv, met))
                    if x is None: cells.append("--"); continue
                    dd, qq = sig(f(x["delta"]), f(x["q"])); cells.append(f"{dd} ({qq})")
            name = NAME.get(arm) or (r"\textsc{" + arm.replace("_", "-") + "}")
            lines.append(f"{name} & {SITE.get(arm, r['locus'].replace('_', ' '))} & " + " & ".join(cells) + r" \\")
        nb = len({r["bloque"] for r in runs}); na = len({r["adapter"] for r in runs})
        (out / f"supps_tab_all_{label}.tex").write_text(banner + rf"""
\begin{{table*}}[!t]
\centering
\caption{{Every arm of the {'extension' if label == 'two' else 'screening'} stage ({na} arms, $B{{=}}{nb}$ blocks; arms pooled over their ranks as in the package): block-median speaker AUROC and macro-F1, below-floor rate, and the package's own confirmatory contrasts against LoRA and DoRA (percentage points, Benjamini--Hochberg $q$ in parentheses over the package's family of $m{{=}}{fam}$, larger than the main-text families and therefore giving larger $q$ for the same difference). Bold: significant in favour of the arm at $q<0.05$. {capnote}}}
\label{{tab:supps_all_{label}}}
\scriptsize
\setlength{{\tabcolsep}}{{3pt}}
\fitwidth{{\begin{{tabular}}{{llcccrrrr}}
\toprule
 & & & & & \multicolumn{{2}}{{c}}{{vs LoRA, $\Delta$ ($q$)}} & \multicolumn{{2}}{{c}}{{vs DoRA, $\Delta$ ($q$)}} \\
\cmidrule(lr){{6-7}}\cmidrule(lr){{8-9}}
Arm & Site & AUROC & macro-F1 & Below floor & AUROC & macro-F1 & AUROC & macro-F1 \\
\midrule
""" + "\n".join(lines) + r"""
\bottomrule
\end{tabular}}
\end{table*}
""")
    if not a.from_runs:
        all_arms_table(p2, R2, "two", r"The in-house variants (\textsc{lora-ln}, \textsc{lora-ln-dw}, \textsc{lora-recipe}, \textsc{dfa-sph}, the anchored hybrids and the unanchored \textsc{dfa-lora}) and full fine-tuning are reported here only; \textsc{lora-ln-dw} and \textsc{lora-recipe} are the readout-factor controls of the main text.")
        all_arms_table(p1, R1, "one", r"The screening stage ran every arm of the programme, including the readout controls \textsc{wls-readout} (SUPERB weighted layer sum, gradient-trained head) and \textsc{cov-readout} (last-layer covariance features, gradient-trained head).")
    else:
        # Family sizes are counts of available arms, not archived statistical values.
        emit("pkgFamilyTwo", str(4 * (len({row["adapter"] for row in R2}) - 1)))
        emit("pkgFamilyOne", str(4 * (len({row["adapter"] for row in R1}) - 1)))

    # ---- supplement: per-block values ----------------------------------------------------------
    def blocks_table(runs, blocks, arms, label, stage):
        for met, ms in MET.items():
            vals = {ar: block_values(runs, ar[0], ar[1], met) for ar in arms}; lines = []
            for b in blocks:
                bestv = max(vals[ar][b][0] for ar in arms)
                cells = " & ".join((r"\textbf{" + f"{vals[ar][b][0]:.3f}" + "}") if abs(vals[ar][b][0] - bestv) < 1e-9 else f"{vals[ar][b][0]:.3f}" for ar in arms)
                lines.append(f"{CORPUS[b.split('/')[0]]} & {BACK[b.split('/')[1]]} & {cells} \\\\")
            head = " & ".join(rk(a, r) for a, r in arms)
            (out / f"supps_tab_blocks_{label}_{ms.lower()}.tex").write_text(banner + rf"""
\begin{{table*}}[!t]
\centering
\caption{{Speaker {'AUROC' if ms == 'Auroc' else 'macro-F1'} per corpus$\times$backbone block in the {stage} stage (mean over the three speaker-disjoint partitions; each value is one of the block values on which the tests operate). Bold: best arm in the row.}}
\label{{tab:supps_blocks_{label}_{ms.lower()}}}
\scriptsize
\setlength{{\tabcolsep}}{{3pt}}
\fitwidth{{\begin{{tabular}}{{ll{'c' * len(arms)}}}
\toprule
Corpus & Backbone & {head} \\
\midrule
""" + "\n".join(lines) + r"""
\bottomrule
\end{tabular}}
\end{table*}
""")
    blocks_table(R2, blocks2, [("dfa", "8"), ("dfa_last", "8"), ("lora", "8"), ("dora", "8"), ("radial_lora_v3", "8"), ("lora_ln_dw", "8"), ("lora_recipe", "8"), ("lora", "512"), ("dora", "512"), ("full_ft", "8"), ("dfa_lora_anchor", "8"), ("dfa_lora_ns", "8")], "two", "extension")
    blocks_table(R1, blocks1, [("dfa", "8"), ("dfa_last", "8"), ("lora", "8"), ("dora", "8"), ("adalora_peft", "8"), ("ia3", "8"), ("hira", "8"), ("radial_lora_v3", "8"), ("wls_readout", "8")], "one", "screening")

    # ---- supplement: additional arms of stage 2 -----------------------------------------------
    extra = []
    for arm, rank in (("full_ft", "8"), ("lora", "256"), ("lora", "512"), ("dora", "256"), ("dora", "512"), ("dfa_lora_anchor", "8"), ("dfa_lora_ns", "8")):
        s_ = arm_stats(R2, arm, rank); fr, k, n = floor_rate(R2, arm, rank)
        t, v = tele(arm, "train_runtime_s", rank), tele(arm, "vram_peak_gb", rank)
        emit(f"{stem(arm, rank)}Floor", f"{100*fr:.1f}")
        if arm == "full_ft":
            for ms in MET.values(): emit(f"FullFt{ms}Med", m3(s_[ms][0]))
        extra.append(f"{rk(arm, rank)} & {s_['Auroc'][0]:.3f} [{s_['Auroc'][1]:.3f}, {s_['Auroc'][2]:.3f}] & {s_['MacroF'][0]:.3f} [{s_['MacroF'][1]:.3f}, {s_['MacroF'][2]:.3f}] & {100*fr:.1f}\\% & {'--' if t is None else f'{t:.0f}'} & {'--' if v is None else f'{v:.2f}'} \\\\")
    (out / "supps_tab_extra.tex").write_text(banner + r"""
\begin{table*}[!t]
\centering
\caption{Arms of the extension stage outside the main comparison ($B{=}$\nBlocks{} blocks): full fine-tuning of all encoder weights, LoRA and DoRA at ranks 256 and 512, and two anchored hybrids (LoRA branches trained beneath the closed-form \textsc{dfa} head, with the frozen readout competing on validation; \textsc{dfa-lora-anchor} adds a spherical projection of the head's input, \textsc{dfa-lora-ns} does not). Median block value with bootstrap 95\% CI, below-floor rate, and per-run median training time (selected run, excluding the search) and peak memory.}
\label{tab:supps_extra}
\footnotesize
\setlength{\tabcolsep}{4pt}
\fitwidth{\begin{tabular}{lccrrr}
\toprule
Arm & Speaker AUROC [95\% CI] & Speaker macro-F1 [95\% CI] & Below floor & Training (s) & Peak VRAM (GB) \\
\midrule
""" + "\n".join(extra) + r"""
\bottomrule
\end{tabular}}
\end{table*}
""")

    # ---- supplement: full statistics of every main-text contrast --------------------------------
    rows = []
    for title, fam in ALLFAM:
        rows.append(r"\addlinespace[2pt]\multicolumn{12}{l}{\emph{" + title + f", $m{{=}}{len(fam)}$" + r"}}\\[1pt]")
        seen = []
        for r in fam:
            key = (r["cand"], r["rival"])
            if key in seen: continue
            seen.append(key); ra = get(fam, r["cand"], r["rival"], "speaker_auroc"); rf = get(fam, r["cand"], r["rival"], "speaker_macro_f1")
            cells = []
            for x in (ra, rf):
                d, q = sig(x["delta"], x["q"]); cells.append(f"{d} & {q3(x['p'])} & {q} & {x['fav']}/{x['n']} & {pp(x['mde'], signed=False)}")
            rows.append(f"\\quad {NAME[r['cand']]} $-$ {NAME[r['rival']]} & {r['stage']} & " + " & ".join(cells) + r" \\")
    (out / "supps_tab_stats.tex").write_text(banner + r"""
\begin{table*}[!t]
\centering
\caption{Full statistics of every paired contrast reported in the main text: median paired block difference (percentage points), exact two-sided Wilcoxon $p$, Benjamini--Hochberg $q$ within the family, blocks in which the first arm is better, and minimum detectable effect at 80\% power (n/a when fewer than six non-zero blocks make a test impossible). Bold: $q<0.05$.}
\label{tab:supps_stats}
\scriptsize
\setlength{\tabcolsep}{3pt}
\fitwidth{\begin{tabular}{llrrrcrrrrcr}
\toprule
 & & \multicolumn{5}{c}{AUROC} & \multicolumn{5}{c}{macro-F1} \\
\cmidrule(lr){3-7}\cmidrule(lr){8-12}
Contrast & Stage & $\Delta$ & $p$ & $q$ & Blocks & MDE & $\Delta$ & $p$ & $q$ & Blocks & MDE \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}}
\end{table*}
""")

    (out / "sota_macros.tex").write_text("\n".join(x for x in M if x is not None) + "\n")
    names = [l.split("{")[1].split("}")[0] for l in M if l and l.startswith("\\newcommand")]
    dup = {n for n in names if names.count(n) > 1}
    if dup: die(f"duplicate macros: {sorted(dup)}")
    bad = [n for n in names if any(ch.isdigit() for ch in n)]
    if bad: die(f"macro names must not contain digits: {bad}")
    print("wrote:", ", ".join(sorted(p.name for p in out.glob("sota_*.tex")) + sorted(p.name for p in out.glob("supps_*.tex"))), "figs/fig_blocks.pdf figs/fig_rank_curve.pdf")


if __name__ == "__main__":
    main()
