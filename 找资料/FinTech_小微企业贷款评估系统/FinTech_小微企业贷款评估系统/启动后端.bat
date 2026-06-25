@echo off
chcp 65001 >nul
title 小微贷款智能评估助手 — 后端API

echo.
echo ╔══════════════════════════════════╗
echo ║  启动后端API服务 (端口8000)      ║
echo ╚══════════════════════════════════╝
echo.

cd /d "%~dp0后端服务"

:: 检查模型是否存在
if not exist "models\xgb_default_predictor.pkl" (
    echo [!] 模型未训练，正在训练...
    python train_ml_enhanced.py
)

echo [*] 启动 FastAPI 服务...
echo [*] API文档: http://localhost:8000/docs
echo [*] 健康检查: http://localhost:8000/api/health
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
