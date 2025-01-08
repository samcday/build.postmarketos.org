# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import shutil

import bpo.config.const
import bpo.repo
import bpo.repo.staging
import bpo.repo.status


def get_path(arch, branch, splitrepo):
    ret = bpo.config.args.repo_final_path

    if splitrepo:
        ret = os.path.join(ret, "extra-repos", splitrepo)

    if "_staging_" in branch:
        branch_orig, name = bpo.repo.staging.branch_split(branch)
        # Have the branch_orig + arch at the end of the path, so it is in the
        # same format as for the original repositories and pmbootstrap is able
        # to use it with "pmbootstrap --mirror-pmOS=..." with a staging URL
        # like https://mirror.postmarketos.org/postmarketos/staging/test. If we
        # used the branch name (master_staging_test) instead of the branch_orig
        # (master), we would need to add additional complexity to pmbootstrap
        # to figure out the correct full URLs.
        ret = os.path.join(ret, "staging", name, branch_orig)
    else:
        ret = os.path.join(ret, branch)

    if arch:
        ret = os.path.join(ret, arch)

    return ret


def copy_new_apks(arch, branch, splitrepo):
    fmt = bpo.repo.fmt(arch, branch, splitrepo)
    logging.info(f"[{fmt}] copying new apks from symlink to final repo")
    repo_final_path = get_path(arch, branch, splitrepo)
    repo_symlink_path = bpo.repo.symlink.get_path(arch, branch, splitrepo)

    os.makedirs(repo_final_path, exist_ok=True)

    for apk in bpo.repo.get_apks(repo_symlink_path):
        src = os.path.realpath(repo_symlink_path + "/" + apk)
        dst = os.path.realpath(repo_final_path + "/" + apk)
        if src == dst:
            logging.debug(apk + ": symlink points to final repo, not copying")
            continue
        logging.debug(apk + ": copying to final repo")
        shutil.copy(src, dst)


def copy_new_apkindex(arch, branch, splitrepo):
    fmt = bpo.repo.fmt(arch, branch, splitrepo)
    logging.info(f"[{fmt}] copying new APKINDEX")
    src = bpo.repo.symlink.get_path(arch, branch, splitrepo) + "/APKINDEX.tar.gz"
    dst = get_path(arch, branch, splitrepo) + "/APKINDEX.tar.gz"
    shutil.copy(src, dst)


def delete_outdated_apks(arch, branch, splitrepo):
    fmt = bpo.repo.fmt(arch, branch, splitrepo)
    logging.info(f"[{fmt}] removing outdated apks")
    repo_final_path = get_path(arch, branch, splitrepo)
    repo_symlink_path = bpo.repo.symlink.get_path(arch, branch, splitrepo)

    for apk in bpo.repo.get_apks(repo_final_path):
        if os.path.exists(repo_symlink_path + "/" + apk):
            continue
        logging.info(apk + ": does not exist in symlink repo, removing")
        os.unlink(repo_final_path + "/" + apk)


def update_from_symlink_repo(arch, branch, splitrepo):
    copy_new_apks(arch, branch, splitrepo)
    copy_new_apkindex(arch, branch, splitrepo)
    delete_outdated_apks(arch, branch, splitrepo)

    # Set package status to published
    path = get_path(arch, branch, splitrepo)
    bpo.repo.status.fix_disk_vs_db(arch, branch, path,
                                   bpo.db.PackageStatus.published)


def publish(arch, branch):
    bpo.repo.build()
