"""Build the Anomaly Detection artifacts end to end.

features -> labels -> baseline envelopes (fit/score) -> AE (train/score, normal-only)
-> fuse -> flag windows -> link labels -> emit -> eval summary.

Run: uv run python scripts/build_ad.py            (all telemetry machines)
     uv run python scripts/build_ad.py "Makine 1" (one machine, fast dev)
"""
import sys
from pathlib import Path
import pandas as pd
from trex.ad import features, labels, baselines, autoencoder, emit, eval as adeval

ART = Path("analysis/artifacts")


def main(machines=None):
    print("[1/6] feature matrix ...")
    feats = features.build_feature_matrix(machines=machines)
    print(f"      {len(feats)} buckets, {feats.machine.nunique()} machines, "
          f"cols={features.feature_columns(feats)}")

    print("[2/6] labels + offline windows ...")
    lab = labels.anomaly_label_windows()
    off = labels.offline_windows()
    print(f"      {len(lab)} label events, {len(off)} offline windows")

    cfg = autoencoder.AEConfig()
    all_scores, all_ae = [], []
    print("[3/6] per-machine baselines + AE ...")
    for m, g in feats.groupby("machine"):
        env = baselines.fit_envelopes(g, exclude_windows=lab)
        if not env:
            continue
        dev = baselines.score_features(g, env)
        bscore = baselines.machine_anomaly_score(dev)
        model, meta = autoencoder.train_ae(
            g, cfg, envelopes=env, exclude_windows=lab,
            out=ART / f"ad_ae_{m.strip().replace(' ', '_')}.pt")
        ae = autoencoder.score_ae(model, g, cfg, envelopes=env) if meta.get("trained") else None
        fused = emit.fuse_scores(g, bscore, ae)
        all_scores.append(fused)
        print(f"      {m:20s} feats={len(env)} buckets={len(g)} "
              f"AE_train={meta.get('n_train')} trained={meta.get('trained')}")

    scores = pd.concat(all_scores, ignore_index=True)

    print("[4/6] flag windows + link labels ...")
    wins = emit.extract_windows(scores, thresh=90.0)
    wins = emit.link_labels(wins, lab)
    print(f"      {len(wins)} flagged anomaly windows")

    print("[5/6] write artifacts ...")
    p1, p2 = emit.write_outputs(scores, wins)
    print(f"      {p1.name} ({len(scores)} rows), {p2.name} ({len(wins)} rows)")

    print("[6/6] eval summary (offline-excluded) ...")
    summ = adeval.summarize(scores, lab, off, thresh=90.0)
    print(summ.to_string(index=False))
    pr = adeval.event_precision_recall(adeval._drop_offline(scores, off), lab)
    print("\nPrecision/Recall vs threshold:")
    print(pr.to_string(index=False))


if __name__ == "__main__":
    args = sys.argv[1:] or None
    main(args)
