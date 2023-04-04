# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import flask
import bpo.config.const
import bpo.db
import bpo.repo.staging

blueprint = flask.Blueprint("bpo_api", __name__)


def get_header(request, key):
    header = "X-BPO-" + key
    if header not in request.headers:
        raise ValueError("missing " + header + " header!")
    return request.headers[header]


def get_arch(request, branch):
    """ Get architecture from X-BPO-Arch header and validate it. """
    arch = get_header(request, "Arch")
    branches_with_staging = bpo.repo.staging.get_branches_with_staging()
    arches = branches_with_staging[branch]["arches"]
    if arch not in arches:
        raise ValueError("invalid X-BPO-Arch: " + arch)
    return arch


def get_branch(request):
    """ Get branch from X-BPO-Branch header and validate it. """
    branch = get_header(request, "Branch")

    if branch in bpo.config.const.branches \
            or branch in bpo.repo.staging.get_branches_with_staging():
        return branch

    raise ValueError(f"invalid X-BPO-Branch: {branch}")


def get_package(session, request):
    pkgname = get_header(request, "Pkgname")
    version = get_header(request, "Version")
    job_id = get_header(request, "Job-Id")
    branch = get_branch(request)
    arch = get_arch(request, branch)
    ret = bpo.db.get_package(session, pkgname, arch, branch, job_id)
    if not ret:
        raise ValueError("no package found with: pkgname=" + pkgname +
                         ", arch=" + arch)
    if ret.version != version:
        raise ValueError(f"unexpected version {version} instead of"
                         f" {ret.version} in package {ret} - old build job"
                         " that should have been stopped (#93)?")
    return ret


def get_version(request, package):
    version = get_header(request, "Version")
    if version != package.version:
        raise ValueError("version " + version + " submitted in the callback is"
                         " different from the package version in the db: " +
                         package + " (this probably is an outdated build job"
                         " that was not stopped after a new version of the"
                         " aport had been pushed?)")
    return version


def get_file(request, filename):
    """ :returns: werkzeug.datastructures.FileStorage object """
    for storage in request.files.getlist("file[]"):
        if storage.filename == filename:
            return storage
    raise ValueError("Missing file " + filename + " in payload.")
