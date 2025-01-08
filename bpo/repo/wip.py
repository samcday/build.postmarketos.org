# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import subprocess

import bpo.config.const
import bpo.repo
import bpo.repo.final
import bpo.repo.staging


def get_path(arch, branch, splitrepo):
    ret = bpo.config.args.repo_wip_path

    if splitrepo:
        ret = os.path.join(ret, "extra-repos", splitrepo)

    if "_staging_" in branch:
        branch_orig, name = bpo.repo.staging.branch_split(branch)
        # Have the branch_orig + arch at the end of the path, so it is in the
        # same format as for the original repositories and pmbootstrap is able
        # to use it with "pmbootstrap --mirror-pmOS=..." with a staging URL
        # like https://build.postmarketos.org/wip. If we
        # used the branch name (master_staging_test) instead of the branch_orig
        # (master), we would need to add additional complexity to pmbootstrap
        # to figure out the correct full URLs.
        ret = os.path.join(ret, "staging", name, branch_orig)
    else:
        ret = os.path.join(ret, branch)

    if arch:
        ret = os.path.join(ret, arch)

    return ret


def do_keygen():
    """ Generate key for signing the APKINDEX of the WIP repository locally."""

    # Skip if pub key exists
    path_dir = bpo.config.const.repo_wip_keys
    path_public = path_dir + "/wip.rsa.pub"
    if os.path.exists(path_public):
        return

    # Generate keys (like do_keygen() in abuild-keygen)
    logging.info("Generating RSA keypair for WIP repository")
    os.makedirs(path_dir, exist_ok=True)
    subprocess.run(["openssl", "genrsa", "-out", "wip.rsa", "2048"],
                   check=True, cwd=path_dir)
    subprocess.run(["openssl", "rsa", "-in", "wip.rsa", "-pubout", "-out",
                    "wip.rsa.pub"], check=True, cwd=path_dir)


def sign(arch, branch):
    splitrepo = None
    cmd = ["abuild-sign.noinclude",
           "-k", bpo.config.const.repo_wip_keys + "/wip.rsa",
           "APKINDEX.tar.gz"]
    bpo.repo.tools.run(arch, branch, "WIP", get_path(arch, branch, splitrepo), cmd)


def update_apkindex(arch, branch):
    splitrepo = None  # FIXME
    path = get_path(arch, branch, splitrepo)
    if os.path.exists(path):
        fmt = bpo.repo.fmt(arch, branch, splitrepo)
        logging.info(f"[{fmt}] update WIP APKINDEX")
        bpo.repo.tools.index(arch, branch, "WIP", path)
        sign(arch, branch)


def clean(arch, branch, splitrepo):
    """ Delete all apks from WIP repo, that are either in final repo or not in
        the db anymore (pmaport updated or deleted), and update the APKINDEX
        of the WIP repo. """
    fmt = bpo.repo.fmt(arch, branch, splitrepo)
    logging.debug(f"[{fmt}] Cleaning WIP repo")
    path_repo_wip = get_path(arch, branch, splitrepo)
    path_repo_final = bpo.repo.final.get_path(arch, branch)
    session = bpo.db.session()

    for apk in bpo.repo.get_apks(path_repo_wip):
        apk_wip = path_repo_wip + "/" + apk
        # Find in final repo
        if os.path.exists(path_repo_final + "/" + apk):
            logging.debug(apk + ": found in final repo, delete from WIP repo")
            os.unlink(apk_wip)
            continue

        # Find in db
        if bpo.repo.is_apk_origin_in_db(session, arch, branch, splitrepo, apk_wip):
            logging.debug(apk + ": not in final repo, but found in db ->"
                          " keeping in WIP repo")
        else:
            logging.debug(apk + ": not found in db, delete from WIP repo")
            os.unlink(apk_wip)

    update_apkindex(arch, branch)
