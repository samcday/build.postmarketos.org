# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import queue
import shutil
import subprocess
import sys
import threading
import traceback
import werkzeug.serving

# Add topdir to import path
topdir = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/../.."))
sys.path.insert(0, topdir)

# Use "noqa" to ignore "E402 module level import not at top of file"
import bpo  # noqa
import bpo.config.const  # noqa
import bpo.config.const.args  # noqa
import bpo.config.args  # noqa
import bpo.job_services.local  # noqa

# Queue for passing test result between threads
result_queue = None


def get_pmb_work_dir():
    work_dir = os.environ.get("PMB_WORK_DIR", "~/.local/var/pmbootstrap")
    work_dir = os.path.expanduser(work_dir)
    assert os.path.exists(work_dir), "pmbootstrap work dir not found! Make" \
        " sure you ran 'pmbootstrap init' before running the bpo testsuite." \
        f" If you use a different work dir than {work_dir}, set the" \
        " PMB_WORK_DIR variable."
    return work_dir


def reset_wip_rsa_pub():
    """ Remove wip.rsa.pub from config_apk_keys in pmbootstrap's work dir, as
        having a file from a previous run will result in the old key getting
        used instead of the new one, and therefore tests will fail. """
    wip_rsa_pub = f"{get_pmb_work_dir()}/config_apk_keys/wip.rsa.pub"
    if os.path.exists(wip_rsa_pub):
        subprocess.run(["sudo", "rm", wip_rsa_pub], check=True)


def reset():
    """ Remove the database, generated binary packages and temp dirs. To be
        used at the start of test cases. Using bpo.config.const.args instead
        of bpo.config.args, because this runs before bpo.config.args.init().
    """
    reset_wip_rsa_pub()

    paths = [bpo.config.const.args.db_path,
             bpo.config.const.args.html_out,
             bpo.config.const.args.images_path,
             bpo.config.const.args.temp_path,
             bpo.config.const.args.repo_final_path,
             bpo.config.const.args.repo_wip_path,
             bpo.config.const.repo_wip_keys]

    logging.info("Removing all BPO data")
    for path in paths:
        if not os.path.exists(path):
            logging.debug(path + ": does not exist, skipping")
            continue
        if os.path.isdir(path):
            logging.debug(path + ": removing path recursively")
            shutil.rmtree(path)
        else:
            logging.debug(path + ": removing file")
            os.unlink(path)


def nop(*args, **kwargs):
    """ Use this for monkeypatching the bpo code, so a function does not do
        anything. For example, when testing the gitlab api push hook, we can
        use this to prevent bpo from building the entire repo. """
    logging.info("Thread called nop: " + threading.current_thread().name)


def true(*args, **kwargs):
    """ Use this for monkeypatching the bpo code, so a function always returns
        True. """
    logging.info("Thread called true: " + threading.current_thread().name)
    return True


def false(*args, **kwargs):
    """ Use this for monkeypatching the bpo code, so a function always returns
        False. """
    logging.info("Thread called false: " + threading.current_thread().name)
    return False


def stop_server(*args, **kwargs):
    """ Use this for monkeypatching the bpo code, so a function finishes the
        test instead of performing the original functionallity. For example,
        when testing the gitlab api push hook, we can use this to prevent bpo
        from building the entire repo. """
    global result_queue
    logging.info("Thread stops bpo server: " + threading.current_thread().name)
    result_queue.put(True)
    bpo.job_services.local.stop_thread()
    bpo.stop()


def stop_server_nok(*args, **kwargs):
    global result_queue
    name = threading.current_thread().name
    logging.info("Thread stops bpo server, NOK: " + name)
    result_queue.put(False)


def raise_exception(*args, **kwargs):
    raise bpo.helpers.ThisExceptionIsExpectedAndCanBeIgnored("ohai")


def bpo_test_exception_handler(e):
    logging.critical(traceback.format_exc())
    stop_server_nok()
    return traceback.format_exc(), 500


class BPOServer():
    """ Run the flask server in a second thread, so we can send requests to it
        from the main thread. Use this as "with statement", i.e.:

        with bpo_test.BPO_Server():
            requests.post("http://127.0.0.1:5000/api/push-hook/gitlab")

        Based on: https://stackoverflow.com/a/45017691 """
    thread = None

    class BPOServerThread(threading.Thread):

        def __init__(self, disable_pmos_mirror=True, fill_image_queue=False):
            """ :param disable_pmos_mirror: set postmarketOS mirror to "". This
                    is useful to test package building, to ensure that
                    pmbootstrap won't refuse to build the package because a
                    binary package has been built already. Set to False to test
                    building images.
                :param fill_image_queue: add new images to the "image" table
                    and start building them immediatelly.
                    """
            threading.Thread.__init__(self, name="BPOServerThread")
            os.environ["FLASK_DEBUG"] = "1"
            sys.argv = ["bpo.py", "-t", "test/test_tokens.cfg"]
            if disable_pmos_mirror:
                sys.argv += ["--mirror", ""]
            sys.argv += ["local"]
            app = bpo.main(True, fill_image_queue=fill_image_queue)
            app.register_error_handler(Exception, bpo_test_exception_handler)
            self.srv = werkzeug.serving.make_server("127.0.0.1", 5000, app,
                                                    threaded=False)
            self.ctx = app.app_context()
            self.ctx.push()

        def run(self):
            self.srv.serve_forever()

    def __init__(self, disable_pmos_mirror=True, fill_image_queue=False):
        """ parameters: see BPOServerThread """
        global result_queue
        reset()
        result_queue = queue.Queue()
        self.thread = self.BPOServerThread(disable_pmos_mirror,
                                           fill_image_queue)

    def __enter__(self):
        self.thread.start()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        global result_queue
        # Wait until result_queue is set with bpo_test.stop_server()
        result = result_queue.get()
        result_queue.task_done()
        self.thread.srv.shutdown()
        assert result


def assert_package(pkgname, arch="x86_64", branch="master", splitrepo=None,
                   status=None, version=None, exists=True, retry_count=0, job_id=False):
    """ Verify that a package exists, and optionally, that certain attributes
        are set to an expected value. This function is called assert_* but we
        are actually raising exceptions, because we can test if they get thrown
        and the error message can be more descriptive.

        :param pkgname: package name (e.g. "hello-world")
        :param arch: package architecture
        :param branch: pmaports.git branch
        :param status: bpo.db.PackageStatus string, e.g. "built"
        :param version: package version, e.g. "1-r4"
        :param exists: set to False if the package should not exist at all
        :param retry_count: how often build failed previously
        :param job_id: the job_id, set to None or an integer to check """
    session = bpo.db.session()
    package = bpo.db.get_package(session, pkgname, arch, branch, splitrepo)

    fmt = f"{bpo.repo.fmt(arch, branch, splitrepo)}/{pkgname}"

    if not exists:
        if not package:
            return
        raise RuntimeError(f"[{fmt}] Package should NOT exist in db")

    if package is None:
        raise RuntimeError(f"[{fmt}] Expected package to exist in db")

    if status:
        status_value = bpo.db.PackageStatus[status]
        if package.status != status_value:
            raise RuntimeError(f"[{fmt}] Expected status {status}, but has {package.status.name}")

    if version and package.version != version:
        raise RuntimeError(f"[{fmt}] Expected version {version}, but has {package.version}")

    if package.retry_count != retry_count:
        raise RuntimeError(f"[{fmt}] Expected retry_count {retry_count}, but has {package.retry_count}")

    if job_id is not False and package.job_id != job_id:
        raise RuntimeError(f"[{fmt}] Expected job_id {job_id}, but has {package.job_id}")

    if package.splitrepo != splitrepo:
        raise RuntimeError(f"[{fmt}] Expected splitrepo {splitrepo}, but has {package.splitrepo}")


def assert_image(device, branch, ui, status=None, count=1):
    session = bpo.db.session()
    image_str = f"{branch}:{device}:{ui}"

    # Do not use bpo.db.get_image, because we want finished entries too.
    result = session.query(bpo.db.Image).\
        filter_by(device=device, branch=branch, ui=ui).all()
    if len(result) != count:
        raise RuntimeError(f"{image_str}: expected {count} entries in db, got"
                           f" {len(result)}")

    for image in result:
        if status:
            status_value = bpo.db.ImageStatus[status]
            if image.status != status_value:
                raise RuntimeError(f"Expected status {status}, but has"
                                   f" {image.status.name}: {image}")


def is_same_file(path_a, path_b):
    with open(path_a, "rb") as f1, open(path_b, "rb") as f2:
        return f1.read() == f2.read()

def init_components():
    """Initialize the config, logging, etc. - use this when you get errors like
       "AttributeError: module 'bpo.config.args' has no attribute 'repo_wip_path'"
       when trying to execute single tests (that do work when executing all tests)."""
    sys.argv = ["bpo.py", "-t", "test/test_tokens.cfg", "local"]
    bpo.init_components()
