"""Model Benchmark: supervised stop-prediction comparison (leakage-safe), with classical
metrics, vs trivial baselines and the unsupervised AD score."""
import sys
import pathlib
sys.path.insert(0, next(str(p) for p in pathlib.Path(__file__).resolve().parents
                        if p.name == "app"))

import pandas as pd
import plotly.express as px
import streamlit as st
from lib import data

st.set_page_config(page_title="Model Benchmark", page_icon="📈", layout="wide")
st.title("📈 Stop-Prediction Benchmark")

m = data.predict_metrics()
if not m:
    st.warning("Run `uv run python scripts/build_predict.py` to generate the benchmark.")
    st.stop()

task = m["task"]
st.caption(f"**Task:** {task['target']} · **Split:** {task['split']} · "
           f"leakage-safe={task['leakage_safe']} · train={task['n_train']:,} / "
           f"test={task['n_test']:,} rows · {task['n_features']} features")

res = pd.DataFrame(m["results"])
best = res.sort_values("PR_AUC", ascending=False).iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Best model", best["model"], f"PR-AUC {best['PR_AUC']}")
c2.metric("Lift over base rate", f"{best['lift_PRAUC_over_base']}×", f"base {best['base_rate']}")
c3.metric("ROC-AUC", best["ROC_AUC"], "↑ >0.5 = real signal")

st.subheader("Model comparison (held-out future)")
st.dataframe(res[["model", "base_rate", "PR_AUC", "ROC_AUC", "lift_PRAUC_over_base",
                  "F1", "precision", "recall"]],
             width="stretch", hide_index=True)

cc = st.columns(2)
with cc[0]:
    fig = px.bar(res.sort_values("PR_AUC"), x="PR_AUC", y="model", orientation="h",
                 color="PR_AUC", color_continuous_scale="Blues",
                 title="PR-AUC by model (dotted = base rate)")
    fig.add_vline(x=float(res.base_rate.iloc[0]), line_dash="dot")
    st.plotly_chart(fig, width="stretch")
with cc[1]:
    fig2 = px.bar(res.sort_values("ROC_AUC"), x="ROC_AUC", y="model", orientation="h",
                  color="ROC_AUC", color_continuous_scale="Greens",
                  title="ROC-AUC by model (0.5 = random)")
    fig2.add_vline(x=0.5, line_dash="dot")
    st.plotly_chart(fig2, width="stretch")

st.subheader("Top predictive features")
imp = pd.DataFrame(m["feature_importance"]).head(12)
st.plotly_chart(px.bar(imp[::-1], x="importance", y="feature", orientation="h",
                       title="Random-forest feature importance"), width="stretch")

st.info("**Read this honestly:** trivial baselines (always-positive, recent-stop) and the "
        "unsupervised AD score (`*`) are included as references. The supervised gradient-boosting "
        "model beats them (PR-AUC ≈2× base rate, ROC-AUC ≈0.70). The unsupervised AD score does "
        "**not** predict significant stops in advance (ROC-AUC ≈0.5) — it is an RCA *evidence* "
        "tool, not a forecaster. Predicting *any* stop is trivial (base rate 0.88–0.96); we "
        "predict *significant* (≥15 min) stops where lift is meaningful.")
