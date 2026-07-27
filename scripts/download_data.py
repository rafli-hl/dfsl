"""Download the Jane Street Kaggle competition data via the kaggle CLI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from dfsl.utils.io import ensure_dir, find_project_root
from dfsl.utils.logger import get_logger

COMPETITION = "jane-street-real-time-market-data-forecasting"


def main(argv: list[str] | None = None) -> int:
    """Download and extract the competition data; return a process exit code."""
    parser = argparse.ArgumentParser(description="Download the Jane Street competition data.")
    parser.add_argument(
        "--dest",
        default=None,
        help="Destination directory (default: data/raw/jane under the project root).",
    )
    args = parser.parse_args(argv)

    logger = get_logger()
    root = find_project_root(Path(__file__).resolve().parent)
    if args.dest is not None:
        dest = Path(args.dest)
        if not dest.is_absolute():
            dest = root / dest
    else:
        dest = root / "data" / "raw" / "jane"

    if (dest / "train.parquet").exists():
        logger.info("Jane Street data already present at {}; nothing to do.", dest)
        return 0

    if shutil.which("kaggle") is None:
        print(
            "The 'kaggle' CLI was not found. To download the data:\n"
            "  1. pip install kaggle\n"
            "  2. Create an API token at https://www.kaggle.com/settings and save it\n"
            "     as kaggle.json in ~/.kaggle (chmod 600 on Unix).\n"
            f"  3. Accept the competition rules for '{COMPETITION}' on Kaggle.\n"
            "  4. Re-run: python scripts/download_data.py"
        )
        return 1

    ensure_dir(dest)
    logger.info("Downloading competition '{}' into {} ...", COMPETITION, dest)
    subprocess.run(
        ["kaggle", "competitions", "download", "-c", COMPETITION, "-p", str(dest)],
        check=True,
    )
    for zip_path in sorted(dest.glob("*.zip")):
        logger.info("Extracting {} ...", zip_path.name)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(dest)
        zip_path.unlink()
    logger.info("Done. Data available at {}", dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
