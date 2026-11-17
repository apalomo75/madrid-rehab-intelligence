"""Optional bounded HTTPS delivery of a pinned runtime archive, never an upload."""

from functools import lru_cache
import hashlib
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import threading
import urllib.request

LIMIT = 2 * 1024**3
_DELIVERY_LOCK = threading.Lock()


def unpack(archive, target):
    target = Path(target)
    if target.exists():
        raise FileExistsError("Runtime target already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="runtime-", dir=target.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        with tarfile.open(archive, "r:*") as handle:
            members = handle.getmembers()
            if sum(m.size for m in members) > LIMIT:
                raise ValueError("Runtime unpacked size exceeds limit")
            names = set()
            for member in members:
                name = Path(member.name)
                if (
                    name.is_absolute()
                    or ".." in name.parts
                    or not member.isfile()
                    or member.name in names
                ):
                    raise ValueError("Unsafe runtime archive member")
                names.add(member.name)
                destination = staging / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = handle.extractfile(member)
                if source is None:
                    raise ValueError("Missing archive content")
                with source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output)
        if not (staging / "manifest.json").is_file():
            raise ValueError("Archive has no runtime manifest")
        staging.rename(target)


@lru_cache(maxsize=1)
def _download(url, sha256, target):
    if (
        not url.startswith("https://")
        or len(sha256) != 64
        or any(c not in "0123456789abcdef" for c in sha256)
    ):
        raise ValueError("Runtime requires HTTPS and a pinned SHA-256")
    # Existing immutable snapshots are verified by production_bundle.metadata at every run.
    if Path(target).exists():
        marker = Path(target) / ".delivery_sha256"
        if not marker.is_file() or marker.read_text().strip() != sha256:
            raise ValueError("Immutable runtime delivery differs; choose a new target")
        return
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "runtime.tar.gz"
        checksum = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(url, timeout=60) as response, archive.open("xb") as output:
            if not response.geturl().startswith("https://"):
                raise ValueError("Insecure runtime redirect")
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > LIMIT:
                    raise ValueError("Runtime download exceeds limit")
                checksum.update(block)
                output.write(block)
        if checksum.hexdigest() != sha256:
            raise ValueError("Runtime archive integrity failure")
        unpack(archive, target)
        (Path(target) / ".delivery_sha256").write_text(sha256 + "\n")


def ensure():
    url = os.environ.get("MADRID_REHAB_BUNDLE_URL")
    if not url:
        return
    if os.environ.get("MADRID_REHAB_PUBLIC") != "1":
        raise ValueError("Runtime delivery requires public mode")
    target = os.environ.get("MADRID_REHAB_BUNDLE_DIR", "data/deployment/cloud_v1")
    with _DELIVERY_LOCK:
        _download(url, os.environ.get("MADRID_REHAB_BUNDLE_SHA256", ""), target)
        os.environ["MADRID_REHAB_BUNDLE_DIR"] = target


def pack(directory, output):
    """Create a deterministic delivery artifact outside the immutable bundle."""
    import gzip

    directory, output = Path(directory).resolve(), Path(output)
    manifest = directory / "manifest.json"
    if manifest.exists():
        import json
        from .public_prtr import validate_release

        meta = json.loads(manifest.read_text())
        if meta.get("policy", {}).get("prtr"):
            validate_release(meta)
    if output.resolve().is_relative_to(directory):
        raise ValueError("Archive must be outside the runtime directory")
    with (
        output.open("xb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive,
    ):
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Runtime symlinks are not supported")
            if path.is_file():
                info = archive.gettarinfo(path, arcname=path.relative_to(directory).as_posix())
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                with path.open("rb") as data:
                    archive.addfile(info, data)
    with output.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("pack")
    build.add_argument("--bundle-dir", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--bundle-dir", type=Path, required=True)
    args = parser.parse_args()
    from . import production_bundle as bundle

    os.environ["MADRID_REHAB_PUBLIC"] = "1"
    os.environ["MADRID_REHAB_BUNDLE_DIR"] = str(args.bundle_dir)
    meta = bundle.metadata()
    result = dict(files=len(meta["files"]), version=meta["version"], verified=True)
    if args.command == "pack":
        result.update(
            archive=str(args.output),
            sha256=pack(args.bundle_dir, args.output),
            bytes=args.output.stat().st_size,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
