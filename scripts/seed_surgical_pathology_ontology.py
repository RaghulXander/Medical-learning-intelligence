"""Seed the versioned Surgical Pathology ontology without publishing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.domain.surgical_pathology_ontology import (  # noqa: E402
    OntologyNodeStatus,
    OntologyNodeType,
    OntologySchemeStatus,
    SEED_PATH,
    load_surgical_pathology_seed,
)
from database.db import get_engine, init_db, session_scope  # noqa: E402
from database.models import (  # noqa: E402
    OntologyAlias,
    OntologyNode,
    OntologyScheme,
    VerificationStatus,
)


def _seed_hash(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def seed_surgical_pathology_ontology(engine, seed_path: Path = SEED_PATH) -> dict[str, Any]:
    """Create or update one draft ontology version and return a compact summary.

    Released versions are immutable. A later edit must use a new version string.
    The operation never removes nodes or aliases that are absent from the seed.
    """

    seed = load_surgical_pathology_seed(seed_path)
    scheme_data = seed["scheme"]
    current_hash = _seed_hash(seed)

    with session_scope(engine) as session:
        scheme = (
            session.query(OntologyScheme)
            .filter_by(code=scheme_data["code"], version=scheme_data["version"])
            .one_or_none()
        )
        created_scheme = scheme is None
        if scheme is None:
            scheme = OntologyScheme(
                code=scheme_data["code"],
                name=scheme_data["name"],
                version=scheme_data["version"],
                status=OntologySchemeStatus(scheme_data["status"]),
                description=scheme_data.get("description"),
                metadata_json={
                    "source_scope": scheme_data.get("source_scope", []),
                    "copyright_note": scheme_data.get("copyright_note"),
                    "seed_hash": current_hash,
                },
                created_by="m14_seed",
            )
            session.add(scheme)
            session.flush()
        else:
            stored_hash = (scheme.metadata_json or {}).get("seed_hash")
            if scheme.status is OntologySchemeStatus.RELEASED and stored_hash != current_hash:
                raise ValueError(
                    f"Ontology {scheme.code} {scheme.version} is released and immutable; "
                    "create a new version before changing its seed."
                )
            if scheme.status is not OntologySchemeStatus.RELEASED:
                scheme.name = scheme_data["name"]
                scheme.status = OntologySchemeStatus(scheme_data["status"])
                scheme.description = scheme_data.get("description")
                scheme.metadata_json = {
                    "source_scope": scheme_data.get("source_scope", []),
                    "copyright_note": scheme_data.get("copyright_note"),
                    "seed_hash": current_hash,
                }

        existing_nodes = {
            node.code: node
            for node in session.query(OntologyNode).filter_by(scheme_id=scheme.id).all()
        }
        created_nodes = 0
        for node_data in seed["nodes"]:
            node = existing_nodes.get(node_data["code"])
            if node is None:
                parent_code = node_data.get("parent_code")
                parent_id = existing_nodes[parent_code].id if parent_code else None
                node = OntologyNode(
                    scheme_id=scheme.id,
                    code=node_data["code"],
                    preferred_name=node_data["preferred_name"],
                    node_type=OntologyNodeType(node_data["node_type"]),
                    parent_id=parent_id,
                    display_order=node_data.get("display_order", 0),
                    status=OntologyNodeStatus(node_data.get("status", "DRAFT")),
                    metadata_json=node_data.get("metadata", {}),
                    created_by="m14_seed",
                )
                session.add(node)
                session.flush()
                existing_nodes[node.code] = node
                created_nodes += 1
            elif scheme.status is not OntologySchemeStatus.RELEASED:
                node.preferred_name = node_data["preferred_name"]
                node.node_type = OntologyNodeType(node_data["node_type"])
                node.display_order = node_data.get("display_order", 0)
                node.status = OntologyNodeStatus(node_data.get("status", "DRAFT"))
                node.metadata_json = node_data.get("metadata", {})

        for node_data in seed["nodes"]:
            node = existing_nodes[node_data["code"]]
            parent_code = node_data.get("parent_code")
            parent_id = existing_nodes[parent_code].id if parent_code else None
            if scheme.status is not OntologySchemeStatus.RELEASED or node.parent_id is None:
                node.parent_id = parent_id

        session.flush()
        created_aliases = 0
        for node_data in seed["nodes"]:
            node = existing_nodes[node_data["code"]]
            existing_aliases = {
                (alias.alias.casefold(), alias.language): alias for alias in node.aliases
            }
            for alias_data in node_data.get("aliases", []):
                alias_key = (alias_data["alias"].casefold(), alias_data.get("language", "en"))
                existing_alias = existing_aliases.get(alias_key)
                if existing_alias is not None:
                    if scheme.status is not OntologySchemeStatus.RELEASED:
                        existing_alias.alias_type = alias_data.get("alias_type", "SYNONYM")
                        existing_alias.source = alias_data.get("source")
                        existing_alias.verification_status = VerificationStatus(
                            alias_data.get("verification_status", "AI_SUGGESTED")
                        )
                    continue
                session.add(
                    OntologyAlias(
                        node_id=node.id,
                        alias=alias_data["alias"],
                        alias_type=alias_data.get("alias_type", "SYNONYM"),
                        language=alias_data.get("language", "en"),
                        source=alias_data.get("source"),
                        verification_status=VerificationStatus(
                            alias_data.get("verification_status", "AI_SUGGESTED")
                        ),
                    )
                )
                existing_aliases[alias_key] = None
                created_aliases += 1

        summary = {
            "scheme": scheme.code,
            "version": scheme.version,
            "status": scheme.status.value,
            "scheme_created": created_scheme,
            "nodes_total": len(existing_nodes),
            "nodes_created": created_nodes,
            "aliases_created": created_aliases,
            "seed_hash": current_hash,
        }

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    args = parser.parse_args()
    engine = get_engine()
    init_db(engine=engine)
    print(json.dumps(seed_surgical_pathology_ontology(engine, args.seed), indent=2))


if __name__ == "__main__":
    main()
