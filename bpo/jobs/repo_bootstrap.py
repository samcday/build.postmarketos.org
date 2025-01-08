# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import shlex

import bpo.db
import bpo.ui
import bpo.helpers.job
import bpo.helpers.pmb


def run(session, rb, test_pmaports_cfg=None):
    """
    Run "pmbootstrap repo_bootstrap" as job and upload the resulting packages.

    :param session: bpo.db.session() object
    :param rb: bpo.db.RepoBootstrap object
    :param test_pmaports_cfg: tests override pmaports.cfg with this
    """
    # Set mirror args (pmOS mirror is needed for cross compilers)
    pmb_v2_mirrors_arg = ""
    if not bpo.helpers.pmb.is_master(rb.branch):
        # NOTE: we don't use pmbv2 to build splitrepo packages
        mirror_final = bpo.helpers.pmb.get_pmos_mirror(rb.branch, None)
        pmb_v2_mirrors_arg += f" -mp {shlex.quote(mirror_final)}\\\n"
        pmb_v2_mirrors_arg += f" -m {shlex.quote(bpo.config.const.mirror_alpine)}\\\n"

    timeout = str(bpo.config.const.pmbootstrap_timeout)

    # Start job
    note = f"repo_bootstrap: `{rb.branch}-{rb.arch}-{rb.dir_name}`"
    tasks = collections.OrderedDict([])

    if test_pmaports_cfg:
        tasks["override_pmaports_cfg"] = f"""
            cp {shlex.quote(test_pmaports_cfg)} pmaports/pmaports.cfg
        """

    if bpo.helpers.pmb.is_master(rb.branch):
        tasks["set_repos"] = bpo.helpers.pmb.set_repos_task(rb.arch, rb.branch, False)

    tasks["repo_bootstrap"] = f"""
        pmbootstrap \\
            {pmb_v2_mirrors_arg} \\
            --aports=$PWD/pmaports \\
            --timeout {shlex.quote(timeout)} \\
            --details-to-stdout \\
            repo_bootstrap \\
            --arch {shlex.quote(rb.arch)} \\
            systemd
    """
    tasks["checksums"] = """
        cd "$(pmbootstrap -q config work)/packages/"
        sha512sum $(find . -name '*.apk')
    """
    tasks["submit"] = f"""
        export BPO_API_ENDPOINT="repo-bootstrap"
        export BPO_ARCH={shlex.quote(rb.arch)}
        export BPO_BRANCH={shlex.quote(rb.branch)}
        export BPO_SPLITREPO={shlex.quote(rb.dir_name)}
        export BPO_DEVICE=""
        packages="$(pmbootstrap -q config work)/packages"
        export BPO_PAYLOAD_FILES="$(find "$packages" -name '*.apk')"
        export BPO_PAYLOAD_FILES_PREVIOUS=""
        export BPO_PAYLOAD_IS_JSON="0"
        export BPO_PKGNAME=""
        export BPO_UI=""
        export BPO_VERSION=""

        exec build.postmarketos.org/helpers/submit.py
    """
    job_id = bpo.helpers.job.run("repo_bootstrap",
                                 note,
                                 tasks,
                                 rb.branch,
                                 rb.arch,
                                 rb.dir_name,  # splitrepo
                                 "[repo_bootstrap]",
                                 dir_name=rb.dir_name)

    # Increase retry count
    if rb.status == bpo.db.RepoBootstrapStatus.failed:
        rb.retry_count += 1
        session.merge(rb)
        session.commit()

    # Change status to building and save job_id
    bpo.db.set_repo_bootstrap_status(session,
                                     rb,
                                     bpo.db.RepoBootstrapStatus.building,
                                     job_id)
    bpo.ui.update(session)
