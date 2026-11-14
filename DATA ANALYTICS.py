"""
PROJECT PULSE — Analytics & Visualization
-----------------------------------------
Input : PROJECT_PULSE_CLEANED.csv
Output: project_pulse_outputs/ (summary CSVs, text report, and PNG charts)

Install dependencies:
    pip install pandas matplotlib

Run:
    python PROJECT_PULSE_ANALYTICS_VISUALIZATION.py

Optional custom input/output:
    python PROJECT_PULSE_ANALYTICS_VISUALIZATION.py --input "PROJECT_PULSE_CLEANED.csv" --output "project_pulse_outputs"
"""

from pathlib import Path
import argparse
import re
import pandas as pd
import matplotlib.pyplot as plt


NUMERIC_COLUMNS = [
    "Experience (Years)",
    "No. of Projects Handled",
    "Rating (out of 5)",
    "Task Completion (%)",
    "Monthly Cost (INR)",
    "Team Size",
    "Bugs Resolved",
    "On-time Delivery (%)",
]


def safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")


def save_chart(filename):
    plt.tight_layout()
    plt.savefig(filename, dpi=160, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Analyze and visualize the Project Pulse employee/project dataset.")
    parser.add_argument("--input", default="PROJECT_PULSE_CLEANED.csv", help="Path to cleaned CSV file")
    parser.add_argument("--output", default="project_pulse_outputs", help="Folder for reports and charts")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    charts_dir = output_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Could not find {input_path}. Place the CSV in the same folder as this script "
            "or pass its location using --input."
        )

    df = pd.read_csv(input_path)
    if df.empty:
        raise ValueError("The input CSV contains no rows.")

    # Convert numeric and date fields safely.
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Date Joined" in df.columns:
        df["Date Joined"] = pd.to_datetime(df["Date Joined"], errors="coerce")

    required = ["Employee ID", "Project", "Role", "Availability Status"]
    missing_required = [col for col in required if col not in df.columns]
    if missing_required:
        raise ValueError("Missing expected columns: " + ", ".join(missing_required))

    total_records = len(df)
    unique_employees = df["Employee ID"].nunique()
    project_count = df["Project"].nunique()
    role_count = df["Role"].nunique()
    avg_rating = df["Rating (out of 5)"].mean() if "Rating (out of 5)" in df else float("nan")
    avg_completion = df["Task Completion (%)"].mean() if "Task Completion (%)" in df else float("nan")
    avg_delivery = df["On-time Delivery (%)"].mean() if "On-time Delivery (%)" in df else float("nan")
    total_monthly_cost = df["Monthly Cost (INR)"].sum() if "Monthly Cost (INR)" in df else float("nan")
    total_bugs = df["Bugs Resolved"].sum() if "Bugs Resolved" in df else float("nan")

    # Export reusable analytical tables.
    df.describe(include="all").transpose().to_csv(output_dir / "descriptive_statistics.csv")
    df.isna().sum().rename("Missing Values").to_csv(output_dir / "missing_values.csv")

    for column in ["Project", "Role", "Availability Status", "Location", "Education"]:
        if column in df.columns:
            (df[column].fillna("Unknown").value_counts()
             .rename_axis(column).reset_index(name="Employee Count")
             .to_csv(output_dir / f"{safe_filename(column.lower())}_counts.csv", index=False))

    if "Project" in df.columns and "Task Completion (%)" in df.columns:
        (df.groupby("Project", dropna=False)
         .agg(Employee_Count=("Employee ID", "nunique"),
              Avg_Task_Completion=("Task Completion (%)", "mean"),
              Avg_Rating=("Rating (out of 5)", "mean"),
              Total_Bugs_Resolved=("Bugs Resolved", "sum"),
              Avg_On_Time_Delivery=("On-time Delivery (%)", "mean"))
         .reset_index().sort_values("Employee_Count", ascending=False)
         .to_csv(output_dir / "project_performance_summary.csv", index=False))

    # 1. Employees by project — horizontal bar chart.
    project_counts = df["Project"].fillna("Unknown").value_counts().sort_values()
    plt.figure(figsize=(10, max(5, len(project_counts) * 0.38)))
    project_counts.plot(kind="barh")
    plt.title("Employees by Project")
    plt.xlabel("Number of Employees")
    plt.ylabel("Project")
    save_chart(charts_dir / "01_employees_by_project.png")

    # 2. Availability mix — pie chart.
    availability = df["Availability Status"].fillna("Unknown").value_counts()
    plt.figure(figsize=(7, 7))
    plt.pie(availability.values, labels=availability.index, autopct="%1.1f%%", startangle=90)
    plt.title("Employee Availability Distribution")
    save_chart(charts_dir / "02_availability_distribution.png")

    # 3. Experience distribution — histogram.
    if "Experience (Years)" in df:
        plt.figure(figsize=(9, 5))
        df["Experience (Years)"].dropna().plot(kind="hist", bins=15, edgecolor="black")
        plt.title("Employee Experience Distribution")
        plt.xlabel("Experience (Years)")
        plt.ylabel("Employee Count")
        save_chart(charts_dir / "03_experience_distribution.png")

    # 4. Task completion by role — horizontal bar chart.
    if "Task Completion (%)" in df:
        role_completion = (df.groupby("Role")["Task Completion (%)"].mean()
                           .dropna().sort_values())
        plt.figure(figsize=(10, max(5, len(role_completion) * 0.38)))
        role_completion.plot(kind="barh")
        plt.title("Average Task Completion by Role")
        plt.xlabel("Average Task Completion (%)")
        plt.ylabel("Role")
        save_chart(charts_dir / "04_task_completion_by_role.png")

    # 5. Experience vs rating — scatter plot.
    if {"Experience (Years)", "Rating (out of 5)"}.issubset(df.columns):
        plot_data = df[["Experience (Years)", "Rating (out of 5)"]].dropna()
        plt.figure(figsize=(8, 5))
        plt.scatter(plot_data["Experience (Years)"], plot_data["Rating (out of 5)"], alpha=0.55)
        plt.title("Employee Experience vs Rating")
        plt.xlabel("Experience (Years)")
        plt.ylabel("Rating (out of 5)")
        save_chart(charts_dir / "05_experience_vs_rating.png")

    # 6. Monthly cost by project — box plot.
    if "Monthly Cost (INR)" in df:
        box_data = [group["Monthly Cost (INR)"].dropna().values
                    for _, group in df.groupby("Project")]
        labels = [str(name) for name, _ in df.groupby("Project")]
        if box_data:
            plt.figure(figsize=(max(10, len(labels) * 0.8), 6))
            plt.boxplot(box_data, tick_labels=labels, showfliers=False)
            plt.title("Monthly Employee Cost by Project")
            plt.xlabel("Project")
            plt.ylabel("Monthly Cost (INR)")
            plt.xticks(rotation=35, ha="right")
            save_chart(charts_dir / "06_monthly_cost_by_project.png")

    # 7. Bugs resolved vs on-time delivery — scatter plot.
    if {"Bugs Resolved", "On-time Delivery (%)"}.issubset(df.columns):
        plot_data = df[["Bugs Resolved", "On-time Delivery (%)"]].dropna()
        plt.figure(figsize=(8, 5))
        plt.scatter(plot_data["Bugs Resolved"], plot_data["On-time Delivery (%)"], alpha=0.55)
        plt.title("Bugs Resolved vs On-time Delivery")
        plt.xlabel("Bugs Resolved")
        plt.ylabel("On-time Delivery (%)")
        save_chart(charts_dir / "07_bugs_vs_delivery.png")

    # 8. Joining trend — line chart by year.
    if "Date Joined" in df:
        joined_year = df.dropna(subset=["Date Joined"]).groupby(
            df["Date Joined"].dropna().dt.year
        ).size()
        if not joined_year.empty:
            plt.figure(figsize=(9, 5))
            joined_year.plot(kind="line", marker="o")
            plt.title("Employee Joining Trend")
            plt.xlabel("Joining Year")
            plt.ylabel("Number of Employees")
            plt.grid(True, alpha=0.3)
            save_chart(charts_dir / "08_employee_joining_trend.png")

    # 9. Correlation heatmap (matplotlib only).
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] >= 2:
        corr = numeric.corr()
        fig, ax = plt.subplots(figsize=(11, 8))
        image = ax.imshow(corr, aspect="auto", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right")
        ax.set_yticklabels(corr.columns)
        ax.set_title("Numeric Variable Correlation Matrix")
        fig.colorbar(image, ax=ax, label="Correlation")
        save_chart(charts_dir / "09_correlation_matrix.png")
        corr.to_csv(output_dir / "correlation_matrix.csv")

    # Text report with key metrics and highest/lowest project averages.
    report = [
        "PROJECT PULSE — DATA ANALYTICS REPORT",
        "=" * 42,
        f"Input file: {input_path.name}",
        f"Total records: {total_records:,}",
        f"Unique employees: {unique_employees:,}",
        f"Projects represented: {project_count:,}",
        f"Roles represented: {role_count:,}",
        f"Average rating: {avg_rating:.2f} / 5" if pd.notna(avg_rating) else "Average rating: Not available",
        f"Average task completion: {avg_completion:.2f}%" if pd.notna(avg_completion) else "Average task completion: Not available",
        f"Average on-time delivery: {avg_delivery:.2f}%" if pd.notna(avg_delivery) else "Average on-time delivery: Not available",
        f"Total monthly employee cost: INR {total_monthly_cost:,.0f}" if pd.notna(total_monthly_cost) else "Total monthly employee cost: Not available",
        f"Total bugs resolved: {total_bugs:,.0f}" if pd.notna(total_bugs) else "Total bugs resolved: Not available",
        "",
        "Availability counts:",
    ]
    report.extend(f"  - {key}: {value}" for key, value in availability.items())
    report += [
        "",
        "Data quality:",
        f"  - Missing cells: {int(df.isna().sum().sum()):,}",
        f"  - Duplicate rows: {int(df.duplicated().sum()):,}",
        "",
        f"Charts saved in: {charts_dir.resolve()}",
        f"Tables and report saved in: {output_dir.resolve()}",
    ]
    (output_dir / "analytics_report.txt").write_text("\n".join(report), encoding="utf-8")

    print("\n".join(report))
    print("\nAnalysis completed successfully.")


if __name__ == "__main__":
    main()
