"""
=====================================================
恒瑞医药官网爬虫
=====================================================

从恒瑞医药官网爬取管线数据：
- 官网：https://www.hengrui.com
- 管线页面：产品研发管线

数据字段：
- 药物代码（drug_code）
- 适应症（indication）
- 研发阶段（phase）
- 药物类型（modality）

实现思路：
1. 访问官网管线页面
2. 解析管线列表 HTML
3. 提取每条管线的数据
4. 标准化阶段名称
5. 入库

注意：
- 遵守 robots.txt
- 速率限制（0.3-0.5 QPS）
- 必须保留 source_url
====================================================="""

import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

from crawlers.base_spider import (
    CompanySpiderBase,
    PipelineDataItem,
    CrawlerStats,
    spider_register,
)
from core.logger import get_logger
from core.intelligence import PipelineParser
from utils.pipeline_parser import DiscontinuationDetector, CombinationTherapyDetector

logger = get_logger(__name__)


@spider_register("hengrui")
class HengruiSpider(CompanySpiderBase):
    """
    恒瑞医药爬虫

    官网：https://www.hengrui.com
    """

    def __init__(self):
        super().__init__()
        self.name = "恒瑞医药"
        self.company_name = "恒瑞医药"
        self.base_url = "https://www.hengrui.com"

        # 尝试自动发现管线页面URL
        self.pipeline_url = self.discover_pipeline_url(self.base_url)

        # 如果自动发现失败，使用硬编码的fallback URL
        if not self.pipeline_url:
            logger.warning(
                f"Pipeline URL auto-discovery failed for {self.name}, "
                f"using hardcoded fallback"
            )
            self.pipeline_url = "https://www.hengrui.com/RD/pipeline.html"
        else:
            logger.info(f"✓ Auto-discovered pipeline URL: {self.pipeline_url}")

    def run(self) -> CrawlerStats:
        """
        运行爬虫

        Returns:
            爬虫统计信息
        """
        logger.info(f"Starting {self.name} spider...")

        logger.info(f"Fetching: {self.pipeline_url}")
        response = self.fetch_page(self.pipeline_url)

        if not response:
            self.stats.add_failed(f"Failed to fetch: {self.pipeline_url}")
            return self.stats

        # 解析管线数据
        pipelines = self.parse_pipeline_page(response.text)
        logger.info(f"Parsed {len(pipelines)} pipelines from page")

        # 收集本次看到的药物代码
        seen_drug_codes = []

        # 入库
        for item in pipelines:
            seen_drug_codes.append(item.drug_code)

            # 检查终止状态
            if DiscontinuationDetector.is_discontinued(item.indication):
                item.status = 'discontinued'
                logger.warning(f"Pipeline {item.drug_code} is discontinued")

            success = self.save_to_database(item)
            if success:
                self.stats.add_success()
            else:
                self.stats.add_failed(f"Failed to save: {item.drug_code}")

        # 检测消失的管线（竞品退场）
        disappeared = self.check_discontinued_pipelines(seen_drug_codes)

        if disappeared:
            logger.warning(f"Detected {len(disappeared)} disappeared pipelines")

        logger.info(f"Spider completed. Stats: {self.stats.to_dict()}")
        return self.stats

    def parse_pipeline_page(self, html: str) -> List[PipelineDataItem]:
        """
        解析管线页面

        Args:
            html: 页面 HTML 内容

        Returns:
            管线数据列表
        """
        import re

        pipelines = []

        # 使用正则表达式提取每个管线项目的HTML块
        # 模式：从 <li class="pipeline-list-item-li"> 开始到 </li> 结束
        pattern = r'<li[^>]*class="pipeline-list-item-li[^"]*"[^>]*>(.*?)</li>'
        matches = re.findall(pattern, html, re.DOTALL)

        logger.info(f"Found {len(matches)} pipeline items in HTML")

        for match in matches:
            try:
                # 使用 BeautifulSoup 解析单个项目
                item_soup = self.parse_html(match)

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
                is_combination = False
                combination_drugs = []

                if pop_div:
                    # 获取所有 p 标签
                    pop_ps = pop_div.find_all('p')

                    if len(pop_ps) >= 1:
                        # 第一个 p 标签：适应症
                        indication_text = pop_ps[0].get_text(separator=' ', strip=True)
                        # 清理文本
                        indication = re.sub(r'\s+', ' ', indication_text).strip()

                        # 检测联合用药（在清理之前检测）
                        is_combination, combination_drugs = CombinationTherapyDetector.detect_combination(
                            indication_text,
                            [drug_code]
                        )

                        # 移除治疗方式信息（已在is_combination中标记）
                        indication = indication.replace('单 药', '').replace('单药', '')
                        indication = indication.replace('药或联合', '').replace('联合', '').strip()

                    if len(pop_ps) >= 2:
                        # 第二个 p 标签：阶段
                        phase_text = pop_ps[1].get_text(separator=' ', strip=True)
                        # 提取阶段信息
                        phase_match = re.search(r'[ⅠⅡⅢⅣ]+期|Phase [123]|上市|批准|临床前|Approved', phase_text)
                        phase = phase_match.group(0) if phase_match else phase_text.strip()

                # 创建数据项（不在此处标准化，让save_to_database处理）
                pipeline_data = PipelineDataItem(
                    drug_code=drug_code,
                    company_name=self.company_name,
                    indication=indication,
                    phase=phase,  # 传递原始阶段，save_to_database会标准化
                    source_url=self.pipeline_url,
                    targets=[target] if target else [],
                    is_combination=is_combination,  # 联合用药标记
                    combination_drugs=combination_drugs  # 联合药物列表
                )

                pipelines.append(pipeline_data)

            except Exception as e:
                logger.error(f"Error parsing pipeline item: {e}")
                continue

        logger.info(f"Parsed {len(pipelines)} pipelines")
        return pipelines

    def parse_pipeline_item(self, item_html: Tag) -> Optional[PipelineDataItem]:
        """
        解析单个管线项目

        Args:
            item_html: 管线项目的 HTML 元素

        Returns:
            管线数据或 None
        """
        try:
            # TODO: 根据实际的 HTML 结构来提取数据
            # 以下是示例代码

            # 提取药物代码
            # 例如：<span class="drug-code">SHR-1210</span>
            drug_code_elem = item_html.find("span", class_="drug-code")
            drug_code = drug_code_elem.text.strip() if drug_code_elem else ""

            # 提取适应症
            # 例如：<span class="indication">非小细胞肺癌</span>
            indication_elem = item_html.find("span", class_="indication")
            indication = indication_elem.text.strip() if indication_elem else ""

            # 提取阶段
            # 例如：<span class="phase">Phase 3</span>
            phase_elem = item_html.find("span", class_="phase")
            phase = phase_elem.text.strip() if phase_elem else ""

            # 提取药物类型
            # 例如：<span class="modality">单抗</span>
            modality_elem = item_html.find("span", class_="modality")
            modality = modality_elem.text.strip() if modality_elem else ""

            # 验证必填字段
            if not drug_code or not indication or not phase:
                logger.warning(f"Missing required fields: {drug_code}")
                return None

            # 创建数据项
            return PipelineDataItem(
                drug_code=drug_code,
                company_name=self.company_name,
                indication=indication,
                phase=phase,
                modality=modality,
                source_url=self.base_url,  # 记录来源
            )

        except Exception as e:
            logger.error(f"Error parsing pipeline item: {e}")
            return None

    def extract_phase_from_text(self, text: str) -> str:
        """
        从文本中提取阶段信息

        Args:
            text: 包含阶段信息的文本

        Returns:
            标准化的阶段名称
        """
        # 常见阶段模式
        patterns = [
            r"Phase\s*(\d+)",  # Phase 1, Phase 2, Phase 3
            r"(\d+)期",       # 1期, 2期, 3期（中文）
            r"(Preclinical|临床前|批准上市|Approved)",
            r"(NDA|BLA|IND)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return "Unknown"

    def extract_indication_from_text(self, text: str) -> str:
        """
        从文本中提取适应症信息

        Args:
            text: 包含适应症信息的文本

        Returns:
            标准化的适应症名称
        """
        # 常见适应症关键词
        cancer_keywords = [
            "肺癌", "NSCLC", "SCLC",
            "乳腺癌", "肝癌", "胃癌", "结直肠癌",
            "淋巴瘤", "白血病",
            "实体瘤",
        ]

        for keyword in cancer_keywords:
            if keyword in text:
                return keyword

        # 如果没有匹配，返回文本的前20个字符
        return text[:20] if text else "Unknown"


# =====================================================
# 手动配置版本（备用）
# =====================================================

class HengruiManualSpider(HengruiSpider):
    """
    恒瑞医药手动配置爬虫

    用于测试或数据手动录入
    """

    # 手动配置的管线数据（示例）
    MANUAL_PIPELINES = [
        {
            "drug_code": "SHR-1210",
            "indication": "非小细胞肺癌",
            "phase": "Phase 3",
            "modality": "单抗",
            "targets": ["PD-1"],
        },
        {
            "drug_code": "SHR-1316",
            "indication": "乳腺癌",
            "phase": "Phase 2",
            "modality": "ADC",
            "targets": ["HER2"],
        },
        {
            "drug_code": "SHR-1701",
            "indication": "实体瘤",
            "phase": "Phase 1",
            "modality": "小分子",
            "targets": ["PARP"],
        },
    ]

    def run(self) -> CrawlerStats:
        """
        运行手动配置的爬虫

        Returns:
            爬虫统计信息
        """
        logger.info(f"Running manual spider for {self.name}...")

        for data in self.MANUAL_PIPELINES:
            item = PipelineDataItem(
                drug_code=data["drug_code"],
                company_name=self.company_name,
                indication=data["indication"],
                phase=data["phase"],
                modality=data["modality"],
                source_url=self.base_url,
                targets=data.get("targets", []),
            )

            success = self.save_to_database(item)
            if success:
                self.stats.add_success()
            else:
                self.stats.add_failed(f"Failed to save: {item.drug_code}")

        logger.info(f"Manual spider completed. Stats: {self.stats.to_dict()}")
        return self.stats


__all__ = ["HengruiSpider", "HengruiManualSpider"]
