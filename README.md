# dfsl — Distribution-Free Sequential Learning

Robust online (sequential) regression under heavy-tailed and contaminated data streams.
`dfsl` plugs robust mean estimators (Catoni's M-estimator, median-of-means, trimmed mean)
into clipped online gradient methods, so that gradient-clipping thresholds are set by
distribution-free robust statistics instead of hand-tuned constants. The library is
evaluated on synthetic heavy-tailed streams (Student-t, Pareto, Cauchy noise with
optional adversarial contamination) and on the Jane Street Real-Time Market Data
Forecasting dataset from Kaggle, using only a finite-variance assumption on the noise.

## Features

- **Robust mean estimators** — `catoni_mean`, `median_of_means`, `trimmed_mean` with a
  uniform "array in, float out" contract and a `get_estimator` registry.
- **Online learners** — `OnlineGradientDescent`, `AdaptiveClip` (quantile-based gradient
  clipping), and `RobustOMD` (online mirror descent with a robust-statistics clipping
  threshold), all sharing the `OnlineLearner` prequential `run` protocol.
- **Sequential datasets** — `SyntheticHeavyTailed` streams with configurable noise and
  contamination, and `JaneStreetDataset` backed by lazy polars scans of the competition
  parquet files.
- **Evaluation toolkit** — weighted MSE/MAE, the competition's weighted zero-mean R²,
  regret curves against the best fixed linear predictor, empirical regret slopes, and
  breakdown-point experiments under target contamination.
- **Config-driven experiments** — YAML configs plus argparse CLIs for training,
  evaluation, benchmarking, and ablations, with reproducible seeding throughout.

## Repository layout

```
distribution-free-sequential-learning/
├── configs/            # YAML experiment configurations (default, synthetic, jane, ablation)
├── data/
│   ├── raw/jane/       # Kaggle competition data (not tracked by git)
│   └── processed/      # cleaned parquet written by scripts/preprocess.py
├── experiments/        # train.py, evaluate.py, benchmark.py, ablation.py CLIs
├── notebooks/          # dataset characterization and analysis notebooks
├── paper/              # LaTeX sources (main.tex, appendix.tex, references.bib)
├── results/            # runs, figures, benchmark and ablation outputs
├── scripts/            # download_data.py, preprocess.py, reproduce.sh, run_all.sh
├── src/dfsl/           # the importable library (src layout)
└── tests/              # pytest suite
```

## Installation

Requires Python >= 3.11.

```bash
pip install -e ".[dev]"
```

## Data download

The Jane Street data comes from the Kaggle competition
`jane-street-real-time-market-data-forecasting`. You need a Kaggle account, an API token
in `~/.kaggle/kaggle.json`, and to have accepted the competition rules. Then:

```bash
python scripts/download_data.py --dest data/raw/jane
```

This downloads and extracts the competition files into `data/raw/jane/` (skipped with a
log message if `train.parquet` is already present). Optionally build a cleaned copy:

```bash
python scripts/preprocess.py --input data/raw/jane --output data/processed/jane --date-range 0 30 --max-rows 200000
```

## Usage

Train a single learner from a config (outputs `run.parquet`, `metrics.json`, and
`config.yaml` into the run directory):

```bash
python experiments/train.py --config configs/default.yaml
python experiments/train.py --config configs/synthetic.yaml --output results/runs/synthetic --seed 0 --max-steps 20000
python experiments/train.py --config configs/jane.yaml
```

`configs/jane.yaml` sets `standardize: true` on the dataset: the raw features span
several orders of magnitude (dynamic ranges beyond 1000), so gradient methods on
unscaled features diverge. Keep it on unless you scale features yourself.

Evaluate one or more finished runs (writes `loss_curve.png` per run and `comparison.csv`
when several run directories are given):

```bash
python experiments/evaluate.py --run-dir results/runs/default
python experiments/evaluate.py --run-dir results/runs/default results/runs/synthetic
```

Benchmark the full learner grid (OGD, AdaptiveClip, RobustOMD with each estimator) on one
dataset, with regret against the best fixed linear predictor:

```bash
python experiments/benchmark.py --config configs/synthetic.yaml --output results/benchmark
```

Run the estimator/window/clip-multiplier ablation sweep:

```bash
python experiments/ablation.py --config configs/ablation.yaml --output results/ablation
```

All experiment CLIs accept `--max-steps` to cap the stream length for quick smoke runs.

## Dataset facts (verified against the raw files)

| Fact                      | Value                                          |
| ------------------------- | ---------------------------------------------- |
| Rows                      | 47,127,338                                     |
| Features                  | 79 (`feature_00` … `feature_78`)               |
| Responders                | 9 (`responder_0` … `responder_8`)              |
| Trading days              | 1,699 (`date_id` 0 … 1698)                     |
| Symbols                   | 39                                             |
| Time steps per day (max)  | 968                                            |
| Competition target        | `responder_6`                                  |
| Competition metric        | sample-weighted zero-mean R²                   |

Additional notes: 47 of the 79 features contain nulls (up to 21.8% missing), there are no
constant features, responders are clipped to `[-5, 5]`, and `weight > 0` is the
evaluation sample weight. The metric is
`R² = 1 - Σ wᵢ (yᵢ - ŷᵢ)² / Σ wᵢ yᵢ²`.

## Testing

```bash
python -m pytest
```

The suite is deterministic, needs no network, and skips Jane Street tests automatically
when the raw data is absent.

## Project structure notes

The package uses a src layout: the import package `dfsl` lives under `src/dfsl` and must
be installed (`pip install -e .`) before running the tests or experiments. Library
modules never print, never show figures, and never configure logging at import time;
randomness flows only through numpy `Generator`s created from explicit seeds.

## License

MIT — see [LICENSE](LICENSE).
