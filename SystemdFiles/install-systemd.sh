#!/bin/bash
set -euo pipefail

script_dir=$(cd -P -- "$(dirname -- "$0")" && printf "%s." "$PWD")
script_dir=${script_dir%.}
project_dir=${script_dir%/*}
project_dir=${project_dir:-/}
tmp_dir=$(mktemp -d)
trap 'rm -rf -- "$tmp_dir"' EXIT

shopt -s nullglob
services=("$script_dir"/*.service)
timers=("$script_dir"/*.timer)
if ((${#services[@]} == 0 || ${#timers[@]} == 0)); then
    echo "Service and timer files are required" >&2
    exit 1
fi

for service in "${services[@]}"; do
    rendered="$tmp_dir/$(basename -- "$service")"
    python3 - "$service" "$rendered" "$project_dir" <<'PY'
import sys
from pathlib import Path

source, destination, directory = sys.argv[1:]
if any(ord(char) < 32 or ord(char) == 127 for char in directory):
    raise SystemExit("Project path must not contain control characters")
escaped = directory.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
text = Path(source).read_text()
lines = text.splitlines(keepends=True)
Path(destination).write_text("".join(
    line.replace("%WorkingDirectory%", escaped.replace("$", "$$")
                 if line.startswith("ExecStart=") else escaped)
    for line in lines
))
PY
    sudo cp -v -- "$rendered" /etc/systemd/system/
done

for timer in "${timers[@]}"; do
    sudo cp -v -- "$timer" /etc/systemd/system/
done
sudo systemctl daemon-reload
for timer in "${timers[@]}"; do
    timer_name=$(basename -- "$timer")
    sudo systemctl enable "$timer_name"
    sudo systemctl start "$timer_name"
done
