"""
DeFi 健康度监控 Agent — 一键启动脚本
用法: python run.py
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")

os.chdir(BACKEND)

print("Starting DeFi Health Monitor Agent Demo...")
print(f"   Backend: {BACKEND}")
print()

# 检查 .env 是否存在
env_file = os.path.join(ROOT, ".env")
env_example = os.path.join(ROOT, ".env.example")
if not os.path.exists(env_file):
    print("[INFO] .env file not found.")
    print("   AI natural language analysis is disabled, but dashboard data works.")
    print(f"   Copy {env_example} -> {env_file} and set DEEPSEEK_API_KEY to enable AI.")
    print()

# 使用 uvicorn 启动
args = [
    sys.executable, "-m", "uvicorn",
    "main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
]

subprocess.run(args)
