# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os

from flask import request
from bpo.helpers.headerauth import header_auth
import bpo.api
import bpo.config.args
import bpo.db
import bpo.repo.wip
import bpo.ui

blueprint = bpo.api.blueprint


@blueprint.route("/api/job-callback/build-package", methods=["POST"])
@header_auth("X-BPO-Token", "job_callback")
def job_callback_build_package():
    session = bpo.db.session()
    package = bpo.api.get_package(session, request)
    apks = bpo.api.get_apks(request)

    # Create WIP dir
    wip = bpo.repo.wip.get_path(package.arch, package.branch, package.splitrepo)
    os.makedirs(wip, exist_ok=True)

    # Save files to disk
    for apk in apks:
        path = wip + "/" + apk.filename
        logging.info("Saving " + path)
        apk.save(path)

    # Index and sign WIP APKINDEX
    bpo.repo.wip.update_apkindex(package.arch, package.branch, package.splitrepo)

    # Change status to built
    bpo.db.set_package_status(session, package, bpo.db.PackageStatus.built,
                              package.job_id)

    bpo.ui.log_package(package, "api_job_callback_build_package")

    # Build next package or publish repo after building all queued packages
    bpo.repo.build()
    return "package received, kthxbye"
