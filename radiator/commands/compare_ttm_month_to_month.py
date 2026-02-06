#!/usr/bin/env python3
"""
Compare TTM Details reports month-to-month by team.

This script compares two TTM Details CSV reports and shows:
- WiP count (tasks in progress)
- Median DevLT

Filtering rules:
- Only tasks with Разработка = 1
- Only tasks with empty Квартал (considered as WiP)
- Only tasks with non-empty DevLT
"""

import csv
import sys
from pathlib import Path
from statistics import mean, median, quantiles
from typing import Dict, List, Optional


def load_csv_data(filepath: str) -> List[Dict[str, str]]:
    """
    Load CSV file and return list of dictionaries.

    Args:
        filepath: Path to CSV file

    Returns:
        List of row dictionaries
    """
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def filter_wip_tasks(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Filter tasks according to rules:
    - Разработка = 1
    - Квартал is empty (WiP)
    - DevLT is not empty

    Args:
        rows: List of row dictionaries

    Returns:
        Filtered list of tasks
    """
    filtered = []
    for row in rows:
        # Check Разработка = 1
        if row.get("Разработка", "").strip() != "1":
            continue

        # Check Квартал is empty (WiP)
        quarter = row.get("Квартал", "").strip()
        if quarter:  # Not empty = not WiP
            continue

        # Check DevLT is not empty
        devlt = row.get("DevLT", "").strip()
        if not devlt:
            continue

        # Try to parse DevLT as number
        try:
            float(devlt)
            filtered.append(row)
        except ValueError:
            # Skip if DevLT is not a valid number
            continue

    return filtered


def aggregate_by_team(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, any]]:
    """
    Aggregate tasks by team.

    Args:
        rows: Filtered list of tasks

    Returns:
        Dictionary with team name as key and aggregated data as value:
        {
            "team_name": {
                "wip_count": int,
                "median_devlt": float,
                "mean_devlt": float,
                "p85_devlt": float
            }
        }
    """
    teams = {}

    for row in rows:
        team = row.get("Команда", "").strip()
        if not team:
            team = "Без команды"

        devlt = float(row.get("DevLT", "0"))

        if team not in teams:
            teams[team] = {"devlt_values": []}

        teams[team]["devlt_values"].append(devlt)

    # Calculate statistics for each team
    result = {}
    for team, data in teams.items():
        devlt_values = data["devlt_values"]

        if devlt_values:
            # Calculate 85th percentile using quantiles
            # quantiles(data, n=100) gives 99 cut points (percentiles 1-99)
            # For 85th percentile, we need the 85th element (index 84)
            if len(devlt_values) == 1:
                p85 = devlt_values[0]
            else:
                try:
                    percentiles = quantiles(devlt_values, n=100)
                    p85 = percentiles[84]  # 85th percentile (0-indexed)
                except:
                    # Fallback for edge cases
                    sorted_values = sorted(devlt_values)
                    idx = int(0.85 * len(sorted_values))
                    p85 = sorted_values[min(idx, len(sorted_values) - 1)]

            result[team] = {
                "wip_count": len(devlt_values),
                "median_devlt": round(median(devlt_values), 1),
                "mean_devlt": round(mean(devlt_values), 1),
                "p85_devlt": round(p85, 1),
            }
        else:
            result[team] = {
                "wip_count": 0,
                "median_devlt": 0.0,
                "mean_devlt": 0.0,
                "p85_devlt": 0.0,
            }

    return result


def compare_months(
    prev_month_data: Dict[str, Dict[str, any]],
    current_month_data: Dict[str, Dict[str, any]],
) -> List[List[any]]:
    """
    Compare data from two months and prepare table rows.

    Args:
        prev_month_data: Aggregated data from previous month
        current_month_data: Aggregated data from current month

    Returns:
        List of table rows for tabulate
    """
    # Get all unique teams
    all_teams = set(prev_month_data.keys()) | set(current_month_data.keys())

    default_data = {
        "wip_count": 0,
        "median_devlt": 0.0,
        "mean_devlt": 0.0,
        "p85_devlt": 0.0,
    }

    rows = []
    for team in sorted(all_teams):
        prev = prev_month_data.get(team, default_data)
        curr = current_month_data.get(team, default_data)

        rows.append(
            [
                team,
                prev["wip_count"],
                curr["wip_count"],
                prev["median_devlt"],
                curr["median_devlt"],
                prev["mean_devlt"],
                curr["mean_devlt"],
                prev["p85_devlt"],
                curr["p85_devlt"],
            ]
        )

    return rows


def main():
    """Main function."""
    if len(sys.argv) != 3:
        print(
            "Usage: python compare_ttm_month_to_month.py <prev_month_csv> <current_month_csv>"
        )
        print()
        print("Example:")
        print("  python compare_ttm_month_to_month.py \\")
        print("    data/reports/new_ttm_details_20260206_123124_aod_20260118.csv \\")
        print("    data/reports/new_ttm_details_20260206_123133.csv")
        sys.exit(1)

    prev_month_file = sys.argv[1]
    current_month_file = sys.argv[2]

    # Check files exist
    if not Path(prev_month_file).exists():
        print(f"Error: File not found: {prev_month_file}")
        sys.exit(1)

    if not Path(current_month_file).exists():
        print(f"Error: File not found: {current_month_file}")
        sys.exit(1)

    print(f"📊 Comparing TTM Details reports month-to-month")
    print(f"   Previous month: {prev_month_file}")
    print(f"   Current month:  {current_month_file}")
    print()

    # Load data
    print("📥 Loading data...")
    prev_month_rows = load_csv_data(prev_month_file)
    current_month_rows = load_csv_data(current_month_file)
    print(f"   Previous month: {len(prev_month_rows)} tasks")
    print(f"   Current month:  {len(current_month_rows)} tasks")
    print()

    # Filter WiP tasks
    print("🔍 Filtering WiP tasks (Разработка=1, Квартал empty, DevLT not empty)...")
    prev_month_filtered = filter_wip_tasks(prev_month_rows)
    current_month_filtered = filter_wip_tasks(current_month_rows)
    print(f"   Previous month: {len(prev_month_filtered)} WiP tasks")
    print(f"   Current month:  {len(current_month_filtered)} WiP tasks")
    print()

    # Aggregate by team
    print("📊 Aggregating by team...")
    prev_month_agg = aggregate_by_team(prev_month_filtered)
    current_month_agg = aggregate_by_team(current_month_filtered)
    print(f"   Previous month: {len(prev_month_agg)} teams")
    print(f"   Current month:  {len(current_month_agg)} teams")
    print()

    # Compare and display results
    print("📈 Month-to-Month Comparison by Team:")
    print()

    comparison_rows = compare_months(prev_month_agg, current_month_agg)

    headers = [
        "Команда",
        "WiP (пред.)",
        "WiP (тек.)",
        "Med. DLT (пред.)",
        "Med. DLT (тек.)",
        "Ср. DLT (пред.)",
        "Ср. DLT (тек.)",
        "P85 DLT (пред.)",
        "P85 DLT (тек.)",
    ]

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in comparison_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = " | ".join(
        headers[i].ljust(col_widths[i]) for i in range(len(headers))
    )
    separator = "-+-".join("-" * w for w in col_widths)
    print(header_line)
    print(separator)

    # Print rows
    for row in comparison_rows:
        row_line = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
        print(row_line)

    print()

    # Summary statistics
    total_prev_wip = sum(row[1] for row in comparison_rows)
    total_curr_wip = sum(row[2] for row in comparison_rows)
    print(
        f"📊 Total WiP: {total_prev_wip} → {total_curr_wip} (Δ {total_curr_wip - total_prev_wip:+d})"
    )


if __name__ == "__main__":
    main()
