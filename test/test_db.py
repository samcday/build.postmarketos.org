# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/db/__init__.py """
import pytest

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
