# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
""" Job service for builds.sr.ht, see: https://man.sr.ht/builds.sr.ht """

import logging
import os
import re
import requests
import shlex

import bpo.config.args
import bpo.config.const
import bpo.config.tokens
import bpo.db
import bpo.helpers.pmb
import bpo.repo.final
import bpo.repo.staging
from bpo.job_services.base import JobService


def api_request(query, variables):
    """Send a GraphQL request: https://docs.sourcehut.org/builds.sr.ht/"""
    url = "https://builds.sr.ht/query"
    headers = {"Authorization": "Bearer " + bpo.config.tokens.sourcehut}
    payload = {"query": query, "variables": variables}
    ret = requests.request("POST", url=url, headers=headers, json=payload)
    print("sourcehut response: " + ret.text)
    if not ret.ok:
        raise RuntimeError("sourcehut API request failed: " + url)
    return ret


def get_secrets_by_job_name(name):
    """ 
    Have some privilege separation by only enabling the secrets, that are
    required for particular job types. In practice, this allows having the
    final repo sign key only available when necessary.

    :param name: job name (see bpo/jobs, e.g. "sign_index")
    :returns: string like "secrets:<newline>- first<newline>- second<newline>" (<newline> is backslash-n)
    """
    tokens = bpo.config.tokens
    secrets = [tokens.job_callback_secret]

    if name == "sign_index":
        secrets.append(tokens.final_sign_secret)

    ret = "secrets:\n"
    for secret in secrets:
        ret += "- " + str(secret) + "\n"
    return ret


def sanitize_task_name(name):
    """ Replace characters that are not allowed in sr.ht task names """
    name = name.lower()
    return re.sub(r'[^a-z0-9_\-]+', '_', name)


def get_manifest(name, tasks, branch, splitrepo):
    url_api = bpo.config.args.url_api

    branches = bpo.repo.staging.get_branches_with_staging()
    pmb_branch = branches[branch].get("pmb_branch",
                                      bpo.config.const.pmb_branch_default)
    pmb_config = "pmbootstrap_v3.cfg" if pmb_branch == "master" else "pmbootstrap.cfg"
    arches = branches[branch]["arches"]

    final_path = bpo.repo.final.get_path(arches[0], branch, splitrepo)
    env_force_missing_repos = ""
    if not os.path.exists(f"{final_path}/APKINDEX.tar.gz"):
        env_force_missing_repos = "export PMB_APK_FORCE_MISSING_REPOSITORIES=1"

    ret = f"""
        image: alpine/latest
        packages:
        - coreutils
        - losetup
        - multipath-tools
        - procps
        - py3-requests
        - xz
        environment:
          BPO_TOKEN_FILE: "/home/build/.token"
          BPO_API_HOST: {shlex.quote(url_api)}
          BPO_JOB_NAME: {shlex.quote(name)}
          PMB_APK_NO_CACHE: 1
        {get_secrets_by_job_name(name)}
        triggers:
        - action: webhook
          condition: failure
          url: {url_api}/api/public/update-job-status
        tasks:
        - clone_sources: |
           git clone -q --depth=1 https://gitlab.postmarketos.org/postmarketOS/pmaports.git/ -b {shlex.quote(branch)} &
           git clone -q --depth=1 https://gitlab.postmarketos.org/postmarketOS/build.postmarketos.org.git/ &
           git clone -q --depth=1 https://gitlab.postmarketos.org/postmarketOS/pmbootstrap.git/ -b {shlex.quote(pmb_branch)} &
           wget -q https://gitlab.postmarketos.org/postmarketOS/pmaports/-/raw/master/channels.cfg &
           wait
           git -C pmaports show --oneline -s --color=always
           git -C pmbootstrap show --oneline -s --color=always
           git -C build.postmarketos.org show --oneline -s --color=always
           sha512sum channels.cfg
        - bpo_setup: |
           export BPO_JOB_ID="$JOB_ID"
           {env_force_missing_repos}

           # Configure pmbootstrap
           mkdir -p ~/.config
           ( echo "[pmbootstrap]"
             echo "is_default_channel = False"
             echo "[mirrors]"
             echo "pmaports = none"
             echo "systemd = none" ) > ~/.config/{pmb_config}

           # Hack for shallow pmaports clones, use PMB_CHANNELS_CFG after
           # https://gitlab.postmarketos.org/postmarketOS/pmbootstrap/-/merge_requests/2620
           # is merged
           ( echo "#!/bin/sh"
             echo 'if [ "$1 $2" = "show origin/master:channels.cfg" ]; then'
             echo "  cat $PWD/channels.cfg"
             echo "else"
             echo '  exec /usr/bin/git "$@"'
             echo "fi" ) | sudo tee /usr/local/bin/git
           sudo chmod +x /usr/local/bin/git

           sudo ln -s "$PWD"/pmbootstrap/pmbootstrap.py /usr/bin/pmbootstrap
           yes "" | pmbootstrap --aports=$PWD/pmaports -q init
           pmbootstrap config mirrors.pmaports -r
           pmbootstrap config mirrors.systemd -r
           sudo modprobe binfmt_misc
           sudo mount -t binfmt_misc none /proc/sys/fs/binfmt_misc

           branch="$(git -C pmaports rev-parse --abbrev-ref HEAD)"
           if [ "$branch" != {shlex.quote(branch)} ]; then
               echo "ERROR: pmbootstrap switched to the wrong branch: $branch"
               exit 1
           fi

           if [ "$(pmbootstrap config mirrors.pmaports)" = "none" ]; then
               echo "ERROR: pmbootstrap failed to reset mirrors.pmaports"
               exit 1
           fi

           if [ "$(pmbootstrap config mirrors.systemd)" = "none" ]; then
               echo "ERROR: pmbootstrap failed to reset mirrors.systemd"
               exit 1
           fi
    """

    ret = bpo.helpers.job.remove_additional_indent(ret, 8)[:-1]

    # Add tasks
    for name, script in tasks.items():
        script_indented = ("   export BPO_JOB_ID=\"$JOB_ID\"\n"
                           "   " + script[:-1].replace("\n", "\n   "))
        name = sanitize_task_name(name)
        ret += "\n- {}: |\n{}".format(name, script_indented)
    return ret


class SourcehutJobService(JobService):

    def run_job(self, name, note, tasks, branch, splitrepo):
        manifest = get_manifest(name, tasks, branch, splitrepo)
        print(manifest)
        result = api_request(
            """
            mutation SubmitBuild($manifest: String!,
                         $tags: [String!],
                         $note: String,
                         $secrets: Boolean,
                         $execute: Boolean,
                         $visibility: Visibility) {
                submit(manifest: $manifest,
                       tags: $tags,
                       note: $note,
                       secrets: $secrets,
                       execute: $execute,
                       visibility: $visibility) {
                    id
                }
            }
            """,
            {"manifest": manifest,
             "tags": [name],
             "note": note,
             "execute": True,
             "secrets": True,
             "visibility": "PUBLIC"},
        )
        job_id = result.json()["data"]["submit"]["id"]
        logging.info("Job started: " + self.get_link(job_id))
        return job_id

    def get_status(self, job_id):
        result = api_request(
            """
            query JobStatus($id: Int!) {
                job(id: $id) { status }
            }
            """,
            {"id": job_id},
        )
        status_str = result.json()["data"]["job"]["status"].lower()
        status = bpo.job_services.base.JobStatus[status_str]
        logging.info("=> status: " + status.name)
        return status

    def get_link(self, job_id):
        user = bpo.config.args.sourcehut_user
        return ("https://builds.sr.ht/~" + user + "/job/" + str(job_id))

    def init(self):
        bpo.config.tokens.require("sourcehut")
        bpo.config.tokens.require("job_callback_secret")
        bpo.config.tokens.require("final_sign_secret")
