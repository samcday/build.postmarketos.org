#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REQUESTED_DEVICE="${1:-oneplus-fajita}"
PMAPORTS_DIR="${PMAPORTS_DIR:-${2:-${WORKSPACE_ROOT}/pmaports}}"

UI="${UI:-phosh}"
PMOS_VER="${PMOS_VER:-edge}"
IMAGE_PASSWORD="${IMAGE_PASSWORD:-147147}"
LOCAL_ARTIFACTS_DIR="${LOCAL_ARTIFACTS_DIR:-${WORKSPACE_ROOT}/local-artifacts}"

OVERRIDE_REPO_DEFAULT="https://pmos.samcday.com"
OVERRIDE_REPO="${OVERRIDE_REPO:-${APK_REPO_BASE_URL:-${OVERRIDE_REPO_DEFAULT}}}"
OVERRIDE_KEY="${OVERRIDE_KEY:-${APK_REPO_KEY_URL:-}}"

if [[ "${REQUESTED_DEVICE}" == *","* ]]; then
  echo "This helper builds one device per execution. Pass a single device."
  exit 1
fi

case "${REQUESTED_DEVICE}" in
  oneplus-fajita)
    PMBOOTSTRAP_DEVICE="oneplus-fajita"
    ARTIFACT_DEVICE="oneplus-fajita"
    OVERRIDE_PACKAGES="linux-postmarketos-qcom-sdm845"
    ;;
  samsung-a5u-eur|samsung-a5)
    PMBOOTSTRAP_DEVICE="samsung-a5"
    ARTIFACT_DEVICE="samsung-a5u-eur"
    OVERRIDE_PACKAGES="linux-postmarketos-qcom-msm8916"
    ;;
  arrow-db410c|db410c)
    PMBOOTSTRAP_DEVICE="arrow-db410c"
    ARTIFACT_DEVICE="db410c"
    OVERRIDE_PACKAGES="linux-postmarketos-qcom-msm8916"
    ;;
  *)
    echo "Unsupported device '${REQUESTED_DEVICE}'."
    echo "Allowed devices: oneplus-fajita, samsung-a5u-eur, arrow-db410c"
    exit 1
    ;;
esac

if [ ! -d "${PMAPORTS_DIR}" ]; then
  echo "pmaports directory not found: ${PMAPORTS_DIR}"
  exit 1
fi

if [[ "${OVERRIDE_REPO}" == file://* ]]; then
  override_path="${OVERRIDE_REPO#file://}"
  if [ -n "${override_path}" ] && [ ! -d "${override_path}" ]; then
    echo "Override APK repo not found: ${override_path}; building without override repo"
    OVERRIDE_REPO=""
    OVERRIDE_KEY=""
  fi
fi

if [ -z "${OVERRIDE_REPO}" ]; then
  echo "Building without override APK repo (set OVERRIDE_REPO to enable it)."
fi

if [ -z "${OVERRIDE_KEY}" ] && [ -n "${OVERRIDE_REPO}" ] && [[ "${OVERRIDE_REPO}" != file://* ]]; then
  OVERRIDE_KEY="${OVERRIDE_REPO%/}/pmos.samcday.com.rsa.pub"
fi

if [ -z "${OVERRIDE_KEY}" ] && [ -n "${OVERRIDE_REPO}" ] && [[ "${OVERRIDE_REPO}" == file://* ]]; then
  if [ -f "${OVERRIDE_REPO#file://}/master/pmos.samcday.com.rsa.pub" ]; then
    OVERRIDE_KEY="${OVERRIDE_REPO}/master/pmos.samcday.com.rsa.pub"
  elif [ -f "${OVERRIDE_REPO#file://}/pmos.samcday.com.rsa.pub" ]; then
    OVERRIDE_KEY="${OVERRIDE_REPO}/pmos.samcday.com.rsa.pub"
  fi
fi

tmp_env_file="$(mktemp)"
export GITHUB_ENV="${tmp_env_file}"
: > "${GITHUB_ENV}"

if [ -n "${OVERRIDE_REPO}" ] && [ -n "${OVERRIDE_KEY}" ]; then
  bash "${SCRIPT_DIR}/.github/scripts/setup-pmbootstrap.sh" \
    "${PMAPORTS_DIR}" "${PMBOOTSTRAP_DEVICE}" "${UI}" "${PMOS_VER}" \
    "${OVERRIDE_REPO}" "${OVERRIDE_KEY}"
elif [ -n "${OVERRIDE_REPO}" ]; then
  bash "${SCRIPT_DIR}/.github/scripts/setup-pmbootstrap.sh" \
    "${PMAPORTS_DIR}" "${PMBOOTSTRAP_DEVICE}" "${UI}" "${PMOS_VER}" \
    "${OVERRIDE_REPO}"
else
  bash "${SCRIPT_DIR}/.github/scripts/setup-pmbootstrap.sh" \
    "${PMAPORTS_DIR}" "${PMBOOTSTRAP_DEVICE}" "${UI}" "${PMOS_VER}"
fi

set -a
source "${GITHUB_ENV}"
set +a

rm -f "${GITHUB_ENV}"
unset GITHUB_ENV

if [ -z "${PMBOOTSTRAP:-}" ] || [ -z "${PMB_WORK:-}" ]; then
  echo "setup-pmbootstrap.sh did not export PMBOOTSTRAP/PMB_WORK"
  exit 1
fi

rm -rf "${SCRIPT_DIR}/out"
mkdir -p "${SCRIPT_DIR}/out"

export IMAGE_PASSWORD

bash "${SCRIPT_DIR}/.github/scripts/build-phosh-artifacts.sh" \
  "${PMAPORTS_DIR}" \
  "${PMBOOTSTRAP_DEVICE}" \
  "${PMOS_VER}" \
  "${UI}" \
  "${OVERRIDE_PACKAGES}" \
  "${ARTIFACT_DEVICE}"

mkdir -p "${LOCAL_ARTIFACTS_DIR}"
cp -f "${SCRIPT_DIR}/out"/* "${LOCAL_ARTIFACTS_DIR}/"

shopt -s nullglob
img_candidates=("${SCRIPT_DIR}/out"/*"${ARTIFACT_DEVICE}"*.img.xz)
if [ "${#img_candidates[@]}" -eq 0 ]; then
  img_candidates=("${SCRIPT_DIR}/out"/*.img.xz)
fi
shopt -u nullglob

if [ "${#img_candidates[@]}" -eq 0 ]; then
  echo "No .img.xz artifact found in ${SCRIPT_DIR}/out"
  exit 1
fi

stable_img="${LOCAL_ARTIFACTS_DIR}/${ARTIFACT_DEVICE}-rootfs.img.xz"
cp -f "${img_candidates[0]}" "${stable_img}"
cp -f "${img_candidates[0]}.sha256" "${stable_img}.sha256" 2>/dev/null || true
cp -f "${img_candidates[0]}.sha512" "${stable_img}.sha512" 2>/dev/null || true

echo "Build complete for ${REQUESTED_DEVICE}"
echo "BPO-style outputs: ${SCRIPT_DIR}/out"
echo "Stable local artifact: ${stable_img}"
ls -lh "${SCRIPT_DIR}/out"
ls -lh "${LOCAL_ARTIFACTS_DIR}"
