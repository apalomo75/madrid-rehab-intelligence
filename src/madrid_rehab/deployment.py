"""Read-only deployment preflight. Presence is never a publication authorization."""

import argparse
import json
from pathlib import Path

CATALOG = Path("data/processed/commercial_catalog/session_24_public_02")


def catalog_requirements(base, catalog=CATALOG):
    """Resolve authenticated catalogue dependencies without opening original sources."""
    base = Path(base).resolve()
    directory = base / catalog
    manifest = directory / "manifest.json"
    if not manifest.is_file():
        return [manifest]
    meta = json.loads(manifest.read_text())
    paths = {manifest}
    for name in meta["inputs"]:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Nonportable catalogue input")
        paths.add(base / path)
    for name in meta["outputs"]:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Nonportable catalogue output")
        paths.add(directory / path)
    return sorted(paths)


def preflight(base, catalog=CATALOG):
    """Check the catalogue's full startup dependency set, not all fiche dependencies."""
    base = Path(base).resolve()
    paths = catalog_requirements(base, catalog)
    missing = [str(p.relative_to(base)) for p in paths if not p.is_file()]
    return {
        "scope": "catalogue startup; fiche runtime inventory required separately",
        "publication_authorized": False,
        "catalogue_dependencies_present": not missing,
        "files": len(paths),
        "bytes_present": sum(p.stat().st_size for p in paths if p.is_file()),
        "missing": missing,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = preflight(args.base, args.catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    raise SystemExit(0 if result["catalogue_dependencies_present"] else 2)


if __name__ == "__main__":
    main()
