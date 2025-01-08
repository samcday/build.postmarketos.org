# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
# Various functions related to pmbootstrap
import bpo.config.const
import bpo.helpers.job
import bpo.repo.staging
import bpo.repo.wip
import logging
import os
import shlex


def is_master(pmaports_branch):
    """Is using pmbootstrap master, instead of 2.3.x"""
    branches = bpo.repo.staging.get_branches_with_staging()
    pmb_branch = branches[pmaports_branch].get(
        "pmb_branch", bpo.config.const.pmb_branch_default)
    return pmb_branch == "master"


def get_pmos_mirror(branch, splitrepo, mirror_type="main", add_branch=False):
    mapping = {
        "main": bpo.config.args.mirror,
        "wip": bpo.config.args.url_repo_wip,
    }

    ret = mapping[mirror_type]
    if not ret:
        return ""

    if splitrepo:
        ret = os.path.join(ret, "extra-repos", splitrepo)

    if "_staging_" in branch:
        branch_orig, name = bpo.repo.staging.branch_split(branch)
        ret = os.path.join(ret, "staging", name)
        if add_branch:
            ret = os.path.join(ret, branch_orig)
    else:
        if add_branch:
            ret = os.path.join(ret, branch)

    return f"{ret}/"


def should_add_wip_repo(branch):
    """The WIP repository always needs to be added when running with sourcehut.
       It is not needed when using the local job service since there the WIP
       packages get copied into the work directory before the test starts.
       However it is desirable to add it there too if possible, to check if
       the URL gets generated correctly and is usable."""
    if not bpo.helpers.job.job_service_is_local():
        return True

    if "_staging_" in branch:
        # Staging branches in the testsuite have names like test1234, which
        # don't exist on the real bpo server
        logging.debug("should_add_wip_repo: no, because staging is in branch")
        return False

    logging.debug("should_add_wip_repo: yes, assuming it exists")
    return True


def set_repos_task(arch, branch, add_wip_repo=True):
    """Configure repositories for pmbootstrap v3"""
    splitrepo = None  # FIXME
    wip_path = bpo.repo.wip.get_path(arch, branch, splitrepo)
    pmaports = get_pmos_mirror(branch, splitrepo) or "none"
    alpine = bpo.config.const.mirror_alpine
    ret = ""

    if add_wip_repo and os.path.exists(f"{wip_path}/APKINDEX.tar.gz"):
        wip_repo_url_line = "pmbootstrap config mirrors.pmaports_custom"
        wip_repo_url_line += f" {shlex.quote(get_pmos_mirror(branch, splitrepo, 'wip'))}\n"
        if should_add_wip_repo(branch):
            ret += wip_repo_url_line

    ret += f"pmbootstrap config mirrors.pmaports {shlex.quote(pmaports)}\n"
    ret += f"pmbootstrap config mirrors.alpine {shlex.quote(alpine)}\n"

    return ret
