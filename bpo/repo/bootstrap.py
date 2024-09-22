# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging

import bpo.jobs.get_depends
import bpo.repo


def get_splitrepos_where_bootstrap_is_needed(payload):
    """
    Get splitrepos for which repo_bootstrap is needed in the current pmaports
    branch, based on the pmaports dir the packages are in. For systemd, the
    systemd packages are in the extra-repos/systemd dir.

    :param payload: from the get_depends api call
        e.g.: [ { "pkgname": "hello-world",
        "repo": None or "systemd",  # splitrepo dir
        "version": "1-r4",
        "depends": []}, … ]
    :returns: e.g. [] or ["systemd"]

    """
    ret = []

    for pkg in payload:
        repo = pkg["repo"]
        if repo in ret:
            continue
        if repo in bpo.config.const.repo_bootstrap_dirs:
            ret += [repo]
    return ret


def init(session, payload, arch, branch):
    """
    Add a new entry to the repo_bootstrap table, if it is needed for the
    current branch, and if there is no entry yet.

    :param payload: from the get_depends api call
        e.g.: [ { "pkgname": "hello-world",
        "repo": None or "systemd",  # splitrepo dir
        "version": "1-r4",
        "depends": []}, … ]
    :returns: True if a new entry was added to the table, False otherwise

    """
    ret = False
    for splitrepo in get_splitrepos_where_bootstrap_is_needed(payload):
        repo_bootstrap = bpo.db.get_repo_bootstrap(session, arch, branch, splitrepo)
        if repo_bootstrap:
            logging.info(f"repo bootstrap exists: {repo_bootstrap}")
            continue

        repo_bootstrap = bpo.db.RepoBootstrap(arch, branch, splitrepo)
        session.merge(repo_bootstrap)
        session.commit()

        bpo.ui.log("repo_bootstrap_add", arch=arch, branch=branch,
                   pkgname="[repo_bootstrap]", dir_name=splitrepo)
        ret = True

    return ret


def update_to_published(arch, branch, dir_name):
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
