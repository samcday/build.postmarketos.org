# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
# Various functions related to pmbootstrap >= 3
import bpo.config.const
import bpo.helpers.job
import bpo.repo.staging
import bpo.repo.wip
import os
import shlex


def is_master(pmaports_branch):
    """Is using pmbootstrap master, instead of 2.3.x"""
    branches = bpo.repo.staging.get_branches_with_staging()
    pmb_branch = branches[pmaports_branch].get(
        "pmb_branch", bpo.config.const.pmb_branch_default)
    return pmb_branch == "master"


def set_repos_task(arch, branch):
    """Configure repositories for pmbootstrap v3"""
    wip_path = bpo.repo.wip.get_path(arch, branch)
    pmaports = bpo.helpers.job.get_pmos_mirror_for_pmbootstrap(branch)
    alpine = bpo.config.const.mirror_alpine
    ret = ""

    if os.path.exists(f"{wip_path}/APKINDEX.tar.gz"):
        # * job service sourcehut: this sets the WIP repo url
        # * job service local: BPO_WIP_REPO_URL is an empty string because we
        #   copy the WIP packages instead. So this just prints the currently
        #   set value for pmaports_custom, which is "none".
        ret += "pmbootstrap config mirrors.pmaports_custom $BPO_WIP_REPO_URL\n"

    ret += f"pmbootstrap config mirrors.pmaports {shlex.quote(pmaports)}\n"
    ret += f"pmbootstrap config mirrors.alpine {shlex.quote(alpine)}\n"

    return ret
