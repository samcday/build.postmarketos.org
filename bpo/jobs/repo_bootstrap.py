# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import shlex

import bpo.db
import bpo.ui
import bpo.helpers.job


def run(session, rb, test_pmaports_cfg=None):
    """
    Run "pmbootstrap repo_bootstrap" as job and upload the resulting packages.

    :param session: bpo.db.session() object
    :param rb: bpo.db.RepoBootstrap object
    :param test_pmaports_cfg: tests override pmaports.cfg with this
    """
    # Set mirror args (pmOS mirror is needed for cross compilers)
    mirror_alpine = shlex.quote(bpo.config.const.mirror_alpine)
    mirror_final = bpo.helpers.job.get_pmos_mirror_for_pmbootstrap(rb.branch)
    mirrors = "-mp " + shlex.quote(mirror_final)

    timeout = str(bpo.config.const.pmbootstrap_timeout)

    # Start job
    note = f"repo_bootstrap: `{rb.branch}-{rb.arch}-{rb.dir_name}`"
    tasks = collections.OrderedDict([])

    if test_pmaports_cfg:
        tasks.update({"override_pmaports_cfg":
            f"cp {shlex.quote(test_pmaports_cfg)} pmaports/pmaports.cfg"})

    tasks.update({"repo_bootstrap": """
                pmbootstrap \\
                    -m """ + mirror_alpine + """ \
                    """ + mirrors + """ \\
                    --aports=$PWD/pmaports \\
                    --timeout """ + timeout + """ \\
                    --details-to-stdout \\
                    repo_bootstrap \\
                    --arch """ + shlex.quote(rb.arch) + """ \\
                    systemd
                """}),
    tasks.update({"checksums": """
                    cd "$(pmbootstrap -q config work)/packages/"
                    sha512sum $(find . -name '*.apk')
                """}),
    tasks.update({"submit": """
                export BPO_API_ENDPOINT="repo-bootstrap"
                export BPO_ARCH=""" + shlex.quote(rb.arch) + """
                export BPO_BRANCH=""" + shlex.quote(rb.branch) + """
                export BPO_DEVICE=""
                packages="$(pmbootstrap -q config work)/packages"
                export BPO_PAYLOAD_FILES="$(find "$packages" -name '*.apk')"
                export BPO_PAYLOAD_FILES_PREVIOUS=""
                export BPO_PAYLOAD_IS_JSON="0"
                export BPO_PKGNAME=""
                export BPO_UI=""
                export BPO_VERSION=""

                exec build.postmarketos.org/helpers/submit.py
                """})
    job_id = bpo.helpers.job.run("repo_bootstrap", note, tasks, rb.branch,
                                 rb.arch, "[repo_bootstrap]",
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
