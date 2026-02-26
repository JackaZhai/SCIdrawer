#!/bin/bash
# a.zhai's ToolBox 服务部署脚本
# 服务器IP: 8.136.3.19
# 操作系统: Ubuntu 20.04/22.04

set -e  # 遇到错误时退出

echo "🚀 a.zhai's ToolBox 服务部署开始"
echo "========================================"

# 配置变量
SERVER_IP="8.136.3.19"
SERVER_USER="root"  # 默认使用root，建议后续创建专用用户
APP_NAME="matchbox"
APP_DIR="/opt/$APP_NAME"
VENV_DIR="$APP_DIR/.venv"
LOG_DIR="/var/log/$APP_NAME"
APP_PORT="1200"  # Gunicorn内部端口
NGINX_PORT="8080"  # Nginx外部端口（因为80端口可能被占用）

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# 检查参数
if [ $# -eq 0 ]; then
    echo "使用方法: $0 [deploy|update|status|logs|restart|stop] [ssh-port]"
    echo "  deploy   - 首次部署应用"
    echo "  update   - 更新应用代码"
    echo "  status   - 查看服务状态"
    echo "  logs     - 查看应用日志"
    echo "  restart  - 重启服务"
    echo "  stop     - 停止服务"
    echo ""
    echo "示例:"
    echo "  $0 deploy           # 使用默认SSH端口22"
    echo "  $0 deploy 2222      # 使用SSH端口2222"
    echo "  $0 deploy 1200      # 使用SSH端口1200"
    exit 1
fi

# SSH端口参数
SSH_PORT="${2:-22}"  # 默认使用22端口

# 部署函数
deploy() {
    print_info "开始部署 a.zhai's ToolBox 服务到 $SERVER_IP"

    # 1. 连接到服务器并更新系统
    print_info "1. 更新系统软件包..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << 'EOF'
        set -e
        echo "更新 apt 包列表..."
        apt update

        echo "升级系统软件包..."
        apt upgrade -y

        echo "安装必要软件..."
        apt install -y python3-pip python3-venv git nginx curl ufw
EOF
    print_success "系统更新完成"

    # 2. 配置防火墙
    print_info "2. 配置防火墙..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << 'EOF'
        set -e
        echo "配置防火墙规则..."
        ufw allow OpenSSH
        ufw allow 'Nginx Full'
        ufw --force enable
        ufw status
EOF
    print_success "防火墙配置完成"

    # 3. 创建应用目录和用户
    print_info "3. 创建应用用户和目录..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP "bash -c '
        set -e
        APP_NAME=\"matchbox\"
        APP_DIR=\"/opt/\$APP_NAME\"
        LOG_DIR=\"/var/log/\$APP_NAME\"

        # 创建应用用户（如果不存在）
        if ! id -u \$APP_NAME >/dev/null 2>&1; then
            useradd -m -s /bin/bash -d \$APP_DIR \$APP_NAME
            echo \"用户 \$APP_NAME 创建成功\"
        else
            echo \"用户 \$APP_NAME 已存在\"
        fi

        # 创建应用目录
        mkdir -p \$APP_DIR
        chown -R \$APP_NAME:\$APP_NAME \$APP_DIR

        # 创建日志目录
        mkdir -p \$LOG_DIR
        chown -R \$APP_NAME:\$APP_NAME \$LOG_DIR
    '"
    print_success "目录和用户创建完成"

    # 4. 上传应用代码
    print_info "4. 上传应用代码..."
    rsync -avz -e "ssh -p $SSH_PORT" --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
        --exclude='data/app.db' ./ $SERVER_USER@$SERVER_IP:$APP_DIR/
    print_success "代码上传完成"

    # 5. 在服务器上设置虚拟环境和依赖
    print_info "5. 设置Python虚拟环境和依赖..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << EOF
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

            # 安装gunicorn（确保安装）
            pip install gunicorn
USEREOF
EOF
    print_success "虚拟环境和依赖安装完成"

    # 6. 创建环境配置文件
    print_info "6. 创建环境配置文件..."

    # 先读取本地的.env文件（如果存在）
    if [ -f .env ]; then
        print_info "使用本地 .env 文件"
        scp -P $SSH_PORT .env $SERVER_USER@$SERVER_IP:$APP_DIR/.env
    else
        print_info "创建默认 .env 文件"
        ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << EOF
            cat > $APP_DIR/.env << 'ENVEOF'
# a.zhai's ToolBox 服务配置
APP_SECRET_KEY=$(openssl rand -hex 32)
APP_USERNAME=admin
APP_PASSWORD=banana123
NANO_BANANA_API_KEY=your-api-key-here  # 请替换为实际API密钥
NANO_BANANA_HOST=https://api.grsai.com
PORT=$APP_PORT
DATA_DIR=data
DB_PATH=data/app.db
MAX_LOGIN_ATTEMPTS=5
LOCK_MINUTES=10
ENVEOF

            # 设置权限
            chown $APP_NAME:$APP_NAME $APP_DIR/.env
            chmod 600 $APP_DIR/.env
EOF
    fi
    print_success "环境配置完成"

    # 7. 创建Gunicorn配置文件
    print_info "7. 创建Gunicorn配置文件..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << EOF
        cat > $APP_DIR/gunicorn_config.py << 'GUNICORNEOF'
import multiprocessing

# 服务器绑定地址
bind = "127.0.0.1:$APP_PORT"

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超时设置
timeout = 120
keepalive = 5

# 日志配置
accesslog = "$LOG_DIR/access.log"
errorlog = "$LOG_DIR/error.log"
loglevel = "info"

# 进程名称
proc_name = "matchbox"

# 防止文件描述符泄漏
worker_tmp_dir = "/dev/shm"
GUNICORNEOF

        chown $APP_NAME:$APP_NAME $APP_DIR/gunicorn_config.py
EOF
    print_success "Gunicorn配置完成"

    # 8. 创建systemd服务文件
    print_info "8. 创建systemd服务..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << EOF
        cat > /etc/systemd/system/$APP_NAME.service << 'SERVICEEOF'
[Unit]
Description=a.zhai's ToolBox Service
After=network.target
Requires=network.target

[Service]
Type=simple
User=$APP_NAME
Group=$APP_NAME
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/stdout.log
StandardError=append:$LOG_DIR/stderr.log

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$APP_DIR/data $LOG_DIR

[Install]
WantedBy=multi-user.target
SERVICEEOF

        # 重新加载systemd配置
        systemctl daemon-reload
EOF
    print_success "systemd服务配置完成"

    # 9. 配置Nginx
    print_info "9. 配置Nginx反向代理..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << EOF
        # 创建Nginx站点配置
        cat > /etc/nginx/sites-available/$APP_NAME << 'NGINXEOF'
server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_IP;  # 使用IP地址

    # 根目录
    root $APP_DIR;

    # 静态文件
    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # 动态请求代理到Gunicorn
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 禁止访问敏感文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~* \.(db|sqlite|env|pyc)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
NGINXEOF

        # 启用站点
        ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/

        # 移除默认站点
        rm -f /etc/nginx/sites-enabled/default

        # 测试Nginx配置
        nginx -t

        # 重启Nginx
        systemctl restart nginx
EOF
    print_success "Nginx配置完成"

    # 10. 启动服务
    print_info "10. 启动a.zhai's ToolBox服务..."
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << EOF
        # 启用并启动服务
        systemctl enable $APP_NAME
        systemctl start $APP_NAME

        # 检查状态
        sleep 2
        systemctl status $APP_NAME --no-pager
EOF
    print_success "服务启动完成"

    # 11. 显示部署信息
    print_info "部署完成！"
    echo "========================================"
    echo "🌐 访问地址: http://$SERVER_IP"
    echo "🔑 默认登录: admin / banana123"
    echo "📝 日志位置: $LOG_DIR/"
    echo "🛠️  管理命令:"
    echo "   查看状态: systemctl status $APP_NAME"
    echo "   查看日志: journalctl -u $APP_NAME -f"
    echo "   重启服务: systemctl restart $APP_NAME"
    echo "========================================"
}

# 更新函数
update() {
    print_info "更新 a.zhai's ToolBox 服务..."

    # 上传最新代码
    rsync -avz -e "ssh -p $SSH_PORT" --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
        --exclude='data/app.db' ./ $SERVER_USER@$SERVER_IP:$APP_DIR/

    # 重启服务
    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP "systemctl restart $APP_NAME"

    print_success "应用更新完成"
}

# 状态函数
status() {
    print_info "检查 a.zhai's ToolBox 服务状态..."

    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP << 'EOF'
        echo "=== 服务状态 ==="
        systemctl status $APP_NAME --no-pager

        echo -e "\n=== 进程状态 ==="
        ps aux | grep gunicorn | grep -v grep

        echo -e "\n=== 端口监听 ==="
        netstat -tlnp | grep :$APP_PORT || echo "端口$APP_PORT未监听"
        netstat -tlnp | grep :80 || echo "端口80未监听"

        echo -e "\n=== 最近日志 ==="
        journalctl -u $APP_NAME -n 20 --no-pager
EOF
}

# 日志函数
logs() {
    print_info "查看 a.zhai's ToolBox 服务日志..."

    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP "journalctl -u $APP_NAME -f"
}

# 重启函数
restart() {
    print_info "重启 a.zhai's ToolBox 服务..."

    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP "systemctl restart $APP_NAME"

    print_success "服务重启完成"
}

# 停止函数
stop() {
    print_info "停止 a.zhai's ToolBox 服务..."

    ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP "systemctl stop $APP_NAME"

    print_success "服务已停止"
}

# 根据参数执行对应函数
case "$1" in
    deploy)
        deploy
        ;;
    update)
        update
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    restart)
        restart
        ;;
    stop)
        stop
        ;;
    *)
        print_error "未知命令: $1"
        echo "可用命令: deploy, update, status, logs, restart, stop"
        exit 1
        ;;
esac

echo "✨ 操作完成"