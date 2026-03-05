"""
=====================================================
Pipeline 模块测试脚本
=====================================================

测试内容：
1. PhaseMapper: Phase 状态映射功能
2. PipelineMonitor: 变化检测功能
3. PipelineService: 业务服务功能

运行方式：
    cd code/back_end
    python tests/test_pipeline.py
=====================================================
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.phase_mapper import PhaseMapper, StandardPhase, get_phase_mapper
from services.pipeline_monitor import PipelineMonitor, ChangeType, get_pipeline_monitor
from services.pipeline_service import PipelineService, get_pipeline_service
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="pipeline_test", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


# =====================================================
# 测试函数
# =====================================================


async def test_phase_mapper():
    """测试 Phase 映射器"""
    logger.info("=" * 60)
    logger.info("测试 1: PhaseMapper 状态映射")
    logger.info("=" * 60)

    mapper = PhaseMapper()

    # 测试 1.1: 标准化英文阶段
    logger.info("测试英文阶段标准化...")
    test_cases = [
        ("Phase II", "Phase 2"),
        ("Phase 1", "Phase 1"),
        ("Phase III trial", "Phase 3"),
        ("Preclinical", "Preclinical"),
        ("Approved", "Approved"),
    ]

    for raw, expected in test_cases:
        normalized = mapper.normalize(raw)
        status = "✓" if normalized == expected else "✗"
        logger.info(f"  {status} '{raw}' -> '{normalized}' (期望: {expected})")

    # 测试 1.2: 标准化中文阶段
    logger.info("\n测试中文阶段标准化...")
    cn_test_cases = [
        ("II期", "Phase 2"),
        ("三期临床", "Phase 3"),
        ("临床前", "Preclinical"),
        ("已上市", "Launched"),
        ("已终止", "Discontinued"),
    ]

    for raw, expected in cn_test_cases:
        normalized = mapper.normalize(raw)
        status = "✓" if normalized == expected else "✗"
        logger.info(f"  {status} '{raw}' -> '{normalized}' (期望: {expected})")

    # 测试 1.3: 阶段比较
    logger.info("\n测试阶段比较...")
    comparison_tests = [
        ("Phase 3", "Phase 2", True),
        ("Phase 2", "Phase 3", False),
        ("Phase 1/2", "Phase 1", True),
        ("Approved", "Phase 3", True),
    ]

    for phase1, phase2, expected in comparison_tests:
        result = mapper.is_later_phase(phase1, phase2)
        status = "✓" if result == expected else "✗"
        logger.info(f"  {status} {phase1} > {phase2}: {result} (期望: {expected})")

    # 测试 1.4: 阶段分组
    logger.info("\n测试阶段分组...")
    group_tests = [
        ("Phase 1", "early"),
        ("Phase 2", "mid"),
        ("Phase 3", "late"),
        ("Approved", "approved"),
        ("Discontinued", "terminated"),
    ]

    for phase, expected_group in group_tests:
        group = mapper.get_phase_group(phase)
        status = "✓" if group == expected_group else "✗"
        logger.info(f"  {status} {phase} -> {group} (期望: {expected_group})")

    # 测试 1.5: 置信度
    logger.info("\n测试识别置信度...")
    confidence_tests = [
        ("Phase 2", 1.0),
        ("phase ii", 0.8),
        ("Phase II trial", 0.6),
        ("Unknown Phase", 0.0),
    ]

    for phase, min_confidence in confidence_tests:
        confidence = mapper.get_phase_confidence(phase)
        status = "✓" if confidence >= min_confidence else "✗"
        logger.info(f"  {status} '{phase}' confidence: {confidence} (>= {min_confidence})")

    logger.info("✓ PhaseMapper 测试通过\n")


async def test_pipeline_monitor():
    """测试 Pipeline 变化检测"""
    logger.info("=" * 60)
    logger.info("测试 2: PipelineMonitor 变化检测")
    logger.info("=" * 60)

    monitor = PipelineMonitor()

    # 模拟旧管线数据
    old_pipelines = [
        {
            "pipeline_id": 1,
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "NSCLC",
            "phase": "Phase 2",
            "first_seen_at": datetime.utcnow() - timedelta(days=100),
            "last_seen_at": datetime.utcnow() - timedelta(days=10),
        },
        {
            "pipeline_id": 2,
            "drug_code": "BGB-A317",
            "company_name": "百济神州",
            "indication": "HCC",
            "phase": "Phase 1",
            "first_seen_at": datetime.utcnow() - timedelta(days=200),
            "last_seen_at": datetime.utcnow() - timedelta(days=10),
        },
        {
            "pipeline_id": 3,
            "drug_code": "IBI308",
            "company_name": "信达生物",
            "indication": "CRC",
            "phase": "Phase 1",
            "first_seen_at": datetime.utcnow() - timedelta(days=300),
            "last_seen_at": datetime.utcnow() - timedelta(days=200),  # 200天前
        },
    ]

    # 模拟新管线数据
    new_pipelines = [
        {
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "NSCLC",
            "phase": "Phase 3",  # Phase Jump: 2 -> 3
            "source_url": "https://hengrui.com/pipeline/shr-1210",
        },
        {
            "drug_code": "BGB-A317",
            "company_name": "百济神州",
            "indication": "HCC",
            "phase": "Phase 1",  # 未变化
            "source_url": "https://beigene.com/pipeline/bgb-a317",
        },
        # 新增管线
        {
            "drug_code": "SHR-1316",
            "company_name": "恒瑞医药",
            "indication": "TNBC",
            "phase": "Phase 2",
            "source_url": "https://hengrui.com/pipeline/shr-1316",
        },
        # IBI308 消失（超过180天）
    ]

    # 测试 2.1: 检测变化
    logger.info("检测管线变化...")
    report = monitor.detect_changes(
        old_pipelines=old_pipelines,
        new_pipelines=new_pipelines,
        disappeared_threshold_days=180,
    )

    logger.info(f"\n变化摘要:")
    logger.info(f"  总变化数: {report.total_changes}")
    logger.info(f"  新增管线: {len(report.new_pipelines)}")
    logger.info(f"  Phase Jump: {len(report.phase_jumps)}")
    logger.info(f"  消失管线: {len(report.disappeared_pipelines)}")
    logger.info(f"  重新出现: {len(report.reappeared_pipelines)}")
    logger.info(f"  信息更新: {report.info_updates}")

    # 测试 2.2: 显示新增管线
    if report.new_pipelines:
        logger.info(f"\n新增管线:")
        for p in report.new_pipelines:
            logger.info(f"  - {p['drug_code']} ({p['company_name']}) Phase {p.get('phase_normalized', p.get('phase'))}")

    # 测试 2.3: 显示 Phase Jump
    if report.phase_jumps:
        logger.info(f"\nPhase Jump 事件:")
        for jump in report.phase_jumps:
            logger.info(f"  - {jump.drug_code}: {jump.old_phase} -> {jump.new_phase} ({jump.jump_days}天)")

    # 测试 2.4: 显示消失管线
    if report.disappeared_pipelines:
        logger.info(f"\n消失管线:")
        for p in report.disappeared_pipelines:
            logger.info(f"  - {p['drug_code']} ({p['company_name']})")

    # 验证结果
    assert len(report.new_pipelines) == 1, "应检测到1个新增管线"
    assert len(report.phase_jumps) == 1, "应检测到1个Phase Jump"
    assert len(report.disappeared_pipelines) == 1, "应检测到1个消失管线"
    assert report.phase_jumps[0].drug_code == "SHR-1210", "Phase Jump应为SHR-1210"
    assert report.phase_jumps[0].old_phase == "Phase 2", "旧阶段应为Phase 2"
    assert report.phase_jumps[0].new_phase == "Phase 3", "新阶段应为Phase 3"

    logger.info("✓ PipelineMonitor 测试通过\n")


async def test_pipeline_service():
    """测试 Pipeline 业务服务"""
    logger.info("=" * 60)
    logger.info("测试 3: PipelineService 业务服务")
    logger.info("=" * 60)

    service = PipelineService()

    # 测试 3.1: 创建管线
    logger.info("测试创建管线...")
    pipeline_data = {
        "drug_code": "TEST-001",
        "company_name": "测试公司",
        "indication": "Test Cancer",
        "phase": "Phase 2",
        "modality": "单抗",
        "source_url": "https://test.com/pipeline/test-001",
    }

    created = await service.create_pipeline(pipeline_data)

    logger.info(f"  ✓ 管线创建成功")
    logger.info(f"    - Drug Code: {created['drug_code']}")
    logger.info(f"    - Phase (原始): {created['phase_raw']}")
    logger.info(f"    - Phase (标准化): {created['phase_normalized']}")

    # 测试 3.2: 更新管线
    logger.info("\n测试更新管线...")
    update_data = {
        "phase": "Phase 3",  # Phase Jump
    }

    updated = await service.update_pipeline(
        pipeline_id=1,
        data=update_data,
    )

    logger.info(f"  ✓ 管线更新成功")
    logger.info(f"    - 新阶段: {updated['phase_normalized']}")

    # 测试 3.3: 获取统计信息
    logger.info("\n测试获取统计信息...")
    stats = await service.get_statistics()

    logger.info(f"  ✓ 统计信息获取成功")
    logger.info(f"    - 总管线数: {stats.total_pipelines}")
    logger.info(f"    - 按公司: {stats.by_company}")
    logger.info(f"    - 按阶段: {stats.by_phase}")

    # 测试 3.4: 搜索管线
    logger.info("\n测试搜索管线...")
    results = await service.search_pipelines(
        keyword="TEST",
        limit=10,
    )

    logger.info(f"  ✓ 搜索完成，找到 {len(results)} 条结果")

    logger.info("✓ PipelineService 测试通过\n")


async def test_integration():
    """集成测试：完整的更新检测流程"""
    logger.info("=" * 60)
    logger.info("测试 4: 集成测试（完整流程）")
    logger.info("=" * 60)

    service = PipelineService()

    # 模拟爬虫数据
    crawler_data = [
        {
            "drug_code": "SHR-1210",
            "indication": "NSCLC",
            "phase": "Phase 3",
            "modality": "单抗",
            "source_url": "https://hengrui.com/pipeline/shr-1210",
        },
        {
            "drug_code": "SHR-1316",
            "indication": "TNBC",
            "phase": "Phase 2",
            "modality": "单抗",
            "source_url": "https://hengrui.com/pipeline/shr-1316",
        },
        {
            "drug_code": "SHR-1501",
            "indication": "SCLC",
            "phase": "Phase 1",
            "modality": "小分子",
            "source_url": "https://hengrui.com/pipeline/shr-1501",
        },
    ]

    # 执行更新并检测
    logger.info("执行批量更新和检测...")
    report = await service.update_and_detect(
        company_name="恒瑞医药",
        new_pipelines=crawler_data,
        disappeared_threshold_days=180,
    )

    logger.info(f"\n检测结果:")
    logger.info(f"  总变化: {report.total_changes}")
    logger.info(f"  新增: {len(report.new_pipelines)}")
    logger.info(f"  Phase Jump: {len(report.phase_jumps)}")
    logger.info(f"  消失: {len(report.disappeared_pipelines)}")

    # 显示是否有显著变化
    if report.has_significant_changes():
        logger.info("\n  ⚠️ 检测到显著变化！")
    else:
        logger.info("\n  ✓ 无显著变化")

    logger.info("✓ 集成测试通过\n")


async def main():
    """主测试函数"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 12 + "Pipeline 模块测试" + " " * 36 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    try:
        # 测试 1: Phase 映射器
        await test_phase_mapper()

        # 测试 2: 变化检测
        await test_pipeline_monitor()

        # 测试 3: 业务服务
        await test_pipeline_service()

        # 测试 4: 集成测试
        await test_integration()

        logger.info("=" * 60)
        logger.info("✓ 所有测试通过！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
