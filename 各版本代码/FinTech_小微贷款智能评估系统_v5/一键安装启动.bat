@echo off
chcp 65001 >nul
title 小微贷款智能评估助手 v4.0 — 一键安装

echo.
echo ==============================================
echo   FinTech期末项目 — 小微贷款智能评估助手 v4.0
echo   30银行匹配 + 1159企业搜索 + AI对话顾问
echo ==============================================
echo.

echo [1/4] 安装Python依赖...
cd /d "%~dp0后端服务"
pip install -r requirements.txt -q
echo [OK]

echo.
echo [2/4] 训练ML模型（首次必须，约2分钟）...
python train_ml_enhanced.py
echo [OK]

echo.
echo [3/4] 安装前端依赖...
cd /d "%~dp0前端源码"
call npm install
echo [OK]

echo.
echo [4/4] 安装完成！
echo.
echo 请打开两个终端分别运行:
echo   终端1: 双击 "启动后端.bat"
echo   终端2: 双击 "启动前端.bat"
echo.
echo 浏览器访问: http://localhost:3000
echo API文档: http://localhost:8000/docs
echo.
pause
