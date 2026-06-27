# 成员A — 后端/ML 改进测试记录

## A1: ml_inference.py 改进

### 改动清单
- [x] 添加 `import json` 和 `import logging`
- [x] `_build_feature_vector()` 修复：25 维 → 24 维，对齐 `model_metadata.json`
- [x] 所有 `print()` → `logger.warning()` / `logger.info()`
- [x] `bank_engine.py` 中 `except: pass` → `except Exception as e: logger.warning(...)`
- [x] ML 模型缺失时返回 `ml_enhanced=False`，不崩溃

### 验证
```python
# 模型正常加载
from ml_inference import MLPredictor
p = MLPredictor()
assert p.load_models() == True  # 6个 .pkl 就绪
fv = p._build_feature_vector({'operating_years':3, 'monthly_revenue':50000})
assert fv.shape[1] == 24  # 维度对齐

# 评估集成验证
from bank_engine import evaluate_loan
from models import LoanInput
inp = LoanInput(requested_amount=200000, loan_term=12, industry='manufacturing',
                operating_years=3, monthly_revenue=50000, tax_level='B')
result = evaluate_loan(inp)
assert result.ml_enhanced == True  # ML 已启用
assert result.ml_default_prob is not None
assert result.ml_credit_rating is not None
```

## A2: 模型文件保证

### 现状
- 6 个 .pkl 文件全部存在（xgb_default_predictor, gb_rating_classifier, rf_risk_classifier, rf_rating_classifier, feature_scaler, label_encoders）
- .gitignore 已排除 *.pkl（组员各自训练）
- `启动后端.bat` 自动检测：`if not exist models\xgb_default_predictor.pkl python train_ml_enhanced.py`

### 组员获取模型的方式
```bash
# 方式1：自动训练（推荐）
双击 启动后端.bat  # 自动检测 → 缺失则训练

# 方式2：手动训练
cd 后端服务
python train_ml_enhanced.py
```

## A3: /api/health + /api/evaluate 增强

### /api/health 返回字段
```json
{
  "status": "healthy",
  "version": "5.0.0",
  "banks_count": 30,
  "ml_available": true,
  "kb_available": true,
  "agent_available": false
}
```

### /api/evaluate 返回字段
```json
{
  "success": true,
  "data": {
    "score": 87.0,
    "risk_level": "low",
    "ml_enhanced": true,
    "ml_default_prob": 0.18,
    "ml_credit_rating": "B+",
    "ml_risk_level": "medium",
    "bank_matches": [...],
    "_meta": {
      "evaluation_time_ms": 45,
      "banks_evaluated": 30,
      "engine_version": "5.0.0",
      "ml_available": true
    }
  }
}
```

### 低风险测试用例
```json
POST /api/evaluate
{
  "merchant_type": "enterprise",
  "operating_years": 6,
  "industry": "manufacturing",
  "monthly_revenue": 300000,
  "monthly_fixed_cost": 160000,
  "requested_amount": 1000000,
  "loan_term": 36,
  "tax_level": "A",
  "has_business_license": true,
  "has_stable_bank_flow": true,
  "has_collateral_or_guarantor": true
}
→ 预期: score > 85, risk_level=low, banks_matched=30
```

### 高风险测试用例
```json
POST /api/evaluate
{
  "merchant_type": "individual",
  "operating_years": 1,
  "industry": "entertainment",
  "monthly_revenue": 15000,
  "monthly_fixed_cost": 12000,
  "existing_liabilities": 5000,
  "requested_amount": 500000,
  "loan_term": 6,
  "tax_level": "D",
  "has_business_license": false,
  "has_stable_bank_flow": false,
  "has_overdue_record": true,
  "overdue_count_2yr": 5,
  "has_collateral_or_guarantor": false
}
→ 预期: score < 45, risk_level=high
```

### 验证结果
- [x] /api/health: status ✅ version ✅ ml_available ✅ kb_available ✅ agent_available ✅
- [x] /api/evaluate (低风险): score=87, risk=low, ml_enhanced=true
- [x] /api/evaluate (高风险): score=37, risk=high, ml_enhanced=true
- [x] ML 模型缺失时: ml_enhanced=false, 不崩溃
- [x] _meta 字段: engine_version=5.0.0, ml_available 正确
