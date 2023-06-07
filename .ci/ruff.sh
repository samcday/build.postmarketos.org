#!/bin/sh -e
# Description: lint all python scripts
# https://postmarketos.org/pmb-ci

if [ "$(id -u)" = 0 ]; then
	set -x
	apk -q add ruff
	exec su "${TESTUSER:-build}" -c "sh -e $0"
fi

set -x

ruff \
	*.py \
	$(find bpo -name "*.py") \
	$(find helpers -name "*.py") \
	$(find test -name "*.py")
