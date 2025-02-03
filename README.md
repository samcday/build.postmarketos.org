# bpo (build.postmarketos.org)

## Installation

NOTE: BPO needs [pmbootstrap](https://wiki.postmarketos.org/wiki/Pmbootstrap)
installed, which needs root rights to perform a lot of actions. Consider
setting up a virtual machine for running BPO and/or the BPO testsuite.

* Install [pmbootstrap](https://wiki.postmarketos.org/wiki/Pmbootstrap), e.g.
  by cloning the git repository (as sibling to the BPO git repo).
* Run `pmbootstrap init` and use all default settings
* Make sure `pmbootstrap` is in your `$PATH`
* Clone this repository and install dependencies into a venv:

```
$ git clone https://gitlab.postmarketos.org/postmarketOS/build.postmarketos.org
$ cd build.postmarketos.org
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

All commands below are intended to be executed in this venv.

## Running the testsuite

* Install test requirements in the venv:

```
$ pip install -r requirements-test.txt
```

* Run the testsuite, e.g.:

```
$ pytest --color=yes -vv -x test -m "not skip_ci"
```

* See `pytest -h` for additional option, e.g. `-k` to only run one test.

* Use `helpers/pytest_logs.sh` to see the detailed logs

## Running
## With local job service

NOTE: running BPO fully with a local job service isn't well supported, you will
run into strange issues. These days the local job service is just for running
the testsuite (see above).

```
$ ./bpo_local.sh
```

### With sourcehut job service

After creating a [sr.ht](https://meta.sr.ht/register) account and a dedicated
[personal access oauth token](https://meta.sr.ht/oauth):

```
$ cp bpo_sourcehut.example.sh bpo_sourcehut.sh
$ $EDITOR bpo_sourcehut.sh # adjust USER
$ ./bpo_sourcehut.sh
```

Running bpo for the first time will generate the `push_hook_gitlab` and
`job_callback` tokens, and display them once (and never again, only a hash is
stored). Copy the tokens and set them up as push hook token in gitlab, and
[create a secret](https://builds.sr.ht/secrets) in sourcehut for the
`job_callback` token (`/home/build/.token`).

Then edit the token file and add `sourcehut` (personal access oauth token) and
`job_callback_secret` (the secret ID that sourcehut generated for the
`job_callback` token).

```
$ EDITOR .tokens.cfg
```

Afterwards, generate the key that will be used to sign the final repo's
APKINDEX. The bpo code was created with privilege separation in mind. For
deploying a production setup, make sure to generate the key on a separate
machine (which will not run the bpo server).

```
$ openssl genrsa -out final.rsa 4096
$ openssl rsa -in final.rsa -pubout -out final.rsa.pub
```

For production setup, you need to place `final.rsa.pub` in pmbootstrap's
`pmb/data/keys` directory. Create a new secret in sourcehut, this time with the
contents of `final.rsa` and path `/home/build/.final.rsa`). Add the secret ID
as `final_sign_secret` to bpo's token file.

Finally start the bpo server again.

```
$ ./bpo_sourcehut.sh
```


### Running tests

Run all CI tests with:

```
$ pmbootstrap ci
```

While pytest is running, follow the logs (in a second terminal) with:
```
$ helpers/pytest_logs.sh
```

Open `_html_out/index.html` in your browser and refresh it manually to see the
current generated HTML output.

Run one specific pytest, after having `pmbootstrap ci pytest` initialize the
venv once:

```
$ source .venv/bin/activate
pytest -xvv test/test_zz_90_slow_other.py -k test_build_final_repo_with_two_pkgs_SLOW_120s
```

### Generating the images.postmarketos.org/bpo directory listing

BPO creates directory listing files whenever publishing an image, and it also
regenerates these files when restarting bpo (to update html files in case the
templates changed).

During development, test with:
```
$ test/manual/test_images_dir_gen.sh
$ test/manual/test_images_dir_host.sh
```

## Network Architecture

### Job service

Either [sourcehut](https://sourcehut.org/) or "local" for local development and
automated testing. The job service runs a shell script to perform a small task,
such as building a package or signing an index. Its purpose is to provide a
safe environment for running this task (where we feel comfortable placing our
signing keys), and to show a pretty log of the shell script (so we can easily
analyze what went wrong during a build). The result gets sent back to the bpo
server. The job services have access to the signing key for the packages and
APKINDEX that end up in the final repository, the bpo server does not.

### Bpo server

Runs the code in this git repository to orchestrate the package builds and
index signing with jobs running on a job service. It should also provide a web
interface, that shows the state of the repository, and links to the build logs
of the job service.

### Package mirror

The URL that one can add to their /etc/apk/repositories file, to make apk
download packages from there.

## Repositories

Instead of immediately publishing each single package after it has been built,
we wait until all packages from the last "push" (as in "git push") have been
built. One of such pushes can consist of multiple commits, and each commit may
change zero or more packages. The idea is, that we don't publish a half-baked
update, where for example, just half the packages of a framework are updated
and the other half isn't.

### WIP repo

This repository is hosted by (a separate webserver running on) the bpo server
and the build jobs running on the job service use it in order to build packages
from the same push that depend on each other. After each package is built, it
gets immediately added to the WIP repository. The WIP repository is indexed and
signed by the server that runs the bpo code, with the WIP repository key, that
is not the same as the final repository key.

### Symlink repo

Once all packages of a push are built, the bpo server creates a symlink
repository. As the name suggests, this consists of symlinks to the updated
packages from the WIP repo, and the existing packages (that were not updated or
deleted) from the final repo. The symlink repo is only used internally in the
bpo code, and not made available to the build jobs. It gets indexed (but not
signed!) by the bpo server. The generated APKINDEX then gets downloaded by a
job service, signed, and uploaded back to the bpo server.

With this architecture, we don't need to keep the signing key for the final
repository on the bpo server, and we don't need to download the entire
repository to a job running at a job service either.

### Final repo

After the index of the symlink repo is signed, the final repo gets updated to
reflect what is currently in the symlink repo. When that is done, it gets
published to the package mirror with rsync.

## FAQ

### Why are there no subdirs in the binary repository?

We have plenty of subdirs in pmaports.git (cross, device, main, ...). For
postmarketOS, it makes a lot of sense to keep the packages sorted that way. But
if we turn each of them into a subdir in the binary repository, we would need
to add a separate URL for them to the repositories list (/etc/apk/repositories)
as well, and apk and pmbootstrap would need to download an APKINDEX for each of
them. This makes the update process slower (especially for pmbootstrap, which
may download these index files for multiple architectures, depending on what
you are doing). So we just use one APKINDEX (per architecture and branch)
without the additional subdir.

### What to do if BPO missed that a sourcehut job failed or completed?

* Run the pmaports.git trigger from gitlab again, then the bpo server will
  re-calculate the missing packages and update the status of the jobs that are
  supposed to be running right now.
* If that does not help, run the build.postmarketos.org.git trigger again from
  gitlab, to restart the bpo server.

### How to trigger a sign_index job for development?

Run `test_build_final_repo_with_two_pkgs_SLOW_45s` to build a test repository
with two packages, then move one of the generated packages from the final repo
to the wip repo. When you start bpo with any job service (e.g. sourcehut), it
will detect, that the package is now in the wip repo, and attempt to finalize
the repository and sign it.

```
$ pytest -xvv test/test_zz_90_slow_other.py
$ mv _repo_final/master/x86_64/hello-world-wrapper-1-r2.apk _repo_wip/master/x86_64/
$ ./bpo_sourcehut.sh
```

### How to generate test pages from data/templates/images?

Run the following, the same directory structure as on
https://images.postmarketos.org/bpo/ will be in the `_images` dir (most
interestingly with the generated `index.html` files):

```
$ source .venv/bin/activate
$ pytest -xvv test/test_zz_70_build_image.py -k "test_build_image_stub"
```
