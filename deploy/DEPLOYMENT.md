# a.zhai's ToolBox 服务部署指南

## 服务器信息
- **IP地址**: 8.136.3.19
- **操作系统**: Ubuntu 20.04/22.04
- **访问地址**: http://8.136.3.19

## 前置要求

### 本地准备
1. **SSH访问权限**
   ```bash
   # 测试连接
   ssh root@8.136.3.19
   ```

2. **API密钥**
   - 获取 `NANO_BANANA_API_KEY`
   - 如果没有，请联系上游API服务商

3. **环境配置文件**
   ```bash
   # 复制示例文件
   cp .env.example .env

   # 编辑 .env 文件，填写实际值
   # 必须修改：APP_SECRET_KEY 和 NANO_BANANA_API_KEY
   ```

## 部署步骤

### 方法一：使用部署脚本（推荐）

1. **给脚本执行权限**
   ```bash
   chmod +x deploy.sh
   ```

2. **首次部署**
   ```bash
   ./deploy.sh deploy
   ```

3. **其他管理命令**
   ```bash
   # 更新代码
   ./deploy.sh update

   # 查看状态
   ./deploy.sh status

   # 查看实时日志
   ./deploy.sh logs

   # 重启服务
   ./deploy.sh restart

   # 停止服务
   ./deploy.sh stop
   ```

### 方法二：手动部署

如果脚本有问题，可以手动执行以下步骤：

#### 1. 连接到服务器
```bash
ssh root@8.136.3.19
```

#### 2. 更新系统和安装依赖
```bash
apt update && apt upgrade -y
apt install -y python3-pip python3-venv git nginx curl ufw
```

#### 3. 配置防火墙
```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
```

#### 4. 创建应用用户和目录
```bash
useradd -m -s /bin/bash -d /opt/matchbox matchbox
mkdir -p /opt/matchbox
chown -R matchbox:matchbox /opt/matchbox
mkdir -p /var/log/matchbox
chown -R matchbox:matchbox /var/log/matchbox
```

#### 5. 上传代码（从本地执行）
```bash
# 在本地终端执行
rsync -avz --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
    --exclude='data/app.db' ./ root@8.136.3.19:/opt/matchbox/
```

#### 6. 设置Python环境（在服务器上执行）
```bash
cd /opt/matchbox
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

#### 7. 配置环境变量
```bash
# 创建 .env 文件（根据实际情况修改）
cat > .env << EOF
APP_SECRET_KEY=$(openssl rand -hex 32)
APP_USERNAME=admin
APP_PASSWORD=banana123
NANO_BANANA_API_KEY=your-api-key-here
NANO_BANANA_HOST=https://api.grsai.com
PORT=1200
DATA_DIR=data
DB_PATH=data/app.db
MAX_LOGIN_ATTEMPTS=5
LOCK_MINUTES=10
EOF

chown matchbox:matchbox .env
chmod 600 .env
```

#### 8. 配置Gunicorn
```bash
cat > gunicorn_config.py << EOF
bind = "127.0.0.1:1200"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "/var/log/matchbox/access.log"
errorlog = "/var/log/matchbox/error.log"
loglevel = "info"
EOF
```

#### 9. 配置systemd服务
```bash
cat > /etc/systemd/system/matchbox.service << EOF
[Unit]
Description=a.zhai's ToolBox Service
After=network.target

[Service]
User=matchbox
Group=matchbox
WorkingDirectory=/opt/matchbox
Environment="PATH=/opt/matchbox/.venv/bin"
EnvironmentFile=/opt/matchbox/.env
ExecStart=/opt/matchbox/.venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable matchbox
systemctl start matchbox
```

#### 10. 配置Nginx
```bash
cat > /etc/nginx/sites-available/matchbox << EOF
server {
    listen 80;
    server_name 8.136.3.19;

    location /static/ {
        alias /opt/matchbox/static/;
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
EOF

ln -sf /etc/nginx/sites-available/matchbox /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

## 验证部署

### 1. 检查服务状态
```bash
systemctl status matchbox
```

### 2. 检查端口监听
```bash
netstat -tlnp | grep -E ':80|:1200'
```

### 3. 访问应用
- 打开浏览器访问：http://8.136.3.19
- 使用默认账号登录：admin / banana123

### 4. 查看日志
```bash
# 应用日志
journalctl -u matchbox -f

# Nginx访问日志
tail -f /var/log/nginx/access.log

# 应用错误日志
tail -f /var/log/matchbox/error.log
```

## 常见问题

### 1. 502 Bad Gateway
```bash
# 检查Gunicorn是否运行
ps aux | grep gunicorn

# 检查端口
netstat -tlnp | grep :1200

# 重启服务
systemctl restart matchbox
```

### 2. 无法连接数据库
```bash
# 检查数据库文件权限
ls -la /opt/matchbox/data/

# 修复权限
chown -R matchbox:matchbox /opt/matchbox/data
```

### 3. 静态文件404
```bash
# 检查Nginx配置
nginx -t

# 检查静态文件目录
ls -la /opt/matchbox/static/
```

### 4. 内存不足
如果服务器内存较小（<1GB），修改Gunicorn配置：
```python
# 减少工作进程数
workers = 2
```

## 维护命令

### 更新代码
```bash
cd /opt/matchbox
git pull
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart matchbox
```

### 备份数据库
```bash
# 手动备份
cp /opt/matchbox/data/app.db /opt/matchbox/data/app.db.backup.$(date +%Y%m%d)

# 自动备份（添加到crontab）
0 2 * * * cp /opt/matchbox/data/app.db /backup/matchbox.db.$(date +\%Y\%m\%d)
```

### 查看资源使用
```bash
# 内存和CPU
htop

# 磁盘空间
df -h

# 日志文件大小
du -sh /var/log/matchbox/*.log
```

## 安全建议

1. **修改默认密码**
   - 登录后立即修改admin密码
   - 或修改 `.env` 中的 `APP_PASSWORD`

2. **配置SSL证书**（可选）
   ```bash
   apt install certbot python3-certbot-nginx
   certbot --nginx -d your-domain.com
   ```

3. **限制访问IP**（如果需要）
   在Nginx配置中添加：
   ```nginx
   allow 192.168.1.0/24;
   deny all;
   ```

4. **定期更新**
   ```bash
   apt update && apt upgrade -y
   ```

## 故障排除

如果遇到问题，按以下步骤排查：

1. 检查服务状态：`systemctl status matchbox`
2. 查看错误日志：`journalctl -u matchbox -n 50`
3. 检查端口监听：`netstat -tlnp`
4. 测试Nginx配置：`nginx -t`
5. 检查文件权限：`ls -la /opt/matchbox/`

如需帮助，请提供以下信息：
- `journalctl -u matchbox -n 100` 的输出
- `nginx -t` 的结果
- 浏览器控制台错误信息