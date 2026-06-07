"""Lightweight reconstruction autoencoder for multivariate leading-indicator AD.

Trains normal-only on the resampled feature matrix (windows that don't overlap labeled
anomalies / offline). Reconstruction error = anomaly score; per-feature error = attribution.

Encoder is swap-able via build_encoder(): "mlp" | "conv" now, "patchtst" later — train_ae/
score_ae and the output schema never change when upgrading to a transformer.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from .baselines import Envelope, _intervals_mask
from .features import feature_columns


@dataclass
class AEConfig:
    window: int = 30          # buckets (~30 min @ 60s)
    stride: int = 5
    bottleneck: int = 8
    hidden: int = 64
    epochs: int = 40
    lr: float = 1e-3
    batch: int = 128
    encoder: str = "conv"     # "mlp" | "conv" | "patchtst" (swap point)
    val_frac: float = 0.2
    seed: int = 0
    features: tuple[str, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------- nets
class MLPEncoder(nn.Module):
    def __init__(self, w, f, hidden, d):
        super().__init__()
        self.net = nn.Sequential(nn.Flatten(), nn.Linear(w * f, hidden), nn.ReLU(),
                                 nn.Linear(hidden, d))

    def forward(self, x):
        return self.net(x)


class ConvEncoder(nn.Module):
    def __init__(self, w, f, hidden, d):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(f, hidden, 3, padding=1), nn.ReLU(),
            nn.Conv1d(hidden, hidden, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool1d(1))
        self.head = nn.Linear(hidden, d)

    def forward(self, x):                      # x: (B, W, F)
        h = self.conv(x.transpose(1, 2)).squeeze(-1)
        return self.head(h)


class Decoder(nn.Module):
    def __init__(self, w, f, hidden, d):
        super().__init__()
        self.w, self.f = w, f
        self.net = nn.Sequential(nn.Linear(d, hidden), nn.ReLU(),
                                 nn.Linear(hidden, w * f))

    def forward(self, z):
        return self.net(z).view(-1, self.w, self.f)


def build_encoder(kind, w, f, hidden, d) -> nn.Module:
    if kind == "mlp":
        return MLPEncoder(w, f, hidden, d)
    if kind == "conv":
        return ConvEncoder(w, f, hidden, d)
    raise ValueError(f"unknown/not-yet-implemented encoder: {kind!r} "
                     "(reserved: 'patchtst' for the transformer upgrade)")


class ReconAutoencoder(nn.Module):
    def __init__(self, encoder, decoder):
        super().__init__()
        self.encoder, self.decoder = encoder, decoder

    def forward(self, x):
        return self.decoder(self.encoder(x))


# --------------------------------------------------------------------- windowing
def _standardize(feats, cols, envelopes):
    X = np.zeros((len(feats), len(cols)), dtype=np.float32)
    for j, c in enumerate(cols):
        v = pd.to_numeric(feats[c], errors="coerce").to_numpy(dtype=float)
        e = envelopes.get(c)
        med = e.median if e else np.nanmedian(v)
        sig = e.sigma if e else (np.nanstd(v) or 1.0)
        z = (v - med) / (sig or 1.0)
        X[:, j] = np.nan_to_num(np.clip(z, -10, 10), nan=0.0)
    return X


def make_windows(feats: pd.DataFrame, cfg: AEConfig, *,
                 envelopes: dict[str, Envelope] | None = None,
                 exclude_windows: pd.DataFrame | None = None):
    """Sliding windows (+ end-timestamps + 'is_normal' flag for training selection)."""
    feats = feats.sort_values("ts").reset_index(drop=True)
    cols = list(cfg.features) or feature_columns(feats)
    X = _standardize(feats, cols, envelopes or {})
    ts = feats["ts"].to_numpy()
    machine = feats["machine"].iloc[0]

    bad = np.zeros(len(feats), dtype=bool)
    if "is_offline" in feats:
        bad |= feats["is_offline"].fillna(False).to_numpy()
    if exclude_windows is not None:
        bad |= _intervals_mask(feats["ts"], exclude_windows, machine)

    W, S = cfg.window, cfg.stride
    wins, ends, normal = [], [], []
    for i in range(0, len(feats) - W + 1, S):
        wins.append(X[i:i + W])
        ends.append(ts[i + W - 1])
        normal.append(not bad[i:i + W].any())
    if not wins:
        return (np.empty((0, W, len(cols)), np.float32),
                np.array([], dtype="datetime64[ns]"), np.array([], bool), cols)
    return np.stack(wins), np.array(ends), np.array(normal), cols


def train_ae(feats: pd.DataFrame, cfg: AEConfig, *, envelopes=None,
             exclude_windows=None, out: str | Path | None = None):
    """Normal-only training (masked by labeled/offline windows). CPU, minutes."""
    torch.manual_seed(cfg.seed)
    Xw, ends, normal, cols = make_windows(feats, cfg, envelopes=envelopes,
                                          exclude_windows=exclude_windows)
    Xn = Xw[normal]
    if len(Xn) < 10:
        return None, {"cols": cols, "n_train": int(len(Xn)), "trained": False}
    n_val = max(1, int(len(Xn) * cfg.val_frac))
    Xtr, Xval = Xn[:-n_val], Xn[-n_val:]
    enc = build_encoder(cfg.encoder, cfg.window, len(cols), cfg.hidden, cfg.bottleneck)
    model = ReconAutoencoder(enc, Decoder(cfg.window, len(cols), cfg.hidden, cfg.bottleneck))
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    lossf = nn.MSELoss()
    tr = torch.tensor(Xtr); va = torch.tensor(Xval)
    best, best_state, hist = float("inf"), None, []
    for ep in range(cfg.epochs):
        model.train()
        perm = torch.randperm(len(tr))
        for i in range(0, len(tr), cfg.batch):
            b = tr[perm[i:i + cfg.batch]]
            opt.zero_grad(); loss = lossf(model(b), b); loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(lossf(model(va), va))
        hist.append(vl)
        if vl < best:
            best, best_state = vl, {k: v.clone() for k, v in model.state_dict().items()}
    if best_state:
        model.load_state_dict(best_state)
    meta = {"cols": cols, "cfg": cfg, "n_train": int(len(Xtr)), "val_loss": best,
            "trained": True, "history": hist}
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state": model.state_dict(), "meta": {k: meta[k] for k in
                    ("cols", "n_train", "val_loss", "trained")}, "cfg": cfg.__dict__}, out)
    return model, meta


def score_ae(model, feats: pd.DataFrame, cfg: AEConfig, *, envelopes=None) -> pd.DataFrame:
    """Per-window reconstruction error + per-feature error attribution."""
    if model is None:
        return pd.DataFrame(columns=["machine", "ts", "recon_err", "per_feature_err"])
    Xw, ends, _, cols = make_windows(feats, cfg, envelopes=envelopes)
    if not len(Xw):
        return pd.DataFrame(columns=["machine", "ts", "recon_err", "per_feature_err"])
    model.eval()
    with torch.no_grad():
        rec = model(torch.tensor(Xw)).numpy()
    err = (rec - Xw) ** 2                      # (N, W, F)
    per_feat = err.mean(axis=1)                # (N, F)
    recon = per_feat.mean(axis=1)              # (N,)
    machine = feats["machine"].iloc[0]
    return pd.DataFrame({
        "machine": machine, "ts": ends, "recon_err": recon,
        "per_feature_err": [dict(zip(cols, row.round(4))) for row in per_feat],
    })
