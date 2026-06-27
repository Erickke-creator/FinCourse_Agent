# FinTech v5 — Docker 一键部署
FROM python:3.11-slim

WORKDIR /app
COPY 后端服务/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 后端服务/ ./backend/
WORKDIR /app/backend

# 自动训练 ML 模型（如缺失）
RUN python -c "import os; os.system('python train_ml_enhanced.py') if not os.path.exists('models/xgb_default_predictor.pkl') else None" || true

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
