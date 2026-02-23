#!/usr/bin/env bash
set -euo pipefail

PMAPORTS_DIR="${1:?Usage: setup-pmbootstrap.sh <pmaports-dir> [device] [ui] [pmos-ver]}"
DEVICE="${2:-oneplus-fajita}"
UI="${3:-phosh}"
PMOS_VER="${4:-edge}"
APK_REPO_BASE_URL="${5:-${APK_REPO_BASE_URL:-}}"
APK_REPO_KEY_URL="${6:-${APK_REPO_KEY_URL:-}}"
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

if [ -n "${APK_REPO_BASE_URL}" ]; then
  python3 "${PMB}" config mirrors.pmaports_custom "${APK_REPO_BASE_URL%/}/"
fi

if [ -n "${APK_REPO_KEY_URL}" ]; then
  key_tmp="$(mktemp)"

  if [ "${APK_REPO_KEY_URL#file://}" != "${APK_REPO_KEY_URL}" ]; then
    cp "${APK_REPO_KEY_URL#file://}" "${key_tmp}"
  else
    wget -qO "${key_tmp}" "${APK_REPO_KEY_URL}"
  fi

  if ! grep -q "BEGIN PUBLIC KEY" "${key_tmp}"; then
    echo "Downloaded key from ${APK_REPO_KEY_URL} does not look like a public key"
    rm -f "${key_tmp}"
    exit 1
  fi

  key_name="$(basename "${APK_REPO_KEY_URL}")"
  if [ -z "${key_name}" ] || [ "${key_name}" = "/" ]; then
    key_name="pmaports-fastboop.rsa.pub"
  fi

  work_dir="$(python3 "${PMB}" config work)"
  mkdir -p "${work_dir}/config_apk_keys"
  install -m 0644 "${key_tmp}" "${work_dir}/config_apk_keys/${key_name}"
  install -m 0644 "${key_tmp}" "${PMB_DIR}/pmb/data/keys/${key_name}"
  rm -f "${key_tmp}"
fi

python3 "${PMB}" config mirrors.pmaports
python3 "${PMB}" config mirrors.pmaports_custom
