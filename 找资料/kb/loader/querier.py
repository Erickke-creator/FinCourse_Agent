"""
KBQuery — query interface with automatic traceability recording.

Every query method records a KBSourceRecord so the evaluation result
can show exactly which knowledge base entries were used.

Usage:
    from kb_loader import KnowledgeBase, KBQuery

    kb = KnowledgeBase()
    query = KBQuery(kb)

    banks = query.get_all_banks()
    tax = query.get_tax_score("A")
    info = query.get_industry_acceptance("manufacturing")

    for src in query.get_accessed_sources():
        print(f"[{src.domain}] {src.file_name}: {src.description}")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    from .loader import KnowledgeBase
except ImportError:
    from loader import KnowledgeBase  # type: ignore[no-redef]


@dataclass
class KBSourceRecord:
    """Records a single knowledge base lookup for traceability reporting."""

    domain: str            # e.g., "banks", "industries", "credit_tax"
    file_name: str         # e.g., "bank_products.json"
    entry_identifier: str  # e.g., "icbc", "manufacturing", "RULE-001"
    field_accessed: str    # e.g., "min_rate", "接受度系数"
    value_returned: Any    # the actual value used (for debugging)
    description: str       # human-readable summary


class KBQuery:
    """
    Fluent query interface over KnowledgeBase.

    Every query method automatically records a KBSourceRecord to
    `_sources`, enabling full traceability of which knowledge base
    entries were consulted during an evaluation.
    """

    def __init__(self, kb: KnowledgeBase):
        self._kb = kb
        self._sources: List[KBSourceRecord] = []

    # ================================================================
    # Bank queries
    # ================================================================

    def get_all_banks(self) -> List[Dict[str, Any]]:
        """Return all 28 bank product records (with normalized fields)."""
        banks = self._kb.banks
        self._record(
            "banks", "bank_products.json", "all",
            "full_record",
            f"Loaded all {len(banks)} bank products",
            len(banks),
        )
        return banks

    def get_bank_by_id(self, bank_id: str) -> Optional[Dict[str, Any]]:
        """Look up a single bank by id (e.g. 'icbc', 'ccb')."""
        for b in self._kb.banks:
            if b.get("id") == bank_id:
                self._record(
                    "banks", "bank_products.json", bank_id,
                    "full_record",
                    f"Looked up bank: {b.get('name', bank_id)}",
                    b,
                )
                return b
        return None

    def get_banks_for_region(self, province: str) -> List[str]:
        """
        Returns list of bank names available in a given province.
        Matches on 全国 coverage or province name in 重点服务区域.
        """
        df = self._kb.bank_regional_availability
        if df.empty:
            self._record("banks", "bank_regional_availability.csv", province,
                         "银行名称", "No regional data loaded", [])
            return []

        short = province.replace("省", "").replace("市", "")
        mask = (
            df["覆盖范围"].str.contains("全国", na=False)
            | df["重点服务区域"].str.contains(short, na=False)
        )
        results = df[mask]["银行名称"].tolist()
        self._record(
            "banks", "bank_regional_availability.csv",
            f"province={province}", "银行名称",
            f"Found {len(results)} banks available in {province}",
            results,
        )
        return results

    # ================================================================
    # Industry queries
    # ================================================================

    def get_industry_acceptance(self, industry_code: str) -> Dict[str, Any]:
        """
        Returns acceptance info for an industry.
        Result keys: 行业代码, 行业名称, 准入等级, 接受度系数, 说明
        Falls back to 接受度系数=0.70 for unknown industries.
        """
        df = self._kb.industry_acceptance
        row = df[df["行业代码"] == industry_code] if not df.empty else pd.DataFrame()
        if row.empty:
            result = {"接受度系数": 0.70, "准入等级": "谨慎准入",
                      "说明": "未知行业，按谨慎准入处理"}
            self._record(
                "industries", "industry_acceptance.csv",
                f"fallback:{industry_code}", "接受度系数",
                f"Unknown industry '{industry_code}', using fallback coef=0.70",
                0.70,
            )
        else:
            result = row.iloc[0].to_dict()
            self._record(
                "industries", "industry_acceptance.csv",
                industry_code, "接受度系数",
                f"Industry {industry_code}: 准入等级={result.get('准入等级')}, "
                f"接受度系数={result.get('接受度系数')}",
                result.get("接受度系数"),
            )
        return result

    def get_regional_adjustment(self, industry_code: str, province: str) -> float:
        """
        Returns regional adjustment coefficient for an industry+province combo.
        Returns 1.0 (no adjustment) when no specific rule matches.
        """
        df = self._kb.regional_adjustments
        if df.empty:
            self._record("industries", "regional_adjustments.csv",
                         f"{industry_code}:{province}", "调整系数",
                         "No regional data, default=1.0", 1.0)
            return 1.0

        short = province.replace("省", "").replace("市", "")
        adj = df[
            (df["行业代码"] == industry_code)
            & (df["地域"].str.contains(short, na=False))
        ]
        if adj.empty:
            coef = 1.0
            self._record(
                "industries", "regional_adjustments.csv",
                f"{industry_code}:{province}", "调整系数",
                f"No specific adjustment for {industry_code} in {province}, default=1.0",
                coef,
            )
        else:
            coef = float(adj.iloc[0]["调整系数"])
            self._record(
                "industries", "regional_adjustments.csv",
                f"{industry_code}:{province}", "调整系数",
                f"Regional adjustment for {industry_code} in {province}: {coef}",
                coef,
            )
        return coef

    # ================================================================
    # Tax queries
    # ================================================================

    def get_tax_score(self, tax_level: str) -> float:
        """
        Returns numeric score for a tax level.
        Mapping: A=5, B=4, M=3, C=2, D=1
        """
        scores = self._kb.tax_scoring
        score = scores.get(tax_level, 3.0)
        self._record(
            "credit_tax", "tax_level_scoring.csv",
            tax_level, "评分值",
            f"Tax level '{tax_level}' -> score {score}",
            score,
        )
        return score

    # ================================================================
    # Credit tolerance queries
    # ================================================================

    def get_credit_tolerance(self, bank_type: str) -> Dict[str, Any]:
        """
        Returns credit tolerance for a bank type.
        Maps bank type strings to credit tolerance tiers.
        """
        tier_map = {
            "国有大型商业银行": "国有大行",
            "股份制商业银行": "股份制/中小银行",
            "城市商业银行": "股份制/中小银行",
            "农村商业银行": "股份制/中小银行",
            "互联网银行": "互联网银行",
            "外资银行": "外资银行",
        }
        tier = tier_map.get(bank_type, "股份制/中小银行")
        df = self._kb.credit_tolerance
        row = df[df["银行层级"] == tier] if not df.empty else pd.DataFrame()
        if row.empty:
            result = {}
        else:
            result = row.iloc[0].to_dict()

        self._record(
            "credit_tax", "credit_tolerance.csv",
            f"bank_type={bank_type} -> tier={tier}",
            "逾期容忍度_近2年",
            f"Credit tolerance for {bank_type} ({tier}): "
            f"{result.get('逾期容忍度_近2年', 'N/A')}",
            result.get("逾期容忍度_近2年"),
        )
        return result

    # ================================================================
    # Risk control queries
    # ================================================================

    def get_rejection_factors(self) -> List[Dict[str, Any]]:
        """Returns all 7 loan rejection factors with weights."""
        df = self._kb.rejection_factors
        result = df.to_dict(orient="records") if not df.empty else []
        self._record(
            "risk_control", "rejection_factors.csv", "all",
            "被拒因子",
            f"Loaded {len(result)} rejection factors",
            len(result),
        )
        return result

    def get_matching_subsidies(
        self,
        industry_code: str,
        is_tech: bool = False,
        is_agriculture: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Find subsidy/贴息 policies matching an enterprise profile.
        Matches on 适用对象 field based on industry and enterprise attributes.
        """
        df = self._kb.subsidy_policies
        if df.empty:
            self._record("risk_control", "subsidy_policies.csv",
                         f"industry={industry_code}", "政策类别",
                         "No subsidy data loaded", 0)
            return []

        matches = []
        for _, row in df.iterrows():
            rowd = row.to_dict()
            policy_target = str(rowd.get("适用对象", ""))
            policy_cat = str(rowd.get("政策类别", ""))
            matched = False

            if is_tech and any(
                t in policy_target
                for t in ["科技", "专精特新", "高新", "数字产业"]
            ):
                matched = True
            if is_agriculture and any(
                t in policy_target for t in ["三农", "农业", "涉农"]
            ):
                matched = True
            if industry_code in ["hospitality_food", "wholesale_retail"] and any(
                t in policy_target for t in ["餐饮", "零售", "文旅", "服务"]
            ):
                matched = True
            if industry_code == "manufacturing" and "制造业" in policy_target:
                matched = True

            if matched:
                matches.append(rowd)

        self._record(
            "risk_control", "subsidy_policies.csv",
            f"industry={industry_code},tech={is_tech},agri={is_agriculture}",
            "政策类别",
            f"Matched {len(matches)} subsidy policies",
            len(matches),
        )
        return matches

    # ================================================================
    # Policy queries
    # ================================================================

    def get_relevant_policies(
        self,
        keywords: Optional[List[str]] = None,
        province: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search national + provincial policies by keywords in
        rule_theme, agent_usage, and applicable_object fields.

        Args:
            keywords: List of Chinese keywords (e.g., ['制造业', '科创'])
            province: Province name to filter provincial policies
        """
        results: List[Dict[str, Any]] = []
        if keywords is None:
            keywords = []

        nat = self._kb.national_policies
        if not nat.empty:
            for kw in keywords:
                mask = (
                    nat["rule_theme"].str.contains(kw, na=False)
                    | nat["agent_usage"].str.contains(kw, na=False)
                    | nat["applicable_object"].str.contains(kw, na=False)
                )
                for _, row in nat[mask].iterrows():
                    d = row.to_dict()
                    d["scope"] = "national"
                    if d not in results:
                        results.append(d)

        if province:
            prov = self._kb.provincial_policies
            if not prov.empty:
                short = province.replace("省", "").replace("市", "")
                prov_mask = prov["province"].str.contains(short, na=False)
                for _, row in prov[prov_mask].iterrows():
                    d = row.to_dict()
                    d["scope"] = "provincial"
                    results.append(d)

                # Also match by keywords in provincial
                if keywords:
                    for kw in keywords:
                        kw_mask = (
                            prov["rule_theme"].str.contains(kw, na=False)
                            | prov["agent_usage"].str.contains(kw, na=False)
                        )
                        kw_match = prov[kw_mask & ~prov_mask]
                        for _, row in kw_match.iterrows():
                            d = row.to_dict()
                            d["scope"] = "provincial"
                            if d not in results:
                                results.append(d)

        self._record(
            "policies",
            "national_policies.csv + provincial_policies.csv",
            f"keywords={keywords},province={province}",
            "rule_theme",
            f"Found {len(results)} relevant policies",
            len(results),
        )
        return results

    # ================================================================
    # Macro statistics
    # ================================================================

    def get_macro_stats(self) -> Dict[str, Any]:
        """Returns macro statistics for report background."""
        stats = self._kb.macro_statistics
        self._record(
            "risk_control", "macro_statistics.json", "all",
            "普惠小微贷款余额_万亿元",
            f"普惠小微贷款余额: {stats.get('普惠小微贷款余额_万亿元', 'N/A')}万亿元",
            stats.get("普惠小微贷款余额_万亿元"),
        )
        return stats

    # ================================================================
    # Similar case matching
    # ================================================================

    def find_similar_cases(
        self,
        industry: Optional[str] = None,
        risk_signal: Optional[str] = None,
        case_type: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find similar teaching cases by industry, risk signal, or case type.

        Args:
            industry: Industry name (Chinese, e.g. '制造业')
            risk_signal: Risk keyword to match in risk_signal/result
            case_type: 'approved', 'rejected', 'overdue', 'default',
                       'guarantee_dispute', 'renewal', 'supply_chain'
            top_k: Max number of cases to return
        """
        df = self._kb.teaching_cases_enhanced
        if df.empty:
            self._record("cases", "teaching_cases_enhanced.csv", "all",
                         "case_id", "No case data loaded", [])
            return []

        # scoring based on matches
        scores = pd.Series(0.0, index=df.index)

        if industry:
            scores += df["industry"].str.contains(
                industry.replace("业", ""), na=False
            ).astype(float) * 3

        if case_type:
            scores += (df["case_type"] == case_type).astype(float) * 5

        if risk_signal:
            scores += df["risk_signal"].str.contains(
                risk_signal, na=False
            ).astype(float) * 2
            scores += df["result"].str.contains(
                risk_signal, na=False
            ).astype(float) * 2

        top_indices = scores.nlargest(min(top_k, len(df))).index
        result = [df.loc[i].to_dict() for i in top_indices if scores[i] > 0]

        self._record(
            "cases", "teaching_cases_enhanced.csv",
            f"industry={industry},type={case_type},risk={risk_signal}",
            "case_id",
            f"Found {len(result)} similar cases",
            [r.get("case_id") for r in result],
        )
        return result

    # ================================================================
    # Field mapping (for diagnostic purposes)
    # ================================================================

    def get_field_mapping(self, input_field: str) -> Optional[Dict[str, Any]]:
        """Look up a single input field's mapping to ML and KB."""
        df = self._kb.field_mapping
        if df.empty:
            return None
        row = df[df["输入字段"] == input_field]
        if row.empty:
            return None
        result = row.iloc[0].to_dict()
        self._record(
            "governance", "field_mapping_ml_kb.csv",
            input_field, "ML模型使用",
            f"Field mapping: {input_field} -> ML={result.get('ML模型使用')}, "
            f"KB={result.get('代理知识库检索', 'N/A')}",
            result,
        )
        return result

    # ================================================================
    # Traceability
    # ================================================================

    def _record(
        self,
        domain: str,
        file_name: str,
        entry_id: str,
        field: str,
        description: str,
        value: Any,
    ) -> None:
        """Record a KB access for traceability."""
        self._sources.append(
            KBSourceRecord(
                domain=domain,
                file_name=file_name,
                entry_identifier=str(entry_id),
                field_accessed=field,
                value_returned=value,
                description=description,
            )
        )

    def get_accessed_sources(self) -> List[KBSourceRecord]:
        """Return all KB sources accessed during this query session."""
        return list(self._sources)

    def get_accessed_sources_dict(self) -> List[Dict[str, Any]]:
        """Return all KB sources as serializable dicts."""
        return [
            {
                "domain": s.domain,
                "file_name": s.file_name,
                "entry_identifier": s.entry_identifier,
                "field_accessed": s.field_accessed,
                "description": s.description,
            }
            for s in self._sources
        ]

    def reset_sources(self) -> None:
        """Clear trace records for a new evaluation session."""
        self._sources.clear()

    def get_kb_version(self) -> str:
        """Get the knowledge base version string."""
        return self._kb.version
