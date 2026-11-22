#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

from summarize_reward_log import calculate_utilization


def task_log_path(metrics_path):
    suffix = metrics_path.stem.removeprefix("reward_metrics_")
    return metrics_path.with_name(f"task_log_{suffix}.csv")


def update_metrics(metrics_path, dry_run=False):
    summary = json.loads(metrics_path.read_text())
    previous = summary.get("utilization")
    if not isinstance(previous, dict):
        return "skipped: utilization section missing"

    edge_vm_count = previous.get("edge_vm_count")
    cloud_vm_count = previous.get("cloud_vm_count")
    if not edge_vm_count or not cloud_vm_count:
        return "skipped: VM counts missing"

    task_path = task_log_path(metrics_path)
    if not task_path.is_file():
        return f"skipped: {task_path.name} missing"

    with task_path.open(newline="") as task_file:
        task_rows = list(csv.DictReader(task_file))

    corrected = calculate_utilization(task_rows, edge_vm_count, cloud_vm_count)
    if corrected is None:
        return "skipped: no valid execution intervals"

    if not dry_run:
        summary["utilization"] = corrected
        temporary_path = metrics_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(summary, indent=2) + "\n")
        temporary_path.replace(metrics_path)

    edge = corrected["edge_time_weighted_vm_utilization"]
    cloud = corrected["cloud_time_weighted_vm_utilization"]
    return f"updated: edge={edge:.6f}, cloud={cloud:.6f}"


def main():
    parser = argparse.ArgumentParser(
        description="Recalculate VM utilization in existing reward metrics files."
    )
    parser.add_argument(
        "roots",
        nargs="+",
        type=Path,
        help="Output directories to search recursively",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate and report values without modifying files",
    )
    args = parser.parse_args()

    metrics_paths = sorted({
        path
        for root in args.roots
        for path in root.rglob("reward_metrics_ite*.json")
    })

    updated = 0
    skipped = 0
    for metrics_path in metrics_paths:
        result = update_metrics(metrics_path, args.dry_run)
        print(f"{metrics_path}: {result}")
        if result.startswith("updated:"):
            updated += 1
        else:
            skipped += 1

    action = "would update" if args.dry_run else "updated"
    print(f"{action} {updated} file(s); skipped {skipped} file(s)")


if __name__ == "__main__":
    main()
