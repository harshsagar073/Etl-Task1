
import logging
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
CLEAN_DIR = PROJECT_DIR / "data" / "clean"

FILES = {
    "employee": "dim_employee.csv",
    "payroll": "fact_payroll.csv",
    "attendance": "fact_attendance_monthly.csv",
    "leave": "fact_leave.csv",
}

DATE_COLUMNS = {
    "employee": [
        "date_of_birth",
        "hire_date",
        "exit_date",
        "valid_from",
        "valid_to",
    ],
    "payroll": ["period_end_date"],
    "attendance": ["period_end_date"],
    "leave": [
        "start_date",
        "end_date",
        "applied_on",
        "decided_on",
    ],
}

NUMERIC_COLUMNS = {
    "payroll": [
        "payable_days",
        "lop_days",
        "monthly_fixed_gross",
        "basic",
        "hra",
        "conveyance",
        "medical",
        "special_allowance",
        "earned_fixed_pay",
        "overtime_pay",
        "variable_pay",
        "gross_pay",
        "total_deductions",
        "net_pay",
        "employer_cost",
    ],
    "attendance": [
        "scheduled_days",
        "present_days",
        "wfh_days",
        "half_days_unpaid",
        "paid_leave_days",
        "unpaid_absence_days",
        "late_arrivals",
        "avg_hours_worked",
        "overtime_hours",
        "attendance_rate",
    ],
    "leave": ["days"],
}


def transform_data():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    for name, filename in FILES.items():
        raw_path = RAW_DIR / filename

        if not raw_path.exists():
            raise FileNotFoundError(
                f"Missing input file: {raw_path}"
            )

        df = pd.read_csv(raw_path, encoding="utf-8-sig")
        rows_before = len(df)

        # Normalize column names.
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        # Clean text fields without changing IDs.
        text_columns = df.select_dtypes(
            include=["object", "string"]
        ).columns

        for column in text_columns:
            df[column] = df[column].str.strip()

        # Remove exact duplicate rows.
        df = df.drop_duplicates().copy()
        duplicates_removed = rows_before - len(df)

        # Convert dates. Invalid dates become missing
        # and will be checked during validation.
        for column in DATE_COLUMNS.get(name, []):
            if column in df.columns:
                df[column] = pd.to_datetime(
                    df[column],
                    errors="coerce",
                )

        # Convert selected numeric columns.
        for column in NUMERIC_COLUMNS.get(name, []):
            if column in df.columns:
                numeric_values = (
                    df[column]
                    .astype("string")
                    .str.replace(",", "", regex=False)
                    .str.strip()
                )
                df[column] = pd.to_numeric(
                    numeric_values,
                    errors="coerce",
                )

        # Add helper columns based on available dates.
        date_source = None

        if name == "payroll" and "period_end_date" in df:
            date_source = "period_end_date"
        elif name == "attendance" and "period_end_date" in df:
            date_source = "period_end_date"
        elif name == "leave" and "start_date" in df:
            date_source = "start_date"
        elif name == "employee" and "hire_date" in df:
            date_source = "hire_date"

        if date_source:
            df["month"] = df[date_source].dt.month
            df["year"] = df[date_source].dt.year

       
        if name == "employee" and "hire_date" in df:
            # Fixed as-of date for repeatable tenure calculations.
            reference_date = pd.Timestamp("2026-10-13")
            df["tenure_days"] = (
                reference_date - df["hire_date"]
            ).dt.days

        output_path = CLEAN_DIR / filename
        df.to_csv(output_path, index=False, date_format="%Y-%m-%d")

        logging.info(
            "TRANSFORM | file=%s | input_rows=%s | output_rows=%s "
            "| duplicates_removed=%s | output=%s",
            filename,
            rows_before,
            len(df),
            duplicates_removed,
            output_path,
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    transform_data()
    logging.info("Transformation completed.")