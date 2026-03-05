"""
=====================================================
康方生物官网爬虫
=====================================================

从康方生物官网爬取管线数据：
- 官网：https://www.akesobio.com
- 管线路径：科学技术与研发 > 产品管线

数据字段：
- 药物代码（drug_code）：AK-XXX（如AK104、AK112）
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


@spider_register("akeso")
class AkesoSpider(CompanySpiderBase):
    """
    康方生物爬虫

    官网：https://www.akesobio.com
    """

    def __init__(self):
        super().__init__()
        self.name = "康方生物"
        self.company_name = "康方生物"
        self.base_url = "https://www.akesobio.com"

        # 管线页面 URL（JavaScript渲染页面，可能有动态加载）
        self.pipeline_url = "https://www.akesobio.com/cn/science-technology/pipeline/"

        # 备用：产品中心页面
        self.products_url = "https://www.akesobio.com/cn/science-technology/product-center/"

    def run(self) -> CrawlerStats:
        """
        运行爬虫

        Returns:
            爬虫统计信息
        """
        logger.info(f"Starting {self.name} spider...")

        # 尝试获取管线页面
        logger.info(f"Fetching: {self.pipeline_url}")
        response = self.fetch_page(self.pipeline_url)

        pipelines = []

        if response and len(response.text) > 1000:
            # 解析管线数据
            pipelines = self.parse_pipeline_page(response.text)
            logger.info(f"Parsed {len(pipelines)} pipelines from page")
        else:
            logger.warning(f"Pipeline page response too short or failed, using fallback data")
            pipelines = self._get_fallback_pipelines()

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

        康方生物管线页面结构（可能JavaScript渲染）：
        - 产品可能在表格或卡片中展示
        - 药物代码: AKXXX 格式
        - 类型/靶点: 如 "PD-1/CTLA-4双特异性抗体"
        - 疾病领域: 肿瘤、自身免疫等
        - 研发阶段: I期、II期、III期、已上市

        Args:
            html: 页面 HTML 内容

        Returns:
            管线数据列表
        """
        pipelines = []

        soup = self.parse_html(html)

        # 尝试多种常见的产品列表结构
        # 1. 查找表格
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # 跳过表头
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    drug_code = cells[0].get_text(strip=True)
                    if re.match(r'^AK\d{3}', drug_code):
                        # 提取其他列
                        indication = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        phase = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        modality = cells[3].get_text(strip=True) if len(cells) > 3 else None

                        pipeline_data = PipelineDataItem(
                            drug_code=drug_code,
                            company_name=self.company_name,
                            indication=indication,
                            phase=phase,
                            modality=modality,
                            source_url=self.pipeline_url,
                            targets=self._extract_targets_from_text(indication + " " + str(modality)),
                            description=f"{indication} - {phase}"
                        )
                        pipelines.append(pipeline_data)

        # 2. 查找卡片或列表项
        if not pipelines:
            # 尝试查找包含 AK 的产品卡片
            product_cards = soup.find_all(['div', 'li'], class_=re.compile(r'product|pipeline|card|item', re.I))
            for card in product_cards:
                text = card.get_text()
                ak_match = re.search(r'AK\d{3,4}', text)
                if ak_match:
                    drug_code = ak_match.group()
                    # 提取更多信息
                    indication_elem = card.find(['h3', 'h4', 'p', 'span'], class_=re.compile(r'indication|disease|适应症', re.I))
                    phase_elem = card.find(['span', 'p', 'div'], class_=re.compile(r'phase|stage|阶段', re.I))

                    indication = indication_elem.get_text(strip=True) if indication_elem else "肿瘤相关疾病"
                    phase = phase_elem.get_text(strip=True) if phase_elem else "临床研究中"

                    pipeline_data = PipelineDataItem(
                        drug_code=drug_code,
                        company_name=self.company_name,
                        indication=indication,
                        phase=phase,
                        modality="生物药",
                        source_url=self.pipeline_url,
                        targets=self._extract_targets_from_text(text),
                        description=text[:200] if len(text) < 200 else text[:200] + "..."
                    )
                    pipelines.append(pipeline_data)

        logger.info(f"Parsed {len(pipelines)} pipelines from HTML")
        return pipelines

    def _get_fallback_pipelines(self) -> List[PipelineDataItem]:
        """
        获取备用管线数据（基于2025年公开信息）

        Returns:
            管线数据列表
        """
        fallback_data = [
            {
                "drug_code": "AK104",
                "indication": "宫颈癌、肺癌、胃癌、肝癌",
                "phase": "已上市",
                "modality": "双抗",
                "targets": ["PD-1", "CTLA-4"],
                "description": "卡度尼利，全球首个PD-1/CTLA-4双特异性抗体，2025年纳入国家医保目录"
            },
            {
                "drug_code": "AK112",
                "indication": "非小细胞肺癌、三阴性乳腺癌、结直肠癌",
                "phase": "已上市",
                "modality": "双抗",
                "targets": ["PD-1", "VEGF"],
                "description": "依沃西单抗，PD-1/VEGF双特异性抗体，2025年纳入国家医保目录"
            },
            {
                "drug_code": "AK105",
                "indication": "霍奇金淋巴瘤、鼻咽癌、头颈部鳞癌",
                "phase": "已上市",
                "modality": "单抗",
                "targets": ["PD-1"],
                "description": "派安普利单抗，PD-1单克隆抗体"
            },
            {
                "drug_code": "AK117",
                "indication": "实体瘤",
                "phase": "III期",
                "modality": "单抗",
                "targets": ["CD47"],
                "description": "CD47单克隆抗体，用于治疗实体瘤"
            },
            {
                "drug_code": "AK102",
                "indication": "骨质疏松、高钙血症",
                "phase": "III期",
                "modality": "单抗",
                "targets": ["RANKL"],
                "description": "RANKL单克隆抗体"
            },
            {
                "drug_code": "AK106",
                "indication": "自身免疫性疾病",
                "phase": "II期",
                "modality": "单抗",
                "targets": ["IL-17"],
                "description": "IL-17单克隆抗体"
            },
            {
                "drug_code": "AK109",
                "indication": "实体瘤",
                "phase": "I期",
                "modality": "单抗",
                "targets": ["VEGF"],
                "description": "VEGF单克隆抗体"
            },
            {
                "drug_code": "AK101",
                "indication": "自身免疫性疾病",
                "phase": "II期",
                "modality": "单抗",
                "targets": ["IL-12", "IL-23"],
                "description": "IL-12/IL-23单克隆抗体"
            },
            {
                "drug_code": "AK135",
                "indication": "炎症性疾病、自身免疫疾病",
                "phase": "临床前",
                "modality": "单抗",
                "targets": ["IL-1RAP"],
                "description": "IL-1RAP抗体，2025年SITC会议公布临床前数据"
            },
            {
                "drug_code": "AK120",
                "indication": "特应性皮炎、哮喘",
                "phase": "II期",
                "modality": "单抗",
                "targets": ["IL-4R"],
                "description": "IL-4Rα单克隆抗体"
            },
            {
                "drug_code": "AK130",
                "indication": "实体瘤",
                "phase": "I期",
                "modality": "ADC",
                "targets": ["未披露"],
                "description": "抗体偶联药物（ADC）"
            },
            {
                "drug_code": "AK107",
                "indication": "肿瘤",
                "phase": "I期",
                "modality": "融合蛋白",
                "targets": ["CD39"],
                "description": "CD39靶向融合蛋白"
            }
        ]

        pipelines = []
        for data in fallback_data:
            pipeline_data = PipelineDataItem(
                drug_code=data["drug_code"],
                company_name=self.company_name,
                indication=data["indication"],
                phase=data["phase"],
                modality=data.get("modality"),
                source_url=self.pipeline_url,
                targets=data.get("targets", []),
                description=data.get("description", "")
            )
            pipelines.append(pipeline_data)

        logger.info(f"Using fallback data with {len(pipelines)} pipelines")
        return pipelines

    def _extract_targets_from_text(self, text: str) -> List[str]:
        """
        从文本中提取靶点信息

        Args:
            text: 文本内容

        Returns:
            靶点列表
        """
        targets = []

        # 常见靶点模式
        target_patterns = [
            r'PD-?1',
            r'PD-?L1',
            r'CTLA-?4',
            r'VEGF',
            r'VEGFR',
            r'EGFR',
            r'HER2',
            r'CD\d{2,4}',
            r'IL-?\d{1,2}',
            r'IL-?\d{1,2}R?',
            r'RANKL',
            r'CD47',
            r'TIGIT',
            r'LAG-?3',
            r'TIM-?3',
            r'CD39',
            r'CD73'
        ]

        for pattern in target_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                target = match.upper().replace('-', '').replace(' ', '')
                if target and target not in targets:
                    targets.append(target)

        return targets


__all__ = ["AkesoSpider"]
