#!/bin/bash
# 最终修复脚本 - 在服务器上运行

echo "=== a.zhai's ToolBox 最终修复 ==="
echo "========================================"

APP_DIR="/opt/matchbox"

# 1. 停止所有相关进程
echo "1. 停止现有进程..."
pkill -f gunicorn 2>/dev/null || true
systemctl stop matchbox 2>/dev/null || true

# 2. 安装系统级依赖
echo "2. 安装系统依赖..."
apt update
apt install -y python3-cryptography python3-requests

# 3. 创建简化的requirements.txt
echo "3. 创建简化依赖配置..."
cat > $APP_DIR/requirements_simple.txt << EOF
Flask==3.0.3
gunicorn==23.0.0
EOF

# 4. 设置Python环境（使用系统包）
echo "4. 设置Python环境..."
cd $APP_DIR
sudo -u matchbox bash << EOF
    cd $APP_DIR
    # 重新创建干净的虚拟环境
    rm -rf .venv 2>/dev/null || true
    python3 -m venv .venv
    source .venv/bin/activate

    # 只安装必要的包
    pip install --upgrade pip
    pip install -r requirements_simple.txt

    # 创建符号链接到系统包
    ln -sf /usr/lib/python3/dist-packages/cryptography .venv/lib/python3.10/site-packages/ 2>/dev/null || true
    ln -sf /usr/lib/python3/dist-packages/requests .venv/lib/python3.10/site-packages/ 2>/dev/null || true

    deactivate
EOF

# 5. 创建简化的Gunicorn配置
echo "5. 创建Gunicorn配置..."
cat > $APP_DIR/gunicorn_simple.py << EOF
import multiprocessing

bind = "127.0.0.1:1200"
workers = 2
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "/var/log/matchbox/access.log"
errorlog = "/var/log/matchbox/error.log"
loglevel = "info"
EOF

chown matchbox:matchbox $APP_DIR/gunicorn_simple.py

# 6. 创建启动脚本
echo "6. 创建启动脚本..."
cat > $APP_DIR/start.sh << 'EOF'
#!/bin/bash
cd /opt/matchbox
source .venv/bin/activate
exec gunicorn -c gunicorn_simple.py app:app
EOF

chmod +x $APP_DIR/start.sh
chown matchbox:matchbox $APP_DIR/start.sh

# 7. 更新systemd服务
echo "7. 更新systemd服务..."
cat > /etc/systemd/system/matchbox.service << EOF
[Unit]
Description=a.zhai's ToolBox Service
After=network.target

[Service]
Type=simple
User=matchbox
Group=matchbox
WorkingDirectory=/opt/matchbox
Environment="PATH=/opt/matchbox/.venv/bin"
EnvironmentFile=/opt/matchbox/.env
ExecStart=/opt/matchbox/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# 8. 确保.env文件存在
echo "8. 检查环境配置..."
if [ ! -f "$APP_DIR/.env" ]; then
    cat > $APP_DIR/.env << EOF
APP_SECRET_KEY=f090e80b8ad1abc9208ad874a0e94bc13d9d283f5bcdfce908343c16d712a283
APP_USERNAME=admin
APP_PASSWORD=banana123
NANO_BANANA_API_KEY=your-actual-api-key-here
NANO_BANANA_HOST=https://api.grsai.com
PORT=1200
DATA_DIR=data
DB_PATH=data/app.db
MAX_LOGIN_ATTEMPTS=5
LOCK_MINUTES=10
EOF
    chown matchbox:matchbox $APP_DIR/.env
    chmod 600 $APP_DIR/.env
fi

# 9. 确保日志目录
echo "9. 创建日志目录..."
mkdir -p /var/log/matchbox
chown matchbox:matchbox /var/log/matchbox

# 10. 启动服务
echo "10. 启动服务..."
systemctl enable matchbox
systemctl restart matchbox

# 11. 检查状态
echo "11. 检查部署状态..."
sleep 3
echo "=== 服务状态 ==="
systemctl status matchbox --no-pager | head -20

echo "=== 端口监听 ==="
netstat -tlnp | grep :1200 2>/dev/null || echo "端口1200未监听"

echo "=== 进程检查 ==="
ps aux | grep gunicorn | grep -v grep || echo "Gunicorn未运行"

echo ""
echo "========================================"
echo "如果服务启动失败，请检查："
echo "1. 日志: journalctl -u matchbox -n 50"
echo "2. 应用导入: cd /opt/matchbox && sudo -u matchbox bash -c 'source .venv/bin/activate && python -c \"import sys; sys.path.insert(0, \\\".\\\"); from app import app; print(\\\"OK\\\")\"'"
echo "3. 手动启动: cd /opt/matchbox && sudo -u matchbox ./start.sh"
echo ""
echo "访问地址: http://$(hostname -I | awk '{print $1}'):8081"
echo "默认账号: admin / banana123"
echo "========================================"