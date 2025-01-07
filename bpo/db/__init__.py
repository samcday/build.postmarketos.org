# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Database code, using sqlalchemy ORM.

Usage example:

    session = bpo.db.session()
    log = bpo.db.Log(action="db_init", details="hello world")
    session.add(logled)
    session.commit()
"""

import datetime
import enum
import sys
import json
import logging

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import sqlalchemy.sql
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, \
    Table, Index, Enum
from sqlalchemy.orm import relationship

import bpo.config.args
import bpo.db.migrate
import bpo.repo.staging


base = sqlalchemy.ext.declarative.declarative_base()
session = None
engine = None
init_relationships_complete = False


class PackageStatus(enum.Enum):
    queued = 0
    building = 1
    built = 2
    published = 3
    failed = 4


class Package(base):
    __tablename__ = "package"

    # === DATABASE LAYOUT, DO NOT CHANGE! (read docs/db.md) ===
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True),
                  server_default=sqlalchemy.sql.func.now())
    last_update = Column(DateTime(timezone=True),
                         onupdate=sqlalchemy.sql.func.now())
    arch = Column(String)
    branch = Column(String)
    pkgname = Column(String)
    status = Column(Enum(PackageStatus))
    job_id = Column(Integer)
    retry_count = Column(Integer, default=0, system=True)  # [v4]
    splitrepo = Column(String, system=True)  # [v9]

    # The following columns represent the latest state. We don't store the
    # history in bpo (avoids complexity, we have the git history for that).
    version = Column(String)
    repo = Column(String)  # Use splitrepo instead!
    # Package.depends: see init_relationships() below.

    # This index has been dropped in [v10], as having this unique is
    # incompatible with splitrepo and bpo#144.
    Index("pkgname-arch-branch", pkgname, arch, branch, unique=True)

    Index("job_id", job_id)
    # [v01]: Index("arch-branch", Package.arch, Package.branch)
    # [v03]: Index("status", Package.status)
    # [v10]: Index("arch-branch-splitrepo", Package.arch, Package.branch, Package.splitrepo)
    # === END OF DATABASE LAYOUT ===

    def __init__(self, arch, branch, pkgname, version,
                 status=PackageStatus.queued):
        self.arch = arch
        self.branch = branch
        self.pkgname = pkgname
        self.version = version
        self.status = status

    def __repr__(self):
        depends = []
        for depend in self.depends:
            depends.append(depend.pkgname)
        return "{}/{}/{}-{}.apk (pmOS depends: {}, retry_count: {}," \
               " job_id: {})" \
               .format(self.branch, self.arch, self.pkgname, self.version,
                       depends, self.retry_count, self.job_id)

    def depends_built(self):
        for depend in self.depends:
            if depend.status not in [PackageStatus.built,
                                     PackageStatus.published]:
                return False
        return True

    def depends_missing_list(self):
        ret = []
        for depend in self.depends:
            if depend.status not in [PackageStatus.built,
                                     PackageStatus.published]:
                ret += [depend]
        return ret


class Log(base):
    __tablename__ = "log"

    # === DATABASE LAYOUT, DO NOT CHANGE! (read docs/db.md) ===
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True),
                  server_default=sqlalchemy.sql.func.now())
    action = Column(String)
    payload = Column(Text)
    arch = Column(String)
    branch = Column(String)
    pkgname = Column(String)
    version = Column(String)
    job_id = Column(Integer)
    commit = Column(String, system=True)  # [v2]
    retry_count = Column(Integer, default=0, system=True)  # [v5]
    device = Column(String, system=True)  # [v6]
    ui = Column(String, system=True)  # [v6]
    dir_name = Column(String, system=True)  # [v6]
    depend_pkgname = Column(String, system=True)  # [v7]
    count = Column(Integer, default=0, system=True)  # [v8]
    # === END OF DATABASE LAYOUT ===

    def __init__(self, action, payload=None, arch=None, branch=None,
                 pkgname=None, version=None, job_id=None, retry_count=None,
                 device=None, ui=None, dir_name=None, depend_pkgname=None,
                 commit=None, count=None):
        self.action = action
        self.payload = json.dumps(payload, indent=4) if payload else None
        self.arch = arch
        self.branch = branch
        self.pkgname = pkgname
        self.version = version
        self.job_id = job_id
        self.retry_count = retry_count
        self.device = device
        self.ui = ui
        self.dir_name = dir_name
        self.depend_pkgname = depend_pkgname
        self.commit = commit
        self.count = count
        logging.info("### " + str(self) + " ###")

    def __repr__(self):
        ret = self.action
        if self.branch:
            ret += " " + self.branch + "/"
        if self.arch:
            ret += self.arch + "/"
        if self.pkgname:
            ret += self.pkgname
            if self.version:
                ret += "-" + self.version
        if self.job_id:
            ret += ", job: " + str(self.job_id)
        if self.device:
            ret += f", device: {self.device}"
        if self.ui:
            ret += f", ui: {self.ui}"
        if self.dir_name:
            ret += f", dir: {self.dir_name}"
        if self.depend_pkgname:
            ret += f", depend_pkgname: {self.depend_pkgname}"
        return ret


class ImageStatus(enum.Enum):
    # Same as PackageStatus, except that "built" is missing. Unlike packages,
    # we don't need to hold images back at the "built" stage until other
    # packages from the same commit are built. However, we could use the
    # "built" stage in the future if we decide to sign the OS images with a
    # separate job that would have the sign keys available. Right now, the
    # images are not signed, but a checksum is generated at the end of the
    # build job for manual verification (build log is on sourcehut builds).
    queued = 0
    building = 1
    published = 3
    failed = 4


class Image(base):
    __tablename__ = "image"

    # === DATABASE LAYOUT, DO NOT CHANGE! (read docs/db.md) ===
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True),
                  server_default=sqlalchemy.sql.func.now())
    last_update = Column(DateTime(timezone=True),
                         onupdate=sqlalchemy.sql.func.now())
    device = Column(String)
    branch = Column(String)
    ui = Column(String)
    status = Column(Enum(ImageStatus))
    job_id = Column(Integer)
    dir_name = Column(String)
    retry_count = Column(Integer, default=0)

    Index("image:branch-device-ui", branch, device, ui)
    Index("image:status", status)
    Index("image:date", status)
    # === END OF DATABASE LAYOUT ===

    def __init__(self, device, branch, ui):
        self.device = device
        self.branch = branch
        self.ui = ui
        self.status = ImageStatus.queued

    def __repr__(self):
        ret = f"({self.id}){self.branch}:{self.device}:{self.ui}"
        if self.job_id:
            ret += f", job: {self.job_id}"
        if self.dir_name:
            ret += f", dir: {self.dir_name}"
        return ret


class RepoBootstrapStatus(enum.Enum):
    queued = 0     # waiting for build slot
    building = 1   # "pmbootstrap repo_bootstrap" is running right now
    built = 2      # packages have been built and uploaded
    published = 3  # repository has been published with repo_bootstrap pkgs
    failed = 4     # the job failed at least once


class RepoBootstrap(base):
    __tablename__ = "repo_bootstrap"

    # === DATABASE LAYOUT, DO NOT CHANGE! (read docs/db.md) ===
    id = Column(Integer, primary_key=True)
    dir_name = Column(String)
    arch = Column(String)
    branch = Column(String)
    status = Column(Enum(RepoBootstrapStatus))
    job_id = Column(Integer, unique=True)
    retry_count = Column(Integer, default=0)

    Index("rb:dir-arch-branch", dir_name, arch, branch, unique=True)
    Index("rb:status", status)
    # === END OF DATABASE LAYOUT ===

    def __init__(self, arch, branch, dir_name=None):
        self.arch = arch
        self.branch = branch
        self.dir_name = dir_name
        self.status = RepoBootstrapStatus.queued

    def __repr__(self):
        return (f"repo_bootstrap: {self.branch}/{self.arch}"
                f" (dir_name={self.dir_name}, retry_count={self.retry_count},"
                f" job_id={self.job_id}")


def init_relationships():
    # Only run this once!
    self = sys.modules[__name__]
    if self.init_relationships_complete:
        return
    self.init_relationships_complete = True

    # === DATABASE LAYOUT, DO NOT CHANGE! (read docs/db.md) ===
    # package.depends - n:n - package.required_by
    # See "Self-Referential Many-to-Many Relationship" in:
    # https://docs.sqlalchemy.org/en/13/orm/join_conditions.html
    assoc = Table("package_dependency", base.metadata,
                  Column("package_id", ForeignKey("package.id"),
                         primary_key=True),
                  Column("dependency_id", ForeignKey("package.id"),
                         primary_key=True))
    primaryjoin = self.Package.id == assoc.c.package_id
    secondaryjoin = self.Package.id == assoc.c.dependency_id
    self.Package.depends = relationship("Package", secondary=assoc,
                                        primaryjoin=primaryjoin,
                                        secondaryjoin=secondaryjoin,
                                        order_by=self.Package.id,
                                        backref="required_by")
    # === END OF DATABASE LAYOUT ===


def init():
    """ Initialize db """
    # Disable check_same_thread, so pysqlite does not print ProgrammingError
    # junk when running the tests with pytest. SQLAlchemy uses pooling to make
    # sure that a single connection is not used in more than one thread, so we
    # can safely disable this check.
    # https://docs.sqlalchemy.org/en/latest/dialects/sqlite.html
    connect_args = {"check_same_thread": False}

    self = sys.modules[__name__]
    url = "sqlite:///" + bpo.config.args.db_path

    # Open database, upgrade, close, open again
    for before_upgrade in [True, False]:
        self.engine = sqlalchemy.create_engine(url, connect_args=connect_args)
        init_relationships()
        self.base.metadata.create_all(engine)
        self.session = sqlalchemy.orm.sessionmaker(bind=engine)
        if before_upgrade:
            bpo.db.migrate.upgrade()
            self.engine.dispose()


def validate_job_id(db_result, job_id):
    """ :param db_result: either None or a db object with job_id param
                          (Package, Image)
        :param job_id: either None or the job ID passed from an API call, that
                       the job service (sourcehut, local) assigned to the job
        :returns: True if the job_id matches,
                  False if either db_result or job_id are None
    """
    if not db_result or job_id is None:
        return False

    if not job_id.isdecimal():
        raise ValueError(f"validate_job_id: invalid: {job_id}")

    job_id_db = db_result[0].job_id
    if job_id_db != int(job_id):
        raise ValueError(f"validate_job_id: got {job_id} instead of"
                         f" {job_id_db}")

    return True


def get_package(session, pkgname, arch, branch, job_id=None):
    result = session.query(bpo.db.Package).filter_by(arch=arch,
                                                     branch=branch,
                                                     pkgname=pkgname).all()
    validate_job_id(result, job_id)
    return result[0] if len(result) else None


def get_image(session, branch, device, ui, job_id=None):
    """ Get a branch:device:ui specific image, that is currently being
        processed (status is not finished). Unlike packages, we keep more than
        just the latest entry in the database. """
    result = session.query(bpo.db.Image).\
        filter_by(branch=branch, device=device, ui=ui).\
        filter(bpo.db.Image.status != bpo.db.ImageStatus.published).\
        all()
    validate_job_id(result, job_id)
    return result[0] if len(result) else None


def get_repo_bootstrap(session, arch, branch, dir_name="/", job_id=None):
    result = session.query(bpo.db.RepoBootstrap).\
        filter_by(arch=arch, branch=branch, dir_name=dir_name).\
        all()
    validate_job_id(result, job_id)
    return result[0] if len(result) else None


def get_recent_packages_by_status(session):
    """ :returns: a dict like this (pkglist is a list of bpo.db.Package objects):

    {"queued": pkglist1, "building": pkglist2,
        "built": pkglist3, "published": pkglist4, "failed": pkglist5, "built_synced": {"master_staging_test": {"x86_64": 5, "aarch64": 3}},
        "published_synced": {...}}  # same format as built_synced

    """
    all_branches = bpo.repo.staging.get_branches_with_staging().keys()

    # Add package list for each status
    ret = {}
    for status in bpo.db.PackageStatus:
        ret[status.name] = session.query(bpo.db.Package).\
            filter_by(status=status).\
            filter(bpo.db.Package.branch.in_(all_branches)).\
            order_by(bpo.db.Package.branch,
                     bpo.db.Package.arch,
                     bpo.db.Package.pkgname).all()

    # Add synced counts
    for status in ["built", "published"]:
        sync_str = f"{status}_synced"
        if sync_str in ret:
            raise RuntimeError(f"{sync_str} must not be in {ret}")

        ret[sync_str] = {}
        for pkg in ret[status]:
            if pkg.job_id:
                continue
            arch = pkg.arch
            branch = pkg.branch
            if branch not in ret[sync_str]:
                ret[sync_str][branch] = {}
            if arch in ret[sync_str][branch]:
                ret[sync_str][branch][arch] += 1
            else:
                ret[sync_str][branch][arch] = 1

    # For repo_bootstrap. before it is in built state, bpo can't display which
    # packages are part of the repo_bootstrap. Add a fake package for it to the
    # UI.
    rb_all = session.query(RepoBootstrap).\
             filter(RepoBootstrap.status != RepoBootstrapStatus.published).\
             filter(RepoBootstrap.status != RepoBootstrapStatus.built).\
             filter(RepoBootstrap.branch.in_(all_branches)).\
             order_by(RepoBootstrap.branch,
                      RepoBootstrap.arch)
    for rb in rb_all:
        status = rb.status.name
        if status not in ret:
            ret[status] = []
        fake_pkg = Package(rb.arch, rb.branch, "[repo_bootstrap]", "")
        fake_pkg.retry_count = rb.retry_count
        fake_pkg.job_id = rb.job_id
        ret[status] += [fake_pkg]

    return ret


def get_recent_images_by_status(session):
    """ :returns: {"failed": imglist1, "building": imglist2, ...}, imglist is a list of bpo.db.Image objects

    """
    ret = {}

    # Don't list images older than 10 weeks
    date_min = datetime.datetime.now() - datetime.timedelta(weeks=10)

    for status in bpo.db.ImageStatus:
        ret[status.name] = session.query(bpo.db.Image).\
            filter_by(status=status).\
            filter(bpo.db.Image.date >= date_min).\
            filter(bpo.db.Image.branch.in_(bpo.config.const.branches.keys())).\
            order_by(bpo.db.Image.date.desc())
    return ret


def get_failed_packages_count_relevant(session):
    """ :returns: count of failed packages, without the branches where ignore_errors is set

    (it's always set for staging branches,
    and usually for branches we build for the first time as we prepare a new release).


    """
    relevant = []
    for branch, branch_data in bpo.config.const.branches.items():
        if not branch_data.get("ignore_errors"):
            relevant += [branch]

    return session.query(bpo.db.Package).\
        filter_by(status=bpo.db.PackageStatus.failed).\
        filter(bpo.db.Package.branch.in_(relevant)).count()


def set_package_status(session, package, status, job_id=None):
    """ :param package: bpo.db.Package object
        :param status: bpo.db.PackageStatus value

    """
    package.status = status
    if job_id:
        package.job_id = job_id
    session.merge(package)
    session.commit()


def set_image_status(session, image, status, job_id=None, dir_name=None,
                     date=None):
    """ :param image: bpo.db.Image object
        :param status: bpo.db.ImageStatus value
        :param job_id: job ID (i.e. job number from sourcehut builds)
        :param dir_name: directory that holds the image files
        :param date: new date (once the image is built, the previous date from
                     when the image was queued gets updated to the date when
                     the image was published)

    """
    image.status = status
    if job_id:
        image.job_id = job_id
    if dir_name:
        image.dir_name = dir_name
    if date:
        image.date = date
    session.merge(image)
    session.commit()


def set_repo_bootstrap_status(session, rb, status, job_id=None):
    rb.status = status
    if job_id:
        rb.job_id = job_id
    session.merge(rb)
    session.commit()


def package_has_version(session, pkgname, arch, branch, version):
    count = session.query(bpo.db.Package).filter_by(arch=arch,
                                                    branch=branch,
                                                    pkgname=pkgname,
                                                    version=version).count()
    return True if count else False
