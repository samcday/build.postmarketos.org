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


def set_repos_task(arch, branch, add_wip_repo=True, always_add_main_repo=False):
    """Configure repositories for pmbootstrap v3"""
    alpine = bpo.config.const.mirror_alpine
    ret = f"pmbootstrap config mirrors.alpine {shlex.quote(alpine)}\n"

    for splitrepo in bpo.config.const.splitrepos:
        # Configure mirrors.pmaports or mirrors.systemd
        # https://docs.postmarketos.org/pmbootstrap/mirrors.html
        mirror_name = splitrepo or "pmaports"

        if add_wip_repo:
            wip_path = bpo.repo.wip.get_path(arch, branch, splitrepo)
            if wip_path and os.path.exists(os.path.join(wip_path, "APKINDEX.tar.gz")) and should_add_wip_repo(branch):
                url_wip = get_pmos_mirror(branch, splitrepo, "wip") or "none"
                ret += f"pmbootstrap config mirrors.{mirror_name}_custom {shlex.quote(url_wip)}\n"

        url = "none"
        final_path = bpo.repo.final.get_path(arch, branch, splitrepo)
        if (splitrepo is None and always_add_main_repo) or \
                (final_path and os.path.exists(os.path.join(final_path, "APKINDEX.tar.gz"))):
            url = get_pmos_mirror(branch, splitrepo) or "none"

        ret += f"pmbootstrap config mirrors.{mirror_name} {shlex.quote(url)}\n"

    return ret
