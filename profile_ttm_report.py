#!/usr/bin/env python
"""Profile TTM report generation to find performance bottlenecks."""

import cProfile
import pstats
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from radiator.commands.generate_time_to_market_report import (
    GenerateTimeToMarketReportCommand,
)
from radiator.commands.models.time_to_market_models import GroupBy

# Global profiler instance
profiler = None


def save_profile_data(signum=None, frame=None):
    """Save profile data on signal or normal exit."""
    global profiler

    if profiler is None:
        return

    print(f"\n\n⚠️  Received signal {signum}, saving profile data...", flush=True)
    profiler.disable()

    # Save to file
    stats_file = "ttm_profile_stats.prof"
    profiler.dump_stats(stats_file)
    print(f"✅ Profile data saved to: {stats_file}", flush=True)

    # Print quick summary
    print("\n📊 QUICK SUMMARY (Top 20 by cumulative time):", flush=True)
    print("-" * 80, flush=True)
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")
    stats.print_stats(20)

    sys.exit(0)


def run_report():
    """Run TTM report generation."""
    print("🔍 Starting TTM report generation with profiling...", flush=True)
    print("⏱️  Timeout: 1 minute (60 seconds)", flush=True)
    print("📊 Профилировщик запущен...\n", flush=True)

    try:
        print("Creating command...", flush=True)
        with GenerateTimeToMarketReportCommand(
            group_by=GroupBy.TEAM, config_dir="data/config"
        ) as command:
            print("Generating report data...", flush=True)
            report = command.generate_report_data()
            print(
                f"\n✅ Report generated with {len(report.quarter_reports)} quarters",
                flush=True,
            )
    except Exception as e:
        print(f"\n❌ Error in run_report: {e}", flush=True)
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGTERM, save_profile_data)
    signal.signal(signal.SIGINT, save_profile_data)

    # Create profiler
    profiler = cProfile.Profile()

    try:
        # Run with profiling
        profiler.enable()
        run_report()
        profiler.disable()

        print("\n" + "=" * 80)
        print("📊 PROFILING RESULTS")
        print("=" * 80 + "\n")

        # Save to file
        stats_file = "ttm_profile_stats.prof"
        profiler.dump_stats(stats_file)
        print(f"✅ Profile data saved to: {stats_file}")

        # Print statistics
        stats = pstats.Stats(profiler)

        # Sort by cumulative time
        print("\n" + "-" * 80)
        print("TOP 30 FUNCTIONS BY CUMULATIVE TIME:")
        print("-" * 80)
        stats.sort_stats("cumulative")
        stats.print_stats(30)

        # Sort by total time
        print("\n" + "-" * 80)
        print("TOP 30 FUNCTIONS BY TOTAL TIME:")
        print("-" * 80)
        stats.sort_stats("tottime")
        stats.print_stats(30)

        # Sort by number of calls
        print("\n" + "-" * 80)
        print("TOP 30 MOST CALLED FUNCTIONS:")
        print("-" * 80)
        stats.sort_stats("ncalls")
        stats.print_stats(30)

        print("\n" + "=" * 80)
        print("✅ Profiling complete!")
        print("=" * 80)

    except KeyboardInterrupt:
        profiler.disable()
        print("\n\n⚠️  Interrupted by user (Ctrl+C)")
        print("💾 Saving profile data...")

        # Save partial results
        stats_file = "ttm_profile_stats_partial.prof"
        profiler.dump_stats(stats_file)
        print(f"✅ Partial profile data saved to: {stats_file}")

        # Print what we have
        print("\n📊 PARTIAL PROFILING RESULTS:")
        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        stats.print_stats(30)

    except Exception as e:
        profiler.disable()
        print(f"\n\n❌ Error: {e}")
        print("💾 Saving profile data...")

        # Save partial results
        stats_file = "ttm_profile_stats_error.prof"
        profiler.dump_stats(stats_file)
        print(f"✅ Profile data saved to: {stats_file}")

        # Print what we have
        print("\n📊 PROFILING RESULTS (before error):")
        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        stats.print_stats(30)

        raise
