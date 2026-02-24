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

install_host_dependencies() {
  local -a deps_apt=(git python3 rsync wget ca-certificates xz-utils)
  local -a deps_dnf=(git python3 rsync wget ca-certificates xz)
  local -i can_use_apt=0
  local pkg

  if command -v apt-get >/dev/null 2>&1; then
    if sudo apt-get update >/dev/null 2>&1; then
      can_use_apt=1
      for pkg in "${deps_apt[@]}"; do
        if ! apt-cache show "${pkg}" >/dev/null 2>&1; then
          can_use_apt=0
          break
        fi
      done

      if [ "${can_use_apt}" -eq 1 ]; then
      sudo apt-get install -y "${deps_apt[@]}"
      return
      fi
      echo "apt package catalog does not provide required host dependencies; falling back to dnf if available."
    fi
  fi

  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y "${deps_dnf[@]}"
    return
  fi

  echo "setup-pmbootstrap.sh could not find a supported package manager."
  echo "Install git, python3, rsync, wget, ca-certificates and xz on this host manually."
  exit 1
}

if [[ "${DEVICE}" != *-* ]]; then
  echo "Device must use vendor-codename format (got: ${DEVICE})"
  exit 1
fi

DEVICE_VENDOR="${DEVICE%%-*}"
DEVICE_CODENAME="${DEVICE#*-}"

install_host_dependencies

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

if [ -d "${HOME}/.local/var/pmbootstrap" ]; then
  sudo chown -R "$(id -u):$(id -g)" "${HOME}/.local/var/pmbootstrap"
fi

build_empty_apkindex() {
  local index_file="$1"
  local tmp_dir
  local tmp_file

  tmp_dir="$(mktemp -d)"
  tmp_file="${tmp_dir}/APKINDEX"
  printf '\n' > "${tmp_file}"

  sudo tar -C "${tmp_dir}" -czf "${index_file}" APKINDEX
  rm -rf "${tmp_dir}"
}

sanitize_override_apkindex() {
  local repo_dir="$1"
  local index_source="${repo_dir}/APKINDEX.tar.gz"
  local tmp_dir
  local tmp_index

  if [ ! -f "${index_source}" ]; then
    return 0
  fi

  tmp_dir="$(mktemp -d)"
  tmp_index="${tmp_dir}/APKINDEX"

  if ! python3 - "$repo_dir" "$tmp_index" <<'PY'
import pathlib
import sys
import tarfile

repo_dir = pathlib.Path(sys.argv[1])
out_index = pathlib.Path(sys.argv[2])
index_tar = repo_dir / 'APKINDEX.tar.gz'

with tarfile.open(index_tar, 'r:gz') as tar:
    source = tar.extractfile('APKINDEX')
    if source is None:
        out_index.write_text('\n', encoding='utf-8')
        raise SystemExit(0)
    lines = source.read().decode('utf-8', errors='ignore').splitlines()

blocks = []
current = []
for line in lines:
    if line == '':
        if current:
            blocks.append(current)
            current = []
        continue
    current.append(line)
if current:
    blocks.append(current)


def keep(block):
    files = [line[2:] for line in block if line.startswith('F:')]
    if not files:
        return True
    return all((repo_dir / filename).is_file() for filename in files)


kept = [b for b in blocks if keep(b)]
if not kept:
    out_index.write_text('\n', encoding='utf-8')
    raise SystemExit(0)

with out_index.open('w', encoding='utf-8') as handle:
    for block in kept:
        handle.write('\n'.join(block))
        handle.write('\n\n')
PY
  then
    build_empty_apkindex "${index_source}"
    rm -rf "${tmp_dir}"
    return 0
  fi

  sudo tar -C "${tmp_dir}" -czf "${index_source}" APKINDEX
  rm -rf "${tmp_dir}"
}

prepare_local_override_repo() {
  local source_root="$1"
  local work_root="$2"
  local aarch64_dir
  local -a x86_apks

  sudo rm -rf "${work_root}"
  sudo mkdir -p "${work_root}"
  sudo cp -R "${source_root}"/. "${work_root}"

  aarch64_dir="${work_root}/aarch64"
  if [ ! -d "${aarch64_dir}" ]; then
    aarch64_dir="${work_root}/master/aarch64"
  fi

  for dir in "${work_root}/x86_64" "${work_root}/master/x86_64"; do
    if [ ! -d "${dir}" ]; then
      sudo mkdir -p "${dir}"
    fi

    if [ ! -f "${dir}/APKINDEX.tar.gz" ]; then
      build_empty_apkindex "${dir}/APKINDEX.tar.gz"
      continue
    fi

    x86_apks=("${dir}"/*.apk)
    if [ -e "${x86_apks[0]}" ]; then
      sanitize_override_apkindex "${dir}"
    else
      build_empty_apkindex "${dir}/APKINDEX.tar.gz"
    fi
  done

  if [ ! -d "${work_root}/master/aarch64" ] && [ -d "${aarch64_dir}" ]; then
    sudo mkdir -p "${work_root}/master"
    sudo cp -R "${aarch64_dir}" "${work_root}/master/"
  fi
}

if [ -n "${APK_REPO_BASE_URL}" ]; then
  work_dir="$(python3 "${PMB}" config work)"
  local_override_url="${APK_REPO_BASE_URL%/}/"
  local_override_root="${APK_REPO_BASE_URL#file://}"
  local_override_key_root="${local_override_root}"

  if [ "${APK_REPO_BASE_URL#file://}" != "${APK_REPO_BASE_URL}" ]; then
    local_override_root="${APK_REPO_BASE_URL#file://}"
    local_override_root_norm="${work_dir}/override-mirror"

    prepare_local_override_repo "${local_override_root%/}" "${local_override_root_norm}"

    local_override_root="${local_override_root_norm}"
    local_override_key_root="${local_override_root_norm}"
    local_override_url="file://${local_override_root_norm}/"
  fi

  local_override_repo="${local_override_root%/}/aarch64"
  if [ ! -d "${local_override_repo}" ]; then
    local_override_repo="${local_override_root%/}/master/aarch64"
  fi

  local_pmb_repo="${work_dir}/packages/${PMOS_VER}/aarch64"
  local_apk_cache="${work_dir}/cache_apk_aarch64"

  if [ -d "${local_override_repo}" ]; then
    sudo mkdir -p "${local_pmb_repo}"
    sudo mkdir -p "${local_apk_cache}"
    sudo cp "${local_override_repo}"/*.apk "${local_pmb_repo}/"
    sudo cp "${local_override_repo}/APKINDEX.tar.gz" "${local_pmb_repo}/"
    sudo cp "${local_override_repo}"/*.apk "${local_apk_cache}/"
  fi

  python3 "${PMB}" config mirrors.pmaports_custom "${local_override_url}"
fi

if [ -n "${APK_REPO_BASE_URL}" ] && [ "${APK_REPO_BASE_URL#file://}" != "${APK_REPO_BASE_URL}" ]; then
  shopt -s nullglob
  local_override_keys=("${local_override_key_root%/}"/*.pub "${local_override_key_root%/}/master"/*.pub)
  shopt -u nullglob

    if [ "${#local_override_keys[@]}" -gt 0 ]; then
      work_dir="$(python3 "${PMB}" config work)"
      sudo mkdir -p "${work_dir}/config_apk_keys"

      for key_path in "${local_override_keys[@]}"; do
        key_name="$(basename "${key_path}")"
        sudo install -m 0644 "${key_path}" "${work_dir}/config_apk_keys/${key_name}"
        sudo install -m 0644 "${key_path}" "${PMB_DIR}/pmb/data/keys/${key_name}"
      done
    fi
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
  sudo mkdir -p "${work_dir}/config_apk_keys"
  sudo install -m 0644 "${key_tmp}" "${work_dir}/config_apk_keys/${key_name}"
  sudo install -m 0644 "${key_tmp}" "${PMB_DIR}/pmb/data/keys/${key_name}"
  rm -f "${key_tmp}"
fi

python3 "${PMB}" config mirrors.pmaports
python3 "${PMB}" config mirrors.pmaports_custom
