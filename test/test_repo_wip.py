# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/repo/wip.py """
import bpo_test
import bpo_test.trigger
import bpo.db
import bpo.repo
import bpo.repo.wip

import os
import shutil
import sys


def test_get_path(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["bpo.py", "--repo-wip-path", "/repo-wip", "local"])
    bpo.config.args.init()

    func = bpo.repo.wip.get_path
    arch = "x86_64"
    branch = "master"
    assert func(arch, branch) == "/repo-wip/master/x86_64"

    branch = "master_staging_test"
    assert func(arch, branch) == "/repo-wip/staging/test/master/x86_64"

    # Reset
    monkeypatch.setattr(sys, "argv", ["bpo.py", "local"])
    bpo.config.args.init()


def test_repo_wip_clean(monkeypatch):
    # *** Preparation ***
    arch = "x86_64"
    branch = "master"
    splitrepo = None
    apk = "hello-world-wrapper-subpkg-1-r2.apk"
    apk_path = bpo.config.const.top_dir + "/test/testdata/" + apk
    wip_path = bpo.repo.wip.get_path(arch, branch)
    final_path = bpo.repo.final.get_path(arch, branch)
    func = bpo.repo.wip.clean

    # Fill the db with "hello-world", "hello-world-wrapper"
    with bpo_test.BPOServer():
        monkeypatch.setattr(bpo.repo, "build", bpo_test.stop_server)
        bpo_test.trigger.job_callback_get_depends("master")

    # Skip updating apkindex at the end of clean()
    monkeypatch.setattr(bpo.repo.wip, "update_apkindex", bpo_test.nop)

    # 1. apk is not in final repo, origin is in db => don't remove apk
    os.makedirs(wip_path)
    shutil.copy(apk_path, wip_path)
    func(arch, branch, splitrepo)
    assert bpo.repo.get_apks(wip_path) == [apk]

    # 2. apk is in final repo, origin is in db => remove apk
    os.makedirs(final_path)
    shutil.copy(apk_path, wip_path)
    shutil.copy(apk_path, final_path)
    func(arch, branch, splitrepo)
    assert bpo.repo.get_apks(wip_path) == []

    # Delete origin from db
    session = bpo.db.session()
    origin_pkgname = "hello-world-wrapper"
    package = bpo.db.get_package(session, origin_pkgname, arch, branch)
    session.delete(package)
    session.commit()
    assert bpo.db.get_package(session, origin_pkgname, arch, branch) is None

    # 3. apk is in final repo, origin is not in db => remove apk
    shutil.copy(apk_path, wip_path)
    func(arch, branch, splitrepo)
    assert bpo.repo.get_apks(wip_path) == []

    # 4. apk is not in final repo, origin is not in db => remove apk
    os.unlink(final_path + "/" + apk)
    shutil.copy(apk_path, wip_path)
    func(arch, branch, splitrepo)
    assert bpo.repo.get_apks(wip_path) == []
