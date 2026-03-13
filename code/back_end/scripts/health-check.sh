#!/bin/bash
# ==============================================
# 健康检查脚本 (P8标准)
# ==============================================
# 特性：
# - 多维度健康检查
# - 依赖检查（数据库、Redis）
# - 性能指标采集
# - 告警输出
# - 支持JSON格式输出（用于监控系统）
# ================================================

set -euo pipefail

# ==============================================
# 配置
# ==============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly API_URL="${API_URL:-http://localhost:8000}"
const TIMEOUT=10

# 颜色
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
const NC='\033[0m'

# 健康状态
HEALTHY=0
UNHEALTHY=0
WARNING=0

# JSON输出开关
JSON_OUTPUT=false

# ==============================================
# 解析参数
# ==============================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --url)
            API_URL="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 [--json] [--url URL]"
            echo ""
            echo "选项:"
            echo "  --json       以JSON格式输出结果"
            echo "  --url URL    指定API URL（默认: http://localhost:8000）"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# ==============================================
# 检查函数
# ==============================================

check_api() {
    local name="API"
    local status="pass"
    local message=""
    local response_time=0

    local start_time=$(date +%s%3N)

    if response=$(curl -sf -w "\n%{http_code}" "${API_URL}/health" --max-time $TIMEOUT 2>/dev/null); then
        local http_code=$(echo "$response" | tail -1)
        local body=$(echo "$response" | head -n -1)

        local end_time=$(date +%s%3N)
        response_time=$((end_time - start_time))

        if [ "$http_code" = "200" ]; then
            message="OK (${response_time}ms)"
        else
            status="fail"
            message="HTTP ${http_code}"
            UNHEALTHY=$((UNHEALTHY + 1))
        fi
    else
        status="fail"
        message="连接失败"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi

    echo "check_${name}=${status}:${message}:${response_time}"

    # JSON输出
    if [ "$JSON_OUTPUT" = true ]; then
        json_checks+=("\"${name}\":{\"status\":\"${status}\",\"message\":\"${message}\",\"response_time\":${response_time}}")
    fi
}

check_database() {
    local name="PostgreSQL"
    local status="pass"
    local message=""
    local response_time=0

    local start_time=$(date +%s%3N)

    if docker exec pathology-ai-postgres pg_isready -U pathology_ai >/dev/null 2>&1; then
        local end_time=$(date +%s%3N)
        response_time=$((end_time - start_time))

        # 检查连接数
        local connections=$(docker exec pathology-ai-postgres psql -U pathology_ai -d pathology_ai -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "0")
        local max_connections=50
        local usage=$((connections * 100 / max_connections))

        if [ $usage -gt 80 ]; then
            status="warn"
            message="连接数过高 (${connections}/${max_connections}, ${usage}%)"
            WARNING=$((WARNING + 1))
        else
            message="OK (${connections} 连接, ${response_time}ms)"
        fi
    else
        status="fail"
        message="数据库不可用"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi

    echo "check_${name}=${status}:${message}:${response_time}"

    if [ "$JSON_OUTPUT" = true ]; then
        json_checks+=("\"${name}\":{\"status\":\"${status}\",\"message\":\"${message}\",\"response_time\":${response_time}}")
    fi
}

check_redis() {
    local name="Redis"
    local status="pass"
    local message=""
    local response_time=0

    local start_time=$(date +%s%3N)

    if docker exec pathology-ai-redis redis-cli ping >/dev/null 2>&1; then
        local end_time=$(date +%s%3N)
        response_time=$((end_time - start_time))

        # 获取内存使用
        local memory_info=$(docker exec pathology-ai-redis redis-cli INFO memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
        message="OK (内存: ${memory_info}, ${response_time}ms)"
    else
        status="fail"
        message="Redis不可用"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi

    echo "check_${name}=${status}:${message}:${response_time}"

    if [ "$JSON_OUTPUT" = true ]; then
        json_checks+=("\"${name}\":{\"status\":\"${status}\",\"message\":\"${message}\",\"response_time\":${response_time}}")
    fi
}

check_containers() {
    local name="Containers"
    local status="pass"
    local message=""

    local expected_containers=("pathology-ai-app" "pathology-ai-postgres" "pathology-ai-redis")
    local running_containers=$(docker ps --format '{{.Names}}' | grep -E 'pathology-ai-(app|postgres|redis)' | wc -l)

    if [ "$running_containers" -eq "${#expected_containers[@]}" ]; then
        message="所有容器运行中 (${running_containers}/${#expected_containers[@]})"
    else
        status="fail"
        message="部分容器未运行 (${running_containers}/${#expected_containers[@]})"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi

    echo "check_${name}=${status}:${message}"

    if [ "$JSON_OUTPUT" = true ]; then
        json_checks+=("\"${name}\":{\"status\":\"${status}\",\"message\":\"${message}\"}")
    fi
}

check_disk_space() {
    local name="DiskSpace"
    local status="pass"
    local message=""

    local disk_usage=$(df -h "${PROJECT_ROOT}" | tail -1 | awk '{print $5}' | tr -d '%')

    if [ "$disk_usage" -gt 90 ]; then
        status="fail"
        message="磁盘空间不足 (${disk_usage}%)"
        UNHEALTHY=$((UNHEALTHY + 1))
    elif [ "$disk_usage" -gt 80 ]; then
        status="warn"
        message="磁盘空间告警 (${disk_usage}%)"
        WARNING=$((WARNING + 1))
    else
        message="OK (${disk_usage}% 使用)"
    fi

    echo "check_${name}=${status}:${message}"

    if [ "$JSON_OUTPUT" = true ]; then
        json_checks+=("\"${name}\":{\"status\":\"${status}\",\"message\":\"${message}\"}")
    fi
}

check_memory() {
    local name="Memory"
    local status="pass"
    local message=""

    # 获取系统内存使用
    local mem_percent=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')

    if [ "$mem_percent" -gt 90 ]; then
        status="fail"
        message="内存使用过高 (${mem_percent}%)"
        UNHEALTHY=$((UNHEALTHY + 1))
    elif [ "$mem_percent" -gt 80 ]; then
        status="warn"
        message="内存使用告警 (${mem_percent}%)"
        WARNING=$((WARNING + 1))
    else
        message="OK (${mem_percent}% 使用)"
    fi

    echo "check_${name}=${status}:${message}"

    if [ "$JSON_OUTPUT" = true ]; then
        json_checks+=("\"${name}\":{\"status\":\"${status}\",\"message\":\"${message}\"}")
    fi
}

# ==============================================
# 输出结果
# ==============================================
output_results() {
    local overall_status="healthy"

    if [ $UNHEALTHY -gt 0 ]; then
        overall_status="unhealthy"
    elif [ $WARNING -gt 0 ]; then
        overall_status="warning"
    fi

    if [ "$JSON_OUTPUT" = true ]; then
        # JSON格式输出
        local checks_json=$(IFS=,; echo "${json_checks[*]}")
        echo "{"
        echo "  \"status\": \"${overall_status}\","
        echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
        echo "  \"checks\": {${checks_json}}"
        echo "}"
        exit $([ $UNHEALTHY -gt 0 ] && echo 1 || echo 0)
    else
        # 人类可读输出
        echo ""
        echo "=========================================="
        echo "       健康检查报告"
        echo "=========================================="
        echo "时间: $(date)"
        echo "状态: ${overall_status}"
        echo ""

        while IFS=':' read -r check_name check_status check_msg check_rt; do
            local display_name="${check_name#check_}"

            if [ "$check_status" = "pass" ]; then
                echo -e "${GREEN}✓${NC} ${display_name}: ${check_msg}"
            elif [ "$check_status" = "warn" ]; then
                echo -e "${YELLOW}⚠${NC} ${display_name}: ${check_msg}"
            else
                echo -e "${RED}✗${NC} ${display_name}: ${check_msg}"
            fi
        done < <(
            check_api
            check_database
            check_redis
            check_containers
            check_disk_space
            check_memory
        )

        echo ""
        echo "=========================================="
        echo "总计: $((UNHEALTHY + WARNING)) 个问题 (${UNHEALTHY} 严重, ${WARNING} 警告)"
        echo "=========================================="

        if [ $UNHEALTHY -gt 0 ]; then
            exit 1
        fi
    fi
}

# ==============================================
# 主流程
# ==============================================
declare -a json_checks

output_results
