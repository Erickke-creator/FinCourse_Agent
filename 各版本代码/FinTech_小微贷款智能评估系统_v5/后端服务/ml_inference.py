"""
ML inference module — loads trained models for prediction.
Integrates with the FastAPI evaluation pipeline.
"""

import os
import json
import logging
import numpy as np
import joblib
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("ml_inference")

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')


class MLPredictor:
    """Wrapper around trained ML models for inference.
    Supports 3-model system: default predictor + rating classifier + risk classifier.
    """

    def __init__(self):
        self.xgb_default = None      # XGBoost default probability predictor
        self.gb_rating = None         # Gradient Boosting credit rating classifier
        self.rf_risk = None           # Random Forest risk level classifier
        self.scaler = None
        self.encoders = None
        self.is_loaded = False

    def load_models(self) -> bool:
        """Load all trained models from disk."""
        try:
            xgb_path = os.path.join(MODEL_DIR, 'xgb_default_predictor.pkl')
            rating_path = os.path.join(MODEL_DIR, 'gb_rating_classifier.pkl')
            risk_path = os.path.join(MODEL_DIR, 'rf_risk_classifier.pkl')
            scaler_path = os.path.join(MODEL_DIR, 'feature_scaler.pkl')
            encoder_path = os.path.join(MODEL_DIR, 'label_encoders.pkl')

            # Fall back to legacy names if enhanced not available
            if not os.path.exists(rating_path):
                rating_path = os.path.join(MODEL_DIR, 'rf_rating_classifier.pkl')
            if not os.path.exists(risk_path):
                risk_path = rating_path

            if not os.path.exists(xgb_path):
                logger.warning("Models not found — run train_ml_enhanced.py first")
                return False

            self.xgb_default = joblib.load(xgb_path)
            self.gb_rating = joblib.load(rating_path)
            self.rf_risk = joblib.load(risk_path) if os.path.exists(risk_path) else self.gb_rating
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            if os.path.exists(encoder_path):
                self.encoders = joblib.load(encoder_path)

            # Load the 24-feature order from model metadata
            metadata_path = os.path.join(MODEL_DIR, 'model_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    meta = json.load(f)
                    self.feature_cols = meta.get('feature_columns', [])

            self.is_loaded = True
            logger.info(f"Models loaded: default={type(self.xgb_default).__name__}, "
                  f"rating={type(self.gb_rating).__name__}, "
                  f"features={len(self.feature_cols)}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load models: {e}")
            return False

    def _build_feature_vector(self, enterprise_data: Dict[str, Any]) -> np.ndarray:
        """Build feature vector from enterprise profile dict."""
        # Handle industry encoding
        industry = enterprise_data.get('industry', 'other')
        industry_encoded = 0  # default
        if self.encoders and 'industry_encoder' in self.encoders:
            try:
                industry_encoded = self.encoders['industry_encoder'].transform([industry])[0]
            except ValueError:
                industry_encoded = len(self.encoders['industry_encoder'].classes_) - 1  # unknown

        # Handle tax encoding
        tax_level = enterprise_data.get('tax_level', 'M')
        tax_encoded = 0
        if self.encoders and 'tax_encoder' in self.encoders:
            try:
                tax_encoded = self.encoders['tax_encoder'].transform([tax_level])[0]
            except ValueError:
                tax_encoded = 0

        tax_score_map = {'A': 5, 'B': 4, 'M': 3, 'C': 2, 'D': 1}
        tax_score = tax_score_map.get(tax_level, 3)

        revenue = float(enterprise_data.get('monthly_revenue', 30000)) * 12
        fixed_cost = float(enterprise_data.get('monthly_fixed_cost', 15000)) * 12
        liabilities = float(enterprise_data.get('existing_liabilities', 0))
        net_monthly = float(enterprise_data.get('monthly_revenue', 30000)) - float(enterprise_data.get('monthly_fixed_cost', 15000)) - liabilities

        features = np.array([[
            float(enterprise_data.get('operating_years', 1)),                    # 0: business_age_years
            revenue / 10000,                                                     # 1: annual_revenue_wan
            (revenue - fixed_cost) / 10000,                                      # 2: annual_profit_wan
            (revenue - fixed_cost) / max(revenue, 1),                            # 3: profit_margin
            net_monthly * 12 / 10000,                                            # 4: cash_flow_wan
            float(enterprise_data.get('asset_liability_ratio', 0.4)),            # 5: asset_liability_ratio
            float(enterprise_data.get('invalid_invoice_ratio', 0.05)),           # 6: invalid_invoice_ratio
            float(enterprise_data.get('supplier_count', 10)),                    # 7: supplier_count
            float(enterprise_data.get('customer_count', 10)),                    # 8: customer_count
            float(enterprise_data.get('customer_concentration', 0.3)),           # 9: customer_concentration
            tax_score,                                                           # 10: tax_score
            revenue * 0.03 / 10000,                                              # 11: annual_tax_wan (approx)
            1 if enterprise_data.get('has_overdue_record') else 0,               # 12: has_default_history
            float(enterprise_data.get('overdue_count_2yr', 0)),                  # 13: overdue_count_2yr
            float(enterprise_data.get('credit_inquiry_3m', 2)),                  # 14: credit_inquiry_3m
            float(enterprise_data.get('legal_disputes', 0)),                     # 15: legal_disputes
            1 if enterprise_data.get('has_real_estate') else 0,                  # 16: has_real_estate
            float(enterprise_data.get('real_estate_value', 0)),                  # 17: real_estate_value_wan
            1 if enterprise_data.get('has_collateral_or_guarantor') else 0,      # 18: has_other_collateral
            float(enterprise_data.get('revenue_volatility', 0.3)),               # 19: revenue_volatility
            1 if enterprise_data.get('is_ecommerce') else 0,                     # 20: is_ecommerce
            1 if enterprise_data.get('is_tech_enterprise') else 0,               # 21: is_tech_enterprise
            industry_encoded,                                                    # 22: industry_encoded
            tax_encoded,                                                         # 23: tax_level_encoded
        ]])

        return features

    def predict_default_probability(self, enterprise_data: Dict[str, Any]) -> Optional[float]:
        """Predict probability of loan default (0-1)."""
        if not self.is_loaded:
            return None
        try:
            X = self._build_feature_vector(enterprise_data)
            X_scaled = self.scaler.transform(X)
            prob = self.xgb_default.predict_proba(X_scaled)[0, 1]
            return float(prob)
        except Exception as e:
            logger.warning(f" Default prediction error: {e}")
            return None

    def predict_credit_rating(self, enterprise_data: Dict[str, Any]) -> Optional[str]:
        """Predict credit rating (A/B/C/D)."""
        if not self.is_loaded:
            return None
        try:
            X = self._build_feature_vector(enterprise_data)
            X_scaled = self.scaler.transform(X)
            rating_encoded = self.gb_rating.predict(X_scaled)[0]
            if self.encoders and 'rating_encoder' in self.encoders:
                rating = self.encoders['rating_encoder'].inverse_transform([rating_encoded])[0]
            else:
                rating_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
                rating = rating_map.get(int(rating_encoded), 'C')
            return rating
        except Exception as e:
            logger.warning(f" Rating error: {e}")
            return None

    def predict_risk_level(self, enterprise_data: Dict[str, Any]) -> Optional[str]:
        """Predict risk level (低风险/中风险/高风险)."""
        if not self.is_loaded:
            return None
        try:
            X = self._build_feature_vector(enterprise_data)
            X_scaled = self.scaler.transform(X)
            risk_encoded = self.rf_risk.predict(X_scaled)[0]
            risk_map = {0: 'low', 1: 'medium', 2: 'high'}
            return risk_map.get(int(risk_encoded), 'medium')
        except Exception as e:
            logger.warning(f" Risk prediction error: {e}")
            return None

    def predict_all(self, enterprise_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run all predictions and return combined result."""
        if not self.is_loaded:
            return None
        return {
            'default_probability': self.predict_default_probability(enterprise_data),
            'credit_rating': self.predict_credit_rating(enterprise_data),
            'risk_level': self.predict_risk_level(enterprise_data),
        }


# Global instance
ml_predictor = MLPredictor()


def get_ml_predictor() -> MLPredictor:
    return ml_predictor


def init_ml() -> bool:
    return ml_predictor.load_models()
