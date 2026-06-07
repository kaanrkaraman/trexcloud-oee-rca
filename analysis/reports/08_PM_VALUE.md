# Prediction to OEE and Financial Value

This report connects the deployed supervised Fanuc stop predictor to attributable OEE and financial value on the held-out future. AD remains a separate unsupervised RCA evidence layer.

## Audited deployed operating point

- Threshold: **0.1778** (unchanged deployed threshold)
- Model: ROC-AUC **0.731**, PR-AUC **0.426**, lift **2.38x**
- Significant stops caught: **364/527** (event recall **69.1%**)
- Alert episodes: **722**; episode precision **44.0%**; false-alarm episodes **404**
- Caught downtime: **2,062.5 h**; attributable prevented time at e=35%: **721.9 h**
- Attributable delta: **+10.44 pp A**, **+10.44 pp OEE**; delta P/Q = 0
- Observed net: **EUR -158,850**; annualized projection: **2,329.7 h**, **EUR -512,666 net**

> USER-PROVIDED ASSUMPTIONS — the dataset contains NO cost/price data; treat all currency figures as hypotheses, not facts.

## Per-machine held-out results

| Machine | Stops | Caught | Recall | Caught h | Prevented h | Episodes | Ep. precision | dOEE pp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Makine 1 | 90 | 65 | 72.2% | 735.3 | 257.4 | 131 | 47.3% | 15.89 |
| Makine 2 | 68 | 24 | 35.3% | 106.8 | 37.4 | 125 | 16.8% | 4.10 |
| Makine 3 | 101 | 70 | 69.3% | 327.7 | 114.7 | 166 | 39.2% | 8.87 |
| Makine 5 | 140 | 109 | 77.9% | 500.0 | 175.0 | 168 | 56.0% | 12.82 |
| Makine 9 | 128 | 96 | 75.0% | 392.7 | 137.4 | 132 | 57.6% | 7.97 |

## Economic threshold sensitivity

The following optimum is selected retrospectively on the held-out window and is not presented as the deployed result.

- Net-EUR optimum threshold: **0.7800**
- Recall: **5.7%**; episodes: **33**; annualized net: **EUR 11,013**

## Headline

> AI kestirimci bakım (Fanuc, yıllık projeksiyon) -> ~2330 saat geri kazanım, +10.44 puan OEE, ~EUR -512,666 net (varsayımlar etiketli).
