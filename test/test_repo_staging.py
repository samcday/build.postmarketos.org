# Copyright 2023 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/repo/staging.py """
import collections
import logging
import os
import pathlib
import sys
import traceback

import bpo_test  # noqa
import bpo.repo.staging
import bpo.db


def test_branch_split():
    func = bpo.repo.staging.branch_split

    assert func("master") is None
    assert func("master_staging_test_branch") == ("master", "test_branch")

    # Orig branch not in config
    assert func("v20.05_staging_test_branch") is None


def test_get_branches_with_staging(monkeypatch, tmp_path):
    # Fake bpo.config.const.branches
    branches = collections.OrderedDict()
    branches["v23.06"] = {"arches": ["x86_64", "aarch64"]}
    branches["master"] = {"arches": ["x86_64",
                                     "aarch64",
                                     "riscv64"]}
    monkeypatch.setattr(bpo.config.const, "branches", branches)
    monkeypatch.setattr(bpo.config.const, "staging_arches", ["aarch64", "riscv64"])

    # Fake staging dir in repo_final_path
    # A staging dir for v22.12 gets created but is not in the result since
    # branches["v22.12"] is not set above
    repo_final_path = f"{tmp_path}"
    setattr(bpo.config.args, "repo_final_path", repo_final_path)
    for branch in ["v22.12", "v23.06", "master"]:
        branch_dir = f"{repo_final_path}/staging/test_branch/{branch}"
        os.makedirs(branch_dir)
        pathlib.Path(f"{branch_dir}/README").touch()

    # Check output
    func = bpo.repo.staging.get_branches_with_staging
    pmb_branch = os.environ.get("BPO_PMA_STAGING_PMB_BRANCH", "2.3.x")
    assert func() == collections.OrderedDict({
        "v23.06": {"arches": ["x86_64", "aarch64"]},
        "master": {"arches": ["x86_64", "aarch64", "riscv64"]},
        "v23.06_staging_test_branch": {"arches": ["aarch64", "riscv64"],
                                       "ignore_errors": True,
                                       "pmb_branch": pmb_branch},
        "master_staging_test_branch": {"arches": ["aarch64", "riscv64"],
                                       "ignore_errors": True,
                                       "pmb_branch": pmb_branch},
    })


def test_remove_wrong_branch():
    assert bpo.repo.staging.remove("master") is False


def test_remove(monkeypatch):
    branches = collections.OrderedDict()
    branches["v23.06"] = {"arches": ["x86_64", "aarch64", "armv7"]}
    branches["master"] = branches["v23.06"]
    monkeypatch.setattr(bpo.config.const, "branches", branches)

    repo_final_path = bpo.config.const.args.repo_final_path
    repo_wip_path = bpo.config.const.args.repo_wip_path

    branch_1 = "master_staging_test_branch"
    path_final_1 = f"{repo_final_path}/staging/test_branch/master"
    path_wip_1 = f"{repo_wip_path}/staging/test_branch/master"

    branch_2 = "v23.06_staging_test_branch"
    path_final_2 = f"{repo_final_path}/staging/test_branch/v23.06"
    path_wip_2 = f"{repo_wip_path}/staging/test_branch/v23.06"

    with bpo_test.BPOServer():
        try:
            logging.info("### Create final and wip dirs")
            os.makedirs(path_final_1)
            os.makedirs(path_final_2)
            os.makedirs(path_wip_1)
            os.makedirs(path_wip_2)

            logging.info("### Create one package for each staging repo")
            session = bpo.db.session()
            arch = "x86_64"
            pkgname = "test-package"
            version = "1.0.0-r0"
            package_1 = bpo.db.Package(arch, branch_1, pkgname, version)
            package_2 = bpo.db.Package(arch, branch_2, pkgname, version)
            session.merge(package_1)
            session.merge(package_2)
            session.commit()

            logging.info("### Check if inserted properly")
            bpo_test.assert_package(pkgname, branch=branch_1, exists=True)
            bpo_test.assert_package(pkgname, branch=branch_2, exists=True)

            logging.info("### Remove branch_1")
            assert bpo.repo.staging.remove(branch_1) is True

            logging.info("### Expect branch_1 to be gone")
            bpo_test.assert_package(pkgname, branch=branch_1, exists=False)
            assert not os.path.exists(path_final_1)
            assert not os.path.exists(path_wip_1)

            logging.info("### Expect branch_2 to still exist")
            bpo_test.assert_package(pkgname, branch=branch_2, exists=True)
            assert os.path.exists(path_final_2)
            assert os.path.exists(path_wip_2)

            logging.info("### Remove branch_2")
            assert bpo.repo.staging.remove(branch_2) is True

            logging.info("### Expect branch_2 to be gone")
            bpo_test.assert_package(pkgname, branch=branch_2, exists=False)
            assert not os.path.exists(path_final_2)
            assert not os.path.exists(path_wip_2)

            logging.info("### Expect staging dir for 'test_branch' to be gone")
            assert not os.path.exists(f"{repo_final_path}/staging/test_branch")

            logging.info("### Stop")
            bpo_test.stop_server()
        except Exception:
            logging.critical("### Exception from test case", file=sys.stderr)
            logging.critical(traceback.format_exc())
