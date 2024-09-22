# Copyright 2024 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/repo/bootstrap.py """
import bpo_test
import bpo_test.trigger
import bpo.db
import bpo.repo.bootstrap


def test_get_splitrepos_where_bootstrap_is_needed(monkeypatch):
    func = bpo.repo.bootstrap.get_splitrepos_where_bootstrap_is_needed
    rb_dirs = ["systemd"]
    monkeypatch.setattr(bpo.config.const, "repo_bootstrap_dirs", rb_dirs)

    payload = [
        {"pkgname": "hello-world",
         "repo": "main",
         "version": "1-r4"}
    ]
    assert func(payload) == []

    payload += [
        {"pkgname": "systemd",
         "repo": "systemd",
         "version": "123"}
    ]
    assert func(payload) == ["systemd"]


def test_init():
    payload = [
        {"pkgname": "hello-world",
         "repo": "main",
         "version": "1-r4"}
    ]
    payload_systemd = [
        {"pkgname": "hello-world",
         "repo": "main",
         "version": "1-r4"},
        {"pkgname": "systemd",
         "repo": "systemd",
         "version": "123"},
    ]

    func = bpo.repo.bootstrap.init
    get_rb = bpo.db.get_repo_bootstrap
    arch = "x86_64"
    branch = "master"
    dir_name = "systemd"

    with bpo_test.BPOServer():
        bpo_test.stop_server()

    session = bpo.db.session()
    # Not existing, not needed -> rb not created
    assert func(session, payload, arch, branch) is False
    assert get_rb(session, arch, branch, dir_name) is None
    # Not existing, needed -> rb gets created
    assert func(session, payload_systemd, arch, branch) is True
    assert get_rb(session, arch, branch, dir_name)
    # Existing -> rb not created
    assert func(session, payload_systemd, arch, branch) is False
    assert get_rb(session, arch, branch, dir_name)


def test_update_to_published():
    payload = [
        {"pkgname": "hello-world",
         "repo": "main",
         "version": "1-r4"},
        {"pkgname": "systemd",
         "repo": "systemd",
         "version": "123"},
    ]

    func = bpo.repo.bootstrap.update_to_published

    get_rb = bpo.db.get_repo_bootstrap
    arch = "x86_64"
    branch = "master"
    dir_name = "systemd"

    with bpo_test.BPOServer():
        bpo_test.stop_server()

    # RepoBootstrap does not exist
    assert func(arch, branch, dir_name) is False

    # Create RepoBootstrap entry
    session = bpo.db.session()
    bpo.repo.bootstrap.init(session, payload, arch, branch)

    # RepoBootstrap exists, but status is queued
    assert func(arch, branch, dir_name) is False

    # Set status to built
    rb = get_rb(session, arch, branch, dir_name)
    bpo.db.set_repo_bootstrap_status(session, rb,
                                     bpo.db.RepoBootstrapStatus.built)

    # RepoBootstrap exists, status is built -> set to published
    assert func(arch, branch, dir_name) is True
    rb = get_rb(session, arch, branch, dir_name)
    assert rb.status == bpo.db.RepoBootstrapStatus.published

    # RepoBootstrap exists, status is published
    assert func(arch, branch, dir_name) is False
