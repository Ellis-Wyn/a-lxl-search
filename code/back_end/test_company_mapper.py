"""
公司名称映射器测试脚本
"""
import sys
import io

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from utils.company_name_mapper import get_company_mapper

def test_company_mapper():
    """测试公司名称映射器的所有功能"""

    mapper = get_company_mapper()

    print("=" * 80)
    print("公司名称映射器测试")
    print("=" * 80)

    # ==================== 测试1: 标准化功能 ====================
    print("\n【测试1】标准化功能（简称→全称）")
    print("-" * 80)

    test_cases_normalize = [
        ("恒瑞", "江苏恒瑞医药股份有限公司"),
        ("百济", "百济神州（北京）生物科技有限公司"),
        ("BeiGene", "百济神州（北京）生物科技有限公司"),
        ("信达", "信达生物制药（苏州）有限公司"),
        ("Innovent", "信达生物制药（苏州）有限公司"),
        ("再鼎", "再鼎医药（上海）有限公司"),
        ("Zai Lab", "再鼎医药（上海）有限公司"),
    ]

    for input_name, expected in test_cases_normalize:
        result = mapper.normalize(input_name)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_name}' → '{result}'")
        if result != expected:
            print(f"   期望: {expected}")

    # ==================== 测试2: 扩展功能 ====================
    print("\n【测试2】扩展功能（获取所有变体）")
    print("-" * 80)

    test_cases_expand = [
        "百济",
        "恒瑞",
        "信达",
        "Pfizer",
    ]

    for input_name in test_cases_expand:
        variants = mapper.expand(input_name)
        print(f"✅ '{input_name}' 的变体:")
        for v in variants:
            print(f"   - {v}")

    # ==================== 测试3: 模糊匹配 ====================
    print("\n【测试3】模糊匹配功能")
    print("-" * 80)

    test_cases_fuzzy = [
        "百济神州生物",
        "恒瑞医药",
        "信达制药",
        "罗氏制药",
    ]

    for input_name in test_cases_fuzzy:
        result = mapper.find_match(input_name)
        status = "✅" if result else "❌"
        print(f"{status} '{input_name}' → '{result}'")

    # ==================== 测试4: 获取公司信息 ====================
    print("\n【测试4】获取公司详细信息")
    print("-" * 80)

    info = mapper.get_company_info("百济")
    if info:
        print("✅ 百济神州的信息:")
        print(f"   标准名称: {info['standard_name']}")
        print(f"   英文名称: {info['english_name']}")
        print(f"   简称列表: {', '.join(info['aliases'])}")
        print(f"   拼音缩写: {info['pinyin_abbr']}")
        print(f"   股票代码: {info['stock_code']}")

    # ==================== 测试5: 验证功能 ====================
    print("\n【测试5】验证功能")
    print("-" * 80)

    test_cases_validate = [
        ("百济神州", True),
        ("不存在的公司", False),
        ("BeiGene", True),
        ("", False),
    ]

    for input_name, expected in test_cases_validate:
        result = mapper.is_valid_company(input_name)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_name}' → {result}")

    # ==================== 测试6: 统计信息 ====================
    print("\n【测试6】映射器统计信息")
    print("-" * 80)

    all_companies = mapper.get_all_companies()
    print(f"✅ 总公司数: {len(all_companies)}")
    print(f"✅ 前5家公司:")
    for i, company in enumerate(all_companies[:5], 1):
        info = mapper.get_company_info(company)
        print(f"   {i}. {company}")
        print(f"      简称: {', '.join(info['aliases'][:3])}")

    print("\n" + "=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_company_mapper()
