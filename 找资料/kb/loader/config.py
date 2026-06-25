"""
Central configuration for knowledge base file paths.

Override the KB root directory via the KB_ROOT_PATH environment variable:
    export KB_ROOT_PATH=/path/to/kb/data
"""

import os
from pathlib import Path


class KBConfig:
    """Central config for knowledge base file paths."""

    _DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data"

    # Allow override via environment variable
    KB_ROOT = Path(os.environ.get("KB_ROOT_PATH", str(_DEFAULT_ROOT)))

    # ---- Subdirectories ----
    DIR_POLICIES = KB_ROOT / "policies"
    DIR_BANKS = KB_ROOT / "banks"
    DIR_INDUSTRIES = KB_ROOT / "industries"
    DIR_CREDIT_TAX = KB_ROOT / "credit_tax"
    DIR_RISK_CONTROL = KB_ROOT / "risk_control"
    DIR_CASES = KB_ROOT / "cases"
    DIR_GOVERNANCE = KB_ROOT / "governance"

    # ---- Known files ----
    FILE_NATIONAL_POLICIES = DIR_POLICIES / "national_policies.csv"
    FILE_PROVINCIAL_POLICIES = DIR_POLICIES / "provincial_policies.csv"

    FILE_BANK_PRODUCTS = DIR_BANKS / "bank_products.json"
    FILE_BANK_REGIONAL = DIR_BANKS / "bank_regional_availability.csv"

    FILE_INDUSTRY_ACCEPTANCE = DIR_INDUSTRIES / "industry_acceptance.csv"
    FILE_REGIONAL_ADJUSTMENTS = DIR_INDUSTRIES / "regional_adjustments.csv"

    FILE_CREDIT_TOLERANCE = DIR_CREDIT_TAX / "credit_tolerance.csv"
    FILE_TAX_SCORING = DIR_CREDIT_TAX / "tax_level_scoring.csv"

    FILE_REJECTION_FACTORS = DIR_RISK_CONTROL / "rejection_factors.csv"
    FILE_SUBSIDY_POLICIES = DIR_RISK_CONTROL / "subsidy_policies.csv"
    FILE_MACRO_STATS = DIR_RISK_CONTROL / "macro_statistics.json"

    FILE_CASES_BASIC = DIR_CASES / "teaching_cases_basic.csv"
    FILE_CASES_ENHANCED = DIR_CASES / "teaching_cases_enhanced.csv"

    FILE_DATA_SOURCE_REGISTRY = DIR_GOVERNANCE / "data_source_registry.csv"
    FILE_DATA_SEMANTICS = DIR_GOVERNANCE / "data_semantics.md"
    FILE_FIELD_MAPPING = DIR_GOVERNANCE / "field_mapping_ml_kb.csv"

    # ---- Version file ----
    FILE_VERSION = KB_ROOT.parent / "VERSION"

    @classmethod
    def validate_paths(cls) -> list:
        """Check that all configured files exist. Returns list of missing paths."""
        missing = []
        for attr_name in dir(cls):
            if attr_name.startswith("FILE_"):
                path = getattr(cls, attr_name)
                if not path.exists():
                    missing.append(str(path))
        return missing
