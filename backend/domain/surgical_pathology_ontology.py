"""Versioned Surgical Pathology ontology seed loading and validation.

The seed contains names and hierarchy only. It deliberately excludes textbook
prose, diagnostic assertions, images, and page-level evidence.
"""

from __future__ import annotations

import enum
import json
import re
from pathlib import Path
from typing import Any


class OntologySchemeStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class OntologyNodeStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class OntologyNodeType(str, enum.Enum):
    ROOT = "ROOT"
    DISCIPLINE = "DISCIPLINE"
    METHOD_GROUP = "METHOD_GROUP"
    METHOD = "METHOD"
    ANATOMIC_SYSTEM = "ANATOMIC_SYSTEM"
    ORGAN = "ORGAN"
    ANATOMIC_SITE = "ANATOMIC_SITE"
    DISEASE_FAMILY = "DISEASE_FAMILY"
    DIAGNOSTIC_ENTITY = "DIAGNOSTIC_ENTITY"
    MORPHOLOGIC_FEATURE = "MORPHOLOGIC_FEATURE"
    CLINICAL_FEATURE = "CLINICAL_FEATURE"
    GROSS_FEATURE = "GROSS_FEATURE"
    IHC_MARKER = "IHC_MARKER"
    MOLECULAR_ALTERATION = "MOLECULAR_ALTERATION"
    GRADING_SYSTEM = "GRADING_SYSTEM"
    STAGING_SYSTEM = "STAGING_SYSTEM"
    LEARNING_OBJECTIVE = "LEARNING_OBJECTIVE"


class OntologyRelationshipType(str, enum.Enum):
    IS_A = "IS_A"
    PART_OF = "PART_OF"
    LOCATED_IN = "LOCATED_IN"
    HAS_CLINICAL_FEATURE = "HAS_CLINICAL_FEATURE"
    HAS_GROSS_FEATURE = "HAS_GROSS_FEATURE"
    HAS_MICROSCOPIC_FEATURE = "HAS_MICROSCOPIC_FEATURE"
    EXPRESSES_MARKER = "EXPRESSES_MARKER"
    LACKS_MARKER = "LACKS_MARKER"
    HAS_MOLECULAR_ALTERATION = "HAS_MOLECULAR_ALTERATION"
    USES_GRADING_SYSTEM = "USES_GRADING_SYSTEM"
    USES_STAGING_SYSTEM = "USES_STAGING_SYSTEM"
    DIFFERENTIAL_OF = "DIFFERENTIAL_OF"
    MIMICS = "MIMICS"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    SUPERSEDES = "SUPERSEDES"


class OntologyMappingRole(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    DIFFERENTIAL = "DIFFERENTIAL"
    METHOD = "METHOD"


class OntologyMappingMethod(str, enum.Enum):
    RULE = "RULE"
    AI_SUGGESTED = "AI_SUGGESTED"
    HUMAN = "HUMAN"


SEED_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "ontology"
    / "surgical-pathology-2026.08-draft.1.json"
)

_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]*$")

_ALLOWED_PARENT_TYPES: dict[OntologyNodeType, set[OntologyNodeType]] = {
    OntologyNodeType.ROOT: set(),
    OntologyNodeType.DISCIPLINE: {OntologyNodeType.ROOT},
    OntologyNodeType.METHOD_GROUP: {
        OntologyNodeType.DISCIPLINE,
        OntologyNodeType.METHOD_GROUP,
    },
    OntologyNodeType.METHOD: {
        OntologyNodeType.METHOD_GROUP,
        OntologyNodeType.METHOD,
    },
    OntologyNodeType.ANATOMIC_SYSTEM: {
        OntologyNodeType.DISCIPLINE,
        OntologyNodeType.ANATOMIC_SYSTEM,
    },
    OntologyNodeType.ORGAN: {
        OntologyNodeType.DISCIPLINE,
        OntologyNodeType.ANATOMIC_SYSTEM,
        OntologyNodeType.ORGAN,
    },
    OntologyNodeType.ANATOMIC_SITE: {
        OntologyNodeType.ANATOMIC_SYSTEM,
        OntologyNodeType.ORGAN,
        OntologyNodeType.ANATOMIC_SITE,
    },
    OntologyNodeType.DISEASE_FAMILY: {
        OntologyNodeType.ANATOMIC_SYSTEM,
        OntologyNodeType.ORGAN,
        OntologyNodeType.ANATOMIC_SITE,
        OntologyNodeType.DISEASE_FAMILY,
        OntologyNodeType.METHOD_GROUP,
    },
    OntologyNodeType.DIAGNOSTIC_ENTITY: {
        OntologyNodeType.ANATOMIC_SYSTEM,
        OntologyNodeType.ORGAN,
        OntologyNodeType.ANATOMIC_SITE,
        OntologyNodeType.DISEASE_FAMILY,
    },
    OntologyNodeType.MORPHOLOGIC_FEATURE: {OntologyNodeType.METHOD_GROUP},
    OntologyNodeType.CLINICAL_FEATURE: {OntologyNodeType.METHOD_GROUP},
    OntologyNodeType.GROSS_FEATURE: {OntologyNodeType.METHOD_GROUP},
    OntologyNodeType.IHC_MARKER: {OntologyNodeType.METHOD_GROUP},
    OntologyNodeType.MOLECULAR_ALTERATION: {OntologyNodeType.METHOD_GROUP},
    OntologyNodeType.GRADING_SYSTEM: {OntologyNodeType.METHOD_GROUP},
    OntologyNodeType.STAGING_SYSTEM: {OntologyNodeType.METHOD_GROUP},
    OntologyNodeType.LEARNING_OBJECTIVE: {
        OntologyNodeType.METHOD,
        OntologyNodeType.DISEASE_FAMILY,
        OntologyNodeType.DIAGNOSTIC_ENTITY,
    },
}


class OntologySeedValidationError(ValueError):
    """Raised when a versioned ontology seed violates structural rules."""


def load_surgical_pathology_seed(path: Path = SEED_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as seed_file:
        seed = json.load(seed_file)
    validate_ontology_seed(seed)
    return seed


def validate_ontology_seed(seed: dict[str, Any]) -> None:
    """Validate codes, parent types, aliases, and cycles before persistence."""

    errors: list[str] = []
    scheme = seed.get("scheme") or {}
    try:
        OntologySchemeStatus(scheme.get("status"))
    except ValueError:
        errors.append("scheme.status is invalid")
    if not scheme.get("code") or not scheme.get("version"):
        errors.append("scheme.code and scheme.version are required")

    nodes = seed.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise OntologySeedValidationError("nodes must be a non-empty list")

    nodes_by_code: dict[str, dict[str, Any]] = {}
    for node in nodes:
        code = node.get("code")
        if not isinstance(code, str) or not _CODE_PATTERN.fullmatch(code):
            errors.append(f"invalid node code: {code!r}")
            continue
        if code in nodes_by_code:
            errors.append(f"duplicate node code: {code}")
        nodes_by_code[code] = node

    root_codes: list[str] = []
    for code, node in nodes_by_code.items():
        try:
            node_type = OntologyNodeType(node.get("node_type"))
        except ValueError:
            errors.append(f"{code}: invalid node_type")
            continue
        try:
            OntologyNodeStatus(node.get("status", "DRAFT"))
        except ValueError:
            errors.append(f"{code}: invalid status")

        parent_code = node.get("parent_code")
        if node_type is OntologyNodeType.ROOT:
            root_codes.append(code)
            if parent_code is not None:
                errors.append(f"{code}: ROOT cannot have a parent")
        elif not parent_code:
            errors.append(f"{code}: non-root node requires parent_code")
        elif parent_code not in nodes_by_code:
            errors.append(f"{code}: unknown parent {parent_code}")
        else:
            try:
                parent_type = OntologyNodeType(nodes_by_code[parent_code].get("node_type"))
            except ValueError:
                continue
            if parent_type not in _ALLOWED_PARENT_TYPES[node_type]:
                errors.append(
                    f"{code}: {node_type.value} cannot be below {parent_type.value}"
                )

        seen_aliases: set[str] = set()
        for alias in node.get("aliases", []):
            alias_text = alias.get("alias") if isinstance(alias, dict) else None
            normalized = " ".join(str(alias_text or "").casefold().split())
            if not normalized:
                errors.append(f"{code}: alias text is required")
            elif normalized in seen_aliases:
                errors.append(f"{code}: duplicate alias {alias_text!r}")
            seen_aliases.add(normalized)

    if len(root_codes) != 1:
        errors.append(f"expected exactly one ROOT node, found {len(root_codes)}")

    visit_state: dict[str, int] = {}

    def visit(code: str, path: list[str]) -> None:
        state = visit_state.get(code, 0)
        if state == 1:
            cycle_start = path.index(code) if code in path else 0
            errors.append("parent cycle: " + " -> ".join(path[cycle_start:] + [code]))
            return
        if state == 2:
            return
        visit_state[code] = 1
        parent_code = nodes_by_code[code].get("parent_code")
        if parent_code in nodes_by_code:
            visit(parent_code, path + [code])
        visit_state[code] = 2

    for node_code in nodes_by_code:
        visit(node_code, [])

    if errors:
        raise OntologySeedValidationError("; ".join(dict.fromkeys(errors)))
