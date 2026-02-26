#!/bin/bash
# 在服务器上运行的部署脚本

set -e

echo "在服务器上部署 a.zhai's ToolBox 服务..."
echo "========================================"

APP_NAME="matchbox"
APP_DIR="/opt/$APP_NAME"
LOG_DIR="/var/log/$APP_NAME"

# 1. 复制代码
echo "1. 复制代码到 $APP_DIR..."
if [ -d "/root/nano_banana" ]; then
    cp -r /root/nano_banana/* $APP_DIR/
    chown -R $APP_NAME:$APP_NAME $APP_DIR
    echo "✓ 代码复制完成"
else
    echo "错误: /root/nano_banana 目录不存在"
    exit 1
fi

# 2. 设置Python环境
echo "2. 设置Python环境..."
sudo -u $APP_NAME bash << EOF
    cd $APP_DIR

    # 创建虚拟环境
    python3 -m venv .venv
    source .venv/bin/activate

    # 安装依赖
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn

    # 退出虚拟环境
    deactivate
EOF
echo "✓ Python环境设置完成"

# 3. 检查环境配置
echo "3. 检查环境配置..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "创建默认 .env 文件..."
    cat > $APP_DIR/.env << 'ENVEOF'
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
ENVEOF
    chown $APP_NAME:$APP_NAME $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    echo "⚠ 请编辑 $APP_DIR/.env 文件填写API密钥"
fi
echo "✓ 环境配置检查完成"

# 4. 创建Gunicorn配置
echo "4. 创建Gunicorn配置..."
cat > $APP_DIR/gunicorn_config.py << 'GUNICORNEOF'
bind = "127.0.0.1:1200"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "/var/log/matchbox/access.log"
errorlog = "/var/log/matchbox/error.log"
loglevel = "info"
GUNICORNEOF
chown $APP_NAME:$APP_NAME $APP_DIR/gunicorn_config.py
echo "✓ Gunicorn配置完成"

# 5. 创建systemd服务
echo "5. 创建systemd服务..."
cat > /etc/systemd/system/$APP_NAME.service << 'SERVICEEOF'
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
ExecStart=/opt/matchbox/.venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
echo "✓ systemd服务配置完成"

# 6. 配置Nginx
echo "6. 配置Nginx..."
cat > /etc/nginx/sites-available/$APP_NAME << 'NGINXEOF'
server {
    listen 8080;
    server_name _;

    location /static/ {
        alias /opt/matchbox/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:1200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

# 启用站点
ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/

# 测试并重启Nginx
nginx -t
systemctl restart nginx
echo "✓ Nginx配置完成"

# 7. 启动服务
echo "7. 启动a.zhai's ToolBox服务..."
systemctl enable $APP_NAME
systemctl start $APP_NAME
sleep 2
systemctl status $APP_NAME --no-pager
echo "✓ 服务启动完成"

# 8. 显示部署信息
echo ""
echo "========================================"
echo "🎉 部署完成！"
echo "🌐 访问地址: http://$(hostname -I | awk '{print $1}'):8080"
echo "🔑 默认登录: admin / banana123"
echo ""
echo "🛠️  管理命令:"
echo "   查看状态: systemctl status $APP_NAME"
echo "   查看日志: journalctl -u $APP_NAME -f"
echo "   重启服务: systemctl restart $APP_NAME"
echo ""
echo "⚠  重要: 请编辑 $APP_DIR/.env 文件填写API密钥"
echo "========================================"