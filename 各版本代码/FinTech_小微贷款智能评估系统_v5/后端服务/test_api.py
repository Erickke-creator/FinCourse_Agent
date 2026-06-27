"""
v5 pytest 自动化测试
用法: cd 后端服务 && pytest test_api.py -v
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import LoanInput, MerchantType, TaxLevel, IndustryType
from bank_engine import evaluate_loan, BANKS_DB
from kb_bridge import get_kb_summary, search_policies


class TestBankEngine:
    def test_banks_loaded(self):
        assert len(BANKS_DB) == 30, f"Expected 30 banks, got {len(BANKS_DB)}"

    def test_low_risk_evaluation(self):
        inp = LoanInput(merchant_type=MerchantType.enterprise, operating_years=6,
                        industry=IndustryType.manufacturing, monthly_revenue=300000,
                        monthly_fixed_cost=160000, requested_amount=1000000,
                        loan_term=36, tax_level=TaxLevel.A, has_business_license=True,
                        has_stable_bank_flow=True, has_collateral_or_guarantor=True)
        r = evaluate_loan(inp)
        assert r.score > 70, f"Low-risk score too low: {r.score}"
        assert str(r.risk_level).lower() == "risklevel.low", f"Expected low risk, got {r.risk_level}"
        assert len(r.bank_matches) >= 1

    def test_high_risk_evaluation(self):
        inp = LoanInput(merchant_type=MerchantType.individual, operating_years=1,
                        industry=IndustryType.entertainment, monthly_revenue=15000,
                        monthly_fixed_cost=12000, existing_liabilities=5000,
                        requested_amount=500000, loan_term=6, tax_level=TaxLevel.D,
                        has_business_license=False, has_stable_bank_flow=False,
                        has_overdue_record=True, overdue_count_2yr=5)
        r = evaluate_loan(inp)
        assert r.score < 55, f"High-risk score too high: {r.score}"

    def test_eval_returns_ml_fields(self):
        inp = LoanInput(requested_amount=200000, loan_term=12, industry=IndustryType.manufacturing,
                        operating_years=3, monthly_revenue=50000, tax_level=TaxLevel.B)
        r = evaluate_loan(inp)
        assert hasattr(r, 'ml_enhanced')
        assert hasattr(r, 'ml_default_prob')


class TestKnowledgeBase:
    def test_kb_summary(self):
        s = get_kb_summary()
        assert "银行" in s
        assert "政策" in s or "国家级" in s

    def test_search_policies(self):
        results = search_policies("制造业")
        assert isinstance(results, list)


class TestModels:
    def test_loan_input_defaults(self):
        inp = LoanInput()
        assert inp.requested_amount == 50000
        assert inp.loan_term == 12

    def test_loan_input_validation(self):
        with pytest.raises(Exception):
            LoanInput(operating_years=-1)  # negative years should fail

    def test_ml_model_dimensions(self):
        from ml_inference import MLPredictor
        p = MLPredictor()
        fv = p._build_feature_vector({"operating_years": 3, "monthly_revenue": 50000,
                                       "industry": "manufacturing", "tax_level": "B",
                                       "monthly_fixed_cost": 20000})
        assert fv.shape[1] == 24, f"Expected 24 features, got {fv.shape[1]}"


class TestStressTest:
    def test_four_scenarios(self):
        from stress_test import run_stress_test, stress_test_summary
        results = run_stress_test(monthly_revenue=50000, monthly_fixed_cost=30000,
                                  existing_liabilities=5000, monthly_repayment=8000)
        assert len(results) == 4
        summary = stress_test_summary(results)
        assert "scenarios_tested" in summary
        assert summary["scenarios_tested"] == 4
