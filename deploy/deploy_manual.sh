#!/bin/bash
# 手动部署脚本 - 从失败的地方继续

set -e

SERVER_IP="8.136.3.19"
SERVER_USER="root"
APP_NAME="matchbox"
APP_DIR="/opt/$APP_NAME"
APP_PORT="1200"

echo "继续部署 a.zhai's ToolBox 服务..."
echo "========================================"

# 1. 创建应用目录和用户
echo "1. 创建应用目录和用户..."
ssh -p 22 $SERVER_USER@$SERVER_IP << 'EOF'
    set -e
    APP_NAME="matchbox"
    APP_DIR="/opt/$APP_NAME"

    # 创建应用用户（如果不存在）
    if ! id -u $APP_NAME >/dev/null 2>&1; then
        useradd -m -s /bin/bash -d $APP_DIR $APP_NAME
        echo "用户 $APP_NAME 创建成功"
    else
        echo "用户 $APP_NAME 已存在"
    fi

    # 创建应用目录
    mkdir -p $APP_DIR
    chown -R $APP_NAME:$APP_NAME $APP_DIR

    # 创建日志目录
    mkdir -p /var/log/$APP_NAME
    chown -R $APP_NAME:$APP_NAME /var/log/$APP_NAME
EOF
echo "✓ 目录和用户创建完成"

# 2. 上传应用代码
echo "2. 上传应用代码..."
# 先创建必要的目录结构
ssh -p 22 $SERVER_USER@$SERVER_IP "mkdir -p $APP_DIR/{static,templates,data,src}"

# 上传主要文件
scp -P 22 -r app.py requirements.txt .env $SERVER_USER@$SERVER_IP:$APP_DIR/

# 上传目录
for dir in static templates src; do
    if [ -d "$dir" ]; then
        echo "上传 $dir 目录..."
        scp -P 22 -r "$dir" $SERVER_USER@$SERVER_IP:$APP_DIR/
    fi
done

echo "✓ 代码上传完成"

# 3. 设置Python环境
echo "3. 设置Python虚拟环境和依赖..."
ssh -p 22 $SERVER_USER@$SERVER_IP << EOF
    set -e
    cd $APP_DIR

    # 切换到应用用户
    sudo -u $APP_NAME bash << 'USEREOF'
        cd $APP_DIR

        # 创建虚拟环境
        python3 -m venv .venv
        source .venv/bin/activate

        # 升级pip
        pip install --upgrade pip

        # 安装依赖
        if [ -f requirements.txt ]; then
            pip install -r requirements.txt
        else
            echo "警告: requirements.txt 不存在"
            pip install flask gunicorn
        fi

        # 安装gunicorn
        pip install gunicorn
USEREOF
EOF
echo "✓ 虚拟环境和依赖安装完成"

# 4. 配置环境变量
echo "4. 配置环境变量..."
if [ -f .env ]; then
    echo "使用本地 .env 文件"
    scp -P 22 .env $SERVER_USER@$SERVER_IP:$APP_DIR/.env
else
    echo "创建默认 .env 文件"
    ssh -p 22 $SERVER_USER@$SERVER_IP << EOF
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
EOF
fi
echo "✓ 环境配置完成"

# 5. 创建Gunicorn配置
echo "5. 创建Gunicorn配置..."
ssh -p 22 $SERVER_USER@$SERVER_IP << EOF
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
EOF
echo "✓ Gunicorn配置完成"

# 6. 创建systemd服务
echo "6. 创建systemd服务..."
ssh -p 22 $SERVER_USER@$SERVER_IP << EOF
    cat > /etc/systemd/system/$APP_NAME.service << 'SERVICEEOF'
[Unit]
Description=a.zhai's ToolBox Service
After=network.target

[Service]
Type=simple
User=$APP_NAME
Group=$APP_NAME
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

    systemctl daemon-reload
EOF
echo "✓ systemd服务配置完成"

# 7. 配置Nginx（使用8080端口）
echo "7. 配置Nginx..."
ssh -p 22 $SERVER_USER@$SERVER_IP << EOF
    # 创建Nginx站点配置
    cat > /etc/nginx/sites-available/$APP_NAME << 'NGINXEOF'
server {
    listen 8080;
    server_name $SERVER_IP;

    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:1200;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINXEOF

    # 启用站点
    ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/

    # 测试并重启Nginx
    nginx -t
    systemctl restart nginx
EOF
echo "✓ Nginx配置完成"

# 8. 启动服务
echo "8. 启动a.zhai's ToolBox服务..."
ssh -p 22 $SERVER_USER@$SERVER_IP << EOF
    systemctl enable $APP_NAME
    systemctl start $APP_NAME
    sleep 2
    systemctl status $APP_NAME --no-pager
EOF
echo "✓ 服务启动完成"

# 9. 显示部署信息
echo ""
echo "========================================"
echo "🎉 部署完成！"
echo "🌐 访问地址: http://$SERVER_IP:8080"
echo "🔑 默认登录: admin / banana123"
echo "🛠️  管理命令:"
echo "   查看状态: systemctl status $APP_NAME"
echo "   查看日志: journalctl -u $APP_NAME -f"
echo "   重启服务: systemctl restart $APP_NAME"
echo "========================================"