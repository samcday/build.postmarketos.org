# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import datetime
import importlib
import logging

import bpo.config.args

jobservice = None


def get_job_service():
    global jobservice
    if jobservice is None:
        name = bpo.config.args.job_service
        module = "bpo.job_services." + name
        jsmodule = importlib.import_module(module)
        jsclass = getattr(jsmodule, '{}JobService'.format(name.capitalize()))
        jobservice = jsclass()
    return jobservice


def remove_additional_indent(script, spaces=12):
    """ Remove leading spaces and leading/trailing empty lines from script
        parameter. This is used, so we can use additional indents when
        embedding shell code in the python code. """
    ret = ""
    for line in script.split("\n"):
        # Remove leading empty lines
        if not line and not ret:
            continue

        # Remove additional indent from line
        if line[:spaces] == " " * spaces:
            ret += line[spaces:] + "\n"
        else:  # Line does not start with indent
            ret += line + "\n"

    # Always have one new line at the end
    ret += "\n"

    # Remove trailing empty lines
    while ret.endswith("\n\n"):
        ret = ret[:-1]

    return ret


def job_check_rate_limit(action, arch, branch, pkgname, version, device, ui,
                         dir_name):
    """ Check if there is a bug and we keep running the same job (bpo#141).
        If that is the case, shutdown bpo. """
    session = bpo.db.session()
    entries = session.query(bpo.db.Log).order_by(bpo.db.Log.id.desc()
                                                 ).limit(10).all()

    if len(entries) < 10:
        logging.debug("job_check_rate_limit: less than 10 log entries")
        return

    now = datetime.datetime.now(datetime.timezone.utc)

    for entry in entries:
        date = entry.date.date()
        if date.year != now.year \
                and date.month != now.month \
                and date.day != now.day:
            logging.debug(f"job_check_rate_limit: job_id={entry.job_id} wasn't today")
            return
        if entry.action != action \
                or entry.arch != arch \
                or entry.branch != branch \
                or entry.pkgname != pkgname \
                or entry.version != version \
                or entry.device != device \
                or entry.ui != ui \
                or entry.dir_name != dir_name:
            logging.debug(f"job_check_rate_limit: job_id={entry.job_id} is different")
            return

        logging.debug(f"job_check_rate_limit: job_id={entry.job_id} is the same")

    bpo.ui.log("bug_found_shutting_down")
    raise RuntimeError("job_check_rate_limit: we keep starting the same job."
                       " There is a bug! Shutting bpo down to avoid API spam!")


def run(name, note, tasks, branch=None, arch=None, pkgname=None,
        version=None, device=None, ui=None, dir_name=None):
    """ :param note: what to send to the job service as description, rendered
                     as markdown in sourcehut
        :param branch: of pmaports to check out before running the job
        :returns: ID of the generated job, as passed by the backend """

    logging.info("[{}] Run job: {} ({})".format(bpo.config.args.job_service,
                                                note, name))

    job_check_rate_limit(f"job_{name}", arch, branch, pkgname, version, device,
                         ui, dir_name)

    js = get_job_service()

    # Format input tasks
    tasks_formatted = collections.OrderedDict()
    for task, script in tasks.items():
        tasks_formatted[task] = remove_additional_indent(script)

    # Pass to bpo.job_services.(...).run_job()
    job_id = js.run_job(name, note, tasks_formatted, branch)

    bpo.ui.log("job_" + name, arch=arch, branch=branch, pkgname=pkgname,
               version=version, job_id=job_id, device=device, ui=ui,
               dir_name=dir_name)

    return job_id


def get_status_package(package):
    result = get_job_service().get_status(package.job_id)
    status = bpo.job_services.base.JobStatus

    if result in [status.pending, status.queued, status.running]:
        return bpo.db.PackageStatus.building

    if result == status.success:
        return bpo.db.PackageStatus.built

    if result in [status.failed, status.timeout, status.cancelled]:
        return bpo.db.PackageStatus.failed

    raise RuntimeError(f"get_status_package: failed on job status: {result}")


def update_status_package():
    logging.info("Checking if 'building' packages have failed or finished")
    building = bpo.db.PackageStatus.building

    session = bpo.db.session()
    result = session.query(bpo.db.Package).filter_by(status=building).all()
    for package in result:
        status_new = get_status_package(package)
        if status_new == building:
            continue
        bpo.db.set_package_status(session, package, status_new)
        action = "job_update_package_status_" + status_new.name
        bpo.ui.log_package(package, action)
    session.commit()


def get_status_image(image):
    result = get_job_service().get_status(image.job_id)
    status = bpo.job_services.base.JobStatus

    if result in [status.pending, status.queued, status.running]:
        return bpo.db.ImageStatus.building

    if result == status.success:
        return bpo.db.ImageStatus.published

    if result in [status.failed, status.timeout, status.cancelled]:
        return bpo.db.ImageStatus.failed

    raise RuntimeError(f"get_status_image: failed on job status: {result}")


def update_status_image():
    logging.info("Checking if 'building' images have failed or finished")
    building = bpo.db.ImageStatus.building

    session = bpo.db.session()
    result = session.query(bpo.db.Image).filter_by(status=building).all()
    for image in result:
        status_new = get_status_image(image)
        if status_new == building:
            continue
        bpo.db.set_image_status(session, image, status_new)
        action = f"job_update_image_status_{status_new.name}"
        bpo.ui.log_image(image, action)
    session.commit()


def get_status_repo_bootstrap(rb):
    result = get_job_service().get_status(rb.job_id)
    status = bpo.job_services.base.JobStatus

    if result in [status.pending, status.queued, status.running]:
        return bpo.db.RepoBootstrapStatus.building

    if result == status.success:
        return bpo.db.RepoBootstrapStatus.built

    if result in [status.failed, status.timeout, status.cancelled]:
        return bpo.db.RepoBootstrapStatus.failed

    raise RuntimeError(f"get_status_repo_bootstrap: failed on job status: {result}")


def update_status_repo_bootstrap():
    logging.info("Checking if 'building' repo_bootstrap jobs have failed or"
                 " finished")
    building = bpo.db.RepoBootstrapStatus.building

    session = bpo.db.session()
    result = session.query(bpo.db.RepoBootstrap).filter_by(status=building).all()
    for rb in result:
        status_new = get_status_repo_bootstrap(rb)
        if status_new == building:
            continue
        bpo.db.set_repo_bootstrap_status(session, rb, status_new)
        action = f"job_update_repo_bootstrap_status_{status_new.name}"
        bpo.ui.log_repo_bootstrap(rb, action)
    session.commit()


def update_status():
    update_status_package()
    update_status_image()
    update_status_repo_bootstrap()


def get_link(job_id):
    """ :returns: the web link, that shows the build log """
    return get_job_service().get_link(job_id)


def init():
    """ Initialize the job service (make sure that tokens are there etc.) """
    return get_job_service().init()


def job_service_is_local():
    """ Use this to run additional code only with the local job service. """
    return bpo.config.args.job_service == "local"
