# Matchbox AI 生产环境部署指南

## 概述

本指南详细介绍如何将 Matchbox AI 应用部署到具有公网 IP 的生产服务器上。适用于 Ubuntu 20.04/22.04 LTS 系统，也可作为其他 Linux 发行版的参考。

## 部署架构

```
用户浏览器 → HTTPS (443) → Nginx (反向代理) → Gunicorn (WSGI) → Flask 应用
                                     ↑
                              静态文件服务
```

## 一、服务器准备

### 1.1 系统要求
- **操作系统**: Ubuntu 20.04/22.04 LTS（推荐）
- **CPU**: 1核以上
- **内存**: 1GB以上（建议2GB）
- **存储**: 10GB以上可用空间
- **网络**: 公网IP，开放80/443端口

### 1.2 域名准备（可选但推荐）
1. 购买域名（如：example.com）
2. 配置DNS解析：
   - A记录：`@` → 服务器公网IP
   - A记录：`www` → 服务器公网IP

## 二、初始服务器设置

### 2.1 连接到服务器
```bash
ssh root@你的服务器IP
```

### 2.2 更新系统
```bash
apt update && apt upgrade -y
apt install -y curl wget vim git htop ufw
```

### 2.3 创建非root用户（安全建议）
```bash
# 创建新用户
adduser deploy
usermod -aG sudo deploy

# 切换到新用户
su - deploy
```

### 2.4 配置防火墙
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

### 2.5 配置SSH安全（可选）
```bash
# 修改SSH端口
sudo vim /etc/ssh/sshd_config
# 修改: Port 2222（或其他非22端口）
# 修改: PasswordAuthentication no（使用密钥登录）

sudo systemctl restart sshd
```

## 三、安装基础软件

### 3.1 Python环境
```bash
sudo apt install -y python3-pip python3-venv python3-dev build-essential
```

### 3.2 数据库（SQLite已内置，无需额外安装）
```bash
# SQLite已包含在Python中
# 如需PostgreSQL或MySQL，可额外安装
```

### 3.3 Web服务器
```bash
sudo apt install -y nginx
```

## 四、应用部署

### 4.1 创建应用目录
```bash
sudo mkdir -p /opt/matchbox
sudo chown -R deploy:deploy /opt/matchbox
```

### 4.2 上传代码
#### 方法一：使用Git（推荐）
```bash
cd /opt/matchbox
sudo -u deploy git clone https://github.com/your-repo/matchbox.git .
```

#### 方法二：使用rsync（从本地）
```bash
# 在本地终端执行
rsync -avz --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
    --exclude='data/app.db' ./ deploy@服务器IP:/opt/matchbox/
```

### 4.3 设置Python虚拟环境
```bash
cd /opt/matchbox
sudo -u deploy python3 -m venv .venv
sudo -u deploy .venv/bin/pip install --upgrade pip
sudo -u deploy .venv/bin/pip install -r requirements.txt
sudo -u deploy .venv/bin/pip install gunicorn
```

### 4.4 配置环境变量
```bash
cd /opt/matchbox
sudo -u deploy cp .env.example .env
sudo -u deploy vim .env
```

#### 必需配置项：
```env
# Flask会话密钥（必须修改！）
APP_SECRET_KEY=your-random-secret-key-here

# 上游API密钥
NANO_BANANA_API_KEY=your-api-key-from-upstream

# 其他配置（根据需要修改）
APP_USERNAME=admin
APP_PASSWORD=strong-password-here  # 必须修改！
NANO_BANANA_HOST=https://api.grsai.com
PORT=1200
DATA_DIR=data
DB_PATH=data/app.db
MAX_LOGIN_ATTEMPTS=5
LOCK_MINUTES=10
```

#### 生成安全密钥：
```bash
# 生成32位随机密钥
openssl rand -hex 32
```

### 4.5 初始化数据库
```bash
cd /opt/matchbox
sudo -u deploy .venv/bin/python -c "from app import init_db; init_db()"
```

## 五、配置Gunicorn（应用服务器）

### 5.1 创建Gunicorn配置文件
```bash
cd /opt/matchbox
sudo -u deploy cat > gunicorn_config.py << EOF
import multiprocessing

# 绑定地址和端口
bind = "127.0.0.1:1200"

# 工作进程数 = CPU核心数 * 2 + 1
workers = multiprocessing.cpu_count() * 2 + 1

# 工作进程类型
worker_class = "sync"

# 超时设置
timeout = 120
keepalive = 5

# 日志配置
accesslog = "/var/log/matchbox/access.log"
errorlog = "/var/log/matchbox/error.log"
loglevel = "info"

# 进程命名
proc_name = "matchbox"

# 最大请求数（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50
EOF
```

### 5.2 创建systemd服务
```bash
sudo vim /etc/systemd/system/matchbox.service
```

内容如下：
```ini
[Unit]
Description=Matchbox AI Service
After=network.target
Requires=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/opt/matchbox
Environment="PATH=/opt/matchbox/.venv/bin"
EnvironmentFile=/opt/matchbox/.env

# 启动命令
ExecStart=/opt/matchbox/.venv/bin/gunicorn -c gunicorn_config.py app:app

# 重启策略
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/matchbox/data

# 资源限制（根据需要调整）
MemoryLimit=512M
CPUQuota=100%

# 日志配置
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5.3 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable matchbox
sudo systemctl start matchbox

# 检查状态
sudo systemctl status matchbox
```

## 六、配置Nginx（Web服务器）

### 6.1 创建Nginx站点配置
```bash
sudo vim /etc/nginx/sites-available/matchbox
```

根据有无域名选择配置：

#### 选项A：使用IP访问
```nginx
server {
    listen 80;
    server_name 你的服务器IP;

    # 静态文件服务
    location /static/ {
        alias /opt/matchbox/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 反向代理到Gunicorn
    location / {
        proxy_pass http://127.0.0.1:1200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 安全头部
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

#### 选项B：使用域名访问
```nginx
server {
    listen 80;
    server_name 你的域名.com www.你的域名.com;

    # 重定向HTTP到HTTPS（配置SSL后启用）
    # return 301 https://$server_name$request_uri;

    # 静态文件服务
    location /static/ {
        alias /opt/matchbox/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:1200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 安全头部
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 6.2 启用站点配置
```bash
sudo ln -sf /etc/nginx/sites-available/matchbox /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

## 七、配置SSL证书（HTTPS）

### 7.1 安装Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 7.2 获取证书（使用域名）
```bash
# 使用域名获取证书
sudo certbot --nginx -d 你的域名.com -d www.你的域名.com

# 自动续期测试
sudo certbot renew --dry-run
```

### 7.3 配置自动续期
```bash
# 查看cron任务
sudo crontab -l

# 通常Certbot会自动配置续期
# 手动添加（如果需要）：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 八、日志配置

### 8.1 创建日志目录
```bash
sudo mkdir -p /var/log/matchbox
sudo chown -R deploy:deploy /var/log/matchbox
sudo chmod 755 /var/log/matchbox
```

### 8.2 日志轮转配置
```bash
sudo vim /etc/logrotate.d/matchbox
```

内容：
```bash
/var/log/matchbox/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 deploy deploy
    sharedscripts
    postrotate
        systemctl reload matchbox > /dev/null 2>/dev/null || true
    endscript
}
```

## 九、安全加固

### 9.1 文件权限检查
```bash
# 检查关键文件权限
sudo ls -la /opt/matchbox/
sudo ls -la /opt/matchbox/.env
sudo ls -la /opt/matchbox/data/

# 确保.env文件权限正确
sudo chmod 600 /opt/matchbox/.env
sudo chown deploy:deploy /opt/matchbox/.env
```

### 9.2 禁用不必要的服务
```bash
# 检查运行的服务
sudo systemctl list-units --type=service

# 禁用不需要的服务（根据实际情况）
# sudo systemctl disable apache2
# sudo systemctl disable mysql
```

### 9.3 配置Fail2ban（防暴力破解）
```bash
sudo apt install -y fail2ban

# 创建Nginx防爬虫配置
sudo vim /etc/fail2ban/jail.local
```

添加：
```ini
[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/access.log
maxretry = 2
```

重启：
```bash
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

## 十、部署验证

### 10.1 检查服务状态
```bash
# 检查所有相关服务
sudo systemctl status matchbox
sudo systemctl status nginx
sudo systemctl status certbot.timer
```

### 10.2 检查端口监听
```bash
sudo netstat -tlnp | grep -E ':80|:443|:1200'
```

### 10.3 测试访问
```bash
# 测试HTTP响应
curl -I http://你的服务器IP或域名

# 测试HTTPS（如果配置了）
curl -I https://你的域名.com
```

### 10.4 功能测试
1. 访问应用首页
2. 使用管理员账号登录
3. 测试API密钥添加
4. 测试图像生成功能
5. 测试聊天功能

## 十一、监控和维护

### 11.1 监控命令
```bash
# 实时查看应用日志
sudo journalctl -u matchbox -f

# 查看Nginx访问日志
sudo tail -f /var/log/nginx/access.log

# 查看错误日志
sudo tail -f /var/log/matchbox/error.log

# 资源监控
htop
df -h
```

### 11.2 备份策略
#### 数据库备份
```bash
# 手动备份
sudo cp /opt/matchbox/data/app.db /opt/matchbox/data/app.db.backup.$(date +%Y%m%d)

# 自动备份（添加到crontab）
# 每天凌晨2点备份
0 2 * * * cp /opt/matchbox/data/app.db /backup/matchbox.db.$(date +\%Y\%m\%d)
```

#### 配置文件备份
```bash
# 备份重要配置
sudo tar -czf /backup/matchbox-config-$(date +%Y%m%d).tar.gz \
    /opt/matchbox/.env \
    /etc/nginx/sites-available/matchbox \
    /etc/systemd/system/matchbox.service
```

### 11.3 更新应用
```bash
# 1. 备份当前版本
cd /opt/matchbox
sudo -u deploy cp -r data data.backup.$(date +%Y%m%d)

# 2. 拉取最新代码
sudo -u deploy git pull

# 3. 更新依赖
sudo -u deploy .venv/bin/pip install -r requirements.txt

# 4. 重启服务
sudo systemctl restart matchbox

# 5. 验证更新
sudo systemctl status matchbox
curl -I http://localhost:1200/health
```

## 十二、故障排除

### 12.1 常见问题

#### 问题1：502 Bad Gateway
```bash
# 检查Gunicorn是否运行
ps aux | grep gunicorn

# 检查端口监听
netstat -tlnp | grep :1200

# 查看错误日志
sudo journalctl -u matchbox -n 50

# 重启服务
sudo systemctl restart matchbox
```

#### 问题2：静态文件404
```bash
# 检查Nginx配置
sudo nginx -t

# 检查静态文件目录
ls -la /opt/matchbox/static/

# 检查Nginx错误日志
sudo tail -f /var/log/nginx/error.log
```

#### 问题3：数据库权限问题
```bash
# 检查数据库文件权限
ls -la /opt/matchbox/data/

# 修复权限
sudo chown -R deploy:deploy /opt/matchbox/data
sudo chmod 755 /opt/matchbox/data
```

#### 问题4：内存不足
修改Gunicorn配置减少工作进程：
```python
# gunicorn_config.py
workers = 2  # 改为2个进程
```

### 12.2 调试模式
如果需要调试，可以临时启用开发模式：
```bash
# 停止systemd服务
sudo systemctl stop matchbox

# 手动启动开发服务器
cd /opt/matchbox
sudo -u deploy .venv/bin/python app.py

# 测试后恢复
sudo systemctl start matchbox
```

## 十三、性能优化

### 13.1 Gunicorn优化
根据服务器配置调整：
```python
# 针对1GB内存服务器
workers = 3
threads = 2
worker_class = "gthread"

# 针对2GB+内存服务器
workers = (CPU核心数 × 2) + 1
```

### 13.2 Nginx优化
```nginx
# /etc/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;

# 启用gzip压缩
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
```

### 13.3 数据库优化
SQLite生产环境建议：
```bash
# 定期清理日志
echo ".vacuum" | sqlite3 /opt/matchbox/data/app.db

# 备份时优化
sqlite3 /opt/matchbox/data/app.db "VACUUM;"
```

## 十四、扩展部署

### 14.1 多服务器部署（可选）
对于高流量场景：
1. 应用服务器集群（多台 + 负载均衡）
2. 独立数据库服务器（PostgreSQL/MySQL）
3. Redis缓存服务器
4. CDN静态文件加速

### 14.2 Docker部署（可选）
```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn
COPY . .
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
```

## 总结

成功部署后，你应该能够：
1. 通过域名或IP访问Matchbox AI服务
2. 使用HTTPS安全连接（如果配置了SSL）
3. 管理员账号正常登录
4. AI图像生成和聊天功能正常工作
5. 查看实时日志监控应用状态

定期维护建议：
- 每周检查日志文件大小
- 每月备份数据库
- 每季度更新系统和Python包
- 监控服务器资源使用情况

如有问题，请参考日志文件或联系系统管理员。