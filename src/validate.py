
import logging
from pathlib import Path

import pandas as pd
import pandera.pandas as pa


PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = PROJECT_DIR / "data" / "clean"
REJECTED_DIR = PROJECT_DIR / "rejected"

FILES = {
    "employee": "dim_employee.csv",
    "payroll": "fact_payroll.csv",
    "attendance": "fact_attendance_monthly.csv",
    "leave": "fact_leave.csv",
}


def employee_schema():
    return pa.DataFrameSchema(
        {
            "employee_key": pa.Column(int, nullable=False, unique=True),
            "employee_id": pa.Column(str, nullable=False),
        },
        strict=False,
        coerce=True,
    )


def payroll_schema():
    return pa.DataFrameSchema(
        {
            "gross_pay": pa.Column(float, nullable=False),
            "net_pay": pa.Column(float, nullable=False),
        },
        strict=False,
        coerce=True,
    )


def validate_file(name, filename):
    path = CLEAN_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Clean file not found: {path}")

    df = pd.read_csv(path)
    original_count = len(df)
    df["_source_file"] = filename

    rejection_reasons = pd.Series("", index=df.index, dtype="object")

    def flag(mask, reason):
        mask = mask.fillna(False)
        existing = rejection_reasons.loc[mask]
        rejection_reasons.loc[mask] = existing.apply(
            lambda value: f"{value}; {reason}" if value else reason
        )

    def check_id(column, prefix, unique=False):
        if column not in df.columns:
            raise ValueError(
                f"Required column '{column}' missing from {filename}"
            )

        values = df[column].astype("string").str.strip()
        flag(
            values.isna() | values.eq(""),
            f"missing_{prefix}",
        )

        if unique:
            flag(
                values.duplicated(keep=False),
                f"duplicate_{prefix}",
            )

    def check_date(column, required=False):
        if column not in df.columns:
            raise ValueError(
                f"Required date column '{column}' missing from {filename}"
            )

        raw = df[column]
        empty = raw.isna() | raw.astype("string").str.strip().eq("")
        parsed = pd.to_datetime(raw, errors="coerce")

        if required:
            flag(empty, f"missing_{column}")

        flag(
            ~empty & parsed.isna(),
            f"invalid_{column}",
        )

        return parsed

    def check_nonnegative(columns):
        for column in columns:
            if column not in df.columns:
                continue

            raw = df[column]
            values = pd.to_numeric(raw.astype("string").str.replace(",", "", regex=False).str.strip(), errors="coerce")
            nonempty = raw.notna() & raw.astype("string").str.strip().ne("")

            flag(
                nonempty & values.isna(),
                f"invalid_{column}",
            )
            flag(values < 0, f"negative_{column}")

    # Employee records
    if name == "employee":
        check_id("employee_key", "employee_key", unique=True)
        check_id("employee_id", "employee_id", unique=False)

        hire = check_date("hire_date", required=True)
        exit_date = check_date("exit_date")

        for column in ["date_of_birth", "valid_from", "valid_to"]:
            if column in df.columns:
                check_date(column)

        flag(
            hire.notna()
            & exit_date.notna()
            & (hire > exit_date),
            "hire_date_after_exit_date",
        )

    # Payroll records
    elif name == "payroll":
        check_id("payroll_item_id", "payroll_item_id", unique=True)
        check_id("employee_id", "employee_id")
        check_date("period_end_date", required=True)

        check_nonnegative([
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
            "net_pay",
            "total_deductions",
            "employer_cost",
            "payable_days",
            "lop_days",
        ])

        for column in ["gross_pay", "net_pay"]:
            raw = df[column]
            values = pd.to_numeric(raw.astype("string").str.replace(",", "", regex=False).str.strip(), errors="coerce")
            flag(values.isna(), f"missing_or_invalid_{column}")

    # Attendance records
    elif name == "attendance":
        check_id(
            "attendance_fact_id",
            "attendance_fact_id",
            unique=True,
        )
        check_id("employee_id", "employee_id")
        check_date("period_end_date", required=True)

        check_nonnegative([
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
        ])

    # Leave records
    elif name == "leave":
        check_id("leave_request_id", "leave_request_id", unique=True)
        check_id("employee_id", "employee_id")

        start = check_date("start_date", required=True)
        end = check_date("end_date", required=True)
        check_date("applied_on")
        check_date("decided_on")

        flag(
            start.notna() & end.notna() & (start > end),
            "start_date_after_end_date",
        )

        check_nonnegative(["days"])

    # Separate invalid rows from accepted rows.
    rejected_mask = rejection_reasons.ne("")
    rejected = df.loc[rejected_mask].copy()
    rejected["rejection_reason"] = rejection_reasons.loc[rejected_mask]

    accepted = df.loc[~rejected_mask].drop(
        columns=["_source_file"]
    ).copy()

    # Apply Pandera schemas to the accepted records.
    try:
        if name == "employee":
            employee_schema().validate(accepted, lazy=True)
        elif name == "payroll":
            payroll_schema().validate(accepted, lazy=True)
    except pa.errors.SchemaErrors as error:
        logging.exception("Pandera schema validation failed for %s", filename)
        raise ValueError(
            f"Pandera validation failed for {filename}; "
            "pipeline stopped."
        ) from error

    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    rejected_path = REJECTED_DIR / f"rejected_{filename}"

    if not rejected.empty:
        rejected.to_csv(rejected_path, index=False)
        logging.info("Rejected rows saved to %s", rejected_path)
    elif rejected_path.exists():
        rejected_path.unlink()

    accepted_path = CLEAN_DIR / filename
    accepted.to_csv(accepted_path, index=False)

    logging.info(
        "VALIDATE | file=%s | input=%d | accepted=%d | rejected=%d",
        filename,
        original_count,
        len(accepted),
        len(rejected),
    )


def validate_all():
    for name, filename in FILES.items():
        validate_file(name, filename)

    logging.info("Validation completed.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    validate_all()