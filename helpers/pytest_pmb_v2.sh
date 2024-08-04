#!/bin/sh
# Wrapper for "pytest" that uses pmbootstrap v2, like in .ci/pytest-pmb-v2.sh
PMBV2_DIR=../pmbootstrap_v2

if ! [ -d "$PMBV2_DIR" ]; then
	echo "ERROR: put pmbootstrap v2 here first: $PMBV2_DIR"
	exit 1
fi

# Put pmbootstrap v2 into PATH
TEMPBIN=$PWD/_temp_bpo_testsuite_bin
rm -rf "$TEMPBIN"
mkdir "$TEMPBIN"
ln -s "$(realpath "$PMBV2_DIR")"/pmbootstrap.py "$TEMPBIN"/pmbootstrap
export PATH="$TEMPBIN:$PATH"

if ! pmbootstrap --version | grep -q '^2\.'; then
	echo "ERROR: failed to put pmbv2 into PATH"
	exit 1
fi

export BPO_PMA_MASTER_PMB_BRANCH="2.3.x"
export BPO_PMA_STAGING_PMB_BRANCH="2.3.x"
export BPO_PMB_PATH="$(realpath "$PWD/../pmbootstrap_v2")"
export BPO_PMA_PATH="$(pmbootstrap -q config aports)"

pytest "$@"
