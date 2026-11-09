#!/usr/bin/env bash
# Chép lại hợp đồng mining.v1.yaml từ repo joblens (bản gốc) vào service/contract/ rồi chạy test hợp đồng.
set -euo pipefail
cd "$(dirname "$0")/.."
URL=https://raw.githubusercontent.com/BD-WM-SA-D/joblens/main/schemas/api/mining.v1.yaml
{ echo "# BẢN SAO – bản gốc: repo joblens schemas/api/mining.v1.yaml. Không sửa tại đây; đồng bộ: bash service/sync_contract.sh"
  curl -fsSL "$URL"; } > service/contract/mining.v1.yaml
uv run pytest -q tests/test_mining_service.py
