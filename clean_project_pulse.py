"""
PROJECT PULSE AI - Data Cleaning Script
Requirements:
    pip install pandas openpyxl

Run:
    python clean_project_pulse.py

Place PROJECT_PULSE_RAW_DATA.xlsx in the same folder as this script.
Outputs:
    PROJECT_PULSE_CLEANED.xlsx
    PROJECT_PULSE_CLEANED.csv
"""
import pandas as pd
import numpy as np
import re
from pathlib import Path

INPUT_FILE = Path("PROJECT_PULSE_RAW_DATA.xlsx")
OUTPUT_EXCEL = Path("PROJECT_PULSE_CLEANED.xlsx")
OUTPUT_CSV = Path("PROJECT_PULSE_CLEANED.csv")

def clean_project_pulse(input_file):
    df = pd.read_excel(input_file, sheet_name="Raw_Data").copy()
    original_rows = len(df)
    log = []

    # 1. Remove only completely identical rows.
    exact_duplicates = int(df.drop(columns=["S.No"]).duplicated().sum())
    df = df.loc[~df.drop(columns=["S.No"]).duplicated()].copy()
    log.append(("Exact duplicate rows removed", exact_duplicates))

    # 2. Trim whitespace and standardize spacing in text columns.
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(
            lambda x: re.sub(r"\\s+", " ", x.strip()) if isinstance(x, str) else x
        )

    # 3. Standardize known category variants.
    project_map = {
        "project pulse ai": "Project Pulse AI",
        "smart food delivery": "Smart Food Delivery",
        "work x services": "WorkX Services",
    }
    df["Project"] = df["Project"].apply(
        lambda x: project_map.get(x.lower(), x) if isinstance(x, str) else x
    )

    role_map = {
        "qa eng.": "QA Engineer",
        "python developer": "Python Developer",
        "data analyst": "Data Analyst",
        "ml enginer": "ML Engineer",
    }
    df["Role"] = df["Role"].apply(
        lambda x: role_map.get(x.lower(), x) if isinstance(x, str) else x
    )

    status_map = {
        "available": "Available", "busy": "Busy", "assigned": "Assigned",
        "on leave": "On Leave", "partially available": "Partially Available",
        "free": "Available", "unknown": "Unknown",
    }
    df["Availability Status"] = df["Availability Status"].apply(
        lambda x: status_map.get(x.lower(), x.title()) if isinstance(x, str) else x
    )

    location_map = {
        "hyd": "Hyderabad", "hyderabad": "Hyderabad", "bengaluru,": "Bengaluru"
    }
    df["Location"] = df["Location"].apply(
        lambda x: location_map.get(x.lower(), x) if isinstance(x, str) else x
    )

    education_map = {
        "btech cse": "B.Tech CSE", "b.tech cse": "B.Tech CSE",
        "b tech cse": "B.Tech CSE",
        "b sc computer science": "B.Sc Computer Science",
        "b.sc computer science": "B.Sc Computer Science",
        "mca": "MCA",
    }
    df["Education"] = df["Education"].apply(
        lambda x: education_map.get(x.lower(), x) if isinstance(x, str) else x
    )

    # 4. Normalize skills separators and remove repeated skills.
    def normalize_skills(value):
        if not isinstance(value, str) or not value.strip():
            return np.nan
        parts = re.split(r"[,;/|]+", value)
        result, seen = [], set()
        for part in parts:
            skill = re.sub(r"\\s+", " ", part.strip())
            if skill and skill.lower() not in seen:
                result.append(skill)
                seen.add(skill.lower())
        return ", ".join(result) if result else np.nan

    df["Skills"] = df["Skills"].apply(normalize_skills)

    # 5. Convert numeric columns; impossible values become missing, then median.
    numeric_ranges = {
        "Experience (Years)": (0, 50),
        "No. of Projects Handled": (0, 200),
        "Rating (out of 5)": (0, 5),
        "Task Completion (%)": (0, 100),
        "Monthly Cost (INR)": (1, 500000),
        "Team Size": (1, 100),
        "Bugs Resolved": (0, 10000),
        "On-time Delivery (%)": (0, 100),
    }
    for col, (minimum, maximum) in numeric_ranges.items():
        values = pd.to_numeric(df[col], errors="coerce")
        invalid = values.notna() & ((values < minimum) | (values > maximum))
        invalid_count = int(invalid.sum())
        values = values.mask(invalid)
        missing_count = int(values.isna().sum())
        median = values.median()
        df[col] = values.fillna(median)
        log.append((f"{col}: range check and median fill",
                    f"{invalid_count} invalid; {missing_count} missing/non-numeric filled; median={median:.2f}"))

    # 6. Parse dates. Invalid or missing dates are left blank.
    df["Date Joined"] = pd.to_datetime(df["Date Joined"], errors="coerce")
    log.append(("Date Joined: parse dates; invalid dates left blank",
                int(df["Date Joined"].isna().sum())))

    # 7. Fill missing text categories with 'Unknown'.
    for col in ["Name", "Project", "Role", "Skills", "Availability Status",
                "Location", "Education"]:
        df[col] = df[col].fillna("Unknown")

    # 8. Preserve duplicate IDs, but create unique IDs with a suffix.
    df["Employee ID Raw"] = df["Employee ID"].astype(str)
    counts, unique_ids = {}, []
    for employee_id in df["Employee ID Raw"]:
        counts[employee_id] = counts.get(employee_id, 0) + 1
        unique_ids.append(
            employee_id if counts[employee_id] == 1
            else f"{employee_id}-DUP{counts[employee_id]-1:02d}"
        )
    df["Employee ID"] = unique_ids
    log.append(("Repeated Employee IDs: suffix added; records preserved",
                int(df["Employee ID Raw"].duplicated(keep=False).sum())))

    # 9. Regenerate serial numbers.
    df["S.No"] = range(1, len(df) + 1)

    log_df = pd.DataFrame(log, columns=["Cleaning Step", "Result / Count"])
    summary = pd.DataFrame({
        "Metric": ["Original rows", "Cleaned rows", "Exact duplicate rows removed",
                   "Missing values remaining", "Unique Employee IDs"],
        "Value": [original_rows, len(df), exact_duplicates,
                  int(df.isna().sum().sum()), df["Employee ID"].nunique()]
    })
    return df, log_df, summary

if __name__ == "__main__":
    cleaned, log, summary = clean_project_pulse(INPUT_FILE)
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl",
                        datetime_format="yyyy-mm-dd") as writer:
        cleaned.to_excel(writer, sheet_name="Cleaned_Data", index=False)
        log.to_excel(writer, sheet_name="Cleaning_Log", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
    cleaned.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print("Cleaning completed successfully!")
    print(summary.to_string(index=False))
    print(f"Saved: {OUTPUT_EXCEL.resolve()}")
    print(f"Saved: {OUTPUT_CSV.resolve()}")
