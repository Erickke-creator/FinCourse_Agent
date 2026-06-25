"""
ML Model Training Pipeline for SME Loan Default Prediction.
Uses simulated data based on Chinese banking research + CUMCM 2020 features.
Trains: 1) Default probability predictor  2) Credit rating classifier
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix,
)
from xgboost import XGBClassifier
import joblib
import os
import json

# ============================================================
# 1. Generate Training Data
# ============================================================
# In production, replace with CUMCM 2020 or ChinaZJB dataset.
# Here we generate realistic synthetic data based on academic research
# on Chinese SME lending patterns.

np.random.seed(42)
N_SAMPLES = 5000

def generate_sme_data(n: int = N_SAMPLES) -> pd.DataFrame:
    """Generate synthetic SME data matching Chinese banking patterns."""

    # Industry distribution (matching real proportions)
    industries = np.random.choice(
        ['manufacturing', 'wholesale_retail', 'it_tech', 'hospitality_food',
         'transportation', 'agriculture', 'construction', 'resident_service',
         'education', 'healthcare', 'other'],
        size=n,
        p=[0.20, 0.28, 0.08, 0.12, 0.06, 0.05, 0.06, 0.06, 0.03, 0.03, 0.03]
    )

    # Tax levels
    tax_levels = np.random.choice(['A', 'B', 'M', 'C', 'D'], size=n, p=[0.15, 0.30, 0.35, 0.15, 0.05])
    tax_score_map = {'A': 5, 'B': 4, 'M': 3, 'C': 2, 'D': 1}
    tax_scores = np.array([tax_score_map[t] for t in tax_levels])

    # Business age (years) - lognormal distribution
    business_age = np.random.lognormal(mean=0.6, sigma=0.8, size=n)
    business_age = np.clip(business_age, 0.1, 30)

    # Registered capital (万元) - lognormal
    registered_capital = np.random.lognormal(mean=3.5, sigma=1.2, size=n)
    registered_capital = np.clip(registered_capital, 5, 5000)

    # Employee count
    employee_count = np.random.lognormal(mean=1.5, sigma=0.8, size=n)
    employee_count = np.clip(employee_count, 1, 500).astype(int)

    # Annual revenue based on business age and capital
    base_revenue = registered_capital * 0.5 + business_age * 20 + np.random.normal(0, 30, n)
    annual_revenue = np.clip(base_revenue, 10, 10000)

    # Profit margin
    profit_margin = np.random.beta(a=3, b=5, size=n) * 0.4 - 0.05
    profit_margin = np.clip(profit_margin, -0.3, 0.5)

    annual_profit = annual_revenue * profit_margin

    # Cash flow (affected by profit and age)
    cash_flow = annual_profit * np.random.uniform(0.5, 1.5, n) + business_age * 5

    # Asset-liability ratio
    asset_liability_ratio = np.random.beta(a=2, b=4, size=n)
    asset_liability_ratio = np.clip(asset_liability_ratio, 0.05, 0.95)

    # Invoice invalid ratio
    invalid_invoice_ratio = np.random.beta(a=1.5, b=20, size=n)
    invalid_invoice_ratio = np.clip(invalid_invoice_ratio, 0, 0.4)

    # Credit features
    has_default_history = np.random.binomial(1, 0.08, n)
    overdue_count_2yr = np.random.poisson(lam=1.2, size=n)
    overdue_count_2yr = np.where(has_default_history == 1,
                                  overdue_count_2yr + np.random.randint(2, 8, n),
                                  overdue_count_2yr)
    credit_inquiry_3m = np.random.poisson(lam=2.5, size=n)
    legal_disputes = np.random.poisson(lam=0.3, size=n)

    # Asset features
    has_real_estate = np.random.binomial(1, 0.25 + profit_margin * 0.5, n)
    real_estate_value = np.where(
        has_real_estate == 1,
        np.random.lognormal(mean=4.5, sigma=0.8, size=n),
        0
    )
    real_estate_value = np.clip(real_estate_value, 0, 5000)
    has_other_collateral = np.random.binomial(1, 0.15, n)

    # Stability
    revenue_volatility = np.random.beta(a=2, b=6, size=n) * 2
    customer_count = np.random.lognormal(mean=2.5, sigma=1.0, size=n).astype(int)
    customer_count = np.clip(customer_count, 1, 1000)
    customer_concentration = np.random.beta(a=2, b=3, size=n)

    # Special labels
    is_ecommerce = np.random.binomial(1, 0.15, n)
    is_tech_enterprise = np.random.binomial(1, 0.08, n)

    # ---- TARGET: Default probability ----
    # Based on academic research on Chinese SME default factors
    # Using stronger signal coefficients for better model training
    default_score = (
        -0.8 * np.log1p(business_age)             # older = much safer
        -0.5 * np.log1p(annual_revenue / 100)      # more revenue = safer
        -0.6 * (profit_margin * 8)                 # higher margin = safer
        +1.2 * has_default_history                 # past default = very risky
        +0.3 * overdue_count_2yr                   # more overdues = risky
        +0.15 * credit_inquiry_3m                  # more inquiries = risky
        +0.3 * legal_disputes                      # legal issues = risky
        -0.5 * has_real_estate                     # collateral = safer
        +0.5 * asset_liability_ratio * 2           # high leverage = risky
        +0.3 * revenue_volatility                  # unstable = risky
        -0.3 * tax_scores / 5.0                    # good tax = safer
        +0.3 * invalid_invoice_ratio * 8           # messy invoices = risky
        -0.15 * np.log1p(customer_count) / 4       # more customers = safer
        +np.random.normal(0, 0.15, n)              # reduced noise
    )

    # Convert to probability via sigmoid with threshold adjustment
    # Shift to achieve realistic ~15% default rate
    default_prob = 1 / (1 + np.exp(-(default_score + 1.5)))
    has_defaulted = np.random.binomial(1, default_prob)

    # Credit rating (A/B/C/D) — based on default score with less noise
    rating_score = -default_score + np.random.normal(0, 0.15, n)
    rating_percentiles = np.percentile(rating_score, [20, 50, 80])
    credit_rating = np.where(
        rating_score >= rating_percentiles[2], 'A',
        np.where(rating_score >= rating_percentiles[1], 'B',
                 np.where(rating_score >= rating_percentiles[0], 'C', 'D'))
    )

    df = pd.DataFrame({
        'business_age_years': business_age,
        'registered_capital_wan': registered_capital,
        'industry': industries,
        'employee_count': employee_count,
        'annual_revenue_wan': annual_revenue,
        'annual_profit_wan': annual_profit,
        'profit_margin': profit_margin,
        'cash_flow_wan': cash_flow,
        'asset_liability_ratio': asset_liability_ratio,
        'tax_level': tax_levels,
        'tax_score': tax_scores,
        'annual_tax_wan': annual_revenue * 0.03 + np.random.normal(0, 2, n),
        'invalid_invoice_ratio': invalid_invoice_ratio,
        'has_default_history': has_default_history,
        'overdue_count_2yr': overdue_count_2yr,
        'credit_inquiry_3m': credit_inquiry_3m,
        'legal_disputes': legal_disputes,
        'has_real_estate': has_real_estate,
        'real_estate_value_wan': real_estate_value,
        'has_other_collateral': has_other_collateral,
        'revenue_volatility': revenue_volatility,
        'customer_count': customer_count,
        'customer_concentration': customer_concentration,
        'is_ecommerce': is_ecommerce,
        'is_tech_enterprise': is_tech_enterprise,
        'default_probability': default_prob,
        'has_defaulted': has_defaulted,
        'credit_rating': credit_rating,
    })

    return df


# ============================================================
# 2. Feature Engineering
# ============================================================

def prepare_features(df: pd.DataFrame) -> tuple:
    """Prepare feature matrix and labels for ML training."""
    # Encode categoricals
    industry_le = LabelEncoder()
    tax_le = LabelEncoder()
    rating_le = LabelEncoder()

    df['industry_encoded'] = industry_le.fit_transform(df['industry'])
    df['tax_level_encoded'] = tax_le.fit_transform(df['tax_level'])
    df['rating_encoded'] = rating_le.fit_transform(df['credit_rating'])

    feature_cols = [
        'business_age_years', 'registered_capital_wan', 'employee_count',
        'annual_revenue_wan', 'annual_profit_wan', 'profit_margin',
        'cash_flow_wan', 'asset_liability_ratio',
        'tax_score', 'annual_tax_wan', 'invalid_invoice_ratio',
        'has_default_history', 'overdue_count_2yr', 'credit_inquiry_3m',
        'legal_disputes', 'has_real_estate', 'real_estate_value_wan',
        'has_other_collateral', 'revenue_volatility',
        'customer_count', 'customer_concentration',
        'is_ecommerce', 'is_tech_enterprise', 'industry_encoded',
        'tax_level_encoded',
    ]

    X = df[feature_cols].values
    y_default = df['has_defaulted'].values
    y_rating = df['rating_encoded'].values
    y_prob = df['default_probability'].values

    return X, y_default, y_rating, y_prob, feature_cols, {
        'industry_encoder': industry_le,
        'tax_encoder': tax_le,
        'rating_encoder': rating_le,
    }


# ============================================================
# 3. Train Models
# ============================================================

def train_models():
    print("=" * 60)
    print("  小微企业贷款违约预测 — ML模型训练")
    print("=" * 60)

    # Generate data
    print("\n[1/5] 生成训练数据...")
    df = generate_sme_data(N_SAMPLES)
    print(f"  样本数: {len(df)}")
    print(f"  违约率: {df['has_defaulted'].mean():.2%}")
    print(f"  评级分布: A={df['credit_rating'].eq('A').mean():.1%}, "
          f"B={df['credit_rating'].eq('B').mean():.1%}, "
          f"C={df['credit_rating'].eq('C').mean():.1%}, "
          f"D={df['credit_rating'].eq('D').mean():.1%}")

    # Prepare features
    print("\n[2/5] 特征工程...")
    X, y_default, y_rating, y_prob, feature_cols, encoders = prepare_features(df)
    print(f"  特征维度: {X.shape[1]}")

    # Train/test split
    X_train, X_test, y_train, y_test, y_prob_train, y_prob_test = train_test_split(
        X, y_default, y_prob, test_size=0.2, random_state=42, stratify=y_default
    )
    _, _, y_rating_train, y_rating_test = train_test_split(
        X, y_rating, test_size=0.2, random_state=42, stratify=y_rating
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ---- Model 1: XGBoost Default Predictor ----
    print("\n[3/5] 训练 XGBoost 违约预测模型...")
    xgb_default = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=(len(y_train) - y_train.sum()) / y_train.sum(),
        eval_metric='auc',
        random_state=42,
    )
    xgb_default.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )

    y_pred_default = xgb_default.predict(X_test_scaled)
    y_pred_proba = xgb_default.predict_proba(X_test_scaled)[:, 1]

    print(f"  Accuracy:  {accuracy_score(y_test, y_pred_default):.4f}")
    print(f"  Precision: {precision_score(y_test, y_pred_default):.4f}")
    print(f"  Recall:    {recall_score(y_test, y_pred_default):.4f}")
    print(f"  F1 Score:  {f1_score(y_test, y_pred_default):.4f}")
    print(f"  ROC-AUC:   {roc_auc_score(y_test, y_pred_proba):.4f}")
    print(f"\n  Classification Report:\n{classification_report(y_test, y_pred_default)}")

    # Feature importance
    importances = xgb_default.feature_importances_
    top_idx = np.argsort(importances)[-10:][::-1]
    print("  Top 10 重要特征:")
    for i, idx in enumerate(top_idx):
        print(f"    {i+1}. {feature_cols[idx]}: {importances[idx]:.4f}")

    # ---- Model 2: Random Forest Rating Classifier ----
    print("\n[4/5] 训练 Random Forest 信用评级分类模型...")
    rf_rating = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=10,
        class_weight='balanced',
        random_state=42,
    )
    rf_rating.fit(X_train_scaled, y_rating_train)

    y_pred_rating = rf_rating.predict(X_test_scaled)
    print(f"  Accuracy:  {accuracy_score(y_rating_test, y_pred_rating):.4f}")
    print(f"  F1 (macro): {f1_score(y_rating_test, y_pred_rating, average='macro'):.4f}")
    print(f"  F1 (weighted): {f1_score(y_rating_test, y_pred_rating, average='weighted'):.4f}")

    # ---- Save models ----
    print("\n[5/5] 保存模型...")
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(xgb_default, os.path.join(model_dir, 'xgb_default_predictor.pkl'))
    joblib.dump(rf_rating, os.path.join(model_dir, 'rf_rating_classifier.pkl'))
    joblib.dump(scaler, os.path.join(model_dir, 'feature_scaler.pkl'))
    joblib.dump(encoders, os.path.join(model_dir, 'label_encoders.pkl'))

    # Save metadata
    metadata = {
        'feature_columns': feature_cols,
        'n_samples': N_SAMPLES,
        'default_rate': float(df['has_defaulted'].mean()),
        'xgb_auc': float(roc_auc_score(y_test, y_pred_proba)),
        'rf_accuracy': float(accuracy_score(y_rating_test, y_pred_rating)),
        'feature_importance': {feature_cols[i]: float(importances[i]) for i in top_idx},
    }
    with open(os.path.join(model_dir, 'model_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"  模型已保存到: {model_dir}/")
    print(f"  - xgb_default_predictor.pkl")
    print(f"  - rf_rating_classifier.pkl")
    print(f"  - feature_scaler.pkl")
    print(f"  - label_encoders.pkl")
    print(f"  - model_metadata.json")
    print("\n" + "=" * 60)
    print("  训练完成！")
    print("=" * 60)

    return xgb_default, rf_rating, scaler, encoders


if __name__ == "__main__":
    models = train_models()
