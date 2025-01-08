# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import os
import shlex

import bpo.config.const
import bpo.helpers.job
import bpo.repo.final


def run(arch, branch):
    uid = bpo.config.const.pmbootstrap_chroot_uid_user
    rsa = bpo.config.args.final_repo_key_name
    splitrepo = None  # FIXME
    fmt = bpo.repo.fmt(arch, branch, splitrepo)
    note = f"Sign index: `{fmt}`"

    tasks = collections.OrderedDict()

    unsigned_apkindex_url = os.path.join(
        bpo.helpers.pmb.get_pmos_mirror(branch, "wip", True),
        arch,
        "APKINDEX-symlink-repo.tar.gz"
    )

    if bpo.helpers.pmb.should_add_wip_repo(branch):
        tasks["download_unsigned_index"] = f"""
                wget {shlex.quote(unsigned_apkindex_url)} -O APKINDEX.tar.gz
        """

    if bpo.helpers.job.job_service_is_local():
        # For the local testsuite, we first download the real current unsigned
        # apkindex from the live bpo server to test that this code path works,
        # even though the APKINDEX file itself doesn't have the packages we
        # have locally. Then remove it and replace it with the local unsigned
        # APKINDEX, which does have the right packages.
        tasks["local_copy_unsigned_index"] = f"""
            rm -f APKINDEX.tar.gz
            cp "$BPO_WIP_REPO_PATH"/{arch}/APKINDEX-symlink-repo.tar.gz \
                    APKINDEX.tar.gz
        """

    # Ignore missing repos before initial build (bpo#137)
    env_force_missing_repos = ""
    final_path = bpo.repo.final.get_path(arch, branch, splitrepo)
    if not os.path.exists(f"{final_path}/APKINDEX.tar.gz"):
        env_force_missing_repos = "export PMB_APK_FORCE_MISSING_REPOSITORIES=1"

    tasks["sign"] = f"""
            {env_force_missing_repos}
            pmbootstrap \\
                --aports=$PWD/pmaports \\
                --no-ccache \\
                build_init
            work_dir="$(pmbootstrap -q config work)"
            chroot_target="$work_dir/chroot_native/home/pmos/"
            sudo cp APKINDEX.tar.gz "$chroot_target"
            sudo cp .final.rsa "$chroot_target"/{shlex.quote(rsa)}
            sudo chown -R {shlex.quote(uid)} "$chroot_target"
            pmbootstrap \\
                --aports=$PWD/pmaports \\
                --details-to-stdout \\
                chroot --user -- \\
                    abuild-sign \\
                        -k /home/pmos/{shlex.quote(rsa)} \\
                        /home/pmos/APKINDEX.tar.gz
            sudo mv "$chroot_target/APKINDEX.tar.gz" .
    """

    tasks["upload"] = f"""
            export BPO_API_ENDPOINT="sign-index"
            export BPO_ARCH={shlex.quote(arch)}
            export BPO_BRANCH={shlex.quote(branch)}
            export BPO_DEVICE=""
            export BPO_PAYLOAD_FILES="APKINDEX.tar.gz"
            export BPO_PAYLOAD_FILES_PREVIOUS=""
            export BPO_PAYLOAD_IS_JSON="0"
            export BPO_PKGNAME=""
            export BPO_SPLITREPO=""  # FIXME
            export BPO_UI=""
            export BPO_VERSION=""

            exec build.postmarketos.org/helpers/submit.py
    """

    bpo.helpers.job.run("sign_index", note, tasks, branch, arch)
