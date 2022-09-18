# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import glob
import logging
import os

from flask import request
from bpo.helpers.headerauth import header_auth
import bpo.api
import bpo.config.args
import bpo.db
import bpo.images
import bpo.ui
import bpo.ui.images

blueprint = bpo.api.blueprint


def get_files(request):
    """ Get all attached files and verify their names. """
    pattern = bpo.config.const.images.pattern_file
    ret = request.files.getlist("file[]")

    for img in ret:
        if not pattern.match(img.filename) or img.filename == "readme.html":
            raise ValueError(f"Invalid filename: {img.filename}")

    return ret


def get_image(session, branch, device, ui, job_id):
    ret = bpo.db.get_image(session, branch, device, ui, job_id)
    if not ret:
        raise ValueError(f"No unfinished image found with: device={device},"
                         " branch={branch}, ui={ui}")
    if ret.status != bpo.db.ImageStatus.building:
        raise RuntimeError(f"Image {ret} has unexpected status {ret.status}"
                           " instead of 'building'")
    return ret


def get_dir_name(request):
    pattern = bpo.config.const.images.pattern_dir
    ret = bpo.api.get_header(request, "Version")
    if not pattern.match(ret):
        raise ValueError(f"Invalid dir_name (X-BPO-Version): {ret}")
    return ret


def get_path_temp(job_id):
    """ One image consists of multiple files. They get big, especially with the
        installer images, so now we upload only one file at once and put them
        into this temp dir until all of them are uploaded.
        :param job_id: already sanitized ID of the image build job
        :returns: the temporary upload path for the current job """
    return f"{bpo.config.args.temp_path}/image_upload/{job_id}"


def verify_previous_files(request, path_temp):
    key = "Payload-Files-Previous"
    prev_arg = bpo.api.get_header(request, key)

    # Create dict with files currently in temp dir as key, False as value
    temp_dir = {}
    for path in glob.glob(f"{path_temp}/*"):
        temp_dir[os.path.basename(path)] = False

    # Check if each file in prev_arg is in the temp dir
    for file_arg in prev_arg.split("#"):
        if not file_arg:
            break
        if file_arg not in temp_dir:
            raise ValueError(f"found '{file_arg}' in {key}, but not in"
                             f" temp dir {path_temp}: {temp_dir}")
        temp_dir[file_arg] = True

    # Check if temp dir doesn't contain additional files
    for file_temp, found in temp_dir.items():
        if not found:
            raise ValueError(f"found '{file_temp}' in temp dir {path_temp},"
                             f" but not in {key}: '{prev_arg}'")


def upload_new_files(path_temp, files):
    """ Receive one or more files and put them into the temp path. """
    os.makedirs(path_temp, exist_ok=True)

    count = 0
    for img in files:
        path_img = os.path.join(path_temp, img.filename)
        logging.info(f"Saving {path_img}")
        img.save(path_img)
        count += 1

    return f"got {count} file(s)"


def upload_finish(session, image, path_temp, dir_name):
    # Create target dir
    path = bpo.images.path(image.branch, image.device, image.ui, dir_name)
    os.makedirs(path, exist_ok=True)

    # Fill target dir
    count = 0
    for path_img_temp in glob.glob(f"{path_temp}/*"):
        path_img = os.path.join(path, os.path.basename(path_img_temp))
        logging.info(f"Moving from tempdir: {path_img}")
        os.replace(path_img_temp, path_img)
        count += 1

    os.rmdir(path_temp)

    # Update database (status, job_id, dir_name, date)
    bpo.db.set_image_status(session, image, bpo.db.ImageStatus.published,
                            image.job_id, dir_name, datetime.datetime.now())
    bpo.ui.log_image(image, "api_job_callback_build_image")

    # Remove old image
    bpo.images.remove_old()

    # Generate HTML files (for all dirs in the images path, including the path
    # of this image and its potentially new parent directories)
    bpo.ui.images.write_index_all()

    # Start next build job
    bpo.repo.build()
    return f"image dir created from {count} files, kthxbye"


@blueprint.route("/api/job-callback/build-image", methods=["POST"])
@header_auth("X-BPO-Token", "job_callback")
def job_callback_build_image():
    branch = bpo.api.get_branch(request)
    device = bpo.api.get_header(request, "Device")
    dir_name = get_dir_name(request)
    job_id = bpo.api.get_header(request, "Job-Id")
    ui = bpo.api.get_header(request, "Ui")

    session = bpo.db.session()
    image = get_image(session, branch, device, ui, job_id)
    files = get_files(request)
    path_temp = get_path_temp(job_id)

    verify_previous_files(request, path_temp)

    if files:
        return upload_new_files(path_temp, files)
    return upload_finish(session, image, path_temp, dir_name)
