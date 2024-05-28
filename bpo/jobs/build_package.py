# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import fnmatch
import logging
import os
import shlex

import bpo.db
import bpo.ui
import bpo.helpers.job


def do_build_strict(pkgname):
    """ Check if --strict should be supplied to "pmbootstrap build". Usually
        we want to use it every time, but in order to work around bugs we may
        need to disable it for certain packages. For example:
        https://gitlab.alpinelinux.org/alpine/apk-tools/issues/10649 """
    for pattern in bpo.config.const.no_build_strict:
        if fnmatch.fnmatch(pkgname, pattern):
            return False
    return True


def run(arch, pkgname, branch):
    """ Start a single package build job.
        :returns: True if a new job was started, False if the apk exists
                  already in the WIP repo and the build was skipped. """
    # Load package from db
    session = bpo.db.session()
    package = bpo.db.get_package(session, pkgname, arch, branch)

    # Skip if package is already in WIP repo (this can happen, if we had a bug
    # before and changed the package status from built to queued by accident)
    wip_path = bpo.repo.wip.get_path(arch, branch)
    apk = "{}/{}-{}.apk".format(wip_path, pkgname, package.version)
    if os.path.exists(apk):
        bpo.ui.log_package(package, "package_exists_in_wip_repo")
        bpo.db.set_package_status(session, package, bpo.db.PackageStatus.built)
        bpo.ui.update(session)
        return False

    # Read WIP repo pub key
    with open(bpo.config.const.repo_wip_keys + "/wip.rsa.pub", "r") as handle:
        pubkey = handle.read()

    # Set mirror args (either primary mirror, or WIP + primary)
    mirror_alpine = shlex.quote(bpo.config.const.mirror_alpine)
    mirror_final = bpo.helpers.job.get_pmos_mirror_for_pmbootstrap(branch)
    mirrors = "-mp " + shlex.quote(mirror_final)
    if os.path.exists(f"{wip_path}/APKINDEX.tar.gz"):
        mirrors = '$BPO_WIP_REPO_ARG ' + mirrors

    # Ignore missing repos before initial build (bpo#137)
    env_force_missing_repos = ""
    final_path = bpo.repo.final.get_path(arch, branch)
    if not os.path.exists(f"{final_path}/APKINDEX.tar.gz"):
        env_force_missing_repos = "export PMB_APK_FORCE_MISSING_REPOSITORIES=1"

    strict_arg = "--strict" if do_build_strict(pkgname) else ""
    timeout = str(bpo.config.const.pmbootstrap_timeout)

    # For now, set systemd=always when we did a repo_bootstrap. This will cause
    # pmbootstrap to do usr-merge and install our custom apk-tools and abuild
    # (that were built during repo_bootstrap).
    systemd_arg = "never"
    if bpo.db.get_repo_bootstrap(session, arch, branch):
        systemd_arg = "always"

    # Start job
    note = "Build package: `{}/{}/{}-{}`".format(branch, arch, pkgname,
                                                 package.version)
    tasks = collections.OrderedDict([
        ("install_pubkey", """
            echo -n '""" + pubkey + """' \
                > pmbootstrap/pmb/data/keys/wip.rsa.pub
            """),
        ("pmbootstrap_build", """
            pmbootstrap config systemd """ + systemd_arg + """
            """ + env_force_missing_repos + """
            pmbootstrap \\
                -m """ + mirror_alpine + """ \
                """ + mirrors + """ \\
                --aports=$PWD/pmaports \\
                --no-ccache \\
                --timeout """ + timeout + """ \\
                --details-to-stdout \\
                build \\
                --no-depends \\
                """ + strict_arg + """ \\
                --arch """ + shlex.quote(arch) + """ \\
                --force \\
                """ + shlex.quote(pkgname) + """
            """),
        ("checksums", """
            cd "$(pmbootstrap -q config work)/packages/"
            sha512sum $(find . -name '*.apk')
        """),
        ("submit", """
            export BPO_API_ENDPOINT="build-package"
            export BPO_ARCH=""" + shlex.quote(arch) + """
            export BPO_BRANCH=""" + shlex.quote(branch) + """
            export BPO_DEVICE=""
            packages="$(pmbootstrap -q config work)/packages"
            export BPO_PAYLOAD_FILES="$(find "$packages" -name '*.apk')"
            export BPO_PAYLOAD_FILES_PREVIOUS=""
            export BPO_PAYLOAD_IS_JSON="0"
            export BPO_PKGNAME=""" + shlex.quote(pkgname) + """
            export BPO_UI=""
            export BPO_VERSION=""" + shlex.quote(package.version) + """

            exec build.postmarketos.org/helpers/submit.py
            """)
    ])
    job_id = bpo.helpers.job.run("build_package", note, tasks, branch, arch,
                                 pkgname, package.version)

    # Increase retry count
    if package.status == bpo.db.PackageStatus.failed:
        package.retry_count += 1
        session.merge(package)
        session.commit()

    # Change status to building and save job_id
    bpo.db.set_package_status(session, package, bpo.db.PackageStatus.building,
                              job_id)
    bpo.ui.update(session)
    return True


def abort(package):
    """ Stop a single package build job.
        :param package: bpo.db.Package object """
    # FIXME
    logging.info(f"STUB: bpo.jobs.build_package (#93): {package}")
