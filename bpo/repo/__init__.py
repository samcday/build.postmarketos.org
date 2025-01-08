# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import glob
import logging
import os
import threading

import bpo.config.const
import bpo.db
import bpo.helpers.apk
import bpo.jobs.build_image
import bpo.jobs.build_package
import bpo.jobs.repo_bootstrap
import bpo.jobs.sign_index
import bpo.repo.symlink
import bpo.repo.tools
import bpo.repo.staging
import bpo.repo.wip


# Let bpo.repo.build() only run from one thread at once (#79)
build_cond = threading.Condition()


def next_package_to_build(session, arch, branch):
    """ :returns: pkgname """

    # Get all packages for arch where status = failed and retries left
    failed = bpo.db.PackageStatus.failed
    retry_count_max = bpo.config.const.retry_count_max
    result = session.query(bpo.db.Package)\
                    .filter_by(arch=arch, branch=branch, status=failed)\
                    .filter(bpo.db.Package.retry_count < retry_count_max)\
                    .all()

    # Get all packages for arch where status = queued
    queued = bpo.db.PackageStatus.queued
    result += session.query(bpo.db.Package)\
                     .filter_by(arch=arch, branch=branch, status=queued)\
                     .all()

    if not len(result):
        return None

    for package in result:
        if package.depends_built():
            return package.pkgname

    # Can't resolve (this is expected, if we only have packages left that
    # depend on packages that are currently building.)
    logging.debug("can't resolve remaining packages: " + str(result))
    return None


def next_image_to_build(session, branch):
    """ :returns: image db object """
    # Check images where status = failed and retries left
    failed = bpo.db.ImageStatus.failed
    retry_count_max = bpo.config.const.retry_count_max
    result = session.query(bpo.db.Image)\
        .filter_by(branch=branch, status=failed)\
        .filter(bpo.db.Image.retry_count < retry_count_max)\
        .all()
    if len(result):
        return result[0]

    # Check images in queue
    queued = bpo.db.ImageStatus.queued
    result = session.query(bpo.db.Image)\
        .filter_by(branch=branch, status=queued)\
        .all()
    return result[0] if len(result) else None


def repo_bootstrap_attempt(session, rb):
    """
    Start a repo_bootstrap job, if it makes sense depending on the status and
    the failed retry attempts.

    :returns: * True if a repo_bootstrap job was started
              * False if it was not started
    """
    rbs = bpo.db.RepoBootstrapStatus

    if rb.status not in [rbs.queued, rbs.failed]:
        return False

    if rb.status == rbs.failed and \
            rb.retry_count >= bpo.config.const.retry_count_max:
        return False

    bpo.jobs.repo_bootstrap.run(session, rb)
    return True


def count_running_builds_packages(session):
    building = bpo.db.PackageStatus.building
    return session.query(bpo.db.Package).filter_by(status=building).count()


def count_running_builds_images(session):
    building = bpo.db.ImageStatus.building
    return session.query(bpo.db.Image).filter_by(status=building).count()

def count_running_builds_repo_bootstrap(session):
    building = bpo.db.RepoBootstrapStatus.building
    return session.query(bpo.db.RepoBootstrap).filter_by(status=building).count()


def count_running_builds(session):
    return (count_running_builds_packages(session) +
            count_running_builds_images(session) +
            count_running_builds_repo_bootstrap(session))


def count_unpublished_packages(session, branch, arch=None):
    if arch:
        return session.query(bpo.db.Package).\
                filter_by(branch=branch).\
                filter_by(arch=arch).\
                filter(bpo.db.Package.status != bpo.db.PackageStatus.published).\
                count()
    return session.query(bpo.db.Package).\
            filter_by(branch=branch).\
            filter(bpo.db.Package.status != bpo.db.PackageStatus.published).\
            count()


def has_unfinished_builds(session, arch, branch):
    for status in bpo.db.PackageStatus.failed, bpo.db.PackageStatus.building, \
            bpo.db.PackageStatus.queued:
        if session.query(bpo.db.Package).filter_by(status=status, arch=arch,
                                                   branch=branch).count():
            return True
    return False


def set_stuck(arch, branch):
    """ No more packages can be built, because all remaining packages in the
        queue have already failed, or depend on packages that have failed. This
        is an extra function, so we can hook it in the tests. """
    logging.info(branch + "/" + arch + ": repo is stuck")


def build_arch_branch(session, slots_available, arch, branch,
                      force_repo_update=False, no_repo_update=False):
    """ :returns: amount of jobs that were started
        :param force_repo_update: rebuild the symlink and final repo, even if
                                  no new packages were built. Set this to True
                                  after deleting packages in the database, so
                                  the apks get removed from the final repo.
        :param no_repo_update: never update symlink and final repo (used from
                               the images timer thread, see #98) """
    splitrepo = None  # FIXME
    fmt_ = fmt(arch, branch, splitrepo)
    logging.info(f"[{fmt_}] starting new package build job(s)")

    if "_staging_" in branch:
        branch_orig, branch_staging = bpo.repo.staging.branch_split(branch)
        if count_unpublished_packages(session, branch_orig):
            # As long as the original branch has unpublished packages, don't
            # build any packages for its staging branches. Otherwise we might
            # have a package failing on an orig branch, therefore not getting
            # synced to the staging repo, and then we try to build the same
            # package in the staging repo just to have it fail there again.
            logging.info(f"[{fmt_}] skip building packages, as"
                         f" {branch_orig} has unpublished packages")
            return 0
        bpo.repo.staging.sync_with_orig_repo(branch, arch, splitrepo)

    started = 0

    # Do repo_bootstrap first if needed
    rb = bpo.db.get_repo_bootstrap(session, arch, branch, "systemd")  # FIXME
    if rb and rb.status != bpo.db.RepoBootstrapStatus.published:
        if slots_available > 0:
            if repo_bootstrap_attempt(session, rb):
                started += 1
                slots_available -= 1
            elif rb.status == bpo.db.RepoBootstrapStatus.built:
                logging.info(f"{rb}: publishing")
                bpo.repo.symlink.create(arch, branch, splitrepo, True)
                started += 1
                slots_available -= 1
        else:
            logging.info(f"{rb}: no more slots available")

        logging.info(f"{rb}: not done, not building any other packages")
        return started

    while True:
        pkgname = next_package_to_build(session, arch, branch)
        if not pkgname:
            if not started:
                if has_unfinished_builds(session, arch, branch):
                    set_stuck(arch, branch)
                else:
                    logging.info(f"[{fmt_}] WIP repo complete")
                    if no_repo_update:
                        logging.info(f"[{fmt_}] build_arch_branch:"
                                     " skipping bpo.repo.symlink.create"
                                     " (no_repo_update=True)")
                    else:
                        bpo.repo.symlink.create(arch, branch, splitrepo,
                                                force_repo_update)
            break

        if slots_available > 0:
            if bpo.jobs.build_package.run(arch, pkgname, branch):
                started += 1
                slots_available -= 1
        else:
            break
    return started


def build_images_branch(session, slots_available, branch):
    """ :returns: amount of jobs that were started """
    logging.info(f"{branch}: starting new image build jobs")
    started = 0

    while slots_available:
        image = next_image_to_build(session, branch)
        if not image:
            break

        bpo.jobs.build_image.run(image.device, image.branch, image.ui)
        started += 1
        slots_available -= 1

    return started


def _build(force_repo_update_branch=None, no_repo_update=False):
    """ Start as many parallel build jobs, as configured. When all packages are
        built, publish the packages. (Images get published right after they
        get submitted to the server in bpo/api/job_callback/build_image.py, not
        here.)

        Always use bpo.repo.build() wrapper below, to make sure that this only
        runs in one thread at once!

        :param force_repo_update_branch: rebuild the symlink and final repo for
                                         this branch, even if no new packages
                                         were built. Set this after deleting
                                         packages in the database, so the apks
                                         get removed from the final repo.
        :param no_repo_update: never update symlink and final repo (used from
                               the images timer thread, see #98) """
    session = bpo.db.session()
    running = count_running_builds(session)
    slots_available = bpo.config.const.max_parallel_build_jobs - running

    # Iterate over all branch-arch combinations, to give them a chance to start
    # a new job or to proceed with rolling out their fully built WIP repo
    branches_with_staging = bpo.repo.staging.get_branches_with_staging()
    for branch, branch_data in branches_with_staging.items():
        arch_is_first = True

        for arch in branch_data["arches"]:
            force_repo_update = (force_repo_update_branch == branch)
            slots_available -= build_arch_branch(session, slots_available,
                                                 arch, branch,
                                                 force_repo_update,
                                                 no_repo_update)
            # Don't build packages in other architectures unless building the
            # first architecture (the native arch) is complete. Otherwise cross
            # compilers may be missing, etc.
            if arch_is_first:
                if count_unpublished_packages(session, branch, arch):
                    logging.info(f"{branch}/{arch}: has unpublished packages,"
                                 " not building packages for other arches")
                    break
                arch_is_first = False

    if slots_available <= 0:
        return

    # Iterate over branches and build images
    for branch in bpo.config.const.branches:
        # Only build images on branches where all packages are published
        if count_unpublished_packages(session, branch):
            continue

        slots_available -= build_images_branch(session, slots_available,
                                               branch)
        if slots_available <= 0:
            break


def build(force_repo_update_branch=None, no_repo_update=False):
    """ Run build() with a threading.Condition(), so it runs at most in one
        thread at once. Otherwise it will lead to corrupt indexes being
        generated. See _build() for parameter description. """
    global build_cond

    with build_cond:
        return _build(force_repo_update_branch, no_repo_update)


def get_apks(cwd):
    """ Get a sorted list of all apks in a repository.
        :param cwd: path to the repository """
    ret = []
    for apk in glob.glob(cwd + "/*.apk"):
        ret += [os.path.basename(apk)]
    ret.sort()

    return ret


def is_apk_origin_in_db(session, arch, branch, splitrepo, apk_path):
    """ :param apk_path: full path to the apk file
        :returns: origin pkgname if the origin is in db and has same version,
                  False otherwise """

    metadata = bpo.helpers.apk.get_metadata(apk_path)
    pkgname = metadata["origin"]
    version = metadata["pkgver"]  # yes, this is actually the full version
    if bpo.db.package_has_version(session, pkgname, arch, branch, splitrepo, version):
        return pkgname
    return False


def fmt(arch, branch, splitrepo):
    """Format arch, branch, splitrepo nicely for log messages"""
    ret = branch
    if splitrepo:
        ret += f":{splitrepo}"
    ret += f"/{arch}"
    return ret
