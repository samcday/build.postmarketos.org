# Copyright 2023 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
import copy
import glob
import logging
import os
import shutil

import bpo.config
import bpo.db
import bpo.repo.final
import bpo.repo.wip
import bpo.ui


def branch_split(branch):
    """ Split a staging branch name in its components.
        :param branch: the full branch name, e.g. "master_staging_lomiri" "v22.12_staging_sp2"
        :returns: * None if it isn't a valid staging branch
        * (branch_orig, name)
        * branch_orig: the original branch as in the config(e.g. "master")
        * name: e.g. "hi_there" (branch "master_staging_hi_there")

    """
    if "_staging_" not in branch:
        return None

    branch_orig = branch.split("_staging_", 1)[0]
    if branch_orig not in bpo.config.const.branches:
        return None

    name = branch.split("_staging_", 1)[1]
    return branch_orig, name


def init(branch):
    """ If the staging repository does not exist yet, create the directory
        structure with a README file. The repository will be filled later on,
        when sync_with_orig_repo gets called for the first time.
        :param branch: staging branch name

    """
    branch_orig, name = branch_split(branch)
    path = f"{bpo.config.args.repo_final_path}/staging/{name}/{branch_orig}"
    path_readme = f"{path}/README"

    # The README file is the marker that the path was already initialized
    if os.path.exists(path_readme):
        return

    bpo.ui.log("init_staging_repo", branch=branch)

    os.makedirs(path, exist_ok=True)
    with open(path_readme, "w+") as handle:
        handle.write("This is a staging branch. More information:\n")
        handle.write("https://postmarketos.org/staging\n")


def sync_with_orig_repo(branch_staging, arch, splitrepo):
    """
    For all packages that are the same in the staging repo and the original
    repository, copy the package and update the copy of the package with the
    staging branch in the database. This function gets called right before
    calculating the next package to build from the staging branch.

    The copies are created in the WIP repository of the staging branch.
    (After potentially building any missing packages, the WIP repository gets
    published, not part of this function.)

    :param branch_staging: name of the staging branch
    :param arch: architecture
    :returns stats: see below

    """
    stats = {
        "skip_already_synced": 0,
        "skip_not_in_staging_branch": 0,
        "synced_additional_subpackage": 0,
        "synced": 0
    }

    branch_orig, name = branch_split(branch_staging)
    path_repo_orig_final = bpo.repo.final.get_path(arch, branch_orig, splitrepo)
    path_repo_staging_wip = bpo.repo.wip.get_path(arch, branch_staging, splitrepo)
    path_repo_staging_final = bpo.repo.final.get_path(arch, branch_staging, splitrepo)

    session = bpo.db.session()

    # Iterate over WIP and final repos of original branch
    fmt = bpo.repo.fmt(arch, branch_staging, splitrepo)
    logging.info(f"[{fmt}] sync with {branch_orig}")

    for apk in bpo.repo.get_apks(path_repo_orig_final):
        # Skip if already synced to staging repo
        if os.path.exists(f"{path_repo_staging_final}/{apk}") or \
                os.path.exists(f"{path_repo_staging_wip}/{apk}"):
            stats["skip_already_synced"] += 1
            continue

        # Read origin pkgname (not same as in filename, if this is a
        # subpackage) and skip if the origin pkgname + version is not on the
        # staging repository branch.
        apk_full_path = f"{path_repo_orig_final}/{apk}"
        pkgname = bpo.repo.is_apk_origin_in_db(session, arch, branch_staging,
                                               splitrepo, apk_full_path)
        if not pkgname:
            stats["skip_not_in_staging_branch"] += 1
            continue

        # Create copy in staging repo's WIP repo
        apk_full_path_staging = f"{path_repo_staging_wip}/{apk}"
        logging.info(f"[{fmt}] syncing {apk} (db + copy: {apk_full_path_staging})")
        os.makedirs(path_repo_staging_wip, exist_ok=True)
        shutil.copy(apk_full_path, apk_full_path_staging)

        # Mark as built in DB
        # job_id set to None together with status == built/published indicates
        # that this package was synced. We don't print the synced packages in
        # the logs as they would be too many (only a count of synced packages)
        # so there won't be a link to the log anyway. Also we would need to
        # change the db layout to store the same job_id in 2 packages (unique).
        package = bpo.db.get_package(session, pkgname, arch, branch_staging)

        if package.job_id is None and package.status == bpo.db.PackageStatus.built:
            # We encountered another subpackage of the same origin package
            # already, don't count it twice
            stats["synced_additional_subpackage"] += 1
            continue

        stats["synced"] += 1
        package.job_id = None
        package.status = bpo.db.PackageStatus.built
        session.commit()

    logging.info(f"[{fmt}] sync done ({stats})")

    if stats["synced"]:
        bpo.repo.wip.update_apkindex(arch, branch_staging, splitrepo)
        bpo.ui.log("sync_with_orig_repo", branch=branch_staging, arch=arch,
                   splitrepo=splitrepo, count=stats["synced"])

    return stats


def get_branches_with_staging():
    """ :returns: a copy of bpo.config.const.branches, with staging branches added. All staging branches have ignore_errors set.
    """
    ret = copy.copy(bpo.config.const.branches)
    repo_final_path = bpo.config.args.repo_final_path

    for branch_orig in bpo.config.const.branches.keys():
        pattern = f"{repo_final_path}/staging/*/{branch_orig}/README"
        for path in glob.glob(pattern):
            name = os.path.basename(os.path.dirname(os.path.dirname(path)))
            branch_staging = f"{branch_orig}_staging_{name}"
            ret[branch_staging] = {"arches": bpo.config.const.staging_arches,
                                   "ignore_errors": True,
                                   "pmb_branch": bpo.config.const.staging_pmb_branch}

    return ret


def remove(branch):
    """ Remove a staging branch.
        :param branch: which branch to remove, e.g. master_staging_testbranch

    """
    ret = branch_split(branch)
    if not ret:
        logging.error(f"Invalid request to delete branch '{branch}', bailing out...")
        return False

    branch_orig, name = ret

    # Remove final repo dir
    path_name = f"{bpo.config.args.repo_final_path}/staging/{name}"
    path_branch = f"{path_name}/{branch_orig}"
    if os.path.exists(path_branch):
        logging.info(f"{branch}: remove {path_branch}")
        shutil.rmtree(path_branch)
        if not any(os.scandir(path_name)):
            logging.info(f"{branch}: remove {path_name}")
            shutil.rmtree(path_name)

    # Remove wip repo dir
    path_name = f"{bpo.config.args.repo_wip_path}/staging/{name}"
    path_branch = f"{path_name}/{branch_orig}"
    if os.path.exists(path_branch):
        logging.info(f"{branch}: remove {path_branch}")
        shutil.rmtree(path_branch)
        if not any(os.scandir(path_name)):
            logging.info(f"{branch}: remove {path_name}")
            shutil.rmtree(path_name)

    # Remove from db
    session = bpo.db.session()
    packages = session.query(bpo.db.Package).\
                    filter_by(branch=branch).\
                    all()
    for package in packages:
        session.delete(package)
    session.commit()

    logging.info(f"{branch}: {len(packages)} packages deleted from DB")
    return True
