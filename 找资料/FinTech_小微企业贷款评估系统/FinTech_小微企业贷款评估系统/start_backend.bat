@echo off
echo ============================================
echo  小微贷款智能评估助手 - 后端API服务
echo ============================================
cd /d "E:\金融科技\backend"
echo.
echo [1/2] 检查模型文件...
if exist "models\xgb_default_predictor.pkl" (
    echo   [OK] 模型已就绪
) else (
    echo   [!] 模型未训练，正在训练...
    python train_ml_model.py
)
echo.
echo [2/2] 启动 FastAPI 服务 (http://localhost:8000)...
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
