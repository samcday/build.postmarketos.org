#!/bin/sh -e
topdir="$(realpath "$(dirname "$0")/..")"

.ci/vermin.sh
.ci/ruff.sh
