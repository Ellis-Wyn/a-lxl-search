"""
=====================================================
PhaseMapper 单元测试
=====================================================

测试覆盖：
- 30+ 种阶段映射
- 边界情况处理
- 默认值处理
- 中英文混合阶段
- 特殊字符处理
=====================================================
"""

import pytest
from services.phase_mapper import PhaseMapper, StandardPhase


class TestPhaseMapper:
    """PhaseMapper 测试类"""

    def test_normalize_phase_preclinical_variations(self):
        """测试临床前阶段的各种变体"""
        test_cases = [
            # 英文变体
            ("preclinical", StandardPhase.PRECLINICAL),
            ("Preclinical", StandardPhase.PRECLINICAL),
            ("PRECLINICAL", StandardPhase.PRECLINICAL),
            ("pre-clinical", StandardPhase.PRECLINICAL),
            ("Pre-Clinical", StandardPhase.PRECLINICAL),

            # 中文变体
            ("临床前", StandardPhase.PRECLINICAL),
            ("临床前研究", StandardPhase.PRECLINICAL),
            ("临床前试验", StandardPhase.PRECLINICAL),
            ("IND前", StandardPhase.PRECLINICAL),
            ("IND申请前", StandardPhase.PRECLINICAL),

            # 简写
            ("PC", StandardPhase.PRECLINICAL),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_phase_1_variations(self):
        """测试 Phase 1 的各种变体"""
        test_cases = [
            # 标准格式
            ("Phase 1", StandardPhase.PHASE_1),
            ("phase 1", StandardPhase.PHASE_1),
            ("PHASE 1", StandardPhase.PHASE_1),

            # 罗马数字
            ("Phase I", StandardPhase.PHASE_1),
            ("Phase i", StandardPhase.PHASE_1),
            ("I期", StandardPhase.PHASE_1),
            ("I 期", StandardPhase.PHASE_1),
            ("1期", StandardPhase.PHASE_1),
            ("1 期", StandardPhase.PHASE_1),

            # 中文
            ("一期", StandardPhase.PHASE_1),
            ("一阶段", StandardPhase.PHASE_1),
            ("阶段一", StandardPhase.PHASE_1),
            ("临床I期", StandardPhase.PHASE_1),
            ("临床1期", StandardPhase.PHASE_1),

            # 其他变体
            ("Phase I/II", StandardPhase.PHASE_1),  # 应返回较早的
            ("I/II期", StandardPhase.PHASE_1),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_phase_2_variations(self):
        """测试 Phase 2 的各种变体"""
        test_cases = [
            # 标准格式
            ("Phase 2", StandardPhase.PHASE_2),
            ("phase 2", StandardPhase.PHASE_2),
            ("PHASE 2", StandardPhase.PHASE_2),

            # 罗马数字
            ("Phase II", StandardPhase.PHASE_2),
            ("Phase ii", StandardPhase.PHASE_2),
            ("II期", StandardPhase.PHASE_2),
            ("II 期", StandardPhase.PHASE_2),
            ("2期", StandardPhase.PHASE_2),
            ("2 期", StandardPhase.PHASE_2),

            # 中文
            ("二期", StandardPhase.PHASE_2),
            ("二阶段", StandardPhase.PHASE_2),
            ("阶段二", StandardPhase.PHASE_2),
            ("临床II期", StandardPhase.PHASE_2),
            ("临床2期", StandardPhase.PHASE_2),

            # 其他变体
            ("Phase II/III", StandardPhase.PHASE_2),
            ("II/III期", StandardPhase.PHASE_2),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_phase_3_variations(self):
        """测试 Phase 3 的各种变体"""
        test_cases = [
            # 标准格式
            ("Phase 3", StandardPhase.PHASE_3),
            ("phase 3", StandardPhase.PHASE_3),
            ("PHASE 3", StandardPhase.PHASE_3),

            # 罗马数字
            ("Phase III", StandardPhase.PHASE_3),
            ("Phase iii", StandardPhase.PHASE_3),
            ("III期", StandardPhase.PHASE_3),
            ("III 期", StandardPhase.PHASE_3),
            ("3期", StandardPhase.PHASE_3),
            ("3 期", StandardPhase.PHASE_3),

            # 中文
            ("三期", StandardPhase.PHASE_3),
            ("三阶段", StandardPhase.PHASE_3),
            ("阶段三", StandardPhase.PHASE_3),
            ("临床III期", StandardPhase.PHASE_3),
            ("临床3期", StandardPhase.PHASE_3),
            ("关键性注册临床", StandardPhase.PHASE_3),
            ("注册临床", StandardPhase.PHASE_3),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_filing_variations(self):
        """测试申报阶段的变体"""
        test_cases = [
            # 英文
            ("filing", StandardPhase.FILING),
            ("Filing", StandardPhase.FILING),
            ("FILING", StandardPhase.FILING),
            ("Filed", StandardPhase.FILING),
            ("NDA", StandardPhase.FILING),
            ("BLA", StandardPhase.FILING),
            ("MAA", StandardPhase.FILING),

            # 中文
            ("申报", StandardPhase.FILING),
            ("上市申报", StandardPhase.FILING),
            ("注册申报", StandardPhase.FILING),
            ("NDA申报", StandardPhase.FILING),
            ("BLA申报", StandardPhase.FILING),
            ("申请上市", StandardPhase.FILING),
            ("已申报", StandardPhase.FILING),
            ("申报中", StandardPhase.FILING),

            # 特殊
            ("Pre-approval", StandardPhase.FILING),
            ("Marketing Application", StandardPhase.FILING),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_approved_variations(self):
        """测试已上市阶段的变体"""
        test_cases = [
            # 英文
            ("approved", StandardPhase.APPROVED),
            ("Approved", StandardPhase.APPROVED),
            ("APPROVED", StandardPhase.APPROVED),
            ("Launched", StandardPhase.APPROVED),
            ("Marketed", StandardPhase.APPROVED),
            ("Marketed", StandardPhase.APPROVED),

            # 中文
            ("已上市", StandardPhase.APPROVED),
            ("上市", StandardPhase.APPROVED),
            ("获批", StandardPhase.APPROVED),
            ("批准上市", StandardPhase.APPROVED),
            ("已批准", StandardPhase.APPROVED),
            ("获得批准", StandardPhase.APPROVED),
            ("已获批", StandardPhase.APPROVED),
            ("已注册", StandardPhase.APPROVED),

            # 特殊
            ("Available", StandardPhase.APPROVED),
            ("Commercially Available", StandardPhase.APPROVED),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_with_extra_spaces(self):
        """测试带额外空格的阶段"""
        test_cases = [
            ("  Phase 1  ", StandardPhase.PHASE_1),
            ("Phase   2", StandardPhase.PHASE_2),
            ("  I  期  ", StandardPhase.PHASE_1),
            ("II   期", StandardPhase.PHASE_2),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: '{input_phase}'"

    def test_normalize_with_special_characters(self):
        """测试带特殊字符的阶段"""
        test_cases = [
            ("Phase-1", StandardPhase.PHASE_1),
            ("Phase_2", StandardPhase.PHASE_2),
            ("Phase.III", StandardPhase.PHASE_3),
            ("I/II期", StandardPhase.PHASE_1),
            ("Phase I-II", StandardPhase.PHASE_1),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_mixed_chinese_english(self):
        """测试中英文混合"""
        test_cases = [
            ("Phase I期", StandardPhase.PHASE_1),
            ("Phase II期", StandardPhase.PHASE_2),
            ("Phase III期", StandardPhase.PHASE_3),
            ("临床Phase 1", StandardPhase.PHASE_1),
            ("临床Phase 2", StandardPhase.PHASE_2),
            ("III期临床", StandardPhase.PHASE_3),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_normalize_unknown_phase(self):
        """测试未知阶段（应返回 UNKNOWN）"""
        unknown_phases = [
            "unknown",
            "UNKNOWN",
            "未知",
            "不确定",
            "?",
            "N/A",
            "",
            "Random Text",
            "XYZ",
        ]

        for phase in unknown_phases:
            result = PhaseMapper.normalize(phase)
            assert result == StandardPhase.UNKNOWN, f"Failed for: {phase}"

    def test_normalize_case_insensitive(self):
        """测试大小写不敏感"""
        test_cases = [
            ("phase 1", "Phase 1"),
            ("PHASE 2", "phase 2"),
            ("i期", "I期"),
            ("ii期", "II期"),
            ("iii期", "III期"),
            ("APPROVED", "approved"),
        ]

        for phase1, phase2 in test_cases:
            result1 = PhaseMapper.normalize(phase1)
            result2 = PhaseMapper.normalize(phase2)
            assert result1 == result2, f"{phase1} != {phase2}"

    def test_get_standard_phase_value(self):
        """测试获取标准阶段值"""
        mapper = PhaseMapper()

        assert mapper.get_standard_value(StandardPhase.PRECLINICAL) == "preclinical"
        assert mapper.get_standard_value(StandardPhase.PHASE_1) == "Phase 1"
        assert mapper.get_standard_value(StandardPhase.PHASE_2) == "Phase 2"
        assert mapper.get_standard_value(StandardPhase.PHASE_3) == "Phase 3"
        assert mapper.get_standard_value(StandardPhase.FILING) == "filing"
        assert mapper.get_standard_value(StandardPhase.APPROVED) == "approved"

    def test_get_phase_order(self):
        """测试获取阶段顺序"""
        mapper = PhaseMapper()

        assert mapper.get_phase_order(StandardPhase.PRECLINICAL) == 1
        assert mapper.get_phase_order(StandardPhase.PHASE_1) == 2
        assert mapper.get_phase_order(StandardPhase.PHASE_2) == 3
        assert mapper.get_phase_order(StandardPhase.PHASE_3) == 4
        assert mapper.get_phase_order(StandardPhase.FILING) == 5
        assert mapper.get_phase_order(StandardPhase.APPROVED) == 6

    def test_normalize_with_common_company_formats(self):
        """测试常见公司的阶段格式"""
        # 恒瑞医药格式
        assert PhaseMapper.normalize("III期") == StandardPhase.PHASE_3
        assert PhaseMapper.normalize("I期临床") == StandardPhase.PHASE_1

        # 百济神州格式
        assert PhaseMapper.normalize("Phase 3") == StandardPhase.PHASE_3

        # 其他公司格式
        assert PhaseMapper.normalize("临床二期") == StandardPhase.PHASE_2
        assert PhaseMapper.normalize("临床前研究") == StandardPhase.PRECLINICAL

    def test_normalize_number_only(self):
        """测试纯数字阶段"""
        assert PhaseMapper.normalize("1") == StandardPhase.PHASE_1
        assert PhaseMapper.normalize("2") == StandardPhase.PHASE_2
        assert PhaseMapper.normalize("3") == StandardPhase.PHASE_3
        assert PhaseMapper.normalize("4") == StandardPhase.UNKNOWN  # 无效

    def test_normalize_with_parentheses(self):
        """测试带括号的阶段"""
        test_cases = [
            ("Phase 1 (active)", StandardPhase.PHASE_1),
            ("Phase 2 (completed)", StandardPhase.PHASE_2),
            ("III期（进行中）", StandardPhase.PHASE_3),
            ("II期（已完成）", StandardPhase.PHASE_2),
        ]

        for input_phase, expected in test_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"

    def test_all_standard_phases_covered(self):
        """测试所有标准阶段都被覆盖"""
        mapper = PhaseMapper()

        # 测试每个标准阶段都能正确映射回自己
        for phase in StandardPhase:
            if phase != StandardPhase.UNKNOWN:
                normalized = mapper.normalize(mapper.get_standard_value(phase))
                assert normalized == phase, f"Failed for: {phase}"

    def test_is_valid_phase(self):
        """测试阶段有效性检查"""
        mapper = PhaseMapper()

        # 有效阶段
        assert mapper.is_valid_phase("Phase 1") is True
        assert mapper.is_valid_phase("I期") is True
        assert mapper.is_valid_phase("approved") is True

        # 无效阶段
        assert mapper.is_valid_phase("invalid") is False
        assert mapper.is_valid_phase("XYZ") is False
        assert mapper.is_valid_phase("") is False

    def test_normalize_comprehensive_coverage(self):
        """综合测试：覆盖所有主要变体"""
        # 这个测试确保映射器能处理大多数实际情况

        comprehensive_cases = [
            # 最常见的中英文格式
            ("Phase 1", StandardPhase.PHASE_1),
            ("Phase 2", StandardPhase.PHASE_2),
            ("Phase 3", StandardPhase.PHASE_3),
            ("I期", StandardPhase.PHASE_1),
            ("II期", StandardPhase.PHASE_2),
            ("III期", StandardPhase.PHASE_3),
            ("已上市", StandardPhase.APPROVED),
            ("申报中", StandardPhase.FILING),
            ("临床前", StandardPhase.PRECLINICAL),

            # 容易混淆的
            ("Phase I", StandardPhase.PHASE_1),
            ("1期", StandardPhase.PHASE_1),
            ("一期", StandardPhase.PHASE_1),
            ("Phase I/II", StandardPhase.PHASE_1),
            ("Phase II/III", StandardPhase.PHASE_2),
        ]

        for input_phase, expected in comprehensive_cases:
            result = PhaseMapper.normalize(input_phase)
            assert result == expected, f"Failed for: {input_phase}"
