#!/usr/bin/env bash
set -euo pipefail

PMAPORTS_DIR="${1:?Usage: build-oneplus-fajita-artifacts.sh <pmaports-dir> [device] [pmos-ver] [ui]}"
DEVICE="${2:-oneplus-fajita}"
PMOS_VER="${3:-edge}"
UI="${4:-phosh}"
IMAGE_PASSWORD="${IMAGE_PASSWORD:-147147}"
APK_REPO_BASE_URL="${APK_REPO_BASE_URL:-}"

if [ -z "${PMBOOTSTRAP:-}" ] || [ -z "${PMB_WORK:-}" ]; then
  echo "PMBOOTSTRAP and PMB_WORK must be set"
  exit 1
fi

python3 "${PMBOOTSTRAP}" -y build_init
python3 "${PMBOOTSTRAP}" -y --details-to-stdout install --no-sshd --no-local-pkgs --password "${IMAGE_PASSWORD}"

img_date="$(date +%Y%m%d-%H%M)"
ui_apkbuild="${PMAPORTS_DIR}/main/postmarketos-ui-${UI}/APKBUILD"

if [ ! -f "${ui_apkbuild}" ]; then
  echo "Missing ${ui_apkbuild}"
  exit 1
fi

ui_version="$(grep '^pkgver=' "${ui_apkbuild}" | cut -d= -f2 | cut -d ' ' -f1)"
img_prefix="${img_date}-postmarketOS-${PMOS_VER}-${UI}-${ui_version}-${DEVICE}"

work="$(python3 "${PMBOOTSTRAP}" config work)"
work_device_rootfs="${work}/chroot_rootfs_${DEVICE}"
work_rootfs="${work}/chroot_native/home/pmos/rootfs"

mkdir -p out

if [ -n "${APK_REPO_BASE_URL}" ]; then
  policy_path="out/apk-policy.txt"
  sudo chroot "${work_device_rootfs}" apk policy \
    linux-postmarketos-qcom-sdm845 \
    device-oneplus-fajita | tee "${policy_path}"

  python3 - "${policy_path}" "${APK_REPO_BASE_URL%/}" <<'PY'
import re
import sys

policy_path = sys.argv[1]
repo_base_url = sys.argv[2]
targets = ["linux-postmarketos-qcom-sdm845", "device-oneplus-fajita"]

seen = {name: False for name in targets}
current = None

with open(policy_path, "r", encoding="utf-8", errors="ignore") as handle:
    for line in handle:
        line = line.rstrip("\n")
        match = re.match(r"^([A-Za-z0-9+._-]+) policy:$", line)
        if match:
            current = match.group(1)
            continue

        if current in seen and repo_base_url in line:
            seen[current] = True

missing = [name for name, found in seen.items() if not found]
if missing:
    print("Override APK repo not visible for: " + ", ".join(missing))
    sys.exit(1)

print("Verified override APK repo visibility for target packages.")
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
