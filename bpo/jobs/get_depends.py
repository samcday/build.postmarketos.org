# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

import collections
import shlex

import bpo.helpers.job
import bpo.repo.staging


def run(branch):
    tasks = collections.OrderedDict()

    mirror_final = bpo.helpers.job.get_pmos_mirror_for_pmbootstrap(branch)
    branches = bpo.repo.staging.get_branches_with_staging()

    for arch in branches[branch]["arches"]:
        tasks[branch + "_" + arch] = """
            export ARCH=""" + shlex.quote(arch) + """
            export JSON="depends.$ARCH.json"

            pmbootstrap \\
                --aports=$PWD/pmaports \\
                -mp """ + shlex.quote(mirror_final) + """ \\
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
