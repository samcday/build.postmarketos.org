# Copyright 2025 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/helpers/pmb.py """
import bpo_test
import bpo.helpers.pmb
import os.path


def test_get_pmos_mirror(monkeypatch):
    bpo_test.init_components()
    monkeypatch.setattr(bpo.config.args, "mirror", "MAIN")
    monkeypatch.setattr(bpo.config.args, "url_repo_wip", "WIP")

    func = bpo.helpers.pmb.get_pmos_mirror

    branch = "master"
    splitrepo = None
    mirror_type = "main"
    add_branch = False
    assert func(branch, splitrepo, mirror_type, add_branch) == "MAIN/"

    branch = "master"
    splitrepo = None
    mirror_type = "wip"
    add_branch = False
    assert func(branch, splitrepo, mirror_type, add_branch) == "WIP/"

    branch = "master"
    splitrepo = None
    mirror_type = "main"
    add_branch = True
    assert func(branch, splitrepo, mirror_type, add_branch) == "MAIN/master/"

    branch = "master"
    splitrepo = "systemd"
    mirror_type = "main"
    add_branch = True
    assert func(branch, splitrepo, mirror_type, add_branch) == "MAIN/extra-repos/systemd/master/"

    branch = "master_staging_TODO"
    splitrepo = None
    mirror_type = "main"
    add_branch = True
    assert func(branch, splitrepo, mirror_type, add_branch) == "MAIN/staging/TODO/master/"

    branch = "master_staging_TODO"
    splitrepo = "systemd"
    mirror_type = "main"
    add_branch = True
    assert func(branch, splitrepo, mirror_type, add_branch) == "MAIN/extra-repos/systemd/staging/TODO/master/"


def test_set_repos_task(monkeypatch):
    bpo_test.init_components()

    monkeypatch.setattr(bpo.config.const, "mirror_alpine", "ALPINE")
    monkeypatch.setattr(bpo.config.args, "mirror", "PMOS_MAIN")
    monkeypatch.setattr(bpo.config.args, "url_repo_wip", "PMOS_WIP")
    monkeypatch.setattr(bpo.helpers.pmb, "should_add_wip_repo", bpo_test.true)

    func = bpo.helpers.pmb.set_repos_task
    arch = "x86_64"

    monkeypatch.setattr(os.path, "exists", bpo_test.false)

    branch = "master"
    add_wip_repo = False
    assert func(arch, branch, add_wip_repo) == \
        "pmbootstrap config mirrors.alpine ALPINE\n"

    monkeypatch.setattr(os.path, "exists", bpo_test.true)

    branch = "master"
    add_wip_repo = False
    assert func(arch, branch, add_wip_repo) == \
        "pmbootstrap config mirrors.alpine ALPINE\n" \
        "pmbootstrap config mirrors.pmaports PMOS_MAIN/\n" \
        "pmbootstrap config mirrors.systemd PMOS_MAIN/extra-repos/systemd/\n"

    branch = "master_staging_TODO"
    add_wip_repo = False
    assert func(arch, branch, add_wip_repo) == \
        "pmbootstrap config mirrors.alpine ALPINE\n" \
        "pmbootstrap config mirrors.pmaports PMOS_MAIN/staging/TODO/\n" \
        "pmbootstrap config mirrors.systemd PMOS_MAIN/extra-repos/systemd/staging/TODO/\n"

    monkeypatch.setattr(os.path, "exists", bpo_test.true)
    branch = "master"
    add_wip_repo = True
    assert func(arch, branch, add_wip_repo) == \
        "pmbootstrap config mirrors.alpine ALPINE\n" \
        "pmbootstrap config mirrors.pmaports_custom PMOS_WIP/\n" \
        "pmbootstrap config mirrors.pmaports PMOS_MAIN/\n" \
        "pmbootstrap config mirrors.systemd_custom PMOS_WIP/extra-repos/systemd/\n" \
        "pmbootstrap config mirrors.systemd PMOS_MAIN/extra-repos/systemd/\n"
