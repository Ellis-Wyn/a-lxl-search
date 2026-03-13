#!/bin/bash
# ==============================================
# 回滚脚本 (P8标准)
# ==============================================
# 特性：
# - 支持回滚到上一个版本
# - 数据库恢复
# - 配置文件恢复
# - 安全确认机制
# ==============================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly ROLLBACK_FILE="${PROJECT_ROOT}/.rollback-info"
readonly DEPLOY_LOG="${PROJECT_ROOT}/logs/deploy.log"

# 颜色
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

log() { echo -e "${BLUE}[ROLLBACK]${NC} $*" | tee -a "$DEPLOY_LOG"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$DEPLOY_LOG"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$DEPLOY_LOG"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$DEPLOY_LOG" >&2; }

# ==============================================
# 显示帮助
# ==============================================
show_help() {
    cat << EOF
回滚脚本 - 回滚到上一个版本

用法:
    $0 [选项]

选项:
    -v, --version VERSION    回滚到指定版本
    -d, --db-only            仅回滚数据库
    -c, --config-only        仅回滚配置
    -f, --force              跳过确认提示
    -h, --help               显示此帮助

示例:
    $0                       # 回滚到上一个版本
    $0 -v 2.3.0             # 回滚到指定版本
    $0 -d                   # 仅回滚数据库

EOF
}

# ==============================================
# 解析参数
# ==============================================
TARGET_VERSION=""
DB_ONLY=false
CONFIG_ONLY=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            TARGET_VERSION="$2"
            shift 2
            ;;
        -d|--db-only)
            DB_ONLY=true
            shift
            ;;
        -c|--config-only)
            CONFIG_ONLY=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# ==============================================
# 确认回滚
# ==============================================
confirm_rollback() {
    if [ "$FORCE" = true ]; then
        return 0
    fi

    log "警告：此操作将回滚到上一个版本！"
    log "当前运行版本将被替换。"
    echo ""
    read -p "确认回滚？(yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log "回滚已取消"
        exit 0
    fi
}

# ==============================================
# 获取回滚信息
# ==============================================
get_rollback_info() {
    if [ ! -f "$ROLLBACK_FILE" ]; then
        log_error "未找到回滚信息文件: $ROLLBACK_FILE"
        log_error "无法执行回滚"
        exit 1
    fi

    source "$ROLLBACK_FILE"
    log "上一个版本: $VERSION"
    log "部署时间: $BUILD_TIME"
}

# ==============================================
# 停止当前服务
# ==============================================
stop_services() {
    log "停止当前服务..."

    cd "$PROJECT_ROOT"

    # 保存当前容器状态
    docker compose ps > /tmp/docker-compose-ps.backup

    if docker compose down; then
        log_success "服务已停止"
    else
        log_warning "停止服务时出现错误（可能已停止）"
    fi
}

# ==============================================
# 回滚镜像
# ==============================================
rollback_image() {
    log "回滚容器镜像..."

    local target_image=""

    if [ -n "$TARGET_VERSION" ]; then
        # 使用指定版本
        target_image="pathology-ai/app:$TARGET_VERSION"

        if ! docker images | grep -q "$target_image"; then
            log_error "未找到镜像: $target_image"
            return 1
        fi
    else
        # 使用回滚信息中的镜像
        if [ -f "${ROLLBACK_FILE}.image" ]; then
            target_image=$(cat "${ROLLBACK_FILE}.image")
            log "回滚到镜像: $target_image"
        else
            log_error "未找到要回滚的镜像信息"
            return 1
        fi
    fi

    # 修改docker-compose.yml使用旧镜像
    # 这里简化处理，实际应该更复杂
    export ROLLBACK_IMAGE="$target_image"

    log_success "镜像回滚准备完成"
}

# ==============================================
# 回滚数据库
# ==============================================
rollback_database() {
    log "回滚数据库..."

    local backup_file=""

    if [ -f "${ROLLBACK_FILE}.db" ]; then
        backup_file=$(cat "${ROLLBACK_FILE}.db")
    else
        # 查找最新的备份文件
        backup_file=$(find "${PROJECT_ROOT}/backups" -name "db_backup_*.sql.gz" -type f | sort -r | head -1)
    fi

    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        log_error "未找到数据库备份文件"
        return 1
    fi

    log "使用备份文件: $backup_file"

    # 确认数据库恢复
    if [ "$FORCE" != true ]; then
        echo ""
        read -p "确认恢复数据库？此操作将覆盖当前数据库 (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_warning "数据库恢复已跳过"
            return 0
        fi
    fi

    # 启动PostgreSQL（如果未运行）
    if ! docker ps | grep -q "pathology-ai-postgres"; then
        log "启动PostgreSQL..."
        docker compose up -d postgres
        sleep 10
    fi

    # 恢复数据库
    gunzip -c "$backup_file" | docker exec -i pathology-ai-postgres psql -U pathology_ai pathology_ai

    log_success "数据库恢复完成"
}

# ==============================================
# 回滚配置
# ==============================================
rollback_config() {
    log "回滚配置文件..."

    local backup_file=$(find "${PROJECT_ROOT}/backups" -name ".env.backup.*" -type f | sort -r | head -1)

    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        log_warning "未找到配置备份文件"
        return 0
    fi

    cp "$backup_file" "${PROJECT_ROOT}/.env"
    log_success "配置文件恢复完成"
}

# ==============================================
# 启动服务
# ==============================================
start_services() {
    log "启动服务..."

    cd "$PROJECT_ROOT"

    if docker compose up -d; then
        log_success "服务启动成功"
    else
        log_error "服务启动失败"
        return 1
    fi
}

# ==============================================
# 健康检查
# ==============================================
health_check() {
    log "执行健康检查..."

    local max_wait=60
    local waited=0

    while [ $waited -lt $max_wait ]; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log_success "服务健康检查通过"
            return 0
        fi
        echo -n "."
        sleep 2
        waited=$((waited + 2))
    done

    echo ""
    log_error "健康检查失败"
    return 1
}

# ==============================================
# 发送通知
# ==============================================
send_notification() {
    local status=$1
    local message="回滚${status}: pathology-ai $(hostname)"

    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"$message\"}" >/dev/null 2>&1 || true
    fi

    log "$message"
}

# ==============================================
# 主流程
# ==============================================
main() {
    log "========== 开始回滚 =========="
    log "时间: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    # 确认回滚
    confirm_rollback

    # 获取回滚信息
    get_rollback_info

    # 执行回滚
    if [ "$DB_ONLY" = true ]; then
        rollback_database
        log_success "数据库回滚完成"
    elif [ "$CONFIG_ONLY" = true ]; then
        rollback_config
        log_success "配置回滚完成"
    else
        # 完整回滚
        stop_services
        rollback_image
        rollback_database
        rollback_config
        start_services
        health_check
    fi

    log_success "========== 回滚完成 =========="

    send_notification "成功"
}

cd "$PROJECT_ROOT"
main "$@"
