@echo off
chcp 65001 >nul
title 小微贷款智能评估助手 — 后端API (端口8000)
cd /d "%~dp0后端服务"
if not exist models\xgb_default_predictor.pkl python train_ml_enhanced.py
echo 启动 FastAPI 服务...
echo API文档: http://localhost:8000/docs
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
