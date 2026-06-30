#!/bin/bash
# ============================================================
# FinTech v5 腾讯云一键部署脚本
# 适用: Ubuntu 20.04/22.04 (轻量应用服务器 / CVM)
# 用法: sudo bash tencent_cloud.sh
# ============================================================
set -e

APP_DIR="/opt/fintech-v5"
DOMAIN="${DOMAIN:-localhost}"   # 有域名则 export DOMAIN=your.domain.com
PORT=8000

echo "=== FinTech v5 腾讯云部署 ==="

# 1. 系统更新 + 基础依赖
echo "[1/6] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx git curl

# 2. 创建应用目录
echo "[2/6] 部署应用代码..."
mkdir -p $APP_DIR
cd $APP_DIR

# 如果是从 GitHub 拉取（需要服务器能连 GitHub）
if [ -n "$GIT_REPO" ]; then
    git clone "$GIT_REPO" .
else
    # 手动上传：scp -r 后端服务/ user@ip:$APP_DIR/
    echo "  请将 v5/后端服务/ 目录上传到 $APP_DIR/backend/"
    echo "  请将 v5/kb/ 目录上传到 $APP_DIR/kb/"
fi

# 3. Python 虚拟环境 + 依赖
echo "[3/6] 安装 Python 依赖..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt 2>/dev/null || pip install -q fastapi uvicorn[standard] pydantic numpy pandas scikit-learn xgboost joblib httpx python-dotenv chromadb sentence-transformers reportlab

# 4. 训练 ML 模型（如缺失）
echo "[4/6] 检查 ML 模型..."
if [ ! -f "$APP_DIR/backend/models/xgb_default_predictor.pkl" ]; then
    echo "  模型缺失，开始训练（2-3分钟）..."
    cd $APP_DIR/backend
    python3 train_ml_enhanced.py || echo "  训练跳过（可用时再训）"
fi

# 5. Systemd 服务
echo "[5/6] 配置 systemd 服务..."
cat > /etc/systemd/system/fintech-v5.service << 'EOF'
[Unit]
Description=FinTech v5 SME Loan Assessment API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fintech-v5/backend
Environment=PATH=/opt/fintech-v5/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
ExecStart=/opt/fintech-v5/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Replace env var placeholder
if [ -f "$APP_DIR/.env" ]; then
    KEY=$(grep DEEPSEEK_API_KEY "$APP_DIR/.env" | cut -d= -f2)
    sed -i "s|\${DEEPSEEK_API_KEY}|$KEY|g" /etc/systemd/system/fintech-v5.service
fi

systemctl daemon-reload
systemctl enable fintech-v5
systemctl start fintech-v5

# 6. Nginx 反向代理
echo "[6/6] 配置 Nginx..."
cat > /etc/nginx/sites-available/fintech-v5 << NGINX
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 50M;

    # API 后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    # SSE 流式对话
    location /api/chat/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }

    # 前端静态文件
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/fintech-v5 /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 7. 防火墙
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true

echo ""
echo "============================================"
echo "  部署完成！"
echo "  后端: http://$DOMAIN:8000"
echo "  前端: http://$DOMAIN"
echo ""
echo "  检查状态: systemctl status fintech-v5"
echo "  查看日志: journalctl -u fintech-v5 -f"
echo "  重启服务: systemctl restart fintech-v5"
echo "============================================"
