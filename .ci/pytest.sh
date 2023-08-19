#!/bin/sh -e
# Description: run python testsuite
# Options: native slow
# https://postmarketos.org/pmb-ci

if [ "$(id -u)" = 0 ]; then
	set -x
	apk -q add \
		py3-coverage \
		py3-flask \
		py3-jsonschema \
		py3-pytest \
		py3-pytest-cov \
		py3-pytest-timeout \
		py3-requests \
		py3-sqlalchemy \
		xz
	touch .ci_pytest_no_venv
	exec su "${TESTUSER:-pmos}" -c "sh -e $0"
fi

if ! [ -e .ci_pytest_no_venv ]; then
	if ! [ -d .venv ]; then
		rm -f .ci_pytest_venv_prepared
	fi

	if [ -e .ci_pytest_venv_prepared ]; then
		. .venv/bin/activate
	else
		echo "Initializing venv..."
		python3 -m venv .venv
		. .venv/bin/activate
		pip install -r requirements.txt
		pip install -r requirements-test.txt
		touch .ci_pytest_venv_prepared
	fi
fi

if [ -e ~/.config/pmbootstrap.cfg ]; then
	../pmbootstrap/pmbootstrap.py work_migrate
else
	echo "Initializing pmbootstrap..."
	if ! yes '' | ../pmbootstrap/pmbootstrap.py \
			--details-to-stdout \
			init \
			>pmb_init_log 2>&1; then
		cat pmb_init_log
		exit 1
	fi
fi

../pmbootstrap/pmbootstrap.py -q shutdown

# Use pytest-cov if it is installed to display code coverage
cov_arg=""
if python -c "import pytest_cov" >/dev/null 2>&1; then
	cov_arg="--cov=bpo"
fi

echo "Running pytest..."
echo "NOTE: use 'helpers/pytest_logs.sh' to see the detailed log if running locally."
pytest \
	--color=yes \
	-vv \
	-x \
	$cov_arg \
	test \
		-m "not skip_ci" \
		"$@"

if command -v coverage >/dev/null; then
	coverage xml -o coverage.xml
fi
