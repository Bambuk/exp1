#!/usr/bin/env python3
"""Optimized profiling of TTM Details report generation with SQL batching."""

import asyncio
import concurrent.futures
import time
from threading import Lock

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator
from radiator.core.database import SessionLocal


class OptimizedSQLProfiledTTMDetailsReportGenerator(TTMDetailsReportGenerator):
    """TTM Details Report Generator with SQL query profiling and batching optimization."""

    def __init__(self, db, config_dir="data/config"):
        super().__init__(db, config_dir)
        self.sql_stats = {
            "total_queries": 0,
            "total_time": 0.0,
            "queries_by_type": {},
            "slow_queries": [],
            "query_times": [],
        }
        self.query_lock = Lock()

        # Add SQL event listeners
        self._setup_sql_profiling()

    def _setup_sql_profiling(self):
        """Setup SQL query profiling."""

        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            context._query_start_time = time.time()

        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            if hasattr(context, "_query_start_time"):
                query_time = time.time() - context._query_start_time

                with self.query_lock:
                    self.sql_stats["total_queries"] += 1
                    self.sql_stats["total_time"] += query_time
                    self.sql_stats["query_times"].append(query_time)

                    # Track slow queries (>0.1s)
                    if query_time > 0.1:
                        self.sql_stats["slow_queries"].append(
                            {
                                "query": statement[:200] + "..."
                                if len(statement) > 200
                                else statement,
                                "time": query_time,
                                "parameters": str(parameters)[:100]
                                if parameters
                                else None,
                            }
                        )

                    # Track queries by type
                    query_type = self._classify_query(statement)
                    if query_type not in self.sql_stats["queries_by_type"]:
                        self.sql_stats["queries_by_type"][query_type] = {
                            "count": 0,
                            "total_time": 0.0,
                        }
                    self.sql_stats["queries_by_type"][query_type]["count"] += 1
                    self.sql_stats["queries_by_type"][query_type][
                        "total_time"
                    ] += query_time

    def _classify_query(self, statement):
        """Classify SQL query by type."""
        statement_lower = statement.lower().strip()

        if "select" in statement_lower:
            if "from tracker_tasks" in statement_lower:
                if "where" in statement_lower and "id" in statement_lower:
                    return "SELECT_task_by_id"
                elif "where" in statement_lower and "key" in statement_lower:
                    return "SELECT_task_by_key"
                elif "key in" in statement_lower:
                    return "SELECT_tasks_batch"
                else:
                    return "SELECT_tasks"
            elif "from task_history" in statement_lower:
                return "SELECT_task_history"
            elif "from tracker_links" in statement_lower:
                return "SELECT_links"
            else:
                return "SELECT_other"
        elif "insert" in statement_lower:
            return "INSERT"
        elif "update" in statement_lower:
            return "UPDATE"
        elif "delete" in statement_lower:
            return "DELETE"
        else:
            return "OTHER"

    def print_sql_stats(self):
        """Print detailed SQL statistics."""
        print("\n" + "=" * 80)
        print("📊 OPTIMIZED SQL QUERY ANALYSIS")
        print("=" * 80)

        stats = self.sql_stats

        print(f"🔢 Total queries executed: {stats['total_queries']}")
        print(f"⏱️  Total SQL time: {stats['total_time']:.2f}s")
        print(
            f"📈 Average query time: {stats['total_time']/stats['total_queries']:.3f}s"
        )

        print(f"\n📋 Query breakdown by type:")
        for query_type, data in sorted(
            stats["queries_by_type"].items(),
            key=lambda x: x[1]["total_time"],
            reverse=True,
        ):
            avg_time = data["total_time"] / data["count"]
            print(
                f"  {query_type:20} | {data['count']:4d} queries | {data['total_time']:6.2f}s total | {avg_time:.3f}s avg"
            )

        if stats["slow_queries"]:
            print(f"\n🐌 Slow queries (>0.1s): {len(stats['slow_queries'])}")
            for i, slow_query in enumerate(stats["slow_queries"][:5]):  # Show top 5
                print(f"  {i+1:2d}. {slow_query['time']:.3f}s - {slow_query['query']}")
                if slow_query["parameters"]:
                    print(f"      Params: {slow_query['parameters']}")

        # Find the most expensive query type
        if stats["queries_by_type"]:
            most_expensive = max(
                stats["queries_by_type"].items(), key=lambda x: x[1]["total_time"]
            )
            print(
                f"\n🎯 Most expensive query type: {most_expensive[0]} ({most_expensive[1]['total_time']:.2f}s)"
            )

        return stats


def run_optimized_profiling():
    """Run optimized SQL profiling on TTM Details report generation (100 tasks limit)."""
    print("🚀 Optimized TTM Details Report Generation (100 tasks limit)")
    print("=" * 80)

    with SessionLocal() as db:
        generator = OptimizedSQLProfiledTTMDetailsReportGenerator(db=db)

        # Override _get_ttm_tasks_for_quarter to limit tasks
        original_get_tasks = generator._get_ttm_tasks_for_quarter

        def limited_get_tasks(quarter):
            tasks = original_get_tasks(quarter)
            return tasks[:100]  # Limit to 100 tasks per quarter

        generator._get_ttm_tasks_for_quarter = limited_get_tasks

        # Time the generation
        start_time = time.time()
        result_path = generator.generate_csv("data/reports/optimized_ttm_details.csv")
        total_time = time.time() - start_time

        print(f"\n⏱️  Total generation time: {total_time:.2f}s")
        print(f"📄 Report generated: {result_path}")

        # Print SQL statistics
        sql_stats = generator.print_sql_stats()

        # Calculate SQL efficiency
        sql_percentage = (sql_stats["total_time"] / total_time) * 100
        print(
            f"\n📊 SQL efficiency: {sql_percentage:.1f}% of total time spent on SQL queries"
        )

        return result_path, total_time, sql_stats


if __name__ == "__main__":
    run_optimized_profiling()
