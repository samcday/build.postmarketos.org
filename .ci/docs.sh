#!/bin/sh -e
# Description: create documentation with sphinx
# Artifacts: public/
# https://postmarketos.org/pmb-ci


# Install sphinx + extensions when running in CI
if [ "$(id -u)" = 0 ]; then
	set -x
	apk -q add \
		py3-flask \
		py3-myst-parser \
		py3-sphinx_rtd_theme \
		py3-sphinxcontrib-autoprogram \
		py3-sphinxcontrib-jquery \
		py3-sqlalchemy
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

sphinx-build \
	docs \
	public \

#	-E -a -v -T
