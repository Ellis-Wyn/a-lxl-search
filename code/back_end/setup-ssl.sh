#!/bin/bash
# ==============================================
# SSL证书自动配置脚本
# ==============================================
# 使用方法：
#   chmod +x setup-ssl.sh
#   sudo ./setup-ssl.sh api.your-domain.com
# ==============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    print_error "请使用sudo运行此脚本"
    exit 1
fi

# 获取域名参数
DOMAIN=${1:-""}
if [ -z "$DOMAIN" ]; then
    print_error "请提供域名作为参数"
    echo "使用方法: sudo ./setup-ssl.sh api.your-domain.com"
    exit 1
fi

print_info "========== 开始配置SSL证书 =========="
print_info "域名: $DOMAIN"

# ==============================================
# 1. 检查Nginx是否已安装
# ==============================================
print_info "检查Nginx..."

if ! command -v nginx &> /dev/null; then
    print_info "安装Nginx..."
    apt update
    apt install -y nginx
    print_success "Nginx安装完成"
else
    print_success "Nginx已安装"
fi

# ==============================================
# 2. 检查域名解析
# ==============================================
print_info "检查域名解析..."

# 获取服务器公网IP
SERVER_IP=$(curl -s -4 ifconfig.me || curl -s -4 icanhazip.com)
print_info "服务器IP: $SERVER_IP"

# 检查域名解析
DOMAIN_IP=$(dig +short $DOMAIN | head -n 1)
if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    print_warning "域名解析检查失败或未生效"
    print_warning "域名 $DOMAIN 解析到: $DOMAIN_IP"
    print_warning "服务器IP: $SERVER_IP"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "域名解析正确"
fi

# ==============================================
# 3. 创建Nginx配置
# ==============================================
print_info "创建Nginx配置..."

NGINX_CONF="/etc/nginx/sites-available/pathology-api"
cat > "$NGINX_CONF" << EOF
# HTTP配置 - 用于SSL验证
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS配置
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL证书（certbot自动配置）
    # ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000" always;

    access_log /var/log/nginx/pathology-api-access.log;
    error_log /var/log/nginx/pathology-api-error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

print_success "Nginx配置已创建: $NGINX_CONF"

# ==============================================
# 4. 启用配置
# ==============================================
print_info "启用Nginx配置..."

ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/

# 删除默认配置（可选）
# rm -f /etc/nginx/sites-enabled/default

# 测试配置
if nginx -t; then
    print_success "Nginx配置测试通过"
    systemctl reload nginx
else
    print_error "Nginx配置测试失败"
    exit 1
fi

# ==============================================
# 5. 安装Certbot
# ==============================================
print_info "检查Certbot..."

if ! command -v certbot &> /dev/null; then
    print_info "安装Certbot..."
    apt install -y certbot python3-certbot-nginx
    print_success "Certbot安装完成"
else
    print_success "Certbot已安装"
fi

# ==============================================
# 6. 创建验证目录
# ==============================================
print_info "创建验证目录..."

mkdir -p /var/www/html/.well-known/acme-challenge
chown -R www-data:www-data /var/www/html

# ==============================================
# 7. 申请SSL证书
# ==============================================
print_info "申请SSL证书..."
print_warning "你将需要输入邮箱地址并同意服务条款"

# 询问邮箱
read -p "请输入邮箱地址（用于证书到期提醒）: " EMAIL

if [ -z "$EMAIL" ]; then
    print_error "邮箱地址不能为空"
    exit 1
fi

# 申请证书
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$EMAIL" --redirect

if [ $? -eq 0 ]; then
    print_success "SSL证书申请成功！"
else
    print_error "SSL证书申请失败"
    print_info "请手动运行: certbot --nginx -d $DOMAIN"
    exit 1
fi

# ==============================================
# 8. 配置自动续期
# ==============================================
print_info "配置证书自动续期..."

systemctl enable certbot.timer
systemctl start certbot.timer

print_success "证书自动续期已启用"

# ==============================================
# 9. 验证配置
# ==============================================
print_info "验证HTTPS配置..."

if curl -sf "https://$DOMAIN/health" >/dev/null 2>&1; then
    print_success "HTTPS配置成功！"
else
    print_warning "健康检查失败，请检查API是否运行"
    print_info "检查命令: curl http://localhost:8000/health"
fi

# ==============================================
# 10. 显示证书信息
# ==============================================
print_info "========== 证书信息 =========="

certbot certificates

# ==============================================
# 11. 完成
# ==============================================
print_success "========== SSL配置完成 =========="

echo ""
print_info "访问地址:"
echo "  - HTTP:  http://$DOMAIN (自动跳转HTTPS)"
echo "  - HTTPS: https://$DOMAIN"
echo "  - API:   https://$DOMAIN/health"
echo "  - 文档:  https://$DOMAIN/docs"
echo ""
print_info "常用命令:"
echo "  - 查看证书状态: certbot certificates"
echo "  - 手动续期:     certbot renew"
echo "  - 测试续期:     certbot renew --dry-run"
echo "  - 查看Nginx日志: tail -f /var/log/nginx/pathology-api-error.log"
echo ""
print_warning "下一步:"
echo "  1. 更新前端API配置: baseURL = 'https://$DOMAIN'"
echo "  2. 重新部署前端到Vercel"
echo ""
