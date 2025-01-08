# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import fnmatch
import logging
import os
import shlex

import bpo.db
import bpo.helpers.job
import bpo.helpers.pmb
import bpo.ui


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
    splitrepo = None  # FIXME
    # Load package from db
    session = bpo.db.session()
    package = bpo.db.get_package(session, pkgname, arch, branch)

    # Skip if package is already in WIP repo (this can happen, if we had a bug
    # before and changed the package status from built to queued by accident)
    wip_path = bpo.repo.wip.get_path(arch, branch, splitrepo)
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
    pmb_v2_mirrors_arg = ""
    if not bpo.helpers.pmb.is_master(branch):
        mirror_final = bpo.helpers.pmb.get_pmos_mirror(branch)

        mp_arg_set = False
        if os.path.exists(f"{wip_path}/APKINDEX.tar.gz"):
            wip_repo_url = bpo.helpers.pmb.get_pmos_mirror(branch, "wip")
            if bpo.helpers.pmb.should_add_wip_repo(branch):
                pmb_v2_mirrors_arg += f" -mp {shlex.quote(wip_repo_url)}\\\n"
                mp_arg_set = True

        # Add the usual pmOS repo URL. If it is empty and no mirror was set
        # yet, we must add it too to explicitly disable the mirror instead of
        # using the default hardcoded into pmbootstrap.
        if not mp_arg_set or mirror_final:
            pmb_v2_mirrors_arg += f" -mp {shlex.quote(mirror_final)}\\\n"

        pmb_v2_mirrors_arg += f" -m {shlex.quote(bpo.config.const.mirror_alpine)}\\\n"

    # Ignore missing repos before initial build (bpo#137)
    env_force_missing_repos = ""
    final_path = bpo.repo.final.get_path(arch, branch, splitrepo)
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
    tasks = collections.OrderedDict([])
    tasks["install_pubkey"] = f"""
        echo -n {shlex.quote(pubkey)} \
            > pmbootstrap/pmb/data/keys/wip.rsa.pub
    """

    if bpo.helpers.pmb.is_master(branch):
        tasks["set_repos"] = bpo.helpers.pmb.set_repos_task(arch, branch)

    tasks["pmbootstrap_build"] = f"""
        pmbootstrap config systemd {shlex.quote(systemd_arg)}
        {env_force_missing_repos}
        pmbootstrap \\
            {pmb_v2_mirrors_arg} \\
            --aports=$PWD/pmaports \\
            --no-ccache \\
            --timeout {shlex.quote(timeout)} \\
            --details-to-stdout \\
            build \\
            --no-depends \\
            {strict_arg} \\
            --arch {shlex.quote(arch)} \\
            --force \\
            {shlex.quote(pkgname)}
    """
    tasks["checksums"] = """
        cd "$(pmbootstrap -q config work)/packages/"
        sha512sum $(find . -name '*.apk')
    """
    tasks["submit"] = f"""
        export BPO_API_ENDPOINT="build-package"
        export BPO_ARCH={shlex.quote(arch)}
        export BPO_BRANCH={shlex.quote(branch)}
        export BPO_DEVICE=""
        packages="$(pmbootstrap -q config work)/packages"
        export BPO_PAYLOAD_FILES="$(find "$packages" -name '*.apk')"
        export BPO_PAYLOAD_FILES_PREVIOUS=""
        export BPO_PAYLOAD_IS_JSON="0"
        export BPO_PKGNAME={shlex.quote(pkgname)}
        export BPO_SPLITREPO=""  # FIXME
        export BPO_UI=""
        export BPO_VERSION={shlex.quote(package.version)}

        exec build.postmarketos.org/helpers/submit.py
    """
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
