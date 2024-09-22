# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os

from flask import request
from bpo.helpers.headerauth import header_auth
import bpo.api
import bpo.config.args
import bpo.db
import bpo.repo
import bpo.ui

blueprint = bpo.api.blueprint


def get_repo_bootstrap(session, request):
    branch = bpo.api.get_branch(request)
    arch = bpo.api.get_arch(request, branch)
    job_id = bpo.api.get_header(request, "Job-Id")
    dir_name = bpo.api.get_splitrepo(request, branch)
    ret = bpo.db.get_repo_bootstrap(session, arch, branch, dir_name, job_id)
    if not ret:
        raise ValueError(f"no repo_bootstrap found with: arch={arch},"
                         f" branch={branch}, dir_name={dir_name},"
                         f" job_id={job_id}")
    return ret


def fail_callback(session, rb, reason):
        bpo.db.set_repo_bootstrap_status(session,
                                         rb,
                                         bpo.db.RepoBootstrapStatus.failed)
        raise RuntimeError("Unexpected packages/versions uploaded by"
                           " repo_bootstrap api call")


@blueprint.route("/api/job-callback/repo-bootstrap", methods=["POST"])
@header_auth("X-BPO-Token", "job_callback")
def job_callback_repo_bootstrap():
    session = bpo.db.session()
    rb = get_repo_bootstrap(session, request)
    apks = bpo.api.get_apks(request)

    wip = bpo.repo.wip.get_path(rb.arch, rb.branch)
    os.makedirs(wip, exist_ok=True)

    # Remove packages from disk that aren't in the DB (e.g. from a failed
    # previous repo_bootstrap run)
    bpo.repo.status.fix_disk_vs_db(
        rb.arch,
        rb.branch,
        bpo.repo.wip.get_path(rb.arch, rb.branch),
        bpo.db.PackageStatus.built,
        True)

    # Save files to disk
    for apk in apks:
        path = f"{wip}/{apk.filename}"
        logging.info(f"Saving: {path}")
        apk.save(path)

    # Update DB status for the packages that were uploaded
    removed, updated = bpo.repo.status.fix_disk_vs_db(
        rb.arch,
        rb.branch,
        bpo.repo.wip.get_path(rb.arch, rb.branch),
        bpo.db.PackageStatus.built,
        True,
        rb.job_id)

    if removed > 0:
        fail_callback(session, rb, "Unexpected packages/versions uploaded by"
                                   " repo_bootstrap api call")
    if updated == 0:
        logging.warning("WARNING: no packages from repo_bootstrap updated in"
                        " database, previous repo_bootstrap failed half-way?")

    bpo.db.set_repo_bootstrap_status(session,
                                     rb,
                                     bpo.db.RepoBootstrapStatus.built)

    bpo.repo.build()

    return "repo_bootstrap received, kthxbye"
