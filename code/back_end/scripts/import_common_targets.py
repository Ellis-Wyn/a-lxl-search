"""
============================================================
常见药物靶点导入脚本
============================================================

从YAML配置文件导入100个常见药物靶点到数据库

特性：
- 幂等性：重复运行不会出错
- 事务安全：失败时自动回滚
- 详细日志：记录每个操作
- 健壮性：完善的错误处理

使用方式：
    # 导入默认配置文件
    python scripts/import_common_targets.py

    # 导入指定配置文件
    python scripts/import_common_targets.py scripts/data/custom_targets.yaml

作者：Claude AI
创建时间：2026-03-07
版本：1.0.0
============================================================
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import setup_logger, get_logger
from services.target_import_service import TargetImportService

# 初始化日志
setup_logger(app_name="import_targets", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


def print_banner():
    """打印横幅"""
    print("\n" + "=" * 70)
    print(">> 常见药物靶点导入工具")
    print("=" * 70)
    print(">> 从YAML配置文件导入真实药物靶点数据")
    print(">> 特性：幂等性 | 事务安全 | 详细日志")
    print("=" * 70 + "\n")


def print_summary(result, summary):
    """打印导入摘要"""
    print("\n" + "=" * 70)
    print(">> 导入摘要")
    print("=" * 70)

    # 总体统计
    print(f"\n总体统计：")
    print(f"  数据库总靶点数：{summary.get('total_targets', 0)}")
    print(f"\n本次导入：")
    print(f"  处理总数：{result.total}")
    print(f"  [+] 新创建：{result.created}")
    print(f"  [o] 已跳过：{result.skipped}")
    print(f"  [!] 失败：{result.failed}")

    # 按类别统计
    if 'by_category' in summary:
        print(f"\n按类别分布：")
        for category, count in sorted(summary['by_category'].items()):
            print(f"  {category}：{count}个")

    # 错误列表
    if result.errors:
        print(f"\n[x] 错误列表：")
        for error in result.errors[:10]:  # 只显示前10个
            print(f"  - {error}")
        if len(result.errors) > 10:
            print(f"  ... 还有{len(result.errors) - 10}个错误")

    print("\n" + "=" * 70)
    print(">> 导入完成！")
    print("=" * 70 + "\n")


def main():
    """主函数"""
    print_banner()

    # 确定配置文件路径
    if len(sys.argv) > 1:
        yaml_path = sys.argv[1]
    else:
        yaml_path = "scripts/data/common_drug_targets.yaml"

    # 检查文件是否存在
    yaml_file = Path(__file__).parent.parent / yaml_path
    if not yaml_file.exists():
        logger.error(f"[x] 配置文件不存在：{yaml_file}")
        logger.info(f"[i] 提示：请检查文件路径或运行：python scripts/import_common_targets.py <yaml_path>")
        sys.exit(1)

    logger.info(f"[*] 配置文件：{yaml_file}")
    logger.info(f"[*] 开始导入...\n")

    try:
        # 使用服务类进行导入
        with TargetImportService() as service:
            result = service.import_from_yaml(str(yaml_file))
            summary = service.get_import_summary()

        # 打印摘要
        print_summary(result, summary)

        # 返回码
        if result.failed > 0:
            sys.exit(1)  # 有失败
        else:
            sys.exit(0)  # 全部成功

    except KeyboardInterrupt:
        logger.warning("\n[!] 用户中断导入")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n[x] 导入失败：{e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
