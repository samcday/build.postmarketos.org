#!/usr/bin/env bash
set -euo pipefail

PMAPORTS_DIR="${1:?Usage: build-phosh-artifacts.sh <pmaports-dir> [device] [pmos-ver] [ui] [override-packages] [artifact-device]}"
DEVICE="${2:-oneplus-fajita}"
PMOS_VER="${3:-edge}"
UI="${4:-phosh}"
OVERRIDE_PACKAGES="${5:-}"
ARTIFACT_DEVICE="${6:-${DEVICE}}"
IMAGE_PASSWORD="${IMAGE_PASSWORD:-147147}"
APK_REPO_BASE_URL="${APK_REPO_BASE_URL:-}"

if [ -z "${PMBOOTSTRAP:-}" ] || [ -z "${PMB_WORK:-}" ]; then
  echo "PMBOOTSTRAP and PMB_WORK must be set"
  exit 1
fi

work="$(python3 "${PMBOOTSTRAP}" config work)"

verify_override_packages_available() {
  if [ -z "${APK_REPO_BASE_URL}" ] || [ -z "${OVERRIDE_PACKAGES}" ]; then
    return
  fi

  python3 - "${APK_REPO_BASE_URL%/}" "${OVERRIDE_PACKAGES}" <<'PY'
import io
import sys
import tarfile
import urllib.request

repo_base_url = sys.argv[1]
targets = [pkg for pkg in sys.argv[2].split(",") if pkg]

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

repo_versions = {pkg: set() for pkg in targets}
current_pkg = None
for line in apkindex_bytes.decode("utf-8", errors="ignore").splitlines():
    if line.startswith("P:"):
        current_pkg = line[2:]
        continue

    if current_pkg in repo_versions and line.startswith("V:"):
        repo_versions[current_pkg].add(line[2:])
        continue

    if line == "":
        current_pkg = None

missing_repo = [pkg for pkg in targets if not repo_versions[pkg]]
if missing_repo:
    print("Override APKINDEX is missing required overlay package metadata for: " + ", ".join(missing_repo))
    sys.exit(1)

print("Verified override APKINDEX contains required overlay package metadata.")
PY
}

mirror_fallback_noarch_packages() {
  if [ -z "${APK_REPO_BASE_URL}" ]; then
    return
  fi

  if [ "${APK_REPO_BASE_URL#file://}" != "${APK_REPO_BASE_URL}" ]; then
    return
  fi

  local repo_base="${APK_REPO_BASE_URL%/}"
  local tmp_dir
  local index_url=""
  local index_root=""
  local noarch_repo="${work}/packages/${PMOS_VER}/noarch"
  local local_apk_cache="${work}/cache_apk_aarch64"
  local mirrored_count=0
  local apk_name

  tmp_dir="$(mktemp -d)"

  for candidate in "${repo_base}/aarch64/APKINDEX.tar.gz" "${repo_base}/master/aarch64/APKINDEX.tar.gz"; do
    if curl -fsSL "${candidate}" -o "${tmp_dir}/APKINDEX.tar.gz"; then
      index_url="${candidate}"
      index_root="${candidate%/aarch64/APKINDEX.tar.gz}"
      break
    fi
  done

  if [ -z "${index_url}" ]; then
    rm -rf "${tmp_dir}"
    return
  fi

  python3 - "${tmp_dir}/APKINDEX.tar.gz" <<'PY' > "${tmp_dir}/noarch-packages.txt"
import sys
import tarfile

index_tar = sys.argv[1]

with tarfile.open(index_tar, "r:gz") as tar:
    source = tar.extractfile("APKINDEX")
    if source is None:
        raise SystemExit(0)

    pkg = None
    ver = None
    arch = None

    for line in source.read().decode("utf-8", errors="ignore").splitlines():
        if line.startswith("P:"):
            pkg = line[2:].strip()
            continue

        if line.startswith("V:"):
            ver = line[2:].strip()
            continue

        if line.startswith("A:"):
            arch = line[2:].strip()
            continue

        if line == "":
            if pkg and ver and arch == "noarch":
                print(f"{pkg}-{ver}.apk")

            pkg = None
            ver = None
            arch = None

    if pkg and ver and arch == "noarch":
        print(f"{pkg}-{ver}.apk")
PY

  if [ ! -s "${tmp_dir}/noarch-packages.txt" ]; then
    rm -rf "${tmp_dir}"
    return
  fi

  mkdir -p "${noarch_repo}" "${local_apk_cache}"

  while IFS= read -r apk_name; do
    if [ -z "${apk_name}" ]; then
      continue
    fi

    if curl -fsSLI "${index_root}/noarch/${apk_name}" >/dev/null; then
      continue
    fi

    if ! curl -fsSL "${index_root}/aarch64/${apk_name}" -o "${tmp_dir}/${apk_name}"; then
      echo "Warning: failed to mirror fallback noarch APK ${apk_name} from ${index_root}/aarch64"
      continue
    fi

    cp -f "${tmp_dir}/${apk_name}" "${noarch_repo}/${apk_name}"
    cp -f "${tmp_dir}/${apk_name}" "${local_apk_cache}/${apk_name}"
    mirrored_count=$((mirrored_count + 1))
  done < "${tmp_dir}/noarch-packages.txt"

  if [ "${mirrored_count}" -gt 0 ]; then
    echo "Mirrored ${mirrored_count} fallback noarch APK(s) after build_init"
  fi

  rm -rf "${tmp_dir}"
}

ensure_local_pkg_output_permissions() {
  local pmos_pkg_dir="${work}/packages/pmos/aarch64"
  local channel_pkg_dir="${work}/packages/${PMOS_VER}/aarch64"
  local -a ccache_dirs=("${work}/cache_ccache_aarch64" "${work}/cache_ccache_x86_64")
  local ccache_dir

  sudo mkdir -p "${pmos_pkg_dir}"
  sudo mkdir -p "${channel_pkg_dir}"
  sudo chmod 0777 "${work}/packages" "${work}/packages/pmos" "${pmos_pkg_dir}"
  sudo chmod 0777 "${work}/packages/${PMOS_VER}" "${channel_pkg_dir}"

  for ccache_dir in "${ccache_dirs[@]}"; do
    sudo mkdir -p "${ccache_dir}/tmp"
    sudo chmod -R a+rwX "${ccache_dir}"
    sudo chmod 1777 "${ccache_dir}/tmp"
  done
}

assert_bpo_image_name() {
  local image_path="$1"
  local image_name

  image_name="$(basename "${image_path}")"

  if [[ ! "${image_name}" =~ ^[0-9]{8}-[0-9]{4}-postmarketOS-.*\.img(\.xz)?$ ]]; then
    echo "Image name is not in BPO-style format: ${image_name}"
    exit 1
  fi

  if [[ "${image_name}" != *"-${ARTIFACT_DEVICE}.img" && "${image_name}" != *"-${ARTIFACT_DEVICE}.img.xz" ]]; then
    echo "Image name does not end with artifact device '${ARTIFACT_DEVICE}': ${image_name}"
    exit 1
  fi
}

assert_sparse_magic() {
  local image_xz="$1"

  python3 - "${image_xz}" <<'PY'
import lzma
import sys
from pathlib import Path

image_path = Path(sys.argv[1])
expected = bytes.fromhex("3aff26ed")

with lzma.open(image_path, "rb") as stream:
    actual = stream.read(4)

if actual != expected:
    found = " ".join(f"{b:02x}" for b in actual)
    print(f"Sparse magic mismatch in {image_path}: expected 3a ff 26 ed, got {found}")
    sys.exit(1)

print(f"Verified sparse magic for {image_path.name}")
PY
}

verify_override_packages_available
ensure_local_pkg_output_permissions

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
    sudo mkdir -p "${local_pmb_repo}"
    sudo mkdir -p "${local_apk_cache}"
    sudo cp "${local_override_repo}"/*.apk "${local_pmb_repo}/"
    sudo cp "${local_override_repo}/APKINDEX.tar.gz" "${local_pmb_repo}/"
    sudo cp "${local_override_repo}"/*.apk "${local_apk_cache}/"
  fi
fi

python3 "${PMBOOTSTRAP}" -y build_init
mirror_fallback_noarch_packages

install_ok=0
for attempt in 1 2 3; do
  ensure_local_pkg_output_permissions

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

if [ -n "${APK_REPO_BASE_URL}" ] && [ -n "${OVERRIDE_PACKAGES}" ]; then
  IFS=',' read -r -a override_pkgs <<< "${OVERRIDE_PACKAGES}"
  installed_path="out/installed-override-packages-${ARTIFACT_DEVICE}.txt"

  sudo chroot "${work_device_rootfs}" apk info -e -v "${override_pkgs[@]}" | tee "${installed_path}"

  python3 - "${installed_path}" "${APK_REPO_BASE_URL%/}" "${OVERRIDE_PACKAGES}" <<'PY'
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

repo_versions = {pkg: set() for pkg in targets}
current_pkg = None
for line in apkindex_bytes.decode("utf-8", errors="ignore").splitlines():
    if line.startswith("P:"):
        current_pkg = line[2:]
        continue

    if current_pkg in repo_versions and line.startswith("V:"):
        repo_versions[current_pkg].add(line[2:])
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

missing_repo = [pkg for pkg in targets if not repo_versions[pkg]]
if missing_repo:
    print("Override APKINDEX is missing required overlay package metadata for: " + ", ".join(missing_repo))
    sys.exit(1)

missing_installed = [pkg for pkg in targets if pkg not in installed_versions]
if missing_installed:
    print("Required overlay package not installed in rootfs: " + ", ".join(missing_installed))
    sys.exit(1)

mismatches = []
for pkg in targets:
    installed = installed_versions[pkg]
    if installed in repo_versions[pkg]:
        continue

    available = ", ".join(sorted(repo_versions[pkg]))
    mismatches.append(f"{pkg}: installed {installed} not in override versions {available}")

if mismatches:
    print("Installed overlay package versions do not match override APK repo:")
    for mismatch in mismatches:
        print("- " + mismatch)
    sys.exit(1)

print("Verified installed overlay package versions match override APK repo.")
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

expected_img="out/${img_prefix}.img"
if [ ! -f "${expected_img}" ]; then
  echo "Expected BPO-style image output not found: ${expected_img}"
  exit 1
fi

assert_bpo_image_name "${expected_img}"

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

shopt -s nullglob
xz_img_files=(out/*.img.xz)
if [ "${#xz_img_files[@]}" -eq 0 ]; then
  echo "No .img.xz files produced"
  exit 1
fi

for file in "${xz_img_files[@]}"; do
  assert_bpo_image_name "${file}"
  assert_sparse_magic "${file}"
done
shopt -u nullglob

ls -lh out

files=(out/*)
for file in "${files[@]}"; do
  sha256sum "${file}" | tee "${file}.sha256"
  sha512sum "${file}" | tee "${file}.sha512"
done

ls -lh out
