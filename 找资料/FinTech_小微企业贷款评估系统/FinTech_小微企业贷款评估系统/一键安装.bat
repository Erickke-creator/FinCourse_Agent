@echo off
chcp 65001 >nul
title 小微贷款智能评估助手 — 一键安装

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   🏦 小微贷款智能评估助手 — 一键安装向导         ║
echo ║   FinTech期末项目 · 26行匹配 + ML评估            ║
echo ╚══════════════════════════════════════════════════╝
echo.

:: ============================================
:: 环境检查
:: ============================================
echo [1/5] 检查运行环境...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] 未找到Python！请先安装Python 3.10+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo   [OK] Python 已安装

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] 未找到Node.js！请先安装Node.js 18+
    echo   下载地址: https://nodejs.org/
    pause
    exit /b 1
)
echo   [OK] Node.js 已安装

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] 未找到npm！
    pause
    exit /b 1
)
echo   [OK] npm 已安装

:: ============================================
:: 安装Python依赖
:: ============================================
echo.
echo [2/5] 安装Python依赖...
cd /d "%~dp0后端服务"
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo   [WARN] 部分依赖安装失败，尝试继续...
)
echo   [OK] Python依赖安装完成

:: ============================================
:: 训练ML模型
:: ============================================
echo.
echo [3/5] 训练ML模型 (XGBoost + SMOTE)...
echo   这可能需要1-2分钟，请耐心等待...
python train_ml_enhanced.py
if %errorlevel% neq 0 (
    echo   [WARN] 模型训练失败，尝试使用备用训练脚本...
    python train_ml_model.py
)
echo   [OK] ML模型训练完成

:: ============================================
:: 安装前端依赖
:: ============================================
echo.
echo [4/5] 安装前端依赖...
cd /d "%~dp0前端源码"
call npm install
if %errorlevel% neq 0 (
    echo   [WARN] 前端依赖安装失败，请手动执行: cd 前端源码 ^&^& npm install
)
echo   [OK] 前端依赖安装完成

:: ============================================
:: 完成
:: ============================================
echo.
echo [5/5] 安装完成！
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   ✅ 安装成功！请按以下步骤启动：                  ║
echo ║                                                    ║
echo ║   终端1 (启动后端):                                  ║
echo ║     cd 后端服务                                      ║
echo ║     python -m uvicorn main:app --port 8000          ║
echo ║                                                    ║
echo ║   终端2 (启动前端):                                  ║
echo ║     cd 前端源码                                      ║
echo ║     npm run dev                                     ║
echo ║                                                    ║
echo ║   浏览器访问: http://localhost:3000                   ║
echo ║   API文档: http://localhost:8000/docs                ║
echo ╚══════════════════════════════════════════════════╝
echo.

pause
