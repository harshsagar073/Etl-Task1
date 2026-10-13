
import logging
from pathlib import Path

import pandas as pd

# Project folders
PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
LOG_DIR = PROJECT_DIR / "logs"

FILES = {
    "employee": "dim_employee.csv",
    "payroll": "fact_payroll.csv",
    "attendance": "fact_attendance_monthly.csv",
    "leave": "fact_leave.csv",
}


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "etl.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def extract_data():
    data = {}

    for name, filename in FILES.items():
        file_path = RAW_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required input file not found: {file_path}"
            )

        df = pd.read_csv(file_path, encoding="utf-8-sig")
        data[name] = df

        logging.info(
            "EXTRACT | file=%s | rows=%s | columns=%s",
            filename,
            len(df),
            len(df.columns),
        )

    return data


if __name__ == "__main__":
    setup_logging()
    extract_data()
    logging.info("Extraction completed successfully.")