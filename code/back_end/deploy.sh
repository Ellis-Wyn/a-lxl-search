#!/bin/bash
# ==============================================
# 腾讯云快速部署脚本
# ==============================================
# 使用方法：
#   1. 将项目上传到服务器 /opt/A_lxl_search
#   2. cd /opt/A_lxl_search/code/back_end
#   3. chmod +x deploy.sh
#   4. ./deploy.sh
# ==============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ==============================================
# 1. 环境检查
# ==============================================
print_info "========== 开始环境检查 =========="

# 检查Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    print_success "Docker已安装: $DOCKER_VERSION"
else
    print_error "Docker未安装，请先安装Docker"
    echo "安装命令: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 检查Docker Compose
if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    if command_exists docker-compose; then
        COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | sed 's/,//')
        print_success "Docker Compose已安装: $COMPOSE_VERSION"
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_VERSION=$(docker compose version | awk '{print $4}')
        print_success "Docker Compose已安装: $COMPOSE_VERSION"
        COMPOSE_CMD="docker compose"
    fi
else
    print_error "Docker Compose未安装"
    echo "安装命令: curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose"
    exit 1
fi

# 检查端口占用
check_port() {
    local port=$1
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        print_warning "端口 $port 已被占用"
        return 1
    fi
    return 0
}

check_port 5432 || print_warning "PostgreSQL端口可能被占用，请检查"
check_port 6379 || print_warning "Redis端口可能被占用，请检查"
check_port 8000 || print_warning "API端口可能被占用，请检查"

# ==============================================
# 2. 配置检查
# ==============================================
print_info "========== 检查配置文件 =========="

if [ ! -f .env ]; then
    if [ -f .env.production.template ]; then
        print_warning ".env文件不存在，从模板创建"
        cp .env.production.template .env
        print_error "请编辑.env文件，设置所有必要的配置项"
        print_info "编辑命令: nano .env"
        exit 1
    else
        print_error "缺少.env文件和模板，请创建配置文件"
        exit 1
    fi
else
    print_success ".env文件存在"
fi

# 检查关键配置项
check_env_var() {
    local var_name=$1
    local var_value=$(grep "^${var_name}=" .env | cut -d'=' -f2-)
    if [ -z "$var_value" ] || echo "$var_value" | grep -q '\['; then
        print_warning "配置项 $var_name 可能未设置（值包含括号或为空）"
        return 1
    fi
    return 0
}

check_env_var "POSTGRES_PASSWORD"
check_env_var "SECRET_KEY"
check_env_var "CORS_ORIGINS"

# ==============================================
# 3. 创建必要目录
# ==============================================
print_info "========== 创建必要目录 =========="

mkdir -p logs static database/init
print_success "目录创建完成"

# ==============================================
# 4. 停止旧容器（如果存在）
# ==============================================
print_info "========== 停止旧容器 =========="

if $COMPOSE_CMD ps | grep -q "pathology-ai"; then
    print_info "发现旧容器，正在停止..."
    $COMPOSE_CMD down
    print_success "旧容器已停止"
fi

# ==============================================
# 5. 拉取最新镜像
# ==============================================
print_info "========== 拉取最新镜像 =========="

$COMPOSE_CMD pull
print_success "镜像拉取完成"

# ==============================================
# 6. 构建应用镜像
# ==============================================
print_info "========== 构建应用镜像 =========="

$COMPOSE_CMD build --no-cache
print_success "镜像构建完成"

# ==============================================
# 7. 启动服务
# ==============================================
print_info "========== 启动服务 =========="

$COMPOSE_CMD up -d
print_success "服务启动完成"

# ==============================================
# 8. 等待服务就绪
# ==============================================
print_info "========== 等待服务就绪 =========="

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        print_success "API服务已就绪"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "API服务启动超时，请检查日志"
    $COMPOSE_CMD logs --tail=50 app
    exit 1
fi

# ==============================================
# 9. 检查服务状态
# ==============================================
print_info "========== 检查服务状态 =========="

$COMPOSE_CMD ps

# 显示容器健康状态
echo ""
print_info "容器健康状态:"
docker ps --format "table {{.Names}}\t{{.Status}}"

# ==============================================
# 10. 数据库初始化检查
# ==============================================
print_info "========== 检查数据库 =========="

DB_CHECK=$($COMPOSE_CMD exec -T postgres psql -U pathology_ai -d pathology_ai -c "SELECT COUNT(*) FROM target;" 2>/dev/null || echo "0")

if [ "$DB_CHECK" != "0" ]; then
    TARGET_COUNT=$(echo "$DB_CHECK" | xargs)
    print_success "数据库已初始化，当前有 $TARGET_COUNT 个靶点"
else
    print_warning "数据库可能未初始化，请运行数据迁移"
fi

# ==============================================
# 11. 显示日志（可选）
# ==============================================
print_info "========== 最近日志 =========="

echo ""
echo "=== FastAPI日志 ==="
$COMPOSE_CMD logs --tail=20 app

# ==============================================
# 12. 部署完成
# ==============================================
print_success "========== 部署完成 =========="

echo ""
print_info "访问地址:"
echo "  - 本地API: http://localhost:8000"
echo "  - 健康检查: http://localhost:8000/health"
echo "  - API文档: http://localhost:8000/docs"
echo ""
print_info "常用命令:"
echo "  - 查看日志: $COMPOSE_CMD logs -f"
echo "  - 停止服务: $COMPOSE_CMD down"
echo "  - 重启服务: $COMPOSE_CMD restart"
echo "  - 查看状态: $COMPOSE_CMD ps"
echo ""
print_warning "下一步:"
echo "  1. 配置域名解析指向服务器IP"
echo "  2. 安装并配置Nginx反向代理"
echo "  3. 申请SSL证书"
echo "  详见: code/docs/TENCENT_DEPLOYMENT.md"
echo ""
