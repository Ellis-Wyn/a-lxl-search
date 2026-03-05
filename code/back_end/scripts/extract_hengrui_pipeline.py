"""
=====================================================
恒瑞医药管线数据提取脚本
=====================================================

从恒瑞医药官网管线页面提取数据：
- 官网：https://www.hengrui.com/RD/pipeline.html
- 数据字段：药物代码、靶点、适应症、阶段

使用方式：
    python scripts/extract_hengrui_pipeline.py hengrui_pipeline.html
=====================================================
"""

import sys
import re
import json
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup


def extract_pipeline_data(html_file: str) -> List[Dict]:
    """
    提取管线数据

    Args:
        html_file: HTML 文件路径

    Returns:
        管线数据列表
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    pipelines = []

    # 使用正则表达式提取每个管线项目的HTML块
    # 模式：从 <li class="pipeline-list-item-li"> 开始到 </li> 结束
    pattern = r'<li[^>]*class="pipeline-list-item-li[^"]*"[^>]*>(.*?)</li>'
    matches = re.findall(pattern, html, re.DOTALL)

    print(f"Found {len(matches)} pipeline items")

    for match in matches:
        try:
            # 使用 BeautifulSoup 解析单个项目
            item_soup = BeautifulSoup(match, 'html.parser')

            # 提取药物代码
            drug_code_elem = item_soup.find('p')
            drug_code = drug_code_elem.text.strip() if drug_code_elem else ''

            if not drug_code or not drug_code.startswith('HRS-'):
                continue

            # 提取靶点（第二个 p 标签，有小字体）
            target_elem = item_soup.find('p', class_='fontSize12 opacity0_6')
            target = target_elem.text.strip() if target_elem else ''

            # 提取详细信息（弹出框）
            pop_div = item_soup.find('div', class_='plist-pop-li')
            indication = ''
            phase = ''
            therapy = ''

            if pop_div:
                # 获取所有 p 标签
                pop_ps = pop_div.find_all('p')

                if len(pop_ps) >= 1:
                    # 第一个 p 标签：适应症
                    indication_text = pop_ps[0].get_text(separator=' ', strip=True)
                    # 清理文本
                    indication = re.sub(r'\s+', ' ', indication_text).strip()

                if len(pop_ps) >= 2:
                    # 第二个 p 标签：阶段
                    phase_text = pop_ps[1].get_text(separator=' ', strip=True)
                    # 提取阶段信息
                    phase_match = re.search(r'[ⅠⅡⅢⅣ]+期|Phase [123]|上市|批准|临床前|Approved', phase_text)
                    phase = phase_match.group(0) if phase_match else phase_text.strip()

                # 提取治疗方式（单药/联合用药）
                if '单药' in indication:
                    therapy = '单药'
                elif '联合' in indication:
                    therapy = '联合用药'

            # 清理数据
            drug_code = drug_code.strip()
            target = target.strip()
            indication = indication.replace('单 药', '').replace('单药', '').strip()
            indication = indication.replace('药或联合', '').replace('联合', '').strip()

            # 验证必填字段
            if not drug_code:
                continue

            pipeline_data = {
                'drug_code': drug_code,
                'target': target,
                'indication': indication,
                'phase': phase,
                'therapy': therapy,
                'company': '恒瑞医药',
                'source_url': 'https://www.hengrui.com/RD/pipeline.html'
            }

            pipelines.append(pipeline_data)

        except Exception as e:
            print(f"Error parsing item: {e}")
            continue

    return pipelines


def normalize_phase(phase_raw: str) -> str:
    """
    标准化阶段名称

    Args:
        phase_raw: 原始阶段文本

    Returns:
        标准化的阶段名称
    """
    phase_map = {
        'Ⅰ期': 'Phase 1',
        'Ⅰ期临床': 'Phase 1',
        'II期': 'Phase 2',
        'Ⅲ期': 'Phase 3',
        'Ⅲ期临床': 'Phase 3',
        '上市': 'Approved',
        '批准': 'Approved',
        '临床前': 'Preclinical',
    }

    for key, value in phase_map.items():
        if key in phase_raw:
            return value

    return phase_raw


def main():
    """主程序"""
    if len(sys.argv) < 2:
        print("Usage: python extract_hengrui_pipeline.py <html_file>")
        sys.exit(1)

    html_file = sys.argv[1]

    if not Path(html_file).exists():
        print(f"Error: File not found: {html_file}")
        sys.exit(1)

    print(f"Extracting pipeline data from: {html_file}")

    # 提取数据
    pipelines = extract_pipeline_data(html_file)

    print(f"\nExtracted {len(pipelines)} pipeline items")

    # 标准化阶段
    for p in pipelines:
        p['phase_normalized'] = normalize_phase(p['phase'])

    # 显示前10条
    print("\n=== First 10 Pipeline Items ===")
    for i, p in enumerate(pipelines[:10], 1):
        print(f"{i}. {p['drug_code']} | {p['target']} | {p['indication'][:40]}... | {p['phase']}")

    # 统计阶段分布
    phase_count = {}
    for p in pipelines:
        phase = p['phase_normalized']
        phase_count[phase] = phase_count.get(phase, 0) + 1

    print("\n=== Phase Distribution ===")
    for phase, count in sorted(phase_count.items(), key=lambda x: x[1], reverse=True):
        print(f"{phase}: {count}")

    # 保存为 JSON
    output_file = html_file.replace('.html', '_extracted.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pipelines, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
