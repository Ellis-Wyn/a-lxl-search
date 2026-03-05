"""
=====================================================
君实生物官网爬虫
=====================================================

从君实生物官网爬取管线数据：
- 官网：https://www.junshipharma.com
- 管线页面：https://www.junshipharma.com/pipeline/

数据字段：
- 药物代码（drug_code）：JSXXX, JTXXX
- 适应症（indication）
- 研发阶段（phase）
- 药物类型（modality）
- 靶点（targets）

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


@spider_register("junshi")
class JunshiSpider(CompanySpiderBase):
    """
    君实生物爬虫

    官网：https://www.junshipharma.com
    """

    def __init__(self):
        super().__init__()
        self.name = "君实生物"
        self.company_name = "君实生物"
        self.base_url = "https://www.junshipharma.com"

        # 管线页面 URL
        self.pipeline_url = "https://www.junshipharma.com/pipeline/"

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

        君实生物管线页面结构：
        - 产品在 <li data-type="*" class="swiper-slide"> 中
        - 药物代码: <span><span>JS212</span></span>
        - 类型/靶点: <p class="type">EGFR×HER3 ADC</p>
        - 疾病领域: <p class="name">肿瘤</p>
        - 描述: <div class="excerpt"><p>...</p></div>

        Args:
            html: 页面 HTML 内容

        Returns:
            管线数据列表
        """
        pipelines = []

        soup = self.parse_html(html)

        # 查找所有产品项 <li> (带有 data-type 属性)
        product_items = soup.find_all('li', attrs={'data-type': True})

        logger.info(f"Found {len(product_items)} product items")

        for item in product_items:
            try:
                # 提取药物代码 <span><span>JS212</span></span>
                drug_code_elem = item.find('span').find('span') if item.find('span') else None
                if not drug_code_elem:
                    continue

                drug_code = drug_code_elem.get_text(strip=True)

                # 过滤：只处理 JS/JT 开头的代码
                if not re.match(r'^(JS|JT)\d{3,4}', drug_code):
                    continue

                # 提取类型/靶点 <p class="type">
                type_elem = item.find('p', class_='type')
                drug_type = type_elem.get_text(strip=True) if type_elem else ''

                # 提取疾病领域 <p class="name">
                area_elem = item.find('p', class_='name')
                area_name = area_elem.get_text(strip=True) if area_elem else ''

                # 提取描述 <div class="excerpt">
                excerpt_div = item.find('div', class_='excerpt')
                description = excerpt_div.get_text(' ', strip=True) if excerpt_div else ''

                # 解析详细信息
                indication, phase, modality, targets = self._parse_product_info(
                    drug_code, drug_type, area_name, description
                )

                # 创建数据项
                pipeline_data = PipelineDataItem(
                    drug_code=drug_code,
                    company_name=self.company_name,
                    indication=indication,
                    phase=phase,
                    modality=modality,
                    source_url=self.pipeline_url,
                    targets=targets,
                    description=description or f"{area_name}领域 - {drug_type}"
                )

                pipelines.append(pipeline_data)

            except Exception as e:
                logger.error(f"Error parsing product item: {e}")
                continue

        logger.info(f"Parsed {len(pipelines)} pipelines")
        return pipelines

    def _parse_product_info(
        self,
        drug_code: str,
        drug_type: str,
        area_name: str,
        description: str
    ) -> tuple:
        """
        解析产品信息

        Args:
            drug_code: 药物代码
            drug_type: 药物类型/靶点（如 "EGFR×HER3 ADC"）
            area_name: 疾病领域名称
            description: 产品描述

        Returns:
            (indication, phase, modality, targets) 元组
        """
        indication = f"{area_name}相关疾病"
        phase = "Phase 1"  # 默认阶段
        modality = None
        targets = []

        # 从 drug_type 中提取靶点信息
        # 格式如: "EGFR×HER3 ADC", "PD-1×IL-2", "CD3+CD20"
        if drug_type:
            # 提取靶点（大写字母组合）
            potential_targets = re.findall(r'[A-Z]{2,4}[-×+][A-Z]{2,4}|[A-Z]{2,6}', drug_type)
            targets = [t for t in potential_targets if t not in ['ADC', 'VEGF']]

            # 识别药物类型
            if 'ADC' in drug_type or '抗体偶联' in drug_type:
                modality = 'ADC'
            elif '×' in drug_type or '+' in drug_type or '双' in drug_type:
                modality = '双抗'
            elif 'IL-' in drug_type:
                modality = '融合蛋白'
            elif '单抗' in drug_type or '抗体' in drug_type:
                modality = '单抗'

        # 从描述中提取更多信息
        if description:
            # 提取阶段信息
            phase_match = re.search(
                r'(I期|II期|III期|Phase\s*[I|1|II|2|III|3]|已上市|批准|Approved)',
                description,
                re.IGNORECASE
            )
            if phase_match:
                phase = phase_match.group(1)

            # 提取适应症关键词
            indication_match = re.search(
                r'用于([^。。]{2,30}?)(?:的|治疗|患者)',
                description
            )
            if indication_match:
                indication = indication_match.group(1).strip()

            # 如果描述中提到具体的肿瘤类型
            cancer_types = re.findall(
                r'(?:肺癌|肝癌|胃癌|结直肠癌|乳腺癌|淋巴瘤|白血病|黑色素瘤|实体瘤)',
                description
            )
            if cancer_types:
                indication = '、'.join(list(set(cancer_types))[:3])

        # 如果没有识别到药物类型，根据药物代码推断
        if not modality:
            if drug_code == 'JS001' or '特瑞普利' in description:
                modality = '单抗'
            elif drug_code.startswith('JS'):
                modality = '生物药'
            elif drug_code.startswith('JT'):
                modality = '生物药'

        # 根据领域和药物代码补充靶点
        if not targets:
            if drug_code == 'JS001' or '特瑞普利' in description:
                targets = ['PD-1']
            elif 'PD-1' in drug_type:
                targets.append('PD-1')

        # 移除重复的靶点
        targets = list(set(targets))

        return indication, phase, modality, targets


__all__ = ["JunshiSpider"]
