#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from statistics import mean


EDGE_TIER = 1
CLOUD_TIER = 2
EXECUTION_TIME_COLUMN = "actual_execution_time_ms"


def execution_times(rows, tier=None):
    values = []
    for row in rows:
        try:
            if tier is not None and int(row["tier"]) != tier:
                continue
            execution_time_ms = float(row[EXECUTION_TIME_COLUMN])
        except (KeyError, TypeError, ValueError):
            continue

        if execution_time_ms >= 0.0:
            values.append(execution_time_ms)
    return values


def execution_stats(values):
    return {
        "count": len(values),
        "mean_execution_time_ms": mean(values) if values else None,
    }


def summarize(rows):
    summary = {
        "completed_tasks": len(rows),
        "overall": {
            "all": execution_stats(execution_times(rows)),
            "edge": execution_stats(execution_times(rows, EDGE_TIER)),
            "cloud": execution_stats(execution_times(rows, CLOUD_TIER)),
        },
        "by_task_type": {},
    }

    task_types = sorted({row.get("task_type", "").strip() for row in rows})
    for task_type in task_types:
        if not task_type:
            continue
        task_rows = [row for row in rows if row.get("task_type", "").strip() == task_type]
        summary["by_task_type"][task_type] = {
            "edge": execution_stats(execution_times(task_rows, EDGE_TIER)),
            "cloud": execution_stats(execution_times(task_rows, CLOUD_TIER)),
        }

    return summary


def print_stats(label, stats):
    mean_ms = stats["mean_execution_time_ms"]
    mean_text = "N/A" if mean_ms is None else f"{mean_ms:.6f}"
    print(f"  {label}: count={stats['count']} mean_execution_time_ms={mean_text}")


def print_summary(path, summary):
    print(f"task_log={path}")
    print(f"completed_tasks={summary['completed_tasks']}")
    print()
    print("overall_execution_time")
    print_stats("all", summary["overall"]["all"])
    print_stats("edge", summary["overall"]["edge"])
    print_stats("cloud", summary["overall"]["cloud"])

    for task_type, tier_stats in summary["by_task_type"].items():
        print()
        print(task_type)
        print_stats("edge", tier_stats["edge"])
        print_stats("cloud", tier_stats["cloud"])


def main():
    parser = argparse.ArgumentParser(
        description="Summarize overall, edge, and cloud task execution times."
    )
    parser.add_argument("task_log", help="Path to task_log.csv")
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args()

    path = Path(args.task_log)
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        if EXECUTION_TIME_COLUMN not in (reader.fieldnames or []):
            parser.error(
                f"{path} does not contain the {EXECUTION_TIME_COLUMN} column; "
                "run the updated simulator first"
            )
        rows = list(reader)

    summary = summarize(rows)
    print_summary(path, summary)

    if args.out:
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
