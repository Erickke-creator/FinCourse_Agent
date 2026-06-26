@echo off
chcp 65001 >nul
title 小微贷款智能评估助手 — 前端 (端口3000)
cd /d "%~dp0前端源码"
if not exist node_modules call npm install
echo 启动 Vite 开发服务器...
echo 访问地址: http://localhost:3000
call npm run dev
pause
