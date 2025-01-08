# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import shlex
import os

import bpo.helpers.job
import bpo.helpers.pmb
import bpo.repo.staging
import bpo.repo.final


def run(branch):
    tasks = collections.OrderedDict()
    splitrepo = None  # FIXME

    # Configure pmbootstrap mirrors
    pmb_v2_mirrors_arg = ""
    if bpo.helpers.pmb.is_master(branch):
        tasks["set_repos"] = bpo.helpers.pmb.set_repos_task(None, branch, False)
    else:
        mirror_final = bpo.helpers.pmb.get_pmos_mirror(branch)
        pmb_v2_mirrors_arg += f" -mp {shlex.quote(mirror_final)}\\\n"

    branches = bpo.repo.staging.get_branches_with_staging()

    for arch in branches[branch]["arches"]:
        # Ignore missing repos before initial build (bpo#137)
        env_force_missing_repos = ""
        final_path = bpo.repo.final.get_path(arch, branch, splitrepo)
        if not os.path.exists(f"{final_path}/APKINDEX.tar.gz"):
            env_force_missing_repos = "export PMB_APK_FORCE_MISSING_REPOSITORIES=1"

        tasks[f"{branch}_{arch}"] = f"""
            export ARCH={shlex.quote(arch)}
            export JSON="depends.$ARCH.json"
            {env_force_missing_repos}

            # Enable systemd, so pmbootstrap doesn't omit the packages in
            # extra-repos/systemd. For repositories that don't have systemd,
            # this does not make a difference. An edge case is having packages
            # with the same name in both systemd and non-systemd repos, but
            # this is currently not supported (bpo#144).
            pmbootstrap config systemd always

            pmbootstrap \\
                {pmb_v2_mirrors_arg} \\
                --aports=$PWD/pmaports \\
                repo_missing --built --arch "$ARCH" \\
                > "$JSON"
            cat "$JSON"
            """

    tasks["submit"] = """
        export BPO_API_ENDPOINT="get-depends"
        export BPO_ARCH=""
        export BPO_BRANCH=""" + shlex.quote(branch) + """
        export BPO_DEVICE=""
        export BPO_PAYLOAD_FILES="$(ls -1 depends.*.json)"
        export BPO_PAYLOAD_FILES_PREVIOUS=""
        export BPO_PAYLOAD_IS_JSON="0"
        export BPO_PKGNAME=""
        export BPO_SPLITREPO=""
        export BPO_UI=""
        export BPO_VERSION=""

        exec build.postmarketos.org/helpers/submit.py
        """

    note = "Parse packages and dependencies from pmaports.git"
    bpo.helpers.job.run("get_depends", note, tasks, branch)
