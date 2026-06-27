#!/bin/bash
# FinTech v5 — macOS/Linux 一键启动脚本
# 用法: bash start.sh

set -e
cd "$(dirname "$0")/后端服务"

echo "=== FinTech v5 启动脚本 ==="

# 1. 检测 Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] 需要 Python 3.10+，请先安装: https://python.org"
    exit 1
fi

# 2. 安装依赖
echo "[1/4] 安装 Python 依赖..."
pip3 install -r requirements.txt -q

# 3. 训练 ML 模型（如缺失）
echo "[2/4] 检查 ML 模型..."
if [ ! -f "models/xgb_default_predictor.pkl" ]; then
    echo "  模型缺失，开始训练（约 2-3 分钟）..."
    python3 train_ml_enhanced.py
else
    echo "  模型已就绪"
fi

# 4. 环境变量提示
echo "[3/4] 检查 .env 配置..."
if [ ! -f ".env" ]; then
    echo "  [提示] 未找到 .env 文件，AI 对话将运行在 Demo 模式"
    echo "  创建 .env 并添加 DEEPSEEK_API_KEY=sk-xxx 以启用 LLM Agent"
fi

# 5. 启动
echo "[4/4] 启动 FastAPI 服务..."
echo "  API 文档: http://localhost:8000/docs"
echo "  前端页面: http://localhost:8000"
echo ""
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
