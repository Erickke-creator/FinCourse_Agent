@echo off
chcp 65001 >nul
title 小微贷款智能评估助手 — 前端

echo.
echo ╔══════════════════════════════════╗
echo ║  启动前端开发服务器 (端口3000)   ║
echo ╚══════════════════════════════════╝
echo.
cd /d "%~dp0前端源码"
echo [*] 检查依赖...
if not exist "node_modules" (
    echo [!] 正在安装依赖...
    call npm install
)
echo [*] 启动 Vite 开发服务器...
echo [*] 访问地址: http://localhost:3000
echo.
call npm run dev
pause
