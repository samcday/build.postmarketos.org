#!/bin/sh -ex
# Follow all relevant logfiles while running the testsuite. Use this during
# development to easily find where a test is hanging etc.
topdir="$(realpath "$(dirname "$0")/..")"
workdir="$(pmbootstrap -q config work)"

cd "$topdir"

tail -F \
	pytest.log \
	_temp/local_job_logs/current.txt \
	"$workdir"/log.txt \
