# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import os
import shlex

import bpo.config.const
import bpo.helpers.job
import bpo.repo.final


def run(arch, branch, splitrepo):
    uid = bpo.config.const.pmbootstrap_chroot_uid_user
    rsa = bpo.config.args.final_repo_key_name
    fmt = bpo.repo.fmt(arch, branch, splitrepo)
    note = f"Sign index: `{fmt}`"

    tasks = collections.OrderedDict()

    unsigned_apkindex_url = os.path.join(
        bpo.helpers.pmb.get_pmos_mirror(branch, splitrepo, "wip", True),
        arch,
        "APKINDEX-symlink-repo.tar.gz"
    )

    if not bpo.helpers.job.job_service_is_local():
        if bpo.helpers.pmb.should_add_wip_repo(branch):
            tasks["download_unsigned_index"] = f"""
                    wget {shlex.quote(unsigned_apkindex_url)} -O APKINDEX.tar.gz
            """
    else:
        tasks["local_copy_unsigned_index"] = f"""
            cp "$BPO_WIP_REPO_PATH"/{arch}/APKINDEX-symlink-repo.tar.gz \
                    APKINDEX.tar.gz
        """

    tasks["set_repos"] = bpo.helpers.pmb.set_repos_task(arch, branch, False)

    tasks["sign"] = f"""
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
            export BPO_SPLITREPO={shlex.quote(splitrepo)}
            export BPO_UI=""
            export BPO_VERSION=""

            exec build.postmarketos.org/helpers/submit.py
    """

    bpo.helpers.job.run("sign_index", note, tasks, branch, arch, splitrepo)
