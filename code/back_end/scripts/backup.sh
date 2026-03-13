#!/bin/bash
# ==============================================
# 数据库备份脚本 (P8标准)
# ==============================================
# 特性：
# - 自动备份PostgreSQL数据库
# - 支持全量和增量备份
# - 自动清理过期备份
# - 备份验证
# - 压缩存储
# - 远程传输（可选）
# ==============================================

set -euo pipefail

# ==============================================
# 配置
# ==============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
readonly BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
readonly BACKUP_FILE="${BACKUP_DIR}/db_full_${TIMESTAMP}.sql.gz"
readonly LOG_FILE="${PROJECT_ROOT}/logs/backup.log"

# 数据库配置（从.env读取或使用默认值）
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-pathology_ai}"
POSTGRES_DB="${POSTGRES_DB:-pathology_ai}"

# 远程备份配置（可选）
REMOTE_BACKUP_ENABLED=${REMOTE_BACKUP_ENABLED:-false}
REMOTE_BACKUP_HOST="${REMOTE_BACKUP_HOST:-}"
REMOTE_BACKUP_USER="${REMOTE_BACKUP_USER:-}"
REMOTE_BACKUP_PATH="${REMOTE_BACKUP_PATH:-}"

# 颜色
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# ==============================================
# 日志函数
# ==============================================
log() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2; }

# ==============================================
# 创建备份目录
# ==============================================
ensure_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
}

# ==============================================
# 获取数据库密码
# ==============================================
get_db_password() {
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        grep "^POSTGRES_PASSWORD=" "${PROJECT_ROOT}/.env" | cut -d'=' -f2
    else
        echo ""
    fi
}

# ==============================================
# 执行备份
# ==============================================
perform_backup() {
    log "========== 开始数据库备份 =========="
    log "备份文件: $BACKUP_FILE"
    log "数据库: ${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

    local db_password
    db_password=$(get_db_password)

    if [ -z "$db_password" ]; then
        log_warning "未找到数据库密码，尝试不使用密码连接"
    fi

    local start_time=$(date +%s)

    # 使用docker exec执行备份
    if docker ps | grep -q "pathology-ai-postgres"; then
        log "通过Docker执行备份..."

        if docker exec pathology-ai-postgres pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" 2>/dev/null | gzip > "$BACKUP_FILE"; then
            log_success "备份完成"
        else
            log_error "备份失败"
            return 1
        fi
    else
        # 直接连接备份（用于非Docker环境）
        log "通过直连执行备份..."

        local pg_dump_args=(
            -h "${POSTGRES_HOST}"
            -p "${POSTGRES_PORT}"
            -U "${POSTGRES_USER}"
            -d "${POSTGRES_DB}"
            --verbose
        )

        if [ -n "$db_password" ]; then
            export PGPASSWORD="$db_password"
        fi

        if pg_dump "${pg_dump_args[@]}" 2>/dev/null | gzip > "$BACKUP_FILE"; then
            log_success "备份完成"
        else
            log_error "备份失败"
            return 1
        fi

        unset PGPASSWORD
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log "备份耗时: ${duration}秒"

    # 显示文件大小
    local file_size=$(du -h "$BACKUP_FILE" | cut -f1)
    log "文件大小: $file_size"
}

# ==============================================
# 验证备份
# ==============================================
verify_backup() {
    log "验证备份文件..."

    # 检查文件是否存在
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "备份文件不存在"
        return 1
    fi

    # 检查文件大小
    local file_size=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
    if [ "$file_size" -lt 1000 ]; then
        log_error "备份文件过小，可能损坏"
        return 1
    fi

    # 验证gzip文件
    if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
        log_error "备份文件gzip验证失败"
        return 1
    fi

    log_success "备份验证通过"
}

# ==============================================
# 清理过期备份
# ==============================================
cleanup_old_backups() {
    log "清理过期备份（保留${BACKUP_RETENTION_DAYS}天）..."

    local deleted_count=0

    # 删除过期的全量备份
    while IFS= read -r -d '' file; do
        log "删除过期备份: $(basename "$file")"
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
    done < <(find "$BACKUP_DIR" -name "db_full_*.sql.gz" -type f -mtime +${BACKUP_RETENTION_DAYS} -print0 2>/dev/null)

    log_success "清理完成，删除了 ${deleted_count} 个过期备份"
}

# ==============================================
# 上传到远程服务器（可选）
# ==============================================
upload_to_remote() {
    if [ "$REMOTE_BACKUP_ENABLED" != "true" ]; then
        return 0
    fi

    if [ -z "$REMOTE_BACKUP_HOST" ] || [ -z "$REMOTE_BACKUP_USER" ]; then
        log_warning "远程备份未正确配置"
        return 0
    fi

    log "上传备份到远程服务器..."

    local remote_file="${REMOTE_BACKUP_PATH:-/backup}/$(basename "$BACKUP_FILE")"

    if scp "$BACKUP_FILE" "${REMOTE_BACKUP_USER}@${REMOTE_BACKUP_HOST}:${remote_file}"; then
        log_success "远程备份完成"
    else
        log_warning "远程备份失败"
    fi
}

# ==============================================
# 生成备份报告
# ==============================================
generate_report() {
    local report_file="${BACKUP_DIR}/backup_report.txt"

    cat > "$report_file" << EOF
数据库备份报告
================
备份时间: $(date)
备份文件: $(basename "$BACKUP_FILE")
文件大小: $(du -h "$BACKUP_FILE" | cut -f1)
数据库: ${POSTGRES_DB}
服务器: $(hostname)

备份文件列表:
$(ls -lh "$BACKUP_DIR"/db_full_*.sql.gz 2>/dev/null | tail -5)

EOF

    log "备份报告: $report_file"
}

# ==============================================
# 主流程
# ==============================================
main() {
    ensure_backup_dir

    # 检查PostgreSQL是否运行
    if ! docker ps | grep -q "pathology-ai-postgres" && ! pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" >/dev/null 2>&1; then
        log_error "PostgreSQL未运行"
        exit 1
    fi

    # 执行备份
    perform_backup

    # 验证备份
    verify_backup

    # 清理过期备份
    cleanup_old_backups

    # 远程上传
    upload_to_remote

    # 生成报告
    generate_report

    log_success "========== 备份完成 =========="
}

# ==============================================
# 入口
# ==============================================
# 解析命令行参数
case "${1:-backup}" in
    backup)
        main
        ;;
    list)
        log "========== 备份列表 =========="
        ls -lh "$BACKUP_DIR"/db_full_*.sql.gz 2>/dev/null || log_warning "没有找到备份文件"
        ;;
    restore)
        if [ -z "${2:-}" ]; then
            log_error "请指定要恢复的备份文件"
            exit 1
        fi
        log "恢复备份: $2"
        gunzip -c "$2" | docker exec -i pathology-ai-postgres psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"
        log_success "恢复完成"
        ;;
    *)
        echo "用法: $0 {backup|list|restore <backup_file>}"
        exit 1
        ;;
esac
