# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/ui/__init__.py """
import collections

import bpo_test
import bpo_test.trigger
import bpo.config.const
import bpo.db
import bpo.repo
import bpo.ui


def test_update_badge(monkeypatch):
    branches = collections.OrderedDict()
    branches["master"] = {"arches": ["x86_64",
                                     "armhf",
                                     "aarch64",
                                     "armv7",
                                     "x86"]}
    monkeypatch.setattr(bpo.config.const, "branches", branches)

    # Fill the db with "hello-world", "hello-world-wrapper"
    with bpo_test.BPOServer():
        monkeypatch.setattr(bpo.repo, "build", bpo_test.stop_server)
        bpo_test.trigger.job_callback_get_depends("master")

    session = bpo.db.session()
    func = bpo.ui.update_badge
    func_pkgs = bpo.db.get_recent_packages_by_status
    func_imgs = bpo.db.get_recent_images_by_status
    arch = "x86_64"
    branch = "master"
    splitrepo = None

    # Building
    badge = func(session, func_pkgs(session), func_imgs(session))
    assert badge == "building"

    # Failed
    pkg_hello = bpo.db.get_package(session, "hello-world", arch, branch, splitrepo)
    bpo.db.set_package_status(session, pkg_hello, bpo.db.PackageStatus.failed)
    badge = func(session, func_pkgs(session), func_imgs(session))
    assert badge == "failed"

    # Up-to-date
    pkg_wrapper = bpo.db.get_package(session, "hello-world-wrapper", arch,
                                     branch, splitrepo)
    bpo.db.set_package_status(session, pkg_hello, bpo.db.PackageStatus.built)
    bpo.db.set_package_status(session, pkg_wrapper, bpo.db.PackageStatus.built)
    badge = func(session, func_pkgs(session), func_imgs(session))
    assert badge == "up-to-date"

    # hello-world-wrapper: change branch, set to failed
    pkg_wrapper.branch = "v20.05"
    pkg_wrapper.status = bpo.db.PackageStatus.failed
    session.merge(pkg_wrapper)
    session.commit()

    # Branch is not in config: still up-to-date
    badge = func(session, func_pkgs(session), func_imgs(session))
    assert badge == "up-to-date"

    # Branch is in config: failed
    branches["v20.05"] = {"arches": ["x86_64"]}
    badge = func(session, func_pkgs(session), func_imgs(session))
    assert badge == "failed"

    # Branch is ignored: up-to-date
    branches["v20.05"]["ignore_errors"] = True
    badge = func(session, func_pkgs(session), func_imgs(session))
    assert badge == "up-to-date"


def test_update_monitoring_txt(monkeypatch):
    # Set branch config
    branches = collections.OrderedDict()
    branches["master"] = {"arches": ["x86_64",
                                     "armhf",
                                     "aarch64",
                                     "armv7",
                                     "x86"]}
    monkeypatch.setattr(bpo.config.const, "branches", branches)

    # Set image config
    monkeypatch.setattr(bpo.config.const.images, "images",
                        {"qemu-amd64": {
                            "branches": ["master"],
                            "branch_configs": {
                                "master": {
                                    "ui": ["console"],
                                    "kernels": ["virt"],
                                }
                            }
                        }})

    def fake_get_link(job_id):
        return f"http://localhost/{job_id}"
    monkeypatch.setattr(bpo.helpers.job, "get_link", fake_get_link)
    monkeypatch.setattr(bpo.jobs.build_image, "run", bpo_test.nop)

    def assert_txt_content(content_expected, list_count_max=5):
        func_pkgs = bpo.db.get_recent_packages_by_status
        func_imgs = bpo.db.get_recent_images_by_status
        bpo.ui.update_monitoring_txt(session, func_pkgs(session),
                                     func_imgs(session),
                                     add_footer=False,
                                     list_count_max=list_count_max)

        output = bpo.config.args.html_out + "/monitoring.txt"
        with open(output) as h:
            content_real = h.read()
        assert content_expected == content_real

    # Fill the db with test packages and image
    with bpo_test.BPOServer(fill_image_queue=True):
        monkeypatch.setattr(bpo.repo, "build", bpo_test.stop_server)
        bpo_test.trigger.job_callback_get_depends("master")

    session = bpo.db.session()

    # No failures
    assert_txt_content("OK\n")

    # One failed package
    arch = "x86_64"
    branch = "master"
    splitrepo = None
    pkgname = "hello-world"
    pkg = bpo.db.get_package(session, pkgname, arch, branch, splitrepo)
    bpo.db.set_package_status(session, pkg, bpo.db.PackageStatus.failed, 1)
    assert_txt_content("1 failure at https://build.postmarketos.org:\n"
                       "* 📦 master/x86_64/hello-world: http://localhost/1\n")

    # Two failed packages
    pkgname = "hello-world-wrapper"
    pkg = bpo.db.get_package(session, pkgname, arch, branch, splitrepo)
    bpo.db.set_package_status(session, pkg, bpo.db.PackageStatus.failed, 2)
    assert_txt_content("2 failures at https://build.postmarketos.org:\n"
                       "* 📦 master/x86_64/hello-world: http://localhost/1\n"
                       "* 📦 master/x86_64/hello-world-wrapper: http://localhost/2\n")

    # Two failed packages, abbreviated
    assert_txt_content("2 failures at https://build.postmarketos.org:\n"
                       "* 📦 master/x86_64/hello-world: http://localhost/1\n"
                       "* ...\n",
                       list_count_max=1)

    # Two failed packages, one failed image
    device = "qemu-amd64"
    ui = "console"
    img = bpo.db.get_image(session, branch, device, ui)
    bpo.db.set_image_status(session, img, bpo.db.ImageStatus.failed, 3)
    assert_txt_content("3 failures at https://build.postmarketos.org:\n"
                       "* 📦 master/x86_64/hello-world: http://localhost/1\n"
                       "* 📦 master/x86_64/hello-world-wrapper: http://localhost/2\n"
                       "* 🖼️ master:qemu-amd64:console: http://localhost/3\n")

    # Two failed packages, one failed image, abbreviated
    assert_txt_content("3 failures at https://build.postmarketos.org:\n"
                       "* 📦 master/x86_64/hello-world: http://localhost/1\n"
                       "* ...\n",
                       list_count_max=1)
