# Copyright 2023 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/repo/final.py """
import sys

import bpo_test  # noqa
import bpo.config.args
import bpo.repo.final


def test_get_path():
    sys.argv = ["bpo.py", "--repo-final-path", "/repo-final", "local"]
    bpo.config.args.init()

    func = bpo.repo.final.get_path
    arch = "x86_64"
    branch = "master"
    splitrepo = None
    assert func(arch, branch, splitrepo) == "/repo-final/master/x86_64"
    splitrepo = "systemd"
    assert func(arch, branch, splitrepo) == "/repo-final/extra-repos/systemd/master/x86_64"

    splitrepo = None
    branch = "master_staging_test"
    assert func(arch, branch, splitrepo) == "/repo-final/staging/test/master/x86_64"
    splitrepo = "systemd"
    assert func(arch, branch, splitrepo) == "/repo-final/extra-repos/systemd/staging/test/master/x86_64"
