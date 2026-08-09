"""Second, non-finance domain: gradient norms during real CNN training on MNIST.

The thesis "nonstationarity of the gradient scale manufactures the pooled heavy tail"
is a claim about gradient-scale processes in general, not about markets. Training a
neural net is the canonical nonstationary gradient-scale process the ML audience knows
(norms are large early, decay, and jump at learning-rate drops). We log the per-step
minibatch gradient norm over a real training run and run the SAME analysis as on Jane:
pooled Hill alpha vs causally scale-normalized alpha, with a non-causal-median control.

Pre-committed: we report whichever way it comes out. If the normalized tail stays heavy,
that is a genuine boundary on the claim (training gradients are intrinsically heavy);
if it lightens, drift manufactures the pooled tail here too and the thesis generalizes.

Usage: python scripts/research_second_domain.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"
GN = RES / "gradnorm_mnist.npy"


def hill(a, k):
    a = np.sort(a[np.isfinite(a) & (a > 0)])[::-1]
    k = min(k, a.size - 2)
    if k <= 0 or a[k] <= 0:
        return float("nan")
    return 1.0 / float(np.mean(np.log(a[:k]) - np.log(a[k])))


def causal_ema(g, decay=0.99, winsor=8.0):
    s = np.empty_like(g)
    cur = g[0]
    for i, v in enumerate(g):
        s[i] = cur
        cur = decay * cur + (1 - decay) * min(v, winsor * cur)
    return s


def collect_gradnorms(epochs=3):
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader
    from torchvision import datasets, transforms

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)
    tf = transforms.Compose([transforms.ToTensor()])
    train = datasets.MNIST(str(ROOT / "data" / "mnist"), train=True, download=True, transform=tf)
    loader = DataLoader(train, batch_size=64, shuffle=True, num_workers=0)

    net = nn.Sequential(
        nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Flatten(), nn.Linear(32 * 7 * 7, 10),
    ).to(dev)
    opt = torch.optim.SGD(net.parameters(), lr=0.1, momentum=0.9)
    # two lr drops -> deliberate scale jumps, the analogue of overnight jumps
    steps_per_epoch = len(loader)
    sched = torch.optim.lr_scheduler.MultiStepLR(
        opt, milestones=[steps_per_epoch, 2 * steps_per_epoch], gamma=0.1)

    norms = []
    for ep in range(epochs):
        for xb, yb in loader:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad()
            loss = F.cross_entropy(net(xb), yb)
            loss.backward()
            g2 = sum(float(p.grad.detach().pow(2).sum()) for p in net.parameters() if p.grad is not None)
            norms.append(g2 ** 0.5)
            opt.step()
            sched.step()
        print(f"  epoch {ep}: {len(norms)} steps, last loss {float(loss):.3f}")
    g = np.asarray(norms, dtype=np.float64)
    np.save(GN, g)
    return g


def main():
    if GN.exists():
        g = np.load(GN)
        print(f"Loaded cached {GN.name}: {g.size} steps")
    else:
        print("Training small CNN on MNIST, logging per-step gradient norms ...")
        g = collect_gradnorms()
    g = g[np.isfinite(g) & (g > 0)]
    n = g.size
    fracs = [0.01, 0.02, 0.05]

    def rep(name, x):
        xs = x[np.isfinite(x) & (x > 0)]
        print(f"  {name:38s} " + "  ".join(f"k={f}:{hill(xs,int(f*xs.size)):.2f}" for f in fracs))

    print(f"\nMNIST training-gradient-norm tail ({n} steps):")
    print(f"  scale drift: min-window median .. max-window median = "
          f"{np.median(g[:200]):.3f} .. {np.median(g[-200:]):.3f} "
          f"(range {np.max([np.median(g[i:i+200]) for i in range(0,n-200,200)]) / (np.min([np.median(g[i:i+200]) for i in range(0,n-200,200)])+1e-9):.1f}x)")
    rep("raw ||g|| (pooled)", g)
    import polars as pl
    rep("||g|| / causal-EMA s_t", (g / np.maximum(causal_ema(g), 1e-12))[200:])
    med = pl.Series(g).rolling_median(window_size=201, center=True, min_samples=1).to_numpy()
    rep("||g|| / non-causal median (ground-truth)", g / np.maximum(med, 1e-12))
    print("\n  VERDICT: normalized alpha >> pooled alpha => drift manufactures the tail (thesis")
    print("  generalizes); normalized ~ pooled => training gradients are intrinsically heavy.")


if __name__ == "__main__":
    main()
