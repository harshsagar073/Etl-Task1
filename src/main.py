
import logging
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_DIR / "src"))

from extract import setup_logging, extract_data
from transform import transform_data
from validate import validate_all


def main():
    setup_logging()

    logging.info("========== ETL PIPELINE STARTED ==========")

    try:
        # Read and log the raw source files.
        extract_data()

        # Transform raw data into data/clean.
        transform_data()

        # Validate clean files and save rejected rows.
        validate_all()

        logging.info("========== ETL PIPELINE COMPLETED ==========")

    except Exception:
        logging.exception("ETL PIPELINE FAILED")
        raise


if __name__ == "__main__":
    main()