#!/usr/bin/env bash
set -euo pipefail

PMAPORTS_DIR="${1:?Usage: build-phosh-artifacts.sh <pmaports-dir> [device] [pmos-ver] [ui] [target-packages] [artifact-device]}"
DEVICE="${2:-oneplus-fajita}"
PMOS_VER="${3:-edge}"
UI="${4:-phosh}"
TARGET_PACKAGES="${5:-}"
ARTIFACT_DEVICE="${6:-${DEVICE}}"
IMAGE_PASSWORD="${IMAGE_PASSWORD:-147147}"
APK_REPO_BASE_URL="${APK_REPO_BASE_URL:-}"

if [ -z "${PMBOOTSTRAP:-}" ] || [ -z "${PMB_WORK:-}" ]; then
  echo "PMBOOTSTRAP and PMB_WORK must be set"
  exit 1
fi

work="$(python3 "${PMBOOTSTRAP}" config work)"

if [ -n "${APK_REPO_BASE_URL}" ] && [ "${APK_REPO_BASE_URL#file://}" != "${APK_REPO_BASE_URL}" ]; then
  local_override_repo="${APK_REPO_BASE_URL#file://}"
  local_override_repo="${local_override_repo%/}/aarch64"
  if [ ! -d "${local_override_repo}" ]; then
    local_override_repo="${APK_REPO_BASE_URL#file://}"
    local_override_repo="${local_override_repo%/}/master/aarch64"
  fi

  local_pmb_repo="${work}/packages/${PMOS_VER}/aarch64"
  local_apk_cache="${work}/cache_apk_aarch64"

  if [ -d "${local_override_repo}" ]; then
    mkdir -p "${local_pmb_repo}"
    mkdir -p "${local_apk_cache}"
    cp "${local_override_repo}"/*.apk "${local_pmb_repo}/"
    cp "${local_override_repo}/APKINDEX.tar.gz" "${local_pmb_repo}/"
    sudo cp "${local_override_repo}"/*.apk "${local_apk_cache}/"
  fi
fi

python3 "${PMBOOTSTRAP}" -y build_init

install_ok=0
for attempt in 1 2 3; do
  if python3 "${PMBOOTSTRAP}" -y --details-to-stdout install --no-sshd --password "${IMAGE_PASSWORD}"; then
    install_ok=1
    break
  fi

  if [ "${attempt}" -lt 3 ]; then
    echo "pmbootstrap install failed on attempt ${attempt}; retrying after 20s"
    sleep 20
  fi
done

if [ "${install_ok}" -ne 1 ]; then
  echo "pmbootstrap install failed after 3 attempts"
  exit 1
fi

img_date="$(date +%Y%m%d-%H%M)"
ui_apkbuild="${PMAPORTS_DIR}/main/postmarketos-ui-${UI}/APKBUILD"

if [ ! -f "${ui_apkbuild}" ]; then
  echo "Missing ${ui_apkbuild}"
  exit 1
fi

ui_version="$(grep '^pkgver=' "${ui_apkbuild}" | cut -d= -f2 | cut -d ' ' -f1)"
img_prefix="${img_date}-postmarketOS-${PMOS_VER}-${UI}-${ui_version}-${ARTIFACT_DEVICE}"

work_device_rootfs="${work}/chroot_rootfs_${DEVICE}"
work_rootfs="${work}/chroot_native/home/pmos/rootfs"

mkdir -p out

if [ -n "${APK_REPO_BASE_URL}" ] && [ -n "${TARGET_PACKAGES}" ]; then
  IFS=',' read -r -a target_pkgs <<< "${TARGET_PACKAGES}"
  installed_path="out/installed-target-packages-${ARTIFACT_DEVICE}.txt"

  sudo chroot "${work_device_rootfs}" apk info -e -v "${target_pkgs[@]}" | tee "${installed_path}"

  python3 - "${installed_path}" "${APK_REPO_BASE_URL%/}" "${TARGET_PACKAGES}" <<'PY'
import io
import sys
import tarfile
import urllib.request

installed_path = sys.argv[1]
repo_base_url = sys.argv[2]
targets = [pkg for pkg in sys.argv[3].split(",") if pkg]

index_candidates = [
    f"{repo_base_url}/aarch64/APKINDEX.tar.gz",
    f"{repo_base_url}/master/aarch64/APKINDEX.tar.gz",
]

apkindex_tar = None
for index_url in index_candidates:
    try:
        with urllib.request.urlopen(index_url, timeout=30) as response:
            apkindex_tar = response.read()
        break
    except Exception:
        continue

if apkindex_tar is None:
    print("Failed to download APKINDEX.tar.gz from override repo")
    sys.exit(1)

with tarfile.open(fileobj=io.BytesIO(apkindex_tar), mode="r:gz") as tar:
    apkindex_bytes = tar.extractfile("APKINDEX").read()

repo_versions = {}
current_pkg = None
for line in apkindex_bytes.decode("utf-8", errors="ignore").splitlines():
    if line.startswith("P:"):
        current_pkg = line[2:]
        continue

    if current_pkg in targets and line.startswith("V:") and current_pkg not in repo_versions:
        repo_versions[current_pkg] = line[2:]
        continue

    if line == "":
        current_pkg = None

installed_versions = {}
with open(installed_path, "r", encoding="utf-8", errors="ignore") as handle:
    for line in handle:
        line = line.strip()
        for pkg in targets:
            prefix = f"{pkg}-"
            if line.startswith(prefix):
                installed_versions[pkg] = line[len(prefix):]

missing_repo = [pkg for pkg in targets if pkg not in repo_versions]
if missing_repo:
    print("Override APKINDEX is missing target package metadata for: " + ", ".join(missing_repo))
    sys.exit(1)

missing_installed = [pkg for pkg in targets if pkg not in installed_versions]
if missing_installed:
    print("Target package not installed in rootfs: " + ", ".join(missing_installed))
    sys.exit(1)

mismatches = [
    f"{pkg}: installed {installed_versions[pkg]} != override {repo_versions[pkg]}"
    for pkg in targets
    if installed_versions[pkg] != repo_versions[pkg]
]

if mismatches:
    print("Installed versions do not match override APK repo:")
    for mismatch in mismatches:
        print("- " + mismatch)
    sys.exit(1)

print("Verified installed target package versions match override APK repo.")
PY
fi

if [ -e "${work_rootfs}/${DEVICE}.img" ]; then
  sudo mv "${work_rootfs}/${DEVICE}.img" "out/${img_prefix}.img"
else
  if [ ! -e "${work_rootfs}/${DEVICE}-root.img" ]; then
    echo "Expected image output in ${work_rootfs}"
    exit 1
  fi

  sudo mv "${work_rootfs}/${DEVICE}-root.img" "out/${img_prefix}.img"
fi

ls -lh out

shopt -s nullglob
img_files=(out/*.img)
if [ "${#img_files[@]}" -eq 0 ]; then
  echo "No .img files produced"
  exit 1
fi

sudo chown "$(id -u):$(id -g)" "${img_files[@]}"

for file in "${img_files[@]}"; do
  xz -0 -T0 "${file}"
done
shopt -u nullglob

ls -lh out

files=(out/*)
for file in "${files[@]}"; do
  sha256sum "${file}" | tee "${file}.sha256"
  sha512sum "${file}" | tee "${file}.sha512"
done

ls -lh out
