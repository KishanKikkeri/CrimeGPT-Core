"""
Stage 5 agent function - Legal Intelligence.

Rule-based v1: a tiny in-memory "knowledge base" keyed by crime_type,
standing in for the real ChromaDB/Pinecone RAG retrieval described in
the architecture doc. Swap `_KNOWLEDGE_BASE` lookups for vector search
over the curated legal corpus - the contract (LegalOutput) doesn't
change.

`source_documents` already points at named KB entries, so once those
become real documents in the vector store, Provenance.derived_from
just starts pointing at real chunk IDs.
"""

from __future__ import annotations

from typing import Optional

from app.contracts.legal import LegalOutput
from app.models.case import Case

_KNOWLEDGE_BASE: dict[str, dict] = {
    "burglary": {
        "statutes": [
            "BNS Section 305 - House-breaking",
            "BNS Section 306 - House-breaking by night",
        ],
        "precedents": ["Illustrative precedent on forced-entry burglary cases"],
        "procedural_requirements": [
            "Document chain of custody for all physical evidence",
            "Record witness statements within 24 hours",
            "Photograph point of entry before processing",
        ],
        "source_documents": ["bns_burglary_2023.md", "crpc_evidence_handling.md"],
    },
    "theft": {
        "statutes": ["BNS Section 303 - Theft"],
        "precedents": ["Illustrative precedent on theft of movable property"],
        "procedural_requirements": [
            "Itemize and value all stolen property",
            "Record witness statements within 24 hours",
        ],
        "source_documents": ["bns_theft_2023.md"],
    },
    "assault": {
        "statutes": ["BNS Section 115 - Voluntarily causing hurt"],
        "precedents": ["Illustrative precedent on assault with injury documentation"],
        "procedural_requirements": [
            "Obtain medical examination report for injuries",
            "Record victim and witness statements separately",
        ],
        "source_documents": ["bns_hurt_2023.md"],
    },
}

_DEFAULT_ENTRY = {
    "statutes": [],
    "precedents": [],
    "procedural_requirements": [
        "Document chain of custody for all physical evidence",
        "Record witness statements within 24 hours",
    ],
    "source_documents": ["crpc_general_procedure.md"],
}


def run(case: Case, raw_input: Optional[str]) -> LegalOutput:
    key = (case.crime_type or "").strip().lower()
    entry = _KNOWLEDGE_BASE.get(key, _DEFAULT_ENTRY)

    confidence = 0.85 if key in _KNOWLEDGE_BASE else 0.4
    warnings = []
    if key not in _KNOWLEDGE_BASE:
        warnings.append(
            f"No knowledge-base entry for crime_type='{case.crime_type}' - "
            "returned general procedural requirements only."
        )

    return LegalOutput(
        confidence=confidence,
        statutes=list(entry["statutes"]),
        precedents=list(entry["precedents"]),
        procedural_requirements=list(entry["procedural_requirements"]),
        source_documents=list(entry["source_documents"]),
        warnings=warnings,
    )
