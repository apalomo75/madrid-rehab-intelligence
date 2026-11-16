"""Explicit, read-only runtime snapshot; no fallback to historical local data."""

from functools import lru_cache
import json
import os
from pathlib import Path

import pandas as pd

from .ingest import digest

VERSION = "public-runtime-v1"


def active():
    return bool(os.environ.get("MADRID_REHAB_BUNDLE_DIR"))


def root():
    return Path(os.environ["MADRID_REHAB_BUNDLE_DIR"]).resolve()


def key(path):
    path = Path(path)
    if path.is_absolute():
        try:
            path = path.relative_to(root())
        except ValueError:
            path = path.relative_to(Path(__file__).resolve().parents[2])
    if ".." in path.parts:
        raise ValueError("Invalid runtime path")
    return path.as_posix()


def resolve(path):
    return root() / key(path)


@lru_cache(maxsize=2)
def _layout(directory, manifest_stat):
    meta = json.loads((Path(directory) / "manifest.json").read_text())
    names = sorted(meta["files"])
    for name in names:
        path = Path(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not (Path(directory) / path).resolve().is_relative_to(Path(directory))
        ):
            raise ValueError("Invalid runtime manifest path")
    return names


def signature():
    directory = root()
    stat = (directory / "manifest.json").stat()
    manifest_stat = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    entries = []
    for name in _layout(str(directory), manifest_stat):
        info = (directory / name).stat()
        entries.append((name, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    return (str(directory), *manifest_stat, tuple(entries))


@lru_cache(maxsize=2)
def _verify(token):
    directory = Path(token[0])
    meta = json.loads((directory / "manifest.json").read_text())
    if meta["version"] != VERSION or meta["policy"]["prtr"] or not meta["policy"]["rehabilita"]:
        raise ValueError("Incompatible public runtime policy")
    for name, item in meta["files"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("Invalid runtime manifest path")
        if digest(directory / name) != item["sha256"]:
            raise ValueError("Runtime file integrity failure")
    return meta


def metadata():
    if os.environ.get("MADRID_REHAB_PUBLIC") != "1":
        raise ValueError("Production bundle requires explicit public mode")
    return _verify(signature())


def read(path, filters=None, columns=None):
    meta = metadata()
    name = key(path)
    if name not in meta["files"]:
        raise FileNotFoundError("Required runtime product unavailable")
    return pd.read_parquet(
        root() / name, filters=filters, columns=columns, pre_buffer=False, use_threads=False
    )


def catalogue():
    return root() / "catalogue"


def allowed_plan():
    return active() and metadata()["policy"]["rehabilita"]
