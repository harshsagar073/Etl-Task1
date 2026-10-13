cat > metrics_dictionary.md <<'EOF'
# PulseIQ ETL Pipeline — Metric Dictionary

## 1. Employee Headcount
- Definition: Number of distinct employees for a reporting period.
- Source: dim_employee.csv
- Calculation: Count distinct employee IDs, applying the appropriate employment-status and reporting-period rules.

## 2. Gross Payroll
- Definition: Total gross pay for a payroll period.
- Source: fact_payroll.csv
- Calculation: Sum of gross_pay for the selected payroll period.

## 3. Net Payroll
- Definition: Total net pay after employee deductions.
- Source: fact_payroll.csv
- Calculation: Sum of net_pay for the selected payroll period.

## 4. Attendance Rate
- Definition: Percentage of scheduled days attended.
- Source: fact_attendance_monthly.csv
- Calculation: Sum of present_days / Sum of scheduled_days * 100, where scheduled_days is greater than zero.
- Note: Confirm the company's rules for paid leave and half-days before using this as an official KPI.

## 5. Rejected Record Rate
- Definition: Percentage of input records rejected during validation.
- Source: ETL validation logs and rejected CSV files.
- Calculation: Total rejected records / Total input records * 100.
- Current run: 2 rejected records out of 19,734 input records, approximately 0.0101%.
EOF