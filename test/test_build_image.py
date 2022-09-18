# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Testing bpo/api/job_callback/build_image.py """
import pytest

import bpo_test  # noqa
import bpo.api.job_callback.build_image


def test_verify_previous_files(monkeypatch, tmp_path):
    prev_header = ""

    def get_header_fake(request, key):
        return prev_header
    monkeypatch.setattr(bpo.api, "get_header", get_header_fake)

    # Empty http header, empty temp dir
    func = bpo.api.job_callback.build_image.verify_previous_files
    path_temp = f"{tmp_path}"
    request = None
    func(request, path_temp)

    # Empty http header, file exists in temp dir
    open(f"{path_temp}/first", "w").close()
    with pytest.raises(ValueError) as e:
        func(request, path_temp)
    assert "not in Payload-Files-Previous" in str(e.value)

    # File in http header missing in temp dir
    prev_header = "first#second#"
    with pytest.raises(ValueError) as e:
        func(request, path_temp)
    assert "not in temp dir" in str(e.value)

    # Http header not empty, but not listing all files in temp dir
    open(f"{path_temp}/second", "w").close()
    open(f"{path_temp}/third", "w").close()
    with pytest.raises(ValueError) as e:
        func(request, path_temp)
    assert "not in Payload-Files-Previous" in str(e.value)

    # Files in http header same as in temp dir
    prev_header = "first#second#third#"
    func(request, path_temp)
