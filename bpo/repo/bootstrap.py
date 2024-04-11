# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging

import bpo.jobs.get_depends
import bpo.repo


def is_needed(payload):
    """
    Check if repo_bootstrap is needed for the current pmaports branch. It is
    needed if any of the packages in the branch are inside a directory that
    needs bootstrap (systemd dir).

    :param payload: from the get_depends api call
                    e.g.: [ { "pkgname": "hello-world",
                              "repo": "main",  # pmaports directory
                              "version": "1-r4",
                              "depends": []}, … ]
    :returns: True if repo_bootstrap is needed, False otherwise
    """
    for pkg in payload:
        if pkg["repo"] in bpo.config.const.repo_bootstrap_dirs:
            return True
    return False


def init(session, payload, arch, branch, dir_name="/"):
    """
    Add a new entry to the repo_bootstrap table, if it is needed for the
    current branch, and if there is no entry yet.

    :param payload: from the get_depends api call
                    e.g.: [ { "pkgname": "hello-world",
                              "repo": "main",  # pmaports directory
                              "version": "1-r4",
                              "depends": []}, … ]
    :returns: True if a new entry was added to the table, False otherwise
    """
    repo_bootstrap = bpo.db.get_repo_bootstrap(session, arch, branch, dir_name)
    if repo_bootstrap:
        logging.info(f"repo bootstrap exists: {repo_bootstrap}")
        return False

    if not is_needed(payload):
        logging.info(f"repo bootstrap is not needed: {arch}, {branch}, {dir_name}")
        return False

    repo_bootstrap = bpo.db.RepoBootstrap(arch, branch, dir_name)
    session.merge(repo_bootstrap)
    session.commit()

    bpo.ui.log("repo_bootstrap_add", arch=arch, branch=branch,
               pkgname="[repo_bootstrap]", dir_name=dir_name)
    return True


def update_to_published(arch, branch, dir_name="/"):
    """ Set the RepoStaging DB entries to published, if they are currently in
        built state. This gets called from job_callback.sign_index. The
        callback has set the status of the packages built by repo_bootstrap
        to built (update_from_symlink_repo -> fix_db_vs_disk).
        Afterwards, trigger the build of packages again.

        :returns: True if the status was changed, False otherwise
    """
    session = bpo.db.session()
    rb = bpo.db.get_repo_bootstrap(session, arch, branch, dir_name)
    if not rb or rb.status != bpo.db.RepoBootstrapStatus.built:
        return False

    bpo.db.set_repo_bootstrap_status(session, rb,
                                     bpo.db.RepoBootstrapStatus.published)

    bpo.ui.log("repo_bootstrap_published", arch=arch, branch=branch,
               pkgname="[repo_bootstrap]", dir_name=dir_name)

    bpo.repo.build()
    return True
