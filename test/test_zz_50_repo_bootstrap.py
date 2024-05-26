# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Integration tests for bpo/repo/bootstrap.py (slow) """
import logging
import pytest

import bpo_test  # noqa
import bpo_test.const
import bpo_test.trigger

import bpo.api.job_callback.repo_bootstrap
import bpo.job_services.local
import bpo.repo
import bpo.repo.final

TEST_STEP_CURRENT = 0


def TEST_STEP(num, title):
    global TEST_STEP_CURRENT
    assert TEST_STEP_CURRENT == num -1
    logging.info("-----------------------------------------------------------")
    logging.info(f"TEST STEP {num}: {title}")
    logging.info("-----------------------------------------------------------")
    TEST_STEP_CURRENT += 1


@pytest.mark.timeout(100)
def test_repo_bootstrap_full(monkeypatch):
    global TEST_STEP_CURRENT

    testdata_dir = f"{bpo.config.const.top_dir}/test/testdata"

    def fake_step3(session, rb):
        TEST_STEP(3, "Run repo_bootstrap job")
        monkeypatch.setattr(bpo.jobs.build_package, "run", fake_step4)
        orig_step3(session, rb, f"{testdata_dir}/pmaports_repo_bootstrap.cfg")

    def fake_step4(arch, pkgname, branch):
        TEST_STEP(4, "Run build_package job")
        assert arch == "x86_64"
        assert pkgname == "hello-world-wrapper"
        assert branch == "master"
        bpo_test.stop_server()
        return True

    orig_step3 = bpo.jobs.repo_bootstrap.run
    monkeypatch.setattr(bpo.jobs.repo_bootstrap, "run", fake_step3)

    TEST_STEP_CURRENT = 0
    TEST_STEP(1, "Start bpo server")
    with bpo_test.BPOServer():
        TEST_STEP(2, "Run get_depends job callback")
        payload_path = f"{testdata_dir}/depends_systemd.json"
        bpo_test.trigger.job_callback_get_depends("master",
                                                  payload_path=payload_path)
