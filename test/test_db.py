# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/db/__init__.py """
import datetime
import pytest
import sys

import bpo_test
import bpo_test.trigger
import bpo.repo


def test_validate_job_id(monkeypatch):
    # Fill the db with "hello-world", "hello-world-wrapper"
    with bpo_test.BPOServer():
        monkeypatch.setattr(bpo.repo, "build", bpo_test.stop_server)
        bpo_test.trigger.job_callback_get_depends("master")

    # result is empty, job_id == 1337
    session = bpo.db.session()
    func = bpo.db.validate_job_id
    result_empty = session.query(bpo.db.Package).filter_by(arch="x86_64",
                                                           branch="master",
                                                           pkgname="404").all()
    assert func(result_empty, "1337") is False

    # Fill result with one package
    pkgname = "hello-world"
    arch = "x86_64"
    branch = "master"
    result = session.query(bpo.db.Package).filter_by(arch=arch,
                                                     branch=branch,
                                                     pkgname=pkgname).all()

    # result[0].job_id is None, job_id == 1337
    job_id = "1337"
    with pytest.raises(ValueError) as e:
        func(result, job_id)
    assert "got 1337 instead of" in str(e.value)

    # result[0].job_id == 1337, job_id == 1337
    result[0].job_id = 1337
    assert func(result, "1337") is True

    # result[0].job_id == 1337, job_id is None
    assert func(result, None) is False

    # result[0].job_id == 1337, job_id is invalid
    job_id = "1337_1"
    with pytest.raises(ValueError) as e:
        func(result, job_id)
    assert "invalid: 1337_1" in str(e.value)


def test_get_recent_packages_by_status(monkeypatch):
    monkeypatch.setattr(bpo.config.const, "branches",
                        {"v22.12": {},
                         "v23.06": {},
                         "master": {}})

    # Initialize bpo
    bpo_test.reset()
    monkeypatch.setattr(sys, "argv", ["bpo.py", "-t", "test/test_tokens.cfg",
                                      "--mirror", "", "local"])
    bpo.init_components()

    # Fill the DB with test packages
    session = bpo.db.session()
    session.merge(bpo.db.Package("x86_64", "master", "hello-world", "1.0.0"))
    session.merge(bpo.db.Package("x86_64", "v22.12", "hello-world", "1.0.0"))
    session.merge(bpo.db.Package("x86_64", "v23.06", "hello-world", "1.0.0"))
    session.merge(bpo.db.Package("x86_64", "v22.06", "hello-world", "1.0.0"))
    session.commit()

    q = bpo.db.get_recent_packages_by_status(session)["queued"]

    # Verify that the v22.06 package does not get returned, as it is not in
    # bpo.config.const.branches
    assert len(q) == 3
    assert q[0].branch == "master"
    assert q[1].branch == "v22.12"
    assert q[2].branch == "v23.06"


def test_get_recent_images_by_status(monkeypatch):
    monkeypatch.setattr(bpo.config.const, "branches",
                        {"v22.12": {},
                         "v23.06": {},
                         "master": {}})

    # Initialize bpo
    bpo_test.reset()
    monkeypatch.setattr(sys, "argv", ["bpo.py", "-t", "test/test_tokens.cfg",
                                      "--mirror", "", "local"])
    bpo.init_components()

    # Fill the DB with test images
    session = bpo.db.session()

    img = bpo.db.Image("qemu-amd64", "master", "phosh")
    img.date = datetime.datetime.fromisoformat("2022-01-01")
    session.merge(img)

    session.merge(bpo.db.Image("qemu-amd64", "master", "phosh"))
    session.merge(bpo.db.Image("qemu-amd64", "v22.12", "phosh"))
    session.merge(bpo.db.Image("qemu-amd64", "v23.06", "phosh"))
    session.merge(bpo.db.Image("qemu-amd64", "v22.06", "phosh"))
    session.commit()

    q = bpo.db.get_recent_images_by_status(session)["queued"]

    # Verify that old images (by date, and the v22.06 image) don't get returned
    assert q.count() == 3
    assert q[0].branch == "master"
    assert q[1].branch == "v22.12"
    assert q[2].branch == "v23.06"
