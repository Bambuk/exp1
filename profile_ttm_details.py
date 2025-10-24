#!/usr/bin/env python3
"""Profile TTM Details report generation to identify bottlenecks."""

import cProfile
import pstats
import time
from io import StringIO

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator
from radiator.core.database import SessionLocal


def profile_ttm_details_generation():
    """Profile TTM Details report generation with detailed timing."""
    print("🔍 Starting TTM Details report profiling...")

    start_time = time.time()

    with SessionLocal() as db:
        print(f"⏱️  Database connection: {time.time() - start_time:.2f}s")

        # Create generator
        generator_start = time.time()
        generator = TTMDetailsReportGenerator(db=db)
        print(f"⏱️  Generator creation: {time.time() - generator_start:.2f}s")

        # Load quarters
        quarters_start = time.time()
        quarters = generator._load_quarters()
        print(
            f"⏱️  Load quarters ({len(quarters)}): {time.time() - quarters_start:.2f}s"
        )

        # Load done statuses
        statuses_start = time.time()
        done_statuses = generator._load_done_statuses()
        print(
            f"⏱️  Load done statuses ({len(done_statuses)}): {time.time() - statuses_start:.2f}s"
        )

        # Collect CSV rows (main processing)
        csv_start = time.time()
        rows = generator._collect_csv_rows()
        csv_time = time.time() - csv_start
        print(f"⏱️  Collect CSV rows ({len(rows)} tasks): {csv_time:.2f}s")

        # Generate CSV file
        file_start = time.time()
        output_path = "data/reports/profiled_ttm_details.csv"
        result_path = generator.generate_csv(output_path)
        file_time = time.time() - file_start
        print(f"⏱️  Generate CSV file: {file_time:.2f}s")

        total_time = time.time() - start_time
        print(f"⏱️  Total time: {total_time:.2f}s")

        # Breakdown by quarter
        print("\n📊 Breakdown by quarter:")
        for quarter in quarters:
            quarter_start = time.time()
            tasks = generator._get_ttm_tasks_for_quarter(quarter)
            quarter_time = time.time() - quarter_start
            print(f"  {quarter.name}: {len(tasks)} tasks in {quarter_time:.2f}s")

        return result_path


def profile_with_cprofile():
    """Profile with cProfile for detailed function call analysis."""
    print("\n🔍 Detailed profiling with cProfile...")

    def run_generation():
        with SessionLocal() as db:
            generator = TTMDetailsReportGenerator(db=db)
            return generator.generate_csv("data/reports/cprofiled_ttm_details.csv")

    # Run with cProfile
    pr = cProfile.Profile()
    pr.enable()
    result_path = run_generation()
    pr.disable()

    # Analyze results
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)  # Top 20 functions

    print("Top 20 functions by cumulative time:")
    print(s.getvalue())

    return result_path


if __name__ == "__main__":
    # Basic timing profile
    profile_ttm_details_generation()

    # Detailed cProfile analysis
    profile_with_cprofile()
