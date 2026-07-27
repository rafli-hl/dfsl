#!/usr/bin/env bash
# Run the full pipeline: synthetic experiments plus the Jane Street pipeline.
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pip install -e .
python -m pytest -q

python experiments/train.py --config configs/default.yaml
python experiments/train.py --config configs/synthetic.yaml
python experiments/benchmark.py --config configs/synthetic.yaml
python experiments/ablation.py --config configs/ablation.yaml

if [ -e "data/raw/jane/train.parquet" ]; then
    python scripts/preprocess.py --input data/raw/jane --output data/processed/jane
    python experiments/train.py --config configs/jane.yaml
else
    echo "Skipping Jane Street pipeline: data/raw/jane/train.parquet not found."
    echo "Run 'python scripts/download_data.py' to fetch the dataset first."
fi

echo "All pipelines finished."
