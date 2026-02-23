#!/usr/bin/env bash
set -euo pipefail

PMAPORTS_DIR="${1:?Usage: setup-pmbootstrap.sh <pmaports-dir> [device] [ui] [pmos-ver]}"
DEVICE="${2:-oneplus-fajita}"
UI="${3:-phosh}"
PMOS_VER="${4:-edge}"
RUNNER_TMP="${RUNNER_TEMP:-/tmp}"
PMB_DIR="${RUNNER_TMP}/pmbootstrap"
DEVICE_VENDOR="${DEVICE%%-*}"
DEVICE_CODENAME="${DEVICE#*-}"

sudo apt-get update
sudo apt-get install -y git python3 rsync wget ca-certificates xz-utils

if [ ! -d "${PMB_DIR}" ]; then
  git clone --depth=1 https://gitlab.postmarketos.org/postmarketOS/pmbootstrap.git "${PMB_DIR}"
fi

if ! git -C "${PMAPORTS_DIR}" remote -v | grep -q 'https://gitlab.postmarketos.org/postmarketOS/pmaports.git'; then
  if git -C "${PMAPORTS_DIR}" remote get-url upstream >/dev/null 2>&1; then
    git -C "${PMAPORTS_DIR}" remote set-url upstream https://gitlab.postmarketos.org/postmarketOS/pmaports.git
  else
    git -C "${PMAPORTS_DIR}" remote add upstream https://gitlab.postmarketos.org/postmarketOS/pmaports.git
  fi
fi

git -C "${PMAPORTS_DIR}" fetch --depth=1 upstream \
  +refs/heads/master:refs/remotes/upstream/master

PMB="${PMB_DIR}/pmbootstrap.py"
chmod +x "${PMB}"

mkdir -p "${HOME}/.config"
cat > "${HOME}/.config/pmbootstrap_v3.cfg" <<EOF
[pmbootstrap]
aports = ${PMAPORTS_DIR}
device = ${DEVICE}
extra_packages =
is_default_channel = False
systemd = never
ui = ${UI}
user = user
work = ${HOME}/.local/var/pmbootstrap
jobs = $(nproc)

[providers]

[mirrors]
EOF

echo "PMBOOTSTRAP=${PMB}" >> "${GITHUB_ENV}"
echo "PMB_WORK=${HOME}/.local/var/pmbootstrap" >> "${GITHUB_ENV}"

python3 "${PMB}" --version

python3 "${PMB}" init <<EOF
${HOME}/.local/var/pmbootstrap
${PMAPORTS_DIR}
${PMOS_VER}
${DEVICE_VENDOR}
${DEVICE_CODENAME}
user
default
default
default
${UI}
never
n
none
y
en_US











EOF
