"""Metrics, bootstrap CIs, ensemble and scoreboard for the detector eval.

Usage: detector_eval.py {metrics,ensemble,charts} [--data DIR] [--version v1] [--scoreboard FILE]
"""
import argparse, datetime, json, math, os, subprocess, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_fscore_support, brier_score_loss

HERE = os.path.dirname(os.path.realpath(__file__))  # realpath: run via the ~/.claude/skills symlink, sl needs the repo
SCOREBOARD = os.path.join(HERE, "..", "data", "detector_metrics.jsonl")
DATA = "~/workspace/datasets/slop-detector-eval/data"
STEMS = ["passages", "sentences", "humanized", "humanized_sentences", "wild", "wild_sentences", "taste"]
EXTRA = {"prompted_subset": "sentences", "taste_prompted": "taste"}  # score file -> item file it scores
MIN_NEG = {0.01: 500, 0.05: 100}
PROMPTED, PROMPTED_THR = "prompted", 2 / 3


def kind(type_):
    return "taste" if type_ == "taste" else "public" if type_.startswith(("raid", "ghostbuster")) else "internal"


def auc(y, s):
    return float(roc_auc_score(y, s)) if len(set(y)) == 2 else float("nan")


def _boot_aucs(y, ss, groups, n=1000, seed=0):
    """AUC of each score vector in ss per bootstrap resample; resamples are shared across ss, so differences are paired."""
    # Resampling groups with replacement = integer weights per item; weighted Mann-Whitney over score levels keeps each resample O(n).
    y = np.asarray(y, dtype=float)
    lvls = [np.unique(np.asarray(s, dtype=float), return_inverse=True)[1] for s in ss]
    _, gi = np.unique(np.asarray(groups), return_inverse=True)
    G = int(gi.max()) + 1
    rng = np.random.default_rng(seed); vals = []
    for _ in range(n):
        w = np.bincount(rng.integers(0, G, G), minlength=G)[gi].astype(float)
        if not ((w * y).sum() and (w * (1 - y)).sum()):
            continue
        row = []
        for lvl in lvls:
            L = int(lvl.max()) + 1
            pos, neg = np.bincount(lvl, w * y, L), np.bincount(lvl, w * (1 - y), L)
            row.append(float((pos * (np.cumsum(neg) - 0.5 * neg)).sum() / (pos.sum() * neg.sum())))
        vals.append(row)
    return np.asarray(vals).reshape(-1, len(ss))


def bootstrap_auc_ci(y, s, groups, n=1000, seed=0):
    vals = _boot_aucs(y, [s], groups, n, seed)[:, 0]
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if len(vals) else (float("nan"), float("nan"))


def tpr_at_fpr(y, s, fpr):
    if sum(1 for v in y if v == 0) < MIN_NEG[fpr]:
        return None
    f, t, _ = roc_curve(y, s)
    return float(t[f <= fpr].max())  # highest TPR at or below the target FPR


def best_f1_threshold(y, s):
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    lv, inv = np.unique(s, return_inverse=True)
    pos = np.bincount(inv, y, len(lv)); tot = np.bincount(inv, minlength=len(lv))
    tp = np.cumsum(pos[::-1])[::-1]; pp = np.cumsum(tot[::-1])[::-1]  # predicted positive = score >= level
    f1 = 2 * tp / (pp + y.sum())
    return float(lv[int(np.argmax(f1))])  # ties go to the lowest threshold


def platt(y_dev, s_dev):
    m = LogisticRegression(C=1e6, max_iter=1000).fit(np.asarray(s_dev).reshape(-1, 1), y_dev)  # unregularised, so Brier is fair across score scales
    return lambda s: m.predict_proba(np.asarray(s).reshape(-1, 1))[:, 1]


def cell_metrics(y, s, groups, thr, calib):
    p = r = f = None
    if thr is not None:
        p, r, f = map(float, precision_recall_fscore_support(y, [v >= thr for v in s], average="binary", zero_division=0)[:3])
    lo, hi = bootstrap_auc_ci(y, s, groups)
    return {"n": len(y), "n_pos": int(sum(y)), "auc": auc(y, s), "auc_lo": lo, "auc_hi": hi,
            "tpr1": tpr_at_fpr(y, s, 0.01), "tpr5": tpr_at_fpr(y, s, 0.05), "precision": p, "recall": r, "f1": f,
            "brier": float(brier_score_loss(y, calib(s))) if calib else None}


def _jsonl(p):
    with open(p) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load(data, version):
    base = os.path.join(os.path.expanduser(data), "internal", version)
    out = {}
    for stem in STEMS:
        if os.path.exists(os.path.join(base, stem + ".jsonl")):
            out[stem] = [dict(r, scores={}) for r in _jsonl(os.path.join(base, stem + ".jsonl"))]
    for score_stem, item_stem in [(s, s) for s in STEMS] + list(EXTRA.items()):
        p = os.path.join(base, "scores", score_stem + ".jsonl")
        if item_stem in out and os.path.exists(p):
            sc = {r["id"]: {m: v for m, v in r["scores"].items() if v is not None} for r in _jsonl(p)}  # null = unanswered
            for r in out[item_stem]:
                r["scores"].update(sc.get(r["id"], {}))
    return out


def fit_dev(rows, method, granularity):
    dev = [r for r in rows if r["split"] == "dev" and r["granularity"] == granularity and kind(r["type"]) == "internal" and method in r["scores"]]
    y = [int(r["label"] == "ai") for r in dev]
    if len(set(y)) < 2:
        return None, None
    s = [r["scores"][method] for r in dev]
    return best_f1_threshold(y, s), platt(y, s)


def _with_humans(ai, humans):
    keys = {(r["type"], r["doc_id"]) for r in ai}
    return ai + [h for h in humans if (h["type"], h["doc_id"]) in keys]


def cells(rows):
    out = []
    for g in sorted({r["granularity"] for r in rows}):
        R = [r for r in rows if r["granularity"] == g]
        add = lambda split, t, c, gen, rs: rs and out.append(({"split": split, "type": t, "granularity": g, "condition": c, "generator": gen}, rs))
        hum = [r for r in R if r["label"] == "human" and kind(r["type"]) == "internal"]
        test_h = [r for r in hum if r["split"] == "test"]
        test_ai = [r for r in R if r["label"] == "ai" and r["split"] == "test" and kind(r["type"]) == "internal"]
        for t in sorted({r["type"] for r in test_ai}) + ["all"]:
            ta = [r for r in test_ai if t in ("all", r["type"])]
            for c in sorted({r["condition"] for r in ta}) + ["all"]:
                add("test", t, c, "all", _with_humans([r for r in ta if c in ("all", r["condition"])], test_h))
        for gen in sorted({r["generator"] for r in test_ai}):
            add("test", "all", "all", gen, _with_humans([r for r in test_ai if r["generator"] == gen], test_h))
        for t in sorted({r["type"] for r in R if kind(r["type"]) == "public"}):
            add("test", t, "public", "all", [r for r in R if r["type"] == t])
        humz = [r for r in R if r["condition"] == "humanized"]
        res_h = [h for h in hum if h["split"] == "reserved"]
        for t in sorted({r["type"] for r in humz}) + ["all"]:
            add("reserved", t, "humanized", "all", _with_humans([r for r in humz if t in ("all", r["type"])], res_h))
        wild = [r for r in R if r["condition"] == "wild"]
        wt = {r["type"] for r in wild}
        if wild:
            add("reserved", next(iter(wt)) if len(wt) == 1 else "all", "wild", "all",
                wild + [h for h in hum if h["type"] in wt and h["split"] in ("reserved", "test")])
        # Prompted-classifier examples come from the taste train split, so the eval split already excludes them.
        add("eval", "taste", "taste", "all", [r for r in R if r["type"] == "taste" and r["split"] == "eval"])
        add("prompted_subset", "all", "all", "all", [r for r in R if PROMPTED in r["scores"] and kind(r["type"]) == "internal"])
    return out


def _clean(v):
    return None if isinstance(v, float) and math.isnan(v) else v


def correlations(rows, methods):
    test = [r for r in rows if r["split"] == "test" and r["granularity"] == "sentence" and kind(r["type"]) == "internal"]
    rho = [[None] * len(methods) for _ in methods]
    for i, a in enumerate(methods):
        for j, b in enumerate(methods[i:], i):
            both = [(r["scores"][a], r["scores"][b]) for r in test if a in r["scores"] and b in r["scores"]]
            if len(both) > 2:
                rho[i][j] = rho[j][i] = _clean(float(spearmanr(*zip(*both)).statistic))
    return {"methods": methods, "rho": rho}


def _cell_row(head, key, rs, s, thr, calib):
    y, groups = [int(r["label"] == "ai") for r in rs], [f'{r["type"]}|{r["doc_id"]}' for r in rs]
    taste = key["type"] == "taste"  # taste cells report AUC only
    met = cell_metrics(y, s, groups, None if taste else thr, None if taste else calib)
    if taste:
        met.update(tpr1=None, tpr5=None)
    return {**head, **key, **{k: _clean(v) for k, v in met.items()}}


def _harness():
    try:
        return subprocess.run(["sl", "log", "-r", ".", "-T", "{node|short}"], cwd=os.path.dirname(os.path.dirname(HERE)),
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def metrics(args):
    data = load(args.data, args.version)
    rows = [r for rs in data.values() for r in rs]
    methods = sorted({m for r in rows for m in r["scores"]})
    harness = _harness()
    C, out, date = cells(rows), [], datetime.date.today().isoformat()
    for m in methods:
        for g in sorted({k["granularity"] for k, _ in C}):
            thr, calib = (PROMPTED_THR, None) if m == PROMPTED else fit_dev(rows, m, g)
            for key, rs in C:
                if key["granularity"] != g or (m == PROMPTED and key["split"] not in ("prompted_subset", "eval")):
                    continue
                rs = [r for r in rs if m in r["scores"]]
                y = [int(r["label"] == "ai") for r in rs]
                if len(set(y)) < 2:
                    continue
                head = {"date": date, "harness": harness, "method": m, "version": args.version}
                out.append(_cell_row(head, key, rs, [r["scores"][m] for r in rs], thr, calib))
    with open(os.path.expanduser(args.scoreboard), "a") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in out)
    corr = os.path.join(os.path.expanduser(args.data), "internal", args.version, "correlations.json")
    with open(corr, "w") as fh:
        json.dump(correlations(rows, methods), fh)
    print(f"{len(out)} rows -> {args.scoreboard}; correlations -> {corr}")
    fmt = lambda v: "n/a" if v is None else f"{v:.3f}"
    print(f"{'method':28} {'gran':8} {'split':16} {'AUC [lo, hi]':24} TPR5")
    for r in out:
        if r["type"] == "all" and r["condition"] == "all" and r["generator"] == "all" and r["split"] in ("test", "prompted_subset"):
            print(f'{r["method"]:28} {r["granularity"]:8} {r["split"]:16} {fmt(r["auc"])} [{fmt(r["auc_lo"])}, {fmt(r["auc_hi"])}]  {fmt(r["tpr5"])}')

GRID = {"lr": [{"C": c} for c in (0.01, 0.1, 1, 10)],
        "gbt": [{"max_depth": d, "learning_rate": lr} for d in (3, 6) for lr in (0.05, 0.1)]}
VARIANTS = ["lr", "lr+len", "gbt", "gbt+len"]


def _model(variant, params):
    if variant.startswith("lr"):
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                             LogisticRegression(C=params["C"], max_iter=2000))
    return HistGradientBoostingClassifier(max_iter=300, random_state=0, **params)  # handles missing scores natively


def _xy(rs, feats, variant):
    X = [[r["scores"].get(f, np.nan) for f in feats] + ([math.log(r["n_words"])] if variant.endswith("+len") else []) for r in rs]
    return (np.asarray(X, dtype=float).reshape(len(rs), -1), np.asarray([int(r["label"] == "ai") for r in rs]),
            np.asarray([f'{r["type"]}|{r["doc_id"]}' for r in rs]))


def _oof_test(v, p, dev, test, feats):
    """Out-of-fold test scores; each fold model also scores all of dev, and the mean dev score sets threshold and Platt."""
    Xd, yd, _ = _xy(dev, feats, v)
    Xt, yt, gt = _xy(test, feats, v)
    oof, devp = np.zeros(len(test)), np.zeros(len(dev))
    for tr, te in GroupKFold(5).split(Xt, yt, gt):
        m = _model(v, p).fit(Xt[tr], yt[tr])
        oof[te] = m.predict_proba(Xt[te])[:, 1]
        devp += m.predict_proba(Xd)[:, 1] / 5
    return oof, best_f1_threshold(yd, devp), platt(yd, devp)


def _final(v, p, dev, feats):
    Xd, yd, gd = _xy(dev, feats, v)
    devp = cross_val_predict(_model(v, p), Xd, yd, groups=gd, cv=GroupKFold(5), method="predict_proba")[:, 1]
    return _model(v, p).fit(Xd, yd), best_f1_threshold(yd, devp), platt(yd, devp)


def ensemble(args):
    t0 = time.time()
    data = load(args.data, args.version)
    rows = [r for rs in data.values() for r in rs]
    head0 = {"date": datetime.date.today().isoformat(), "harness": _harness(), "version": args.version}
    C, out, report = cells(rows), [], {}
    for g in sorted({r["granularity"] for r in rows}):
        R = [r for r in rows if r["granularity"] == g]
        internal = [r for r in R if kind(r["type"]) == "internal"]
        dev, test = [r for r in internal if r["split"] == "dev"], [r for r in internal if r["split"] == "test"]
        feats = sorted({m for r in dev for m in r["scores"]} - {PROMPTED})
        if not feats:
            continue
        cv = {}
        for v in VARIANTS:
            Xd, yd, gd = _xy(dev, feats, v)
            a, p = max(((float(cross_val_score(_model(v, p), Xd, yd, groups=gd, cv=GroupKFold(5), scoring="roc_auc").mean()), p)
                        for p in GRID[v.split("+")[0]]), key=lambda t: t[0])
            cv[v] = {"params": p, "cv_auc": a}
        hv = max(VARIANTS, key=lambda v: cv[v]["cv_auc"])
        single = {m: auc(*zip(*[(int(r["label"] == "ai"), r["scores"][m]) for r in dev if m in r["scores"]])) for m in feats}
        best = max(feats, key=lambda m: -1.0 if math.isnan(single[m]) else single[m])
        fin_scores, info = {}, {"lr_coef": {}, "gbt_importance": {}}
        names = feats + ["log_n_words"]
        for v in VARIANTS:
            p = cv[v]["params"]
            oof, tthr, tcal = _oof_test(v, p, dev, test, feats)
            fm, fthr, fcal = _final(v, p, dev, feats)
            oof_map = dict(zip(map(id, test), oof))
            fin = dict(zip(map(id, R), fm.predict_proba(_xy(R, feats, v)[0])[:, 1]))
            fin_scores[v] = (oof, fin, fthr)
            head = dict(head0, method=f"ens-{v}", headline=v == hv)
            for key, rs in C:
                if key["granularity"] != g or len({r["label"] for r in rs}) < 2:
                    continue
                if key["split"] == "test" and key["condition"] != "public":  # internal test cells: out-of-fold scores
                    out.append(_cell_row(head, key, rs, [oof_map[id(r)] for r in rs], tthr, tcal))
                else:
                    out.append(_cell_row(head, key, rs, [fin[id(r)] for r in rs], fthr, fcal))
            if v.startswith("lr"):
                info["lr_coef"][v] = dict(zip(names, map(float, fm[-1].coef_[0])))
            else:
                Xt, yt, _ = _xy(test, feats, v)
                imp = permutation_importance(fm, Xt, yt, scoring="roc_auc", n_repeats=5, random_state=0).importances_mean
                info["gbt_importance"][v] = dict(zip(names, map(float, imp)))
        oof, fin, fthr = fin_scores[hv]
        keep = [i for i, r in enumerate(test) if best in r["scores"]]
        y, ens_s = [int(test[i]["label"] == "ai") for i in keep], oof[keep]
        one_s = [test[i]["scores"][best] for i in keep]
        B = _boot_aucs(y, [ens_s, one_s], [f'{test[i]["type"]}|{test[i]["doc_id"]}' for i in keep])
        lo, hi = (float(v) for v in np.percentile(B[:, 0] - B[:, 1], [2.5, 97.5]))
        loto = {}
        for t in sorted({r["type"] for r in test}):
            tr, te = [r for r in dev + test if r["type"] != t], [r for r in test if r["type"] == t]
            X, yy, _ = _xy(tr, feats, hv)
            s = _model(hv, cv[hv]["params"]).fit(X, yy).predict_proba(_xy(te, feats, hv)[0])[:, 1]
            key = {"split": "test", "type": t, "granularity": g, "condition": "all", "generator": "all"}
            out.append(_cell_row(dict(head0, method=f"ens-{hv}-loto-{t}", headline=False), key, te, s, None, None))
            ts = [r for r in te if best in r["scores"]]
            loto[t] = {"ens_auc": out[-1]["auc"], "single_auc": _clean(auc([int(r["label"] == "ai") for r in ts], [r["scores"][best] for r in ts]))}
        agree = {}
        for name, sel in [("prompted_subset", lambda r: kind(r["type"]) == "internal"), ("taste", lambda r: r["type"] == "taste" and r["split"] == "eval")]:
            rs = [r for r in R if PROMPTED in r["scores"] and sel(r)]
            if len(rs) > 2:
                pv, ev = [r["scores"][PROMPTED] for r in rs], [fin[id(r)] for r in rs]
                agree[name] = {"n": len(rs), "spearman": _clean(float(spearmanr(pv, ev).statistic)),
                               "agreement": float(np.mean([(a >= PROMPTED_THR) == (b >= fthr) for a, b in zip(pv, ev)]))}
        report[g] = {"features": names if hv.endswith("+len") else feats, "headline": hv, "cv": cv,
                     "best_single": {"method": best, "dev_auc": _clean(single[best]), "test_auc": auc(y, one_s)},
                     "headline_test": {"auc": auc(y, ens_s), "auc_lo": float(np.percentile(B[:, 0], 2.5)), "auc_hi": float(np.percentile(B[:, 0], 97.5))},
                     "auc_diff": {"diff": auc(y, ens_s) - auc(y, one_s), "lo": lo, "hi": hi},
                     "win": lo > 0, "loto": loto, "prompted_agreement": agree, **info}
    with open(os.path.expanduser(args.scoreboard), "a") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in out)
    path = os.path.join(os.path.expanduser(args.data), "internal", args.version, "ensemble.json")
    with open(path, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"{len(out)} rows -> {args.scoreboard}; report -> {path}")
    for g, r in report.items():
        b, h, d = r["best_single"], r["headline_test"], r["auc_diff"]
        sane = r["cv"][r["headline"]]["cv_auc"] >= b["dev_auc"] - 0.02
        print(f"\n[{g}] headline ens-{r['headline']}  dev CV AUC " + ", ".join(f"{v}={c['cv_auc']:.3f}" for v, c in r["cv"].items())
              + f"  (best single dev {b['dev_auc']:.3f}{'' if sane else '  SANITY FAIL: inspect for a join bug'})")
        print(f"  test AUC {h['auc']:.3f} [{h['auc_lo']:.3f}, {h['auc_hi']:.3f}]  vs  {b['method']} {b['test_auc']:.3f}  "
              f"diff {d['diff']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]  {'WIN' if r['win'] else 'NO-WIN'}")
        print(f"  {'LOTO type':12} ens    single")
        for t, l in r["loto"].items():
            print(f"  {t:12} {l['ens_auc']:.3f}  {l['single_auc']:.3f}")
    print(f"\n{time.time() - t0:.1f}s")


CHART_DIR = "~/.claude/docs/slop-detector-eval"
CHART_METHODS = ["ens-lr", "ens-gbt", "superannotate", "mpu-env3", "mpu-env3short", "desklib", "binoculars", "fast-detectgpt",
                 "roberta-openai", "lex-humanize-tells", "lex-slopscore-word", "lex-vale-any", "lex-antislop-regex"]
FAMILY = {"ens": ("ensemble", "#2a78d6"), "lex": ("lexical list", "#1baf7a"), "": ("model detector", "#eb6834")}  # categorical slots 1, 3, 2
PAIR = ("#2a78d6", "#eb6834")
GENERATORS = ["claude-opus", "claude-sonnet", "claude-haiku", "gpt-5.6-sol", "gpt-5.5", "gpt-5.4"]
TYPES = ["diff", "post", "wiki", "task", "codedoc", "all"]


def _family(m):
    if m == PROMPTED:
        return ("prompted classifier", "#4a3aa7")  # categorical slot 7
    return FAMILY["ens" if m.startswith("ens") else "lex" if m.startswith("lex") else ""]


def _latest(path, version):
    """Newest row per cell key, so re-runs supersede older rows."""
    best = {}
    for r in _jsonl(os.path.expanduser(path)):
        if r["version"] == version:
            k = (r["method"], r["split"], r["type"], r["granularity"], r["condition"], r["generator"])
            if k not in best or r["date"] >= best[k]["date"]:
                best[k] = r
    return best


def charts(args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 10})
    out = os.path.expanduser(args.out)
    os.makedirs(out, exist_ok=True)
    rows = _latest(args.scoreboard, args.version)
    base = os.path.join(os.path.expanduser(args.data), "internal", args.version)
    ens = json.load(open(os.path.join(base, "ensemble.json")))
    corr = json.load(open(os.path.join(base, "correlations.json")))

    def get(m, split="test", type_="all", g="passage", cond="all", gen="all"):
        return rows.get((m, split, type_, g, cond, gen))

    def order(g):  # methods by pooled test AUC, best at top
        return sorted([m for m in CHART_METHODS if get(m, g=g)], key=lambda m: get(m, g=g)["auc"])

    def hbars(ax, items, color=None, offset=0.0, height=0.8, label=None):
        """items: (label, row|None); bars with CI whiskers; missing rows leave a gap."""
        for i, (lab, r) in enumerate(items):
            if r is None or r["auc"] is None:
                continue
            c = color or _family(lab)[1]
            ax.barh(i + offset, r["auc"], height=height, color=c, label=label if i == 0 or label is None else None)
            if r["auc_lo"] is not None:
                ax.errorbar(r["auc"], i + offset, xerr=[[r["auc"] - r["auc_lo"]], [r["auc_hi"] - r["auc"]]], fmt="none", ecolor="#52514e", lw=0.8, capsize=2)
        ax.axvline(0.5, color="#52514e", ls="--", lw=0.8)
        ax.set_xlim(0, 1.0)
        ax.grid(axis="x", color="#e5e4e0", lw=0.6); ax.set_axisbelow(True)

    def family_legend(fig):
        fig.legend(handles=[Patch(color=c, label=n) for n, c in FAMILY.values()], loc="lower center", ncol=3, frameon=False)

    def save(fig, name):
        fig.savefig(os.path.join(out, name), dpi=130, bbox_inches="tight"); plt.close(fig)
        print(os.path.join(out, name))

    for g in ("passage", "sentence"):
        ms = order(g)
        fig, axes = plt.subplots(2, 3, figsize=(13, 8), sharey=True)
        for ax, t in zip(axes.flat, TYPES):
            items = [(m, get(m, type_=t, g=g)) for m in ms]
            hbars(ax, items)
            n = next((r for _, r in items if r), None)
            ax.set_title(f"{'pooled' if t == 'all' else t}  (n={n['n']}, {n['n_pos']} AI)" if n else t)
            ax.set_yticks(range(len(ms)), ms)
        for ax in axes[-1]:
            ax.set_xlabel("AUC (95% CI)")
        fig.suptitle(f"AUC by content type, {g} level, test split", y=0.995)
        family_legend(fig); fig.tight_layout(rect=(0, 0.04, 1, 0.98))
        save(fig, f"auc_by_type_{g}.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, g in zip(axes, ("passage", "sentence")):
        ms = order(g)
        neg = get(ms[0], g=g)["n"] - get(ms[0], g=g)["n_pos"]
        key = "tpr1" if neg >= MIN_NEG[0.01] else "tpr5"
        vals = [get(m, g=g)[key] or 0.0 for m in ms]
        ax.barh(range(len(ms)), vals, color=[_family(m)[1] for m in ms])
        for i, v in enumerate(vals):
            ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8, color="#52514e")
        ax.set_yticks(range(len(ms)), ms); ax.set_xlim(0, 1)
        ax.set_xlabel(f"TPR at {'1' if key == 'tpr1' else '5'}% FPR")
        ax.set_title(f"{g}: TPR at {'1' if key == 'tpr1' else '5'}% FPR ({neg} human negatives"
                     + ("" if key == "tpr1" else ", too few for 1%") + ")")
        ax.grid(axis="x", color="#e5e4e0", lw=0.6); ax.set_axisbelow(True)
    family_legend(fig); fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "tpr.png")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, g in zip(axes, ("passage", "sentence")):
        ms = order(g)[::-1]
        M = np.array([[(get(m, g=g, gen=gen) or {}).get("auc", np.nan) for gen in GENERATORS] for m in ms], dtype=float)
        ax.imshow(M, cmap="Blues", vmin=0.3, vmax=1.0, aspect="auto")
        for i in range(len(ms)):
            for j in range(len(GENERATORS)):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=8, color="white" if M[i, j] > 0.75 else "#0b0b0b")
        ax.set_xticks(range(len(GENERATORS)), GENERATORS, rotation=30, ha="right"); ax.set_yticks(range(len(ms)), ms)
        ax.set_title(f"{g}: test AUC per generator")
        ax.spines[:].set_visible(False)
    fig.tight_layout(); save(fig, "generators.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
    ms = order("passage")
    for ax, (cond, title) in zip(axes, [("humanized", "humanized (reserved split)"), ("wild", "wild 2024 AI diffs vs 2022 human diffs")]):
        for k, g in enumerate(("passage", "sentence")):
            typ = "diff" if cond == "wild" else "all"  # wild positives are diffs only
            items = [(m, get(m, "reserved", typ, g, cond)) for m in ms]
            n = next(r for _, r in items if r)
            hbars(ax, items, color=PAIR[k], offset=0.2 - 0.4 * k, height=0.38, label=f"{g} (n={n['n']}, {n['n_pos']} AI)")
        ax.set_yticks(range(len(ms)), ms); ax.set_title(title); ax.set_xlabel("AUC (95% CI)")
        ax.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout(); save(fig, "hard_wild.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={"width_ratios": [3, 2]})
    labels, items = [], []
    for g in ("passage", "sentence"):
        e = ens[g]
        hm, b = f"ens-{e['headline']}", e["best_single"]["method"]
        for m in (b, hm):
            labels.append(f"{g}: {m}" + (" (headline)" if m == hm else " (best single)")); items.append((m, get(m, g=g)))
    hbars(axes[0], items)
    axes[0].set_yticks(range(len(labels)), labels); axes[0].set_xlabel("pooled test AUC (95% CI)")
    axes[0].set_title("headline ensemble vs best single method")
    for i, g in enumerate(("passage", "sentence")):
        d = ens[g]["auc_diff"]
        axes[1].errorbar(d["diff"], i, xerr=[[d["diff"] - d["lo"]], [d["hi"] - d["diff"]]], fmt="o", color=PAIR[0], ms=8, capsize=4)
        axes[1].text(d["diff"], i + 0.18, f"{d['diff']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]", ha="center", fontsize=8)
    axes[1].axvline(0, color="#52514e", ls="--", lw=0.8); axes[1].set_ylim(-0.6, 1.6)
    axes[1].set_yticks([0, 1], ["passage", "sentence"]); axes[1].set_xlabel("AUC difference, paired bootstrap 95% CI")
    axes[1].set_title("ensemble minus best single")
    fig.tight_layout(); save(fig, "ensemble_vs_best.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    types = [t for t in TYPES if t != "all"]
    for ax, g in zip(axes, ("passage", "sentence")):
        e = ens[g]; hv, b = e["headline"], e["best_single"]["method"]
        hbars(ax, [(t, get(f"ens-{hv}-loto-{t}", type_=t, g=g)) for t in types], color=PAIR[0], offset=0.2, height=0.38, label=f"ens-{hv}, type held out")
        hbars(ax, [(t, get(b, type_=t, g=g)) for t in types], color=PAIR[1], offset=-0.2, height=0.38, label=f"{b} (best single)")
        ax.set_yticks(range(len(types)), types); ax.set_title(f"{g}: leave-one-type-out"); ax.set_xlabel("test AUC on held-out type (95% CI)")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False, fontsize=8)
    fig.tight_layout(); save(fig, "loto.png")

    keep = [m for m in CHART_METHODS + ["lex-vale-Passive", "lex-vale-Dash", "prompted"] if m in corr["methods"]]
    idx = [corr["methods"].index(m) for m in keep]
    R = np.array([[np.nan if corr["rho"][i][j] is None else corr["rho"][i][j] for j in idx] for i in idx], dtype=float)
    fig, ax = plt.subplots(figsize=(9, 7.5))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
    im = ax.imshow(R, cmap=cmap, vmin=-1, vmax=1)
    for i in range(len(keep)):
        for j in range(len(keep)):
            if not np.isnan(R[i, j]):
                ax.text(j, i, f"{R[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(R[i, j]) > 0.6 else "#0b0b0b")
    ax.set_xticks(range(len(keep)), keep, rotation=45, ha="right"); ax.set_yticks(range(len(keep)), keep)
    ax.spines[:].set_visible(False); fig.colorbar(im, ax=ax, shrink=0.7, label="Spearman rho")
    ax.set_title("Spearman correlation on test sentences (prompted: 200-sentence subset only)")
    fig.tight_layout(); save(fig, "correlations.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    ms = order("sentence") + ["prompted"]
    for ax, (split, typ, cond, title) in zip(axes, [("prompted_subset", "all", "all", "provenance subset (200 test sentences)"),
                                                    ("eval", "taste", "taste", "author taste labels (25 eval sentences)")]):
        items = [(m, get(m, split, typ, "sentence", cond)) for m in ms]
        hbars(ax, items)
        ax.set_yticks(range(len(ms)), ms); ax.set_title(title); ax.set_xlabel("AUC (95% CI)")
    fig.legend(handles=[Patch(color=c, label=n) for n, c in list(FAMILY.values()) + [_family(PROMPTED)]],
               loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1)); save(fig, "taste.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("metrics", "ensemble", "charts"):
        p = sub.add_parser(name)
        p.add_argument("--data", default=DATA)
        p.add_argument("--version", default="v1")
        p.add_argument("--scoreboard", default=SCOREBOARD)
        if name == "charts":
            p.add_argument("--out", default=CHART_DIR)
    args = ap.parse_args()
    # HistGradientBoosting's OpenMP defaults to every core; on a busy shared host a small fit took 150 s vs <1 s with 8 threads.
    with threadpool_limits(8):
        {"metrics": metrics, "ensemble": ensemble, "charts": charts}[args.cmd](args)


if __name__ == "__main__":
    main()
