# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Integration tests for bpo/repo/staging.py (slow) """
import logging
import os
import pytest
import subprocess
import sys
import traceback

import bpo_test  # noqa
import bpo_test.const
import bpo_test.trigger

import bpo.job_services.local
import bpo.repo
import bpo.repo.final


def job_failed():
    raise RuntimeError("job failed")


@pytest.mark.timeout(300)
def test_no_sync_while_orig_repo_has_unpublished_pkgs(monkeypatch, tmpdir):
    """ Build hello-world in the original repository. While it is still in the
        WIP repository (not published yet), push the staging branch with
        hello-world and hello-world-wrapper packages, and test that hello-world
        does *not* get copied from the original repository's WIP repo. """
    branch_staging = "master_staging_test_1234"
    payload_path = str(tmpdir) + "/payload.json"

    bpo_jobs_get_depends_run = bpo.jobs.get_depends.run
    bpo_repo_symlink_sign = bpo.repo.symlink.sign

    repo_final_path = bpo.config.const.args.repo_final_path
    repo_wip_path = bpo.config.const.args.repo_wip_path

    v_hello = bpo_test.const.version_hello_world
    v_wrapper = bpo_test.const.version_hello_world_wrapper

    def repo_final_publish(*args, **kwargs):
        # This function gets called right after the original repository's WIP
        # repo has been published to final. Check that the hello-world package
        # was not synced to the staging repository earlier, as this should not
        # happen as long as the original repository has unpublished packages.
        logging.info(" ### [part 7] staging: verify packages not synced")
        hello_apk = f"hello-world-{v_hello}.apk"
        path_hello_orig = f"{repo_final_path}/master/x86_64/{hello_apk}"
        path_hello_staging = f"{repo_final_path}/staging/test_1234/master/x86_64/{hello_apk}"
        assert os.path.exists(path_hello_orig)
        assert not os.path.exists(path_hello_staging)

        bpo_test.stop_server()

    def jobs_get_depends_run(branch):
        readme_path = f"{repo_final_path}/staging/test_1234/master/README"
        logging.info(f" ### [part 3] check for {readme_path}")
        assert os.path.exists(readme_path)

        # Clear pmb packages, so it doesn't take hello-world from there
        logging.info(" ### [part 4] clear pmbootstrap packages")
        subprocess.run(["pmbootstrap", "-y", "zap", "-p"], check=True)

        # Reset overrides
        monkeypatch.setattr(bpo.repo.symlink, "sign", bpo_repo_symlink_sign)
        monkeypatch.setattr(bpo.jobs.get_depends, "run", bpo_jobs_get_depends_run)

        # Override to continue with next part
        monkeypatch.setattr(bpo.repo.final, "publish", repo_final_publish)

        logging.info(" ### [part 5] check for hello-world in wip orig repo")
        hello_apk = f"hello-world-{v_hello}.apk"
        path_hello_orig = f"{repo_wip_path}/master/x86_64/{hello_apk}"
        assert os.path.exists(path_hello_orig)

        # Run get_depends job callback:
        # * Pretend that the get_depends job ran and figured out that the
        #   staging branch has two packages, hello-world at the same version as
        #   in the orig repository and (not in orig) hello-world-wrapper.
        # * hello-world-wrapper does *not* get built by BPO as the orig repo
        #   has unpublished packages (hello-world is still in its WIP repo).
        # * BPO publishes hello-world in the original repo (WIP -> final).
        logging.info(" ### [part 6] run get_depends for staging")
        overrides = {"hello-world": {"version": v_hello},
                     "hello-world-wrapper": {"version": v_wrapper}}
        bpo_test.trigger.override_depends_json(payload_path, overrides)
        bpo_test.trigger.job_callback_get_depends(branch_staging,
                                                  payload_path=payload_path,
                                                  background=True)

    def repo_symlink_sign(*args, **kwargs):
        logging.info(f" ### [part 2] staging: push new branch {branch_staging}")
        monkeypatch.setattr(bpo.jobs.get_depends, "run", jobs_get_depends_run)
        bpo_test.trigger.push_hook_gitlab(branch_staging, background=True)

    logging.info(" ### [part 1] original: build hello-world")

    # Abort when any job fails
    monkeypatch.setattr(bpo.job_services.local, "job_failed", job_failed)

    # Prepare get-depends payload for orig repo
    overrides = {"hello-world": {"version": v_hello}}
    testfile = "depends.x86_64_hello-world_only.json"
    bpo_test.trigger.override_depends_json(payload_path, overrides, testfile)

    # Trigger job-callback/get-depends to trigger the package build
    with bpo_test.BPOServer():
        monkeypatch.setattr(bpo.repo.symlink, "sign", repo_symlink_sign)
        bpo_test.trigger.job_callback_get_depends("master",
                                                  payload_path=payload_path)

@pytest.mark.timeout(300)
def test_build_publish_remove_staging_repo(monkeypatch, tmpdir):
    """ Build hello-world in the original repository, and wait until the
        package is published to the final repository. Afterwards, push the
        staging branch with hello-world and hello-world-wrapper packages, and
        test that hello-world gets properly copied from the original
        repository's final repo. Build hello-world-wrapper from the staging
        repo. Wait until it is published and remove the staging repository.
    """
    branch_staging = "master_staging_test_1234"
    payload_path = str(tmpdir) + "/payload.json"

    repo_final_path = bpo.config.const.args.repo_final_path
    repo_wip_path = bpo.config.const.args.repo_wip_path
    v_hello = bpo_test.const.version_hello_world
    v_wrapper = bpo_test.const.version_hello_world_wrapper

    def bpo_ui_log(action, *args, **kwargs):
        assert action == "delete_staging_repo"
        assert not os.path.exists(f"{repo_final_path}/staging/test_1234")
        assert not os.path.exists(f"{repo_wip_path}/staging/test_1234/master")
        logging.info(" ### [part 8] done, stopping bpo server")
        bpo_test.stop_server()

    def repo_final_publish_2(*args, **kwargs):
        # Check that hello-world was properly synced from the original repo.
        # (We could check for the hardlink, but this would not work with gitlab
        # CI where instead of hardlinking we have to actually copy the file.)
        logging.info(" ### [part 6] staging: verify packages in repository")
        hello_apk = f"hello-world-{v_hello}.apk"
        path_hello_orig = f"{repo_final_path}/master/x86_64/{hello_apk}"
        path_hello_staging = f"{repo_final_path}/staging/test_1234/master/x86_64/{hello_apk}"
        assert bpo_test.is_same_file(path_hello_orig, path_hello_staging)

        hello_wrapper_apk = f"hello-world-wrapper-{v_wrapper}.apk"
        path_hello_wrapper = (f"{repo_final_path}/staging/test_1234/master/"
                              f"x86_64/{hello_wrapper_apk}")
        assert os.path.exists(path_hello_wrapper)

        logging.info(" ### [part 7] staging: remove")
        monkeypatch.setattr(bpo.ui, "log", bpo_ui_log)
        assert os.path.exists(f"{repo_final_path}/staging/test_1234")
        assert os.path.exists(f"{repo_wip_path}/staging/test_1234/master")
        bpo_test.trigger.push_hook_gitlab(branch=branch_staging, background=True,
                                          after="0000000000000000000000000000000000000000")

    def jobs_get_depends_run(branch):
        readme_path = f"{repo_final_path}/staging/test_1234/master/README"
        logging.info(f" ### [part 3] check for {readme_path}")
        assert os.path.exists(readme_path)

        # Clear pmb packages, so it doesn't take hello-world from there
        logging.info(" ### [part 4] clear pmbootstrap packages")
        subprocess.run(["pmbootstrap", "-y", "zap", "-p"], check=True)

        logging.info(" ### [part 5] staging: build hello-world-wrapper")
        monkeypatch.setattr(bpo.repo.final, "publish", repo_final_publish_2)
        overrides = {"hello-world": {"version": v_hello},
                     "hello-world-wrapper": {"version": v_wrapper}}
        bpo_test.trigger.override_depends_json(payload_path, overrides)
        bpo_test.trigger.job_callback_get_depends(branch_staging,
                                                  payload_path=payload_path,
                                                  background=True)

    def repo_final_publish(*args, **kwargs):
        logging.info(f" ### [part 2] staging: push new branch {branch_staging}")
        monkeypatch.setattr(bpo.jobs.get_depends, "run", jobs_get_depends_run)
        bpo_test.trigger.push_hook_gitlab(branch_staging, background=True)

    logging.info(" ### [part 1] original: build hello-world")

    # Abort when any job fails
    monkeypatch.setattr(bpo.job_services.local, "job_failed", job_failed)

    # Prepare get-depends payload for orig repo
    overrides = {"hello-world": {"version": v_hello}}
    testfile = "depends.x86_64_hello-world_only.json"
    bpo_test.trigger.override_depends_json(payload_path, overrides, testfile)

    # Trigger job-callback/get-depends to trigger the package build
    with bpo_test.BPOServer():
        try:
            monkeypatch.setattr(bpo.repo.final, "publish", repo_final_publish)
            bpo_test.trigger.job_callback_get_depends("master",
                                                      payload_path=payload_path)
        except Exception:
            logging.error("### Exception (see stderr)")
            print("### Exception from test case", file=sys.stderr)
            traceback.print_exc()
