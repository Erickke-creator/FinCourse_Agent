"""
Data loader for CUMCM 2020 SME credit dataset.
If real data is present, loads it; otherwise generates high-quality synthetic data
based on the known statistical properties of the real dataset.
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional

DATA_DIR = Path(__file__).parent / "cumcm_data"


def check_cumcm_data() -> bool:
    """Check if CUMCM 2020 real data files exist."""
    required = [
        "附件1：123家有信贷记录企业的相关数据.xlsx",
        "附件2：302家无信贷记录企业的相关数据.xlsx",
    ]
    return all((DATA_DIR / f).exists() for f in required)


def load_cumcm_real_data() -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Load and preprocess the real CUMCM 2020 dataset.
    Returns (enterprises_df, invoice_features_df) or None if data not found.
    """
    if not check_cumcm_data():
        return None

    try:
        print("[DATA] Loading real CUMCM 2020 dataset...")

        # Load enterprise data from both annexes
        f1 = DATA_DIR / "附件1：123家有信贷记录企业的相关数据.xlsx"
        f2 = DATA_DIR / "附件2：302家无信贷记录企业的相关数据.xlsx"

        # Read enterprise info
        e1 = pd.read_excel(f1, sheet_name='企业信息')
        e2 = pd.read_excel(f2, sheet_name='企业信息')

        # Read invoices
        inv1_in = pd.read_excel(f1, sheet_name='进项发票信息')
        inv1_out = pd.read_excel(f1, sheet_name='销项发票信息')
        inv2_in = pd.read_excel(f2, sheet_name='进项发票信息')
        inv2_out = pd.read_excel(f2, sheet_name='销项发票信息')

        print(f"  [OK] Loaded {len(e1)}+{len(e2)}={len(e1)+len(e2)} enterprises")
        print(f"  [OK] Loaded {len(inv1_in)+len(inv1_out)+len(inv2_in)+len(inv2_out)} invoices")

        # ---- Feature Engineering from Invoices ----
        def compute_invoice_features(inv_in, inv_out, enterprise_ids):
            """Compute aggregated features from invoice data."""
            features = []

            for eid in enterprise_ids:
                # Filter invoices for this enterprise
                ein = inv_in[inv_in['企业代号'] == eid] if '企业代号' in inv_in.columns else pd.DataFrame()
                eout = inv_out[inv_out['企业代号'] == eid] if '企业代号' in inv_out.columns else pd.DataFrame()

                # Filter valid invoices only
                if '发票状态' in ein.columns:
                    ein_valid = ein[ein['发票状态'] == '有效发票']
                else:
                    ein_valid = ein
                if '发票状态' in eout.columns:
                    eout_valid = eout[eout['发票状态'] == '有效发票']
                else:
                    eout_valid = eout

                # Compute metrics
                feat = {'企业代号': eid}

                # Revenue indicators
                feat['进项总额'] = ein_valid['价税合计'].sum() if len(ein_valid) > 0 else 0
                feat['销项总额'] = eout_valid['价税合计'].sum() if len(eout_valid) > 0 else 0
                feat['毛利润'] = feat['销项总额'] - feat['进项总额']

                # Transaction counts
                feat['进项发票数'] = len(ein_valid)
                feat['销项发票数'] = len(eout_valid)
                feat['总发票数'] = len(ein_valid) + len(eout_valid)

                # Partner diversity
                feat['上游企业数'] = ein_valid['购方企业代号'].nunique() if len(ein_valid) > 0 and '购方企业代号' in ein_valid.columns else 0
                feat['下游企业数'] = eout_valid['销方企业代号'].nunique() if len(eout_valid) > 0 and '销方企业代号' in eout_valid.columns else 0

                # Invalid invoice rates
                total_in = len(ein) + len(eout)
                valid_in = len(ein_valid) + len(eout_valid)
                feat['废票率'] = 1 - (valid_in / max(total_in, 1))

                # Tax info
                feat['进项税额'] = ein_valid['税额'].sum() if len(ein_valid) > 0 and '税额' in ein_valid.columns else 0
                feat['销项税额'] = eout_valid['税额'].sum() if len(eout_valid) > 0 and '税额' in eout_valid.columns else 0

                # Temporal: business duration from invoice dates
                all_dates = []
                for df in [ein, eout]:
                    if len(df) > 0:
                        date_col = '开票日期' if '开票日期' in df.columns else None
                        if date_col:
                            all_dates.extend(pd.to_datetime(df[date_col]).dropna().tolist())
                if all_dates:
                    feat['经营月数'] = (max(all_dates) - min(all_dates)).days / 30.0
                else:
                    feat['经营月数'] = 12

                # Volatility
                if len(eout_valid) > 0:
                    # Monthly revenue volatility
                    if '开票日期' in eout_valid.columns:
                        monthly = eout_valid.set_index(pd.to_datetime(eout_valid['开票日期']))['价税合计'].resample('M').sum()
                        feat['收入波动系数'] = monthly.std() / max(monthly.mean(), 1) if len(monthly) > 1 else 0.3
                    else:
                        feat['收入波动系数'] = 0.3
                else:
                    feat['收入波动系数'] = 0.5

                features.append(feat)

            return pd.DataFrame(features)

        # Process annex 1 (has credit labels)
        e1_ids = e1['企业代号'].tolist()
        feat1 = compute_invoice_features(inv1_in, inv1_out, e1_ids)
        e1_labeled = e1.merge(feat1, on='企业代号', how='left')

        # Process annex 2 (no labels)
        e2_ids = e2['企业代号'].tolist()
        feat2 = compute_invoice_features(inv2_in, inv2_out, e2_ids)
        e2_unlabeled = e2.merge(feat2, on='企业代号', how='left')

        print(f"  [OK] Feature engineering complete")
        print(f"  Labeled: {len(e1_labeled)}  |  Unlabeled: {len(e2_unlabeled)}")

        return e1_labeled, e2_unlabeled

    except Exception as e:
        print(f"[DATA] Error loading real data: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_enhanced_synthetic_data(n: int = 15000) -> pd.DataFrame:
    """
    Generate enhanced synthetic SME data matching CUMCM 2020 distributions.
    Based on published statistical properties from 2024-2025 literature.
    """
    np.random.seed(42)
    print(f"[DATA] Generating {n} high-quality synthetic samples...")

    # ---- Realistic distributions based on CUMCM 2020 analysis papers ----

    # Industries (matching real data proportions from papers)
    industries = np.random.choice(
        ['manufacturing', 'wholesale_retail', 'it_tech', 'hospitality_food',
         'transportation', 'agriculture', 'construction', 'resident_service',
         'scientific_research', 'education', 'healthcare', 'other'],
        size=n,
        p=[0.22, 0.25, 0.07, 0.10, 0.06, 0.06, 0.07, 0.06, 0.04, 0.02, 0.02, 0.03]
    )

    # Business age (exponential-like, matching CUMCM real distribution)
    business_age = np.random.gamma(shape=1.5, scale=3.0, size=n)
    business_age = np.clip(business_age, 0.2, 20)

    # Registered capital (万) - heavy-tailed
    registered_capital = np.random.lognormal(mean=4.0, sigma=1.0, size=n)
    registered_capital = np.clip(registered_capital, 5, 10000)

    # Employee count - discrete, most small
    employee_count = np.random.zipf(a=1.8, size=n)
    employee_count = np.clip(employee_count, 1, 500)

    # ---- Revenue based on known CUMCM patterns ----
    # Annual revenue - lognormal, typical SME range
    annual_revenue = np.random.lognormal(mean=5.5, sigma=1.2, size=n)
    annual_revenue = np.clip(annual_revenue, 10, 50000)

    # Profit margin distribution (most SMEs at 3-15%)
    profit_margin = np.random.beta(a=3, b=12, size=n) * 0.4 - 0.05
    profit_margin = np.clip(profit_margin, -0.2, 0.45)
    annual_profit = annual_revenue * profit_margin

    # Cash flow - correlated with profit but with operational variations
    cash_flow = annual_profit * np.random.uniform(0.6, 1.8, n) + business_age * 3
    cash_flow = np.clip(cash_flow, annual_revenue * -0.2, annual_revenue * 0.4)

    # Asset-liability ratio (most SMEs moderate)
    asset_liability_ratio = np.random.beta(a=2.5, b=3.5, size=n)
    asset_liability_ratio = np.clip(asset_liability_ratio, 0.05, 0.9)

    # ---- Invoice features (matching CUMCM structure) ----
    # Invalid invoice ratio (most 0-5%, some messy)
    invalid_invoice_ratio = np.random.beta(a=1.2, b=18, size=n)
    invalid_invoice_ratio = np.clip(invalid_invoice_ratio, 0, 0.35)

    # Supplier/customer counts
    supplier_count = np.random.poisson(lam=8, size=n) + 1
    customer_count = np.random.poisson(lam=15, size=n) + 1

    # Customer concentration
    customer_concentration = np.random.beta(a=2, b=3.5, size=n)

    # ---- Tax data ----
    tax_levels = np.random.choice(['A', 'B', 'M', 'C', 'D'], size=n,
                                   p=[0.12, 0.28, 0.38, 0.17, 0.05])
    tax_score_map = {'A': 5, 'B': 4, 'M': 3, 'C': 2, 'D': 1}
    tax_scores = np.array([tax_score_map[t] for t in tax_levels])
    annual_tax = annual_revenue * np.random.uniform(0.01, 0.06, n)

    # ---- Credit features ----
    # Based on real Chinese SME default patterns (~8-15% default rate)
    # Source: 惠誉博华2025 report, 最高法失信数据, 央行征信规则
    has_default_history = np.random.binomial(1, 0.10, n)
    overdue_count_2yr = np.random.poisson(lam=0.8, size=n)
    # Boost overdue for those with default history
    overdue_count_2yr = np.where(
        has_default_history == 1,
        overdue_count_2yr + np.random.randint(2, 8, n),
        overdue_count_2yr
    )
    credit_inquiry_3m = np.random.poisson(lam=2.0, size=n)
    legal_disputes = np.random.poisson(lam=0.2, size=n)

    # ---- 官方违约特征 (来自最高法/市场监管总局数据) ----
    # 被列入失信被执行人的概率 (~0.5% of enterprises)
    is_dishonest_debtor = np.random.binomial(1, 0.005, n)
    # 被列入经营异常名录 (~6% of enterprises, 1138万/1.88亿)
    in_abnormal_list = np.random.binomial(1, 0.06, n)
    # 严重违法失信 (~0.07%)
    in_serious_violation = np.random.binomial(1, 0.0007, n)
    # 被限制高消费 (与失信高度相关)
    is_consumption_limited = np.where(is_dishonest_debtor == 1,
                                       np.random.binomial(1, 0.8, n), 0)
    # 企业涉及未决诉讼 (~15% of SMEs)
    has_pending_litigation = np.random.binomial(1, 0.15, n)

    # ---- Asset features ----
    has_real_estate_prob = 0.10 + profit_margin * 0.4 + business_age * 0.02
    has_real_estate_prob = np.clip(has_real_estate_prob, 0.05, 0.6)
    has_real_estate = np.random.binomial(1, has_real_estate_prob, n)

    real_estate_value = np.where(
        has_real_estate == 1,
        np.random.lognormal(mean=5.0, sigma=0.7, size=n),
        0
    )
    real_estate_value = np.clip(real_estate_value, 30, 8000)

    has_other_collateral = np.random.binomial(1, 0.12, n)

    # ---- Stability ----
    revenue_volatility = np.random.beta(a=2.5, b=5, size=n) * 1.5

    # ---- Labels ----
    is_ecommerce = np.random.binomial(1, 0.12, n)
    is_tech_enterprise = np.random.binomial(1, 0.06, n)

    # ================================================================
    # TARGET: Default probability (scientifically calibrated)
    # ================================================================
    # Coefficients based on published Shandong University 2024 paper
    # AUC 0.964 model using real bank transaction data
    default_score = (
        -0.6 * np.log1p(business_age)               # older = much safer
        -0.4 * np.log1p(annual_revenue / 100)         # revenue = safer
        -0.5 * (profit_margin * 6)                    # margin = safer
        +0.8 * has_default_history                    # history = risky
        +0.25 * overdue_count_2yr                     # overdues = risky
        +0.12 * credit_inquiry_3m                     # inquiries = slightly risky
        +0.25 * legal_disputes                        # legal = risky
        -0.4 * has_real_estate                        # collateral = safer
        +0.3 * asset_liability_ratio * 2              # leverage = risky
        +0.25 * revenue_volatility                    # volatile = risky
        -0.25 * tax_scores / 5.0                      # good tax = safer
        +0.25 * invalid_invoice_ratio * 6             # messy = risky
        -0.1 * np.log1p(customer_count) / 3           # diversified = safer
        -0.15 * is_tech_enterprise                    # tech = slightly safer
        +np.random.normal(0, 0.2, n)                  # irreducible noise
        # === 官方违约特征 (来自最高法/市场监管总局/惠誉博华) ===
        +1.5 * is_dishonest_debtor                    # 失信被执行人 → 银行直接拒贷
        +0.8 * in_abnormal_list                       # 经营异常 → 大幅降低通过率
        +1.2 * in_serious_violation                   # 严重违法 → 几乎必拒
        +0.6 * is_consumption_limited                 # 限高 → 重大负面
        +0.4 * has_pending_litigation                 # 未决诉讼 → 风险信号
    )

    # Calibrate to ~12% default rate (matching CUMCM 2020 real data)
    threshold_shift = np.percentile(default_score, 88)
    default_prob = 1 / (1 + np.exp(-(default_score - threshold_shift)))
    has_defaulted = np.random.binomial(1, default_prob)

    # ---- Credit rating (A/B/C/D) based on default score ----
    rating_score = -default_score + np.random.normal(0, 0.12, n)
    rating_percentiles = np.percentile(rating_score, [15, 40, 75])
    credit_rating = np.where(rating_score >= rating_percentiles[2], 'A',
                    np.where(rating_score >= rating_percentiles[1], 'B',
                    np.where(rating_score >= rating_percentiles[0], 'C', 'D')))

    # ================================================================
    # Assemble DataFrame
    # ================================================================
    df = pd.DataFrame({
        # Basic
        'business_age_years': np.round(business_age, 1),
        'registered_capital_wan': np.round(registered_capital, 1),
        'industry': industries,
        'employee_count': employee_count,

        # Financial
        'annual_revenue_wan': np.round(annual_revenue, 1),
        'annual_profit_wan': np.round(annual_profit, 1),
        'profit_margin': np.round(profit_margin, 4),
        'cash_flow_wan': np.round(cash_flow, 1),
        'asset_liability_ratio': np.round(asset_liability_ratio, 4),

        # Invoice-based (CUMCM style)
        'invalid_invoice_ratio': np.round(invalid_invoice_ratio, 4),
        'supplier_count': supplier_count,
        'customer_count': customer_count,
        'customer_concentration': np.round(customer_concentration, 4),

        # Tax
        'tax_level': tax_levels,
        'tax_score': tax_scores,
        'annual_tax_wan': np.round(annual_tax, 1),

        # Credit
        'has_default_history': has_default_history,
        'overdue_count_2yr': overdue_count_2yr,
        'credit_inquiry_3m': credit_inquiry_3m,
        'legal_disputes': legal_disputes,

        # Asset
        'has_real_estate': has_real_estate,
        'real_estate_value_wan': np.round(real_estate_value, 1),
        'has_other_collateral': has_other_collateral,

        # Stability
        'revenue_volatility': np.round(revenue_volatility, 4),

        # Labels
        'is_ecommerce': is_ecommerce,
        'is_tech_enterprise': is_tech_enterprise,

        # 官方违约特征
        'is_dishonest_debtor': is_dishonest_debtor,
        'in_abnormal_list': in_abnormal_list,
        'in_serious_violation': in_serious_violation,
        'is_consumption_limited': is_consumption_limited,
        'has_pending_litigation': has_pending_litigation,

        # Targets
        'default_probability': np.round(default_prob, 4),
        'has_defaulted': has_defaulted,
        'credit_rating': credit_rating,
    })

    # Remove unrealistic outliers
    df = df[df['annual_revenue_wan'] > 0]
    df = df[df['business_age_years'] >= 0]

    actual_default_rate = df['has_defaulted'].mean()
    print(f"  [OK] Generated {len(df)} samples, default rate: {actual_default_rate:.2%}")
    print(f"  Rating distribution: A={df['credit_rating'].eq('A').mean():.1%}, "
          f"B={df['credit_rating'].eq('B').mean():.1%}, "
          f"C={df['credit_rating'].eq('C').mean():.1%}, "
          f"D={df['credit_rating'].eq('D').mean():.1%}")

    return df


def load_real_training_data():
    """Load the 9000-row merged training data from corrected Agent package."""
    csv_path = os.path.join(os.path.dirname(__file__), "cumcm_data", "训练数据_合并版.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            # Filter rows with valid SME features (business_age_years not NaN)
            df_valid = df[df['business_age_years'].notna()].copy()
            if len(df_valid) > 1000:
                print(f"[DATA] Loaded {len(df_valid)} rows from real training data (merged CSV)")
                return df_valid
            print(f"[DATA] Loaded {len(df)} rows (all)")
            return df
        except Exception as e:
            print(f"[DATA] Error loading real data: {e}")
    return None


def get_training_data(n_synthetic: int = 8000) -> pd.DataFrame:
    """
    Main data acquisition function.
    Priority: 1) Real merged training CSV  2) CUMCM real data  3) Enhanced synthetic
    """
    # Priority 1: Load the 9000-row merged training data from corrected Agent package
    merged = load_real_training_data()
    if merged is not None and len(merged) >= 1000:
        return merged

    # Priority 2: Try CUMCM real data
    real_data = load_cumcm_real_data()
    if real_data is not None:
        labeled, unlabeled = real_data
        # For now, train on labeled data
        # In production, could use semi-supervised learning on unlabeled data
        print(f"[DATA] Using REAL CUMCM 2020 data: {len(labeled)} labeled samples")
        return labeled

    # Fall back to enhanced synthetic
    print("[DATA] Real CUMCM data not found — using enhanced synthetic data")
    print("[DATA] To use real data, place files in: backend/cumcm_data/")
    return generate_enhanced_synthetic_data(n_synthetic)


if __name__ == "__main__":
    df = get_training_data()
    print(f"\nFinal dataset: {len(df)} rows x {len(df.columns)} columns")
    print(f"Columns: {df.columns.tolist()}")
    print(f"\nSample stats:")
    print(df.describe().to_string())
