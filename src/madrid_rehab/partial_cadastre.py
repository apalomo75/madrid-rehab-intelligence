"""Ingesta parcial explícita del piloto: fuentes completas, selección y cuarentena separadas."""

import argparse
import hashlib
import json
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.parsers import expat
from xml.sax.saxutils import quoteattr

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely as sh

from .cadastre_download import MANIFEST, load_manifest
from .grants import DEFAULT as GRANTS
from .ingest import digest, save_json
from .municipal_boundaries import DEFAULT as BOUNDARIES
from .normalize import reference
from .pilot_grants import CONFIRMED, match_municipality
from .pilot_objects import audit_objects
from .regional import load_official_boundaries
from .sources import first_text, local_name, parse_buildings, parse_parcels
from .territorial_prtr import DEFAULT as TERRITORY

EVIDENCE = Path("data/processed/grants/regional/session_12_2_validation_real_01")
POLICY = "partial-quarantine-all-colliding-identities-v1"
GML_ID = "{http://www.opengis.net/gml/3.2}id"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def checksum(value):
    return hashlib.sha256(value).hexdigest()


def normalized_tree(node):
    """QName expandido, atributos ordenados, texto XML normalizado; sin perder hijos/atributos."""
    return [
        node.tag,
        sorted((k, " ".join(v.split())) for k, v in node.attrib.items()),
        " ".join((node.text or "").split()),
        [[normalized_tree(c), " ".join((c.tail or "").split())] for c in node],
    ]


def feature_fragments(data):
    """Offsets exactos en el GML original; no serializa ni altera los bytes conservados."""
    parser = expat.ParserCreate(namespace_separator="}")
    stack, ranges, namespaces = [], [], {}
    encoding = "utf-8"
    start = None
    start_is_empty = False
    start_namespaces = ()
    namespace_scopes = defaultdict(list)
    scope_cache = {}

    def declaration(version, name, standalone):
        nonlocal encoding
        encoding = name or "utf-8"

    def forbidden(*args):
        raise ValueError("DTD/entidades no permitidas")

    def opened(name, attrs):
        nonlocal start, start_is_empty, start_namespaces
        stack.append(name)
        if len(stack) == 3:
            if stack[-2].rsplit("}", 1)[-1] not in {"member", "featureMember"}:
                raise ValueError("Estructura fuera de miembros GML revisados")
            start = parser.CurrentByteIndex
            scope = tuple(sorted(namespaces.items()))
            start_namespaces = scope_cache.setdefault(scope, scope)
            quote = None
            cursor = start
            while cursor < len(data):
                char = data[cursor]
                if quote is not None:
                    if char == quote:
                        quote = None
                elif char in (34, 39):
                    quote = char
                elif char == 62:
                    break
                cursor += 1
            start_is_empty = data[start:cursor].rstrip().endswith(b"/")

    def closed(name):
        if len(stack) == 3:
            end = parser.CurrentByteIndex
            # En un elemento vacío Expat sitúa el evento después de '/>'.
            if not start_is_empty:
                if not data.startswith(b"</", end):
                    raise ValueError("No se localiza cierre de entidad")
                end = data.index(b">", end) + 1
            ranges.append((start, end, start_namespaces))
        stack.pop()

    def namespace_opened(prefix, uri):
        key = prefix or ""
        namespace_scopes[key].append(namespaces.get(key))
        if uri:
            namespaces[key] = uri
        else:
            namespaces.pop(key, None)

    def namespace_closed(prefix):
        key = prefix or ""
        previous = namespace_scopes[key].pop()
        if previous is None:
            namespaces.pop(key, None)
        else:
            namespaces[key] = previous

    parser.XmlDeclHandler = declaration
    parser.StartNamespaceDeclHandler = namespace_opened
    parser.EndNamespaceDeclHandler = namespace_closed
    parser.StartDoctypeDeclHandler = forbidden
    parser.EntityDeclHandler = forbidden
    parser.StartElementHandler = opened
    parser.EndElementHandler = closed
    parser.Parse(data, True)  # EOF y CRC se verifican durante la lectura de ingesta.
    wrappers = {}
    for ordinal, (begin, end, scope) in enumerate(ranges, 1):
        if scope not in wrappers:
            attrs = " ".join(
                ("xmlns:" + k if k else "xmlns") + "=" + quoteattr(v) for k, v in scope
            )
            wrappers[scope] = (
                f'<?xml version="1.0" encoding="{encoding}"?><records {attrs}>'.encode(encoding)
            )
        raw = data[begin:end]
        node = ET.fromstring(wrappers[scope] + raw + b"</records>")[0]
        yield ordinal, begin, end, raw, node


def parse_object(node, kind):
    typ = local_name(node.tag)
    if kind == "cp":
        if typ != "CadastralParcel":
            raise ValueError("Entidad inesperada en capa CP revisada")
        row = parse_parcels(ET.tostring(node))[0]
    else:
        if typ not in {"Building", "BuildingPart"}:
            raise ValueError("Entidad inesperada en capa BU revisada")
        if any(local_name(n.tag) in {"Building", "BuildingPart"} for c in node for n in c.iter()):
            raise ValueError("Esquema BU anidado no autorizado por esta ingesta parcial")
        isolated = ET.Element("Building", node.attrib)
        isolated.extend(node)
        row = parse_buildings(ET.tostring(isolated))[0]
    inspire = next((n for n in node if local_name(n.tag) == "inspireId"), None)
    namespace = first_text(inspire, "namespace") if inspire is not None else None
    namespace = namespace.strip() if namespace else None
    local_id = first_text(inspire, "localId") if inspire is not None else None
    local_id = local_id.strip() if local_id else None
    row.update(
        source_feature_type=typ,
        inspire_namespace=namespace,
        inspire_local_id=local_id,
        inspire_version=first_text(inspire, "versionId") if inspire is not None else None,
        inspire_key=encoded([namespace, local_id]) if namespace and local_id else None,
        lifespan_begin=first_text(node, "beginLifespanVersion"),
        lifespan_end=first_text(node, "endLifespanVersion"),
        area_value=first_text(node, "areaValue"),
        gml_ids=encoded([n.get(GML_ID) for n in node.iter() if n.get(GML_ID)]),
        normalized_sha256=checksum(encoded(normalized_tree(node)).encode()),
    )
    return row


def identity_reasons(frame, kind):
    """Cuarentena de TODAS las ocurrencias, sin escoger primera/última ni fusionar geometrías."""
    reasons = [set() for _ in range(len(frame))]
    keys = ["parcel_id" if kind == "cp" else "building_id", "inspire_key"]
    if kind == "cp":
        keys.append("parcel_ref14")
    for key in keys:
        missing = frame[key].isna() | frame[key].astype("string").str.strip().eq("").fillna(True)
        duplicated = frame[key].notna() & frame[key].duplicated(keep=False)
        for i in frame.index[missing]:
            reasons[i].add("missing_" + key)
        for i in frame.index[duplicated]:
            reasons[i].add("collision_" + key)
    ids = defaultdict(list)
    for i, value in enumerate(frame.gml_ids):
        for ident in json.loads(value):
            ids[ident].append(i)
    for occurrences in ids.values():
        if len(occurrences) > 1:
            for i in occurrences:
                reasons[i].add("collision_gml_id")
    return reasons


def select_objects(frame, kind, boundary, code):
    frame = frame.copy().reset_index(drop=True)
    # Se contrasta también la clave normalizada usada por el matcher.
    frame["reference_original"] = frame.parcel_ref14
    frame["parcel_ref14"] = frame.parcel_ref14.map(lambda v: reference(v)["parcel_ref14"])
    identity = identity_reasons(frame, kind)
    audited, issues = audit_objects(frame, kind, boundary)
    reasons = []
    for i, row in enumerate(audited.itertuples()):
        flags = identity[i]
        if not row.geometry_valid:
            flags.add("geometry_unusable")
        if row.boundary_status != "inside":
            flags.add("municipal_" + row.boundary_status)
        reasons.append(";".join(sorted(flags)))
    audited["selection_reason"] = reasons
    audited["selection_status"] = audited.selection_reason.map(
        lambda r: "quarantined" if r else "accepted"
    )
    audited["usable_geometry"] = audited.selection_status.eq("accepted")
    audited["municipality_assignment_verified"] = audited.usable_geometry
    audited["source_municipality_code"] = code
    audited["municipality_code"] = audited.usable_geometry.map(lambda ok: code if ok else None)
    audited["coverage_status"] = "partial_validated"
    audited["selection_policy"] = POLICY
    return audited


def compare_groups(frame, kind):
    """Compara contenido completo y geometría, sin interpretar fechas como vigencia."""
    key = "parcel_id" if kind == "cp" else "building_id"
    comparisons = []
    for ident, group in frame.groupby(key, dropna=False):
        if len(group) < 2:
            continue
        shapes = sh.from_wkt(group.geometry_wkt.to_numpy(), on_invalid="ignore")
        geometric_difference = any(
            a is None or shapes[0] is None or not sh.equals(shapes[0], a) for a in shapes[1:]
        )
        differences = {
            col: group[col].nunique(dropna=False) > 1
            for col in [
                "inspire_key",
                "parcel_ref14",
                "area_value",
                "lifespan_begin",
                "lifespan_end",
                "inspire_version",
            ]
        }
        comparisons.append(
            dict(
                source_id=ident,
                occurrences=len(group),
                distinct_normalized_contents=group.normalized_sha256.nunique(),
                exact_duplicate_only=group.normalized_sha256.nunique() == 1,
                geometry_different=geometric_difference,
                date_difference=any(
                    differences[c] for c in ["lifespan_begin", "lifespan_end", "inspire_version"]
                ),
                field_differences=differences,
                interpretation="unresolved_identity_collision_no_version_selected",
                records=group[
                    [
                        "source_record_id",
                        "source_gml_member",
                        "source_ordinal",
                        "source_xml_sha256",
                        "normalized_sha256",
                        "inspire_key",
                        "parcel_ref14",
                        "area_value",
                        "lifespan_begin",
                        "lifespan_end",
                        "geometry_wkt",
                    ]
                ].to_dict("records"),
            )
        )
    return comparisons


def ingest_layer(path, kind, directory, boundary, code, evidence):
    """Cada objeto tiene bytes originales, hashes, posición y una decisión conservada."""
    rows = []
    xml_path = directory / (kind + "_source_records.parquet")
    schema = pa.schema(
        [
            ("source_record_id", pa.string()),
            ("source_zip_sha256", pa.string()),
            ("source_gml_member", pa.string()),
            ("source_ordinal", pa.int64()),
            ("source_byte_start", pa.int64()),
            ("source_byte_end", pa.int64()),
            ("source_xml", pa.binary()),
            ("source_xml_sha256", pa.string()),
            ("normalized_sha256", pa.string()),
        ]
    )
    archive_sha = evidence["sha256"]
    expected = {r["name"]: r for r in evidence["members"]}
    with (
        pq.ParquetWriter(xml_path, schema, compression="zstd") as writer,
        zipfile.ZipFile(path) as archive,
    ):
        layers = [
            n
            for n in archive.namelist()
            if n.lower().endswith(
                ("cadastralparcel.gml",) if kind == "cp" else ("building.gml", "buildingpart.gml")
            )
        ]
        if len(layers) != (1 if kind == "cp" else 2):
            raise ValueError("Capas distintas de las previamente revisadas")
        for name in layers:
            counts, batch = Counter(), []
            data = archive.read(name)
            for ordinal, begin, end, raw, node in feature_fragments(data):
                row = parse_object(node, kind)
                counts[node.tag] += 1
                locator = checksum(encoded([archive_sha, name, ordinal]).encode())
                source = dict(
                    source_record_id=locator,
                    source_zip_sha256=archive_sha,
                    source_gml_member=name,
                    source_ordinal=ordinal,
                    source_byte_start=begin,
                    source_byte_end=end,
                    source_xml=raw,
                    source_xml_sha256=checksum(raw),
                    normalized_sha256=row["normalized_sha256"],
                )
                batch.append(source)
                rows.append({**row, **{k: v for k, v in source.items() if k != "source_xml"}})
                if len(batch) == 1000:
                    writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                    batch.clear()
            if batch:
                writer.write_table(pa.Table.from_pylist(batch, schema=schema))
            if dict(counts) != expected[name]["entities"]:
                raise ValueError("Recuento observado distinto de la evidencia congelada")
            del data
    frame = select_objects(pd.DataFrame(rows), kind, boundary, code)
    comparisons = compare_groups(frame, kind)
    frame.to_parquet(directory / (kind + "_all.parquet"), index=False)
    accepted = frame[frame.selection_status.eq("accepted")]
    rejected = frame[frame.selection_status.eq("quarantined")]
    accepted.to_parquet(directory / (kind + ".parquet"), index=False)
    rejected.to_parquet(directory / (kind + "_quarantine.parquet"), index=False)
    # Ninguna fila desaparece de la vista sin una decisión explícita de cuarentena.
    assert len(accepted) + len(rejected) == len(frame)
    save_json(directory / (kind + "_comparisons.json"), comparisons)
    return frame, dict(
        observed=len(frame),
        accepted=len(accepted),
        quarantined=len(rejected),
        accepted_types=accepted.source_feature_type.value_counts().to_dict(),
        quarantine_reasons=rejected.selection_reason.value_counts().to_dict(),
        collision_groups=len(comparisons),
    )


def load_evidence(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    name = "collection_inventory.json"
    if digest(root / name) != manifest["outputs"][name]:
        raise ValueError("Evidencia anterior alterada")
    inventory = json.loads((root / name).read_text())
    for r in inventory:
        if r["zip_integrity"] != "verified" or r["xml_integrity"] != "verified":
            raise ValueError("Se requiere evidencia previa de ZIP/XML completos")
        if digest(r["path"]) != r["sha256"] or manifest["inputs"][r["path"]] != r["sha256"]:
            raise ValueError("Fuente distinta de la previamente validada")
    return {(r["municipality_code"], r["kind"]): r for r in inventory}


def run(output, evidence_dir=EVIDENCE):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Usar un snapshot nuevo")
    evidence = load_evidence(evidence_dir)
    plan = load_manifest(MANIFEST)
    boundaries = load_official_boundaries(
        BOUNDARIES / "municipality_boundaries.parquet", BOUNDARIES / "manifest.json"
    ).set_index("municipality_code")
    for root, manifest_name in [
        (TERRITORY, "manifest.json"),
        (GRANTS, "grant_source_manifest.json"),
    ]:
        m = json.loads((root / manifest_name).read_text())
        if any(digest(root / n) != h for n, h in m["outputs"].items()):
            raise ValueError("Fuente PRTR/territorial alterada")
    decisions = pd.read_parquet(TERRITORY / "grant_municipality_links.parquet")
    baseline = pd.read_parquet(TERRITORY / "grant_parcel_links.parquet")
    grants = (
        pd.read_parquet(GRANTS / "grants.parquet")
        .drop(columns="municipality_code")
        .merge(
            decisions[["expediente_id", "municipality_code"]],
            on="expediente_id",
            validate="one_to_one",
        )
    )
    if len(grants) != 7532 or int(grants.importe_centimos.sum()) != 31552733899:
        raise ValueError("Contabilidad PRTR no reconciliada")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".partial-cadastre-") as temp:
        stage = Path(temp) / "snapshot"
        stage.mkdir()
        summaries, new_links, candidates = [], [], []
        codes = list(dict.fromkeys(r["municipality_code"] for r in plan["resources"]))
        for code in codes:
            folder = stage / code
            folder.mkdir()
            summary = dict(municipality_code=code, coverage_status="partial_validated")
            boundary = sh.from_wkt(boundaries.loc[code].geometry_wkt)
            # BU se acepta por su propia identidad/geometría/límite, sin depender de CP.
            for kind in ["bu", "cp"]:
                e = evidence[(code, kind)]
                frame, quality = ingest_layer(Path(e["path"]), kind, folder, boundary, code, e)
                summary[kind] = quality
                if kind == "cp":
                    selected = grants[grants.municipality_code.eq(code)]
                    refs = baseline[baseline.expediente_id.isin(selected.expediente_id)][
                        ["expediente_id", "parcel_ref14"]
                    ]
                    # Incluye toda la cuarentena para que nunca se lave una ambigüedad por filtrado.
                    links, spatial = match_municipality(selected, refs, frame, code)
                    new_links.append(links)
                    candidates.append(spatial)
                    confirmed = set(links.loc[links.match_status.isin(CONFIRMED), "expediente_id"])
                    summary.update(
                        prtr=len(selected),
                        prtr_confirmed=len(confirmed),
                        prtr_pending=len(selected) - len(confirmed),
                        ambiguous_relations=int(links.match_status.eq("ambiguous").sum()),
                        candidate_relations=len(spatial),
                    )
            # Cabeceras y capas auxiliares quedan visibles; no se declara completitud.
            save_json(
                folder / "source_inventory.json", {k: evidence[(code, k)] for k in ["cp", "bu"]}
            )
            save_json(
                folder / "manifest.json",
                dict(
                    version="partial-cadastre-v1",
                    policy=POLICY,
                    validation_status="partial_validated",
                    independent_bu=True,
                    cp_bu_relations_created=False,
                    quality=summary,
                    inputs={
                        evidence[(code, k)]["path"]: evidence[(code, k)]["sha256"]
                        for k in ["cp", "bu"]
                    },
                    outputs={p.name: digest(p) for p in folder.iterdir() if p.is_file()},
                ),
            )
            summaries.append(summary)
            print(encoded(summary), flush=True)
        excluded = set(grants.loc[grants.municipality_code.isin(codes), "expediente_id"])
        links = pd.concat(
            [baseline[~baseline.expediente_id.isin(excluded)], *new_links], ignore_index=True
        )
        links["geographic_municipality_code"] = links.expediente_id.map(
            decisions.set_index("expediente_id").municipality_code
        )
        links.to_parquet(stage / "grant_parcel_links.parquet", index=False)
        pd.concat(candidates, ignore_index=True).to_parquet(
            stage / "grant_spatial_candidates.parquet", index=False
        )
        (stage / "grant_municipality_links.parquet").write_bytes(
            (TERRITORY / "grant_municipality_links.parquet").read_bytes()
        )
        save_json(stage / "summary.json", summaries)
        save_json(
            stage / "manifest.json",
            dict(
                version="partial-cadastre-v1",
                policy=POLICY,
                validation_status="partial_validated",
                coverage="observed_objects_only_unknown_source_omissions",
                active_pointer_created=False,
                independent_bu=True,
                cp_bu_relations_created=False,
                regional_grants=len(grants),
                regional_amount_cents=int(grants.importe_centimos.sum()),
                inputs={
                    str(Path(evidence_dir) / "manifest.json"): digest(
                        Path(evidence_dir) / "manifest.json"
                    ),
                    str(BOUNDARIES / "manifest.json"): digest(BOUNDARIES / "manifest.json"),
                    str(TERRITORY / "manifest.json"): digest(TERRITORY / "manifest.json"),
                    str(GRANTS / "grant_source_manifest.json"): digest(
                        GRANTS / "grant_source_manifest.json"
                    ),
                    **{r["path"]: r["sha256"] for r in evidence.values()},
                },
                code_sha256={str(Path(__file__)): digest(__file__)},
                outputs={
                    str(p.relative_to(stage)): digest(p) for p in stage.rglob("*") if p.is_file()
                },
            ),
        )
        stage.rename(output)
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_dir, args.evidence_dir)


if __name__ == "__main__":
    main()
