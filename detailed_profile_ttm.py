#!/usr/bin/env python3
"""Detailed profiling of TTM Details report generation with method-level timing."""

import functools
import time
from collections import defaultdict

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator
from radiator.core.database import SessionLocal


class MethodProfiler:
    """Profiler to track time spent in specific methods."""

    def __init__(self):
        self.times = defaultdict(float)
        self.call_counts = defaultdict(int)
        self.original_methods = {}

    def profile_method(self, obj, method_name):
        """Profile a specific method on an object."""
        if hasattr(obj, method_name):
            original_method = getattr(obj, method_name)
            self.original_methods[(obj, method_name)] = original_method

            @functools.wraps(original_method)
            def profiled_method(*args, **kwargs):
                start_time = time.time()
                result = original_method(*args, **kwargs)
                elapsed = time.time() - start_time

                self.times[method_name] += elapsed
                self.call_counts[method_name] += 1

                return result

            setattr(obj, method_name, profiled_method)

    def get_report(self):
        """Get profiling report sorted by total time."""
        report = []
        for method_name in self.times:
            total_time = self.times[method_name]
            call_count = self.call_counts[method_name]
            avg_time = total_time / call_count if call_count > 0 else 0

            report.append(
                {
                    "method": method_name,
                    "total_time": total_time,
                    "call_count": call_count,
                    "avg_time": avg_time,
                }
            )

        return sorted(report, key=lambda x: x["total_time"], reverse=True)


def detailed_profile():
    """Run detailed profiling with method-level timing."""
    print("🔍 Detailed TTM Details Report Profiling")
    print("=" * 60)

    profiler = MethodProfiler()

    with SessionLocal() as db:
        # Create generator
        generator = TTMDetailsReportGenerator(db=db)

        # Profile key methods
        profiler.profile_method(generator, "_calculate_ttm")
        profiler.profile_method(generator, "_calculate_tail")
        profiler.profile_method(generator, "_calculate_devlt")
        profiler.profile_method(generator, "_calculate_ttd")
        profiler.profile_method(generator, "_calculate_pause")
        profiler.profile_method(generator, "_calculate_ttd_pause")
        profiler.profile_method(generator, "_calculate_discovery_backlog_days")
        profiler.profile_method(generator, "_calculate_ready_for_dev_days")
        profiler.profile_method(generator, "_calculate_testing_returns")

        # Profile data service methods
        profiler.profile_method(generator.data_service, "get_task_history")
        profiler.profile_method(generator.data_service, "get_task_history_by_key")

        # Profile testing returns service methods
        profiler.profile_method(
            generator.testing_returns_service, "get_fullstack_links"
        )
        profiler.profile_method(generator.testing_returns_service, "get_task_hierarchy")
        profiler.profile_method(
            generator.testing_returns_service, "calculate_testing_returns_for_cpo_task"
        )
        profiler.profile_method(
            generator.testing_returns_service, "calculate_testing_returns_for_task"
        )
        profiler.profile_method(
            generator.testing_returns_service, "count_status_returns"
        )

        # Profile metrics service methods
        profiler.profile_method(generator.metrics_service, "calculate_time_to_market")
        profiler.profile_method(generator.metrics_service, "calculate_tail_metric")
        profiler.profile_method(generator.metrics_service, "calculate_dev_lead_time")
        profiler.profile_method(generator.metrics_service, "calculate_time_to_delivery")
        profiler.profile_method(generator.metrics_service, "calculate_pause_time")
        profiler.profile_method(
            generator.metrics_service, "calculate_pause_time_up_to_date"
        )
        profiler.profile_method(generator.metrics_service, "calculate_status_duration")

        # Run the generation
        start_time = time.time()
        result_path = generator.generate_csv(
            "data/reports/detailed_profiled_ttm_details.csv"
        )
        total_time = time.time() - start_time

        print(f"⏱️  Total generation time: {total_time:.2f}s")
        print(f"📄 Report generated: {result_path}")
        print()

        # Get and display profiling report
        report = profiler.get_report()

        print("📊 Method-level timing breakdown:")
        print("-" * 80)
        print(f"{'Method':<50} {'Total (s)':<10} {'Calls':<8} {'Avg (s)':<10}")
        print("-" * 80)

        for entry in report:
            if entry["total_time"] > 0.01:  # Only show methods that took > 10ms
                print(
                    f"{entry['method']:<50} {entry['total_time']:<10.2f} {entry['call_count']:<8} {entry['avg_time']:<10.4f}"
                )

        print("-" * 80)

        # Calculate percentages
        total_profiled_time = sum(entry["total_time"] for entry in report)
        print(f"\n📈 Top time consumers:")
        for i, entry in enumerate(report[:10]):
            if entry["total_time"] > 0.01:
                percentage = (entry["total_time"] / total_profiled_time) * 100
                print(
                    f"{i+1:2d}. {entry['method']:<45} {entry['total_time']:6.2f}s ({percentage:5.1f}%)"
                )

        return result_path


def analyze_testing_returns_bottleneck():
    """Analyze the testing returns bottleneck in detail."""
    print("\n🔍 Testing Returns Bottleneck Analysis")
    print("=" * 60)

    with SessionLocal() as db:
        generator = TTMDetailsReportGenerator(db=db)

        # Get a sample of tasks
        quarters = generator._load_quarters()
        done_statuses = generator._load_done_statuses()

        sample_tasks = []
        for quarter in quarters[:1]:  # Only first quarter for analysis
            tasks = generator._get_ttm_tasks_for_quarter(quarter)
            sample_tasks.extend(tasks[:5])  # First 5 tasks

        print(f"📊 Analyzing {len(sample_tasks)} sample tasks...")

        total_time = 0
        for i, task in enumerate(sample_tasks):
            print(f"\nTask {i+1}: {task.key}")

            # Time each step
            start = time.time()

            # Step 1: Get FULLSTACK links
            links_start = time.time()
            fullstack_epics = generator.testing_returns_service.get_fullstack_links(
                task.key
            )
            links_time = time.time() - links_start

            print(f"  FULLSTACK links ({len(fullstack_epics)}): {links_time:.3f}s")

            if fullstack_epics:
                # Step 2: Get task hierarchy for each epic
                hierarchy_time = 0
                total_tasks = 0
                for epic_key in fullstack_epics:
                    epic_start = time.time()
                    epic_tasks = generator.testing_returns_service.get_task_hierarchy(
                        epic_key
                    )
                    epic_time = time.time() - epic_start
                    hierarchy_time += epic_time
                    total_tasks += len(epic_tasks)
                    print(
                        f"    Epic {epic_key}: {len(epic_tasks)} tasks in {epic_time:.3f}s"
                    )

                # Step 3: Calculate returns for each task
                returns_time = 0
                for epic_key in fullstack_epics:
                    epic_tasks = generator.testing_returns_service.get_task_hierarchy(
                        epic_key
                    )
                    for task_key in epic_tasks:
                        task_start = time.time()
                        history = generator.data_service.get_task_history_by_key(
                            task_key
                        )
                        if history:
                            (
                                testing_returns,
                                external_returns,
                            ) = generator.testing_returns_service.calculate_testing_returns_for_task(
                                task_key, history
                            )
                        task_time = time.time() - task_start
                        returns_time += task_time

                print(
                    f"  Returns calculation ({total_tasks} tasks): {returns_time:.3f}s"
                )

            task_total = time.time() - start
            total_time += task_total
            print(f"  Total for {task.key}: {task_total:.3f}s")

        print(f"\n📊 Sample analysis total: {total_time:.3f}s")
        print(f"📊 Average per task: {total_time/len(sample_tasks):.3f}s")
        print(f"📊 Estimated for 703 tasks: {(total_time/len(sample_tasks)) * 703:.1f}s")


if __name__ == "__main__":
    # Run detailed profiling
    detailed_profile()

    # Analyze testing returns bottleneck
    analyze_testing_returns_bottleneck()
