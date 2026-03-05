"""
=====================================================
百济神州官网爬虫
=====================================================

从百济神州官网爬取管线数据：
- 官网：https://www.beonemedicines.com.cn
- 管线页面：https://www.beonemedicines.com.cn/science/pipeline/

数据字段：
- 药物代码（drug_code）：BGB-*
- 适应症（indication）
- 研发阶段（phase）
- 药物类型（modality）

注意：
- 遵守 robots.txt
- 速率限制（0.3-0.5 QPS）
- 必须保留 source_url
=====================================================
"""

import re
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


@spider_register("beigene")
class BeiGeneSpider(CompanySpiderBase):
    """
    百济神州爬虫

    官网：https://www.beonemedicines.com.cn
    """

    def __init__(self):
        super().__init__()
        self.name = "百济神州"
        self.company_name = "百济神州"
        self.base_url = "https://www.beonemedicines.com.cn"

        # 管线页面 URL
        self.pipeline_url = "https://www.beonemedicines.com.cn/science/pipeline/"

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

        # 解析管线数据（百济神州官网数据结构复杂，直接使用备用方法）
        logger.info("Using fallback parsing method for BeiGene...")
        pipelines = self.parse_from_text(response.text)
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

        # 输出性能指标
        metrics = self.get_metrics()
        logger.info(f"Spider completed. Stats: {self.stats.to_dict()}")
        logger.info(f"Performance: {metrics}")

        return self.stats

    def parse_pipeline_page(self, html: str) -> List[PipelineDataItem]:
        """
        解析管线页面

        Args:
            html: 页面 HTML 内容

        Returns:
            管线数据列表
        """
        pipelines = []

        # 移除script和style标签，避免误匹配
        html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)

        # 使用更精确的正则表达式提取BGB药物及其描述
        # 匹配：BGB-XXXX + 中文描述（不是JavaScript代码）
        bgb_pattern = r'BGB-(\d+)[A-Za-z]*[：:：\s]*([^\n.。<>{]{20,200}?)(?:期|Phase|临床前|Preclinical|已上市|上市|Approved)'
        matches = re.findall(bgb_pattern, html_clean, re.IGNORECASE)

        logger.info(f"Found {len(matches)} potential pipeline items")

        for match in matches:
            try:
                drug_num, description = match
                drug_code = f"BGB-{drug_num}"

                # 清理描述文本
                description = re.sub(r'\s+', ' ', description).strip()

                # 过滤掉JavaScript/CSS代码
                if any(keyword in description for keyword in ['function(', '=>', '{', '}', 'css', 'jQuery']):
                    logger.debug(f"Skipping JS/CSS content for {drug_code}")
                    continue

                # 提取适应症（从描述中）
                indication_match = re.search(
                    r'(?:针对|治疗|用于|适应症为|indication|for|treat)[：:：\s]*([^\n，。.]{2,40}?)(?:[,，.。]|(?:的|进行|研究中))',
                    description,
                    re.IGNORECASE
                )
                indication = indication_match.group(1).strip() if indication_match else "多种适应症"

                # 如果找不到明确的适应症，使用部分描述
                if indication == "多种适应症":
                    # 尝试提取疾病相关关键词
                    disease_keywords = re.findall(
                        r'(?:血液|实体瘤|免疫|肿瘤|癌|炎症|疾病)',
                        description
                    )
                    if disease_keywords:
                        indication = '、'.join(list(set(disease_keywords))[:3])

                # 提取阶段
                phase_match = re.search(
                    r'(I期|II期|III期|Phase [I|1]|Phase [II|2]|Phase [III|3]|临床前|Preclinical|批准|Approved|上市|Launched)',
                    description,
                    re.IGNORECASE
                )
                phase = phase_match.group(1) if phase_match else "Phase 1"

                # 检测联合用药
                is_combination, combination_drugs = CombinationTherapyDetector.detect_combination(
                    description,
                    [drug_code]
                )

                # 创建数据项
                pipeline_data = PipelineDataItem(
                    drug_code=drug_code,
                    company_name=self.company_name,
                    indication=indication,
                    phase=phase,
                    source_url=self.pipeline_url,
                    is_combination=is_combination,
                    combination_drugs=combination_drugs
                )

                pipelines.append(pipeline_data)

            except Exception as e:
                logger.error(f"Error parsing pipeline item: {e}")
                continue

        logger.info(f"Parsed {len(pipelines)} pipelines")
        return pipelines

    def parse_from_text(self, html: str) -> List[PipelineDataItem]:
        """
        从纯文本中解析管线（备用方法）

        Args:
            html: HTML 内容

        Returns:
            管线数据列表
        """
        pipelines = []

        # 移除HTML标签
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()

        # 查找所有BGB代码
        bgb_codes = list(set(re.findall(r'BGB-\d+[A-Za-z]*', text)))

        logger.info(f"Found {len(bgb_codes)} unique BGB codes")

        for drug_code in bgb_codes:
            try:
                # 简化处理：只记录药物代码，其他信息标记为待确认
                pipeline_data = PipelineDataItem(
                    drug_code=drug_code,
                    company_name=self.company_name,
                    indication="多种适应症（待人工确认）",  # 简化处理
                    phase="Phase 1",  # 默认阶段
                    source_url=self.pipeline_url
                )

                pipelines.append(pipeline_data)

            except Exception as e:
                logger.error(f"Error parsing drug {drug_code}: {e}")
                continue

        return pipelines


__all__ = ["BeiGeneSpider"]
