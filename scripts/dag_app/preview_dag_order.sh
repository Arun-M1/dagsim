#!/usr/bin/env bash
set -euo pipefail

# Usage: ./preview_dag_order.sh <config_name> <edge_devices_file> <applications_file> [limit]
# Use limit=0 to print the complete order.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CONFIG_NAME="${1:-DAG_1K_V3}"
EDGE_DEVICES_FILE="${2:-edge_ai_devices_2.1.xml}"
APPLICATIONS_FILE="${3:-applications_dag.xml}"
LIMIT="${4:-20}"

CONFIG_FILE="${SCRIPT_DIR}/config/${CONFIG_NAME}.properties"
EDGE_DEVICES_PATH="${SCRIPT_DIR}/config/${EDGE_DEVICES_FILE}"
APPLICATIONS_PATH="${SCRIPT_DIR}/config/${APPLICATIONS_FILE}"

for file in "${CONFIG_FILE}" "${EDGE_DEVICES_PATH}" "${APPLICATIONS_PATH}"; do
  if [[ ! -f "${file}" ]]; then
    echo "File not found: ${file}" >&2
    exit 1
  fi
done

PREVIEW_CLASS="${REPO_ROOT}/bin/edu/boun/edgecloudsim/dagsim/DagOrderPreview.class"
if [[ ! -f "${PREVIEW_CLASS}" ]]; then
  echo "Compiling preview tool..."
  "${SCRIPT_DIR}/compile.sh"
fi

java -cp "${REPO_ROOT}/bin:${REPO_ROOT}/lib/*" \
  edu.boun.edgecloudsim.dagsim.DagOrderPreview \
  "${CONFIG_FILE}" "${EDGE_DEVICES_PATH}" "${APPLICATIONS_PATH}" "${LIMIT}"
