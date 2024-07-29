# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import shlex

import bpo.helpers.job
import bpo.helpers.pmb
import bpo.repo.staging


def run(branch):
    tasks = collections.OrderedDict()

    # Configure pmbootstrap mirrors
    pmb_v2_mirrors_arg = ""
    if bpo.helpers.pmb.is_master(branch):
        tasks["set_repos"] = bpo.helpers.pmb.set_repos_task(None, branch, False)
    else:
        mirror_final = bpo.helpers.job.get_pmos_mirror_for_pmbootstrap(branch)
        pmb_v2_mirrors_arg += f" -mp {shlex.quote(mirror_final)}\\\n"

    branches = bpo.repo.staging.get_branches_with_staging()

    for arch in branches[branch]["arches"]:
        tasks[f"{branch}_{arch}"] = f"""
            export ARCH={shlex.quote(arch)}
            export JSON="depends.$ARCH.json"

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
        export BPO_UI=""
        export BPO_VERSION=""

        exec build.postmarketos.org/helpers/submit.py
        """

    note = "Parse packages and dependencies from pmaports.git"
    bpo.helpers.job.run("get_depends", note, tasks, branch)
