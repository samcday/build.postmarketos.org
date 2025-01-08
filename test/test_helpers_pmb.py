# Copyright 2025 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/helpers/pmb.py """
import bpo_test
import bpo.helpers.pmb


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
