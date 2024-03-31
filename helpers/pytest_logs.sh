#!/bin/sh
# Script to follow log output while running "pmbootstrap ci pytest"
topdir="$(realpath "$(dirname "$0")/..")"
cd "$topdir"

logs=""

mkdir -p _temp/local_job_logs

for i in $(seq 1 30); do
	i_path="_temp/local_job_logs/$i.txt"
	touch "$i_path"
	logs="$logs $i_path"
done

touch pytest.log
tail -F $logs pytest.log
