# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
import collections
import shlex

import bpo.db
import bpo.helpers.job
import bpo.helpers.pmb
import bpo.images
import bpo.images.config
import bpo.ui


def get_pmbootstrap_install_cmd(branch):
    """ pmbootstrap install command for image building. This is a separate
        function, so we can override it with a stub in a test. """

    pmb_v2_mirrors_arg = ""
    if not bpo.helpers.pmb.is_master(branch):
        mirror_final = bpo.helpers.job.get_pmos_mirror_for_pmbootstrap(branch)
        pmb_v2_mirrors_arg += f" -mp {shlex.quote(mirror_final)}\\\n"
        pmb_v2_mirrors_arg += f" -m {shlex.quote(bpo.config.const.mirror_alpine)}\\\n"

    return f"""pmbootstrap \\
                --details-to-stdout \\
                {pmb_v2_mirrors_arg} \\
                install \\
                --no-sshd \\
                --no-local-pkgs"""


def get_task_name(prefix, kernel):
    if kernel:
        return f"{prefix}_{kernel}".replace("-", "_")
    return prefix


def get_arg_img_prefix(kernel):
    ret = "$(cat img-prefix)"
    if kernel:
        ret += shlex.quote(f"-{kernel}")
    return ret


def run(device, branch, ui):
    """ Start a single image build job. """
    # Put the pkgver from this package into the image name
    ui_apkbuild = f"main/postmarketos-ui-{ui}/APKBUILD"

    # Shell arguments
    arg_branch = shlex.quote(branch)
    arg_device = shlex.quote(device)
    arg_pass = shlex.quote(bpo.config.const.images.password)
    arg_pmos_ver = shlex.quote(bpo.images.pmos_ver(branch))
    arg_ui = shlex.quote(ui)
    arg_ui_apkbuild = shlex.quote(ui_apkbuild)
    arg_work = "$(pmbootstrap config work)"
    arg_work_boot = f"{arg_work}/chroot_rootfs_{arg_device}/boot"
    arg_work_rootfs = f"{arg_work}/chroot_native/home/pmos/rootfs"
    tasks = collections.OrderedDict()

    # Configure pmbootstrap mirrors
    if bpo.helpers.pmb.is_master(branch):
        tasks["set_repos"] = bpo.helpers.pmb.set_repos_task(None, branch, False)

    # Task: img_prepare (generate image prefix, configure pmb, create tmpdir)
    tasks["img_prepare"] = f"""
        IMG_DATE="$(date +%Y%m%d-%H%M)"
        echo "$IMG_DATE" > img-date

        # Image prefix format:
        # <YYYYMMDD-HHMM>-postmarketOS-<PMOS VER>-<UI>-<UI VER>-<DEVICE>
        UI_VERSION=$(grep "^pkgver=" "$(pmbootstrap config aports \\
            )"/{arg_ui_apkbuild} | cut -d= -f2)
        IMG_PREFIX="$IMG_DATE"-postmarketOS-{arg_pmos_ver}-{arg_ui}
        IMG_PREFIX="$IMG_PREFIX"-"$UI_VERSION"-{arg_device}
        echo "$IMG_PREFIX" > img-prefix

        pmbootstrap config ui {arg_ui}
        pmbootstrap config device {arg_device}

        mkdir out
    """

    pmbootstrap_install = get_pmbootstrap_install_cmd(branch)

    # Iterate over kernels to generate the images, with zap in-between
    branch_cfg = bpo.images.config.get_branch_config(device, branch)
    arg_extra_packages = ["lang", "musl-locales"]
    for kernel in branch_cfg["kernels"]:
        # Task and image name, add kernel suffix if having multiple kernels
        task_name = get_task_name("img", kernel)
        arg_img_prefix = get_arg_img_prefix(kernel)

        # Task: img
        arg_kernel = shlex.quote(kernel)
        tasks[task_name] = f"""
            IMG_PREFIX={arg_img_prefix}

            pmbootstrap config kernel {arg_kernel}
            pmbootstrap config extra_space 0
            pmbootstrap config extra_packages {",".join(arg_extra_packages)}
            pmbootstrap -q -y zap -p

            {pmbootstrap_install} \\
                --password {arg_pass}

            if [ -e {arg_work_rootfs}/{arg_device}.img ]; then
                sudo mv {arg_work_rootfs}/{arg_device}.img \\
                        "out/$IMG_PREFIX.img"
            else
                # Boot and root partitions in separate files (pmbootstrap!1871)
                # Name the second file -bootpart.img instead of -boot.img to
                # avoid confusion with Android boot.img files.
                sudo mv {arg_work_rootfs}/{arg_device}-root.img \\
                        "out/$IMG_PREFIX.img"
                sudo mv {arg_work_rootfs}/{arg_device}-boot.img \\
                        "out/$IMG_PREFIX-bootpart.img"
            fi
            ls -lh out
        """

        # Task: img_bootimg
        # For Android devices, postmarketos-mkinitfs generates a boot.img
        # inside the rootfs img (above). Make it available as separate file, to
        # make flashing easier. 'boot.img*', because the kernel name was
        # appended with the pre 1.0.0 postmarketos-mkinitfs used in v21.06 and
        # earlier (e.g. boot.img-postmarketos-qcom-msm8916).
        tasks[f"{task_name}_bootimg"] = f"""
            IMG_PREFIX={arg_img_prefix}

            for i in {arg_work_boot}/boot.img*; do
                if [ -e "$i" ]; then
                    sudo mv "$i" "out/$IMG_PREFIX-boot.img"
                fi
            done

            ls -lh out
        """

        # Task: img_lk2nd
        # For Androids, it's useful to have the proper lk2nd image available
        # besides the other image files (#127).
        tasks[f"{task_name}_lk2nd"] = f"""
            IMG_PREFIX={arg_img_prefix}

            for i in {arg_work_boot}/lk2nd.img; do
                if [ -e "$i" ]; then
                    sudo mv "$i" "out/$IMG_PREFIX-lk2nd.img"
                fi
            done

            ls -lh out
        """

    tasks["compress"] = """
            sudo chown "$(id -u):$(id -g)" out/*.img

            for i in out/*.img; do
                xz -0 -T0 "$i"
            done

            ls -lh out
    """

    # Build the android recovery zip after compressing previously built images,
    # so we consume less space while building
    if branch_cfg["android-recovery-zip"]:
        for kernel in branch_cfg["kernels"]:
            task_name = get_task_name("recovery_zip", kernel)
            arg_img_prefix = get_arg_img_prefix(kernel)

            tasks[task_name] = f"""
            OUTPUT_FILE=out/{arg_img_prefix}-android-recovery.zip

            pmbootstrap -q -y zap -p

            {pmbootstrap_install} \\
                    --password {arg_pass} \\
                    --android-recovery-zip \\
                    --recovery-install-partition=data

            sudo mv {arg_work}/chroot_*/var/lib/postmarketos-android-recovery-installer/pmos-{arg_device}.zip \
                    "$OUTPUT_FILE"

            sudo chown "$(id -u):$(id -g)" "$OUTPUT_FILE"
            ls -lh "$OUTPUT_FILE"
            """

    tasks["checksums"] = """
            cd out
            for i in *; do
                sha256sum "$i" | tee "$i.sha256"
                sha512sum "$i" | tee "$i.sha512"
            done
    """

    tasks["submit"] = f"""
            export BPO_API_ENDPOINT="build-image"
            export BPO_ARCH=""
            export BPO_BRANCH={arg_branch}
            export BPO_DEVICE={arg_device}
            export BPO_UI={arg_ui}
            export BPO_PAYLOAD_IS_JSON="0"
            export BPO_PKGNAME=""
            export BPO_VERSION="$(cat img-date)"

            # Upload one file at a time
            prev=""
            for i in out/*; do
                export BPO_PAYLOAD_FILES_PREVIOUS="$prev"
                export BPO_PAYLOAD_FILES="$i"
                build.postmarketos.org/helpers/submit.py
                prev="$prev$(basename "$i")#"
            done

            # Finalize upload
            export BPO_PAYLOAD_FILES_PREVIOUS="$prev"
            export BPO_PAYLOAD_FILES=""
            build.postmarketos.org/helpers/submit.py
    """

    # Submit to job service
    note = f"Build image: `{branch}:{device}:{ui}`"
    job_id = bpo.helpers.job.run("build_image", note, tasks, branch,
                                 device=device, ui=ui)

    # Update DB and UI
    session = bpo.db.session()
    image = bpo.db.get_image(session, branch, device, ui)
    if image.status == bpo.db.ImageStatus.failed:
        image.retry_count += 1
    bpo.db.set_image_status(session, image, bpo.db.ImageStatus.building,
                            job_id)
    bpo.ui.update(session)
