"""
Shared enums for the CrimeGPT Case Object.

Keeping these centralized means every model, agent, and the frontend
(via generated TS types) reference the exact same set of allowed values.
"""

from enum import Enum


class CaseStatus(str, Enum):
    """Lifecycle stages a Case moves through."""

    CREATED = "created"
    EVIDENCE_ADDED = "evidence_added"
    ANALYSIS_RUNNING = "analysis_running"
    LEGAL_REVIEW = "legal_review"
    COMPLIANCE_REVIEW = "compliance_review"
    REPORT_GENERATED = "report_generated"
    CLOSED = "closed"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuspectStatus(str, Enum):
    UNKNOWN = "unknown"
    IDENTIFIED = "identified"
    DETAINED = "detained"
    ARRESTED = "arrested"


class EvidenceType(str, Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"
    DOCUMENT = "document"
    CCTV = "cctv"
    PHOTO = "photo"
    AUDIO = "audio"
    FORENSIC = "forensic"
    OTHER = "other"


class AdmissibilityStatus(str, Enum):
    PENDING = "pending"
    ADMISSIBLE = "admissible"
    QUESTIONABLE = "questionable"
    INADMISSIBLE = "inadmissible"


class GapCategory(str, Enum):
    MISSING_EVIDENCE = "missing_evidence"
    TIMELINE_CONTRADICTION = "timeline_contradiction"
    CHAIN_OF_CUSTODY = "chain_of_custody"
    MISSING_WITNESS = "missing_witness"
    PROCEDURAL_VIOLATION = "procedural_violation"
    LEGAL_DEFICIENCY = "legal_deficiency"
    DOCUMENTATION_GAP = "documentation_gap"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceCategory(str, Enum):
    PRIVACY = "privacy"
    ADMISSIBILITY = "admissibility"
    RIGHTS = "rights"
    BIAS = "bias"
    SOURCE_GROUNDING = "source_grounding"
    DOCUMENTATION = "documentation"


class ReportType(str, Enum):
    CASE_SUMMARY = "case_summary"
    INVESTIGATION_REPORT = "investigation_report"
    COURT_BRIEF = "court_brief"
    EVIDENCE_SUMMARY = "evidence_summary"
    EXECUTIVE_INTELLIGENCE_REPORT = "executive_intelligence_report"


class WorkflowStage(str, Enum):
    """
    Maps 1:1 to the LangGraph node sequence. Stored on the Case so the
    UI can show "where the AI currently is" and so re-runs can resume
    from a specific stage instead of starting over.
    """

    CASE_CREATED = "case_created"
    CASE_BUILDER = "case_builder"
    TIMELINE_BUILDER = "timeline_builder"
    EVIDENCE_INTELLIGENCE = "evidence_intelligence"
    GAP_DETECTION = "gap_detection"
    GAP_ENHANCEMENT = "gap_enhancement"
    LEGAL_INTELLIGENCE = "legal_intelligence"
    COMPLIANCE_REVIEW = "compliance_review"
    HEALTH_SCORING = "health_scoring"
    REPORT_GENERATION = "report_generation"
    DONE = "done"
