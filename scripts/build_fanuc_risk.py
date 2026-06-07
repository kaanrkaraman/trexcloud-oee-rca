"""Train the deployed Fanuc predictor and emit risk artifacts for the dashboard.

Outputs (analysis/artifacts/):
  fanuc_risk.parquet        per-bucket risk on the held-out future [machine, ts, y, risk]
  fanuc_risk_episodes.csv   above-threshold risk episodes [machine, start, end, peak/mean, hit]
  fanuc_model_meta.json     metrics + params + operating threshold + test period

Run: uv run python scripts/build_fanuc_risk.py
"""
import json
from pathlib import Path
from trex.predict import fanuc

ART = Path("analysis/artifacts")


def main():
    print("training deployed Fanuc predictor (per-machine z-norm, tuned HistGBDT)…")
    model, scored, feat, metrics = fanuc.train_score()
    print(f"  test rows={metrics['n_test']:,}  ROC={metrics['ROC_AUC']}  "
          f"PR-AUC={metrics['PR_AUC']}  lift={metrics['lift']}  thr={metrics['threshold']}")

    ep = fanuc.risk_episodes(scored, metrics["threshold"])
    hit_rate = float(ep["hit"].mean()) if len(ep) else 0.0
    print(f"  risk episodes={len(ep)}  precision@episodes={hit_rate:.2f} "
          f"(share of flagged episodes followed by a real significant stop)")

    scored.to_parquet(ART / "fanuc_risk.parquet", index=False)
    ep.to_csv(ART / "fanuc_risk_episodes.csv", index=False)
    meta = {**metrics, "machines": fanuc.FANUC, "params": fanuc.best_params(),
            "n_episodes": int(len(ep)), "episode_precision": round(hit_rate, 3),
            "feature_count": len(feat)}
    (ART / "fanuc_model_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    print("wrote fanuc_risk.parquet, fanuc_risk_episodes.csv, fanuc_model_meta.json")


if __name__ == "__main__":
    main()
