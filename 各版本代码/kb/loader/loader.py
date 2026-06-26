"""
KnowledgeBase — unified loader for all knowledge base data files.

Lazy-loads each domain on first access. Caches results in memory.
Normalizes field names between the KB JSON schema and the existing
codebase conventions (e.g., min_interest_rate -> min_rate).

Usage:
    kb = KnowledgeBase()
    banks = kb.banks               # list of 28 bank product dicts
    tax = kb.tax_scoring           # {'A': 5.0, 'B': 4.0, ...}
    df = kb.industry_acceptance    # pandas DataFrame
"""

import json as _json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pandas import DataFrame

try:
    from .config import KBConfig
except ImportError:
    from config import KBConfig  # type: ignore[no-redef]


class KnowledgeBase:
    """
    Unified knowledge base loader.

    Each data domain is exposed as a @property that lazy-loads and caches
    on first access. Field names are normalized at load time for backward
    compatibility with existing code that uses legacy field names.
    """

    def __init__(self, kb_root: Optional[str] = None):
        """
        Args:
            kb_root: Path to kb/data/ directory. Overrides KB_ROOT_PATH env var.
                     Defaults to the data/ directory sibling to this loader.
        """
        if kb_root is not None:
            KBConfig.KB_ROOT = Path(kb_root)
        self._cache: Dict[str, Any] = {}
        self._version: Optional[str] = None
        self._load_errors: List[str] = []

    # ================================================================
    # Version
    # ================================================================

    @property
    def version(self) -> str:
        """Returns the KB version string from VERSION file."""
        if self._version is None:
            vf = KBConfig.FILE_VERSION
            if vf.exists():
                self._version = vf.read_text(encoding="utf-8-sig").strip()
            else:
                self._version = "unknown"
        return self._version

    @property
    def load_errors(self) -> List[str]:
        """Errors encountered during loading (empty list if all OK)."""
        return list(self._load_errors)

    # ================================================================
    # Banks
    # ================================================================

    @property
    def banks(self) -> List[Dict[str, Any]]:
        """
        Returns list of 28 bank product dicts with normalized field names.

        Normalized fields added for backward compatibility:
        - min_rate / max_rate (maps from min_interest_rate / max_interest_rate)
        - estimated_base_approval (maps from estimated_approval_rate)
        - requires_collateral_strict (derived from requirements)
        - tax_friendly (derived from tax_level_required presence)
        - collateral_weight / cashflow_weight / credit_weight / tax_weight
          (extracted from nested preferences dict)
        """
        if "banks" not in self._cache:
            try:
                raw = self._read_json(KBConfig.FILE_BANK_PRODUCTS)
                raw_banks = raw.get("banks", raw) if isinstance(raw, dict) else raw
                for b in raw_banks:
                    self._normalize_bank(b)
                self._cache["banks"] = raw_banks
            except Exception as e:
                self._load_errors.append(f"banks: {e}")
                self._cache["banks"] = []
        return self._cache["banks"]

    @staticmethod
    def _normalize_bank(b: dict) -> None:
        """Normalize field names in-place for backward compatibility."""
        # Field name mappings
        _map = {
            "min_interest_rate": "min_rate",
            "max_interest_rate": "max_rate",
            "estimated_approval_rate": "estimated_base_approval",
            "max_term_years": "max_term_years",
            "product_name": "product_name",
        }
        for kb_key, code_key in _map.items():
            if kb_key in b and code_key not in b:
                b[code_key] = b.pop(kb_key)

        # Extract nested preferences
        prefs = b.get("preferences", {})
        for w in ["collateral_weight", "cashflow_weight", "credit_weight", "tax_weight"]:
            if w not in b:
                b[w] = prefs.get(w, 0.25)

        # Extract min_business_years from requirements if absent at top level
        if "min_business_years" not in b:
            b["min_business_years"] = b.get("requirements", {}).get(
                "min_business_years", 1
            )

        # Derive requires_collateral_strict from rejection_sensitivity
        if "requires_collateral_strict" not in b:
            sens = b.get("rejection_sensitivity", {})
            b["requires_collateral_strict"] = sens.get("no_collateral") == "high"

        # Derive tax_friendly from requirements.tax_level_required
        if "tax_friendly" not in b:
            tax_req = b.get("requirements", {}).get("tax_level_required", [])
            b["tax_friendly"] = isinstance(tax_req, list) and len(tax_req) > 0

    @property
    def bank_regional_availability(self) -> DataFrame:
        """Returns DataFrame of bank regional coverage (30 rows)."""
        if "bank_regional" not in self._cache:
            try:
                self._cache["bank_regional"] = pd.read_csv(
                    KBConfig.FILE_BANK_REGIONAL, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"bank_regional: {e}")
                self._cache["bank_regional"] = DataFrame()
        return self._cache["bank_regional"]

    # ================================================================
    # Industries
    # ================================================================

    @property
    def industry_acceptance(self) -> DataFrame:
        """DataFrame with cols: 行业代码, 行业名称, 准入等级, 接受度系数, 说明"""
        if "industry_acceptance" not in self._cache:
            try:
                self._cache["industry_acceptance"] = pd.read_csv(
                    KBConfig.FILE_INDUSTRY_ACCEPTANCE, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"industry_acceptance: {e}")
                self._cache["industry_acceptance"] = DataFrame()
        return self._cache["industry_acceptance"]

    @property
    def regional_adjustments(self) -> DataFrame:
        """DataFrame with cols: 行业代码, 行业名称, 地域, 调整系数, 调整说明"""
        if "regional_adjustments" not in self._cache:
            try:
                self._cache["regional_adjustments"] = pd.read_csv(
                    KBConfig.FILE_REGIONAL_ADJUSTMENTS, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"regional_adjustments: {e}")
                self._cache["regional_adjustments"] = DataFrame()
        return self._cache["regional_adjustments"]

    # ================================================================
    # Credit & Tax
    # ================================================================

    @property
    def credit_tolerance(self) -> DataFrame:
        """DataFrame with cols: 银行层级, 逾期容忍度_近2年, ..."""
        if "credit_tolerance" not in self._cache:
            try:
                self._cache["credit_tolerance"] = pd.read_csv(
                    KBConfig.FILE_CREDIT_TOLERANCE, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"credit_tolerance: {e}")
                self._cache["credit_tolerance"] = DataFrame()
        return self._cache["credit_tolerance"]

    @property
    def tax_scoring(self) -> Dict[str, float]:
        """Returns dict: {'A': 5.0, 'B': 4.0, 'M': 3.0, 'C': 2.0, 'D': 1.0}"""
        if "tax_scoring" not in self._cache:
            try:
                df = pd.read_csv(KBConfig.FILE_TAX_SCORING, encoding="utf-8-sig")
                self._cache["tax_scoring"] = dict(
                    zip(df["纳税等级"].astype(str), df["评分值"].astype(float))
                )
            except Exception as e:
                self._load_errors.append(f"tax_scoring: {e}")
                self._cache["tax_scoring"] = {"A": 5, "B": 4, "M": 3, "C": 2, "D": 1}
        return self._cache["tax_scoring"]

    # ================================================================
    # Risk Control
    # ================================================================

    @property
    def rejection_factors(self) -> DataFrame:
        """DataFrame with cols: 被拒因子, 估计占比_pct, 严重程度, Agent诊断用途"""
        if "rejection_factors" not in self._cache:
            try:
                self._cache["rejection_factors"] = pd.read_csv(
                    KBConfig.FILE_REJECTION_FACTORS, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"rejection_factors: {e}")
                self._cache["rejection_factors"] = DataFrame()
        return self._cache["rejection_factors"]

    @property
    def subsidy_policies(self) -> DataFrame:
        """DataFrame with cols: 政策类别, 适用对象, 补贴内容, 额度上限_万元, ..."""
        if "subsidy_policies" not in self._cache:
            try:
                self._cache["subsidy_policies"] = pd.read_csv(
                    KBConfig.FILE_SUBSIDY_POLICIES, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"subsidy_policies: {e}")
                self._cache["subsidy_policies"] = DataFrame()
        return self._cache["subsidy_policies"]

    @property
    def macro_statistics(self) -> Dict[str, Any]:
        """Returns macro statistics dict."""
        if "macro_stats" not in self._cache:
            try:
                self._cache["macro_stats"] = self._read_json(KBConfig.FILE_MACRO_STATS)
            except Exception as e:
                self._load_errors.append(f"macro_stats: {e}")
                self._cache["macro_stats"] = {}
        return self._cache["macro_stats"]

    # ================================================================
    # Policies
    # ================================================================

    @property
    def national_policies(self) -> DataFrame:
        """18 national policy rules."""
        if "national_policies" not in self._cache:
            try:
                self._cache["national_policies"] = pd.read_csv(
                    KBConfig.FILE_NATIONAL_POLICIES, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"national_policies: {e}")
                self._cache["national_policies"] = DataFrame()
        return self._cache["national_policies"]

    @property
    def provincial_policies(self) -> DataFrame:
        """24 provincial policy rules."""
        if "provincial_policies" not in self._cache:
            try:
                self._cache["provincial_policies"] = pd.read_csv(
                    KBConfig.FILE_PROVINCIAL_POLICIES, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"provincial_policies: {e}")
                self._cache["provincial_policies"] = DataFrame()
        return self._cache["provincial_policies"]

    # ================================================================
    # Teaching Cases
    # ================================================================

    @property
    def teaching_cases_basic(self) -> DataFrame:
        """30 basic teaching cases."""
        if "cases_basic" not in self._cache:
            try:
                self._cache["cases_basic"] = pd.read_csv(
                    KBConfig.FILE_CASES_BASIC, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"cases_basic: {e}")
                self._cache["cases_basic"] = DataFrame()
        return self._cache["cases_basic"]

    @property
    def teaching_cases_enhanced(self) -> DataFrame:
        """20 enhanced teaching cases with diagnosis_chain."""
        if "cases_enhanced" not in self._cache:
            try:
                self._cache["cases_enhanced"] = pd.read_csv(
                    KBConfig.FILE_CASES_ENHANCED, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"cases_enhanced: {e}")
                self._cache["cases_enhanced"] = DataFrame()
        return self._cache["cases_enhanced"]

    # ================================================================
    # Governance
    # ================================================================

    @property
    def field_mapping(self) -> DataFrame:
        """35-row field mapping table (input -> ML -> KB)."""
        if "field_mapping" not in self._cache:
            try:
                self._cache["field_mapping"] = pd.read_csv(
                    KBConfig.FILE_FIELD_MAPPING, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"field_mapping: {e}")
                self._cache["field_mapping"] = DataFrame()
        return self._cache["field_mapping"]

    @property
    def data_source_registry(self) -> DataFrame:
        """Data source registry."""
        if "data_sources" not in self._cache:
            try:
                self._cache["data_sources"] = pd.read_csv(
                    KBConfig.FILE_DATA_SOURCE_REGISTRY, encoding="utf-8-sig"
                )
            except Exception as e:
                self._load_errors.append(f"data_sources: {e}")
                self._cache["data_sources"] = DataFrame()
        return self._cache["data_sources"]

    # ================================================================
    # Utility
    # ================================================================

    @staticmethod
    def _read_json(path: Path) -> Any:
        """Read a JSON file, trying UTF-8 first then UTF-16."""
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return _json.load(f)
        except (UnicodeDecodeError, _json.JSONDecodeError):
            with open(path, "r", encoding="utf-16") as f:
                return _json.load(f)

    def clear_cache(self) -> None:
        """Clear all cached data. Forces reload on next access."""
        self._cache.clear()
        self._version = None
        self._load_errors.clear()

    def health_check(self) -> Dict[str, Any]:
        """Run a health check on all data files. Returns status dict."""
        result = {
            "kb_version": self.version,
            "kb_root": str(KBConfig.KB_ROOT),
            "files_checked": 0,
            "files_ok": 0,
            "files_missing": [],
            "data_stats": {},
            "load_errors": [],
        }
        checks = [
            ("banks", self.banks, len),
            ("industry_acceptance", self.industry_acceptance, len),
            ("regional_adjustments", self.regional_adjustments, len),
            ("credit_tolerance", self.credit_tolerance, len),
            ("tax_scoring", self.tax_scoring, len),
            ("rejection_factors", self.rejection_factors, len),
            ("subsidy_policies", self.subsidy_policies, len),
            ("macro_statistics", self.macro_statistics, len),
            ("national_policies", self.national_policies, len),
            ("provincial_policies", self.provincial_policies, len),
            ("teaching_cases_basic", self.teaching_cases_basic, len),
            ("teaching_cases_enhanced", self.teaching_cases_enhanced, len),
            ("field_mapping", self.field_mapping, len),
        ]
        for name, data, fn in checks:
            result["files_checked"] += 1
            try:
                count = fn(data)
                result["files_ok"] += 1
                result["data_stats"][name] = count
            except Exception:
                result["files_missing"].append(name)

        result["load_errors"] = self.load_errors
        return result
