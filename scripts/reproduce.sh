#!/usr/bin/env bash
# Reproduce the synthetic-data experiments end to end.
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pip install -e .
python -m pytest -q

python experiments/train.py --config configs/default.yaml
python experiments/train.py --config configs/synthetic.yaml
python experiments/benchmark.py --config configs/synthetic.yaml
python experiments/ablation.py --config configs/ablation.yaml

echo "Reproduction finished. See results/runs, results/benchmark and results/ablation."
