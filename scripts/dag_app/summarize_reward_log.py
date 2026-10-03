#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from statistics import mean
import xml.etree.ElementTree as ET


DEFAULT_COLUMNS = [
    "ready_wait_ms",
    "latency_ms",
    "wait_for_execution_start_ms",
    "network_ms",
    "edge_total_waiting_task_count",
    "edge_avg_waiting_tasks_per_vm",
    "edge_max_waiting_tasks_per_vm",
    "cloud_total_waiting_task_count",
    "cloud_avg_waiting_tasks_per_vm",
    "cloud_max_waiting_tasks_per_vm",
    "estimated_latency_ms",
    "estimated_cost",
    "estimated_reward",
    "estimate_latency_error_ms",
    "estimate_cost_error",
    "estimate_reward_error",
    "estimated_upload_delay_ms",
    "estimated_processing_time_ms",
    "estimated_download_delay_ms",
    "estimate_vm_active_cloudlets",
    "task_ready_at_dc_ms",
    "reserved_vm_id",
    "predicted_vm_available_time_ms",
    "reserved_vm_start_ms",
    "reserved_vm_finish_ms",
    "reserved_dc_wait_ms",
    "reserved_estimated_response_done_ms",
    "reserved_estimated_latency_ms",
    "bw_cost",
    "cpu_cost",
    "actual_cost",
    "latency_term",
    "cost_term",
    "reward",
]

LEGACY_COLUMN_ALIASES = {
    "wait_for_execution_start_ms": "queue_wait_ms",
    "predicted_vm_available_time_ms": "reserved_vm_available_before_ms",
    "task_ready_at_dc_ms": "dc_queue_arrival_ms",
    "estimated_upload_delay_ms": "estimate_upload_ms",
    "estimated_processing_time_ms": "estimate_execution_ms",
    "estimated_download_delay_ms": "estimate_download_ms",
}

QUEUE_COLUMNS = {
    "edge_total_waiting_task_count",
    "edge_avg_waiting_tasks_per_vm",
    "edge_max_waiting_tasks_per_vm",
    "cloud_total_waiting_task_count",
    "cloud_avg_waiting_tasks_per_vm",
    "cloud_max_waiting_tasks_per_vm",
    "selected_vm_waiting_task_count",
    "selected_vm_total_task_count",
}


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def numeric_values(rows, column, nonnegative=False):
    values = []
    for row in rows:
        raw = row.get(column, "")
        if raw == "" and column in LEGACY_COLUMN_ALIASES:
            raw = row.get(LEGACY_COLUMN_ALIASES[column], "")
        if raw == "":
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if nonnegative and value < 0:
            continue
        values.append(value)
    return values


def describe(values):
    return {
        "count": len(values),
        "nonzero": sum(1 for v in values if v != 0.0),
        "min": min(values),
        "mean": mean(values),
        "p50": percentile(values, 50),
        "p90": percentile(values, 90),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": max(values),
    }


def tier_name(row):
    tier = row.get("tier", "").strip().upper()
    if tier in {"1", "EDGE", "EDGE_VM"}:
        return "edge"
    if tier in {"2", "CLOUD", "CLOUD_VM"}:
        return "cloud"
    return None


def add_selected_vm_summaries(summary, rows):
    for tier in ("edge", "cloud"):
        tier_rows = [row for row in rows if tier_name(row) == tier]
        for column in ("selected_vm_waiting_task_count", "selected_vm_total_task_count"):
            values = numeric_values(tier_rows, column, nonnegative=True)
            if values:
                summary["columns"][f"{tier}_{column}"] = describe(values)


def read_properties(path):
    properties = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "!")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()
    return properties


def get_vm_counts(properties_path, edge_devices_path):
    edge_vm_count = None
    cloud_vm_count = None

    if edge_devices_path:
        root = ET.parse(edge_devices_path).getroot()
        edge_vm_count = sum(1 for _ in root.iter("VM"))

    if properties_path:
        properties = read_properties(properties_path)
        host_count = int(properties["number_of_host_on_cloud_datacenter"])
        vms_per_host = int(properties["number_of_vm_on_cloud_host"])
        cloud_vm_count = host_count * vms_per_host

    return edge_vm_count, cloud_vm_count


def calculate_utilization(rows, edge_vm_count, cloud_vm_count):
    intervals = []
    busy_ms = {"edge": 0.0, "cloud": 0.0}
    for row in rows:
        tier = tier_name(row)
        if tier is None:
            continue
        try:
            start_ms = float(row.get("start_ms", ""))
            finish_ms = float(row.get("finish_ms", ""))
        except ValueError:
            continue
        if start_ms < 0 or finish_ms < start_ms:
            continue
        intervals.append((start_ms, finish_ms))
        busy_ms[tier] += finish_ms - start_ms

    if not intervals:
        return None

    measurement_start_ms = min(start for start, _ in intervals)
    measurement_end_ms = max(finish for _, finish in intervals)
    measurement_duration_ms = measurement_end_ms - measurement_start_ms
    if measurement_duration_ms <= 0:
        return None

    utilization = {
        "measurement_start_ms": measurement_start_ms,
        "measurement_end_ms": measurement_end_ms,
        "measurement_duration_ms": measurement_duration_ms,
        "edge_vm_count": edge_vm_count,
        "cloud_vm_count": cloud_vm_count,
        "edge_busy_vm_ms": busy_ms["edge"],
        "cloud_busy_vm_ms": busy_ms["cloud"],
    }
    if edge_vm_count and edge_vm_count > 0:
        utilization["edge_time_weighted_vm_utilization"] = (
            busy_ms["edge"] / (edge_vm_count * measurement_duration_ms)
        )
    if cloud_vm_count and cloud_vm_count > 0:
        utilization["cloud_time_weighted_vm_utilization"] = (
            busy_ms["cloud"] / (cloud_vm_count * measurement_duration_ms)
        )
    return utilization


def summarize(rows, columns, edge_vm_count=None, cloud_vm_count=None):
    summary = {"rows": len(rows), "columns": {}}
    for column in columns:
        values = numeric_values(rows, column, nonnegative=column in QUEUE_COLUMNS)
        if values:
            summary["columns"][column] = describe(values)

    add_selected_vm_summaries(summary, rows)

    utilization = calculate_utilization(rows, edge_vm_count, cloud_vm_count)
    if utilization:
        summary["utilization"] = utilization

    if rows and "cost_source" in rows[0]:
        counts = {}
        for row in rows:
            source = row.get("cost_source", "")
            counts[source] = counts.get(source, 0) + 1
        summary["cost_source_counts"] = counts

    return summary


def print_summary(path, summary):
    print(f"reward_log={path}")
    print(f"rows={summary['rows']}")
    for column, stats in summary["columns"].items():
        print()
        print(column)
        print(f"  count={stats['count']} nonzero={stats['nonzero']}")
        for key in ["min", "mean", "p50", "p90", "p95", "p99", "max"]:
            print(f"  {key}={stats[key]:.12g}")

    if "cost_source_counts" in summary:
        print()
        print("cost_source")
        for source, count in sorted(summary["cost_source_counts"].items()):
            print(f"  {source}: {count}")

    if "utilization" in summary:
        print()
        print("time_weighted_vm_utilization")
        for key, value in summary["utilization"].items():
            if isinstance(value, float):
                print(f"  {key}={value:.12g}")
            else:
                print(f"  {key}={value}")


def main():
    parser = argparse.ArgumentParser(description="Summarize reward_log.csv percentile statistics.")
    parser.add_argument("reward_log", help="Path to reward_log.csv")
    parser.add_argument("--out", help="Optional JSON output path")
    parser.add_argument("--properties", help="Properties file used for the run")
    parser.add_argument("--edge-devices", help="Edge devices XML used for the run")
    parser.add_argument(
        "--columns",
        nargs="+",
        default=DEFAULT_COLUMNS,
        help="Numeric columns to summarize",
    )
    args = parser.parse_args()

    path = Path(args.reward_log)
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    edge_vm_count, cloud_vm_count = get_vm_counts(args.properties, args.edge_devices)
    summary = summarize(rows, args.columns, edge_vm_count, cloud_vm_count)
    print_summary(path, summary)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
