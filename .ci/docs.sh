#!/bin/sh -e
# Description: create documentation with sphinx
# Options: native
# https://postmarketos.org/pmb-ci

# Install required packages in CI
if [ "$(id -u)" = 0 ]; then
	set -x
	apk -q add \
		git \
		make \
		py3-pip
	exec su "${TESTUSER:-build}" -c "sh -e $0"
fi

# Validate that all modules are documented.
fail=0
modules="$(find bpo/ -name "*.py" | grep -v '/__init__.py' | sort | sed 's|\.py$||' | sed 's|/|.|g')"
for module in $modules; do
	if ! grep -q "automodule:: $module" docs/api/*.rst; then
		echo "Undocumented module: $module"
		fail=1
	fi
done
if [ "$fail" -eq 1 ]; then
	echo "ERROR: Found undocumented modules!"
	echo "ERROR: Please add this module to the correct .rst file in docs/"
	exit 1
fi

make -C docs
