#!/bin/sh
# Script to follow log output while running "pmbootstrap ci pytest"
topdir="$(realpath "$(dirname "$0")/..")"
cd "$topdir"

logs="test/pytest.log"

for i in $(seq 1 30); do
	i_path="_temp/local_job_logs/$i.txt"
	touch "$i_path"
	logs="$logs $i_path"
done

tail -F $logs
