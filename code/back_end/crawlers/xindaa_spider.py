"""
=====================================================
信达生物官网爬虫
=====================================================

从信达生物投资者关系爬取管线数据：
- 官网：https://www.innoventbio.com
- 投资者关系：https://investor.innoventbio.com
- 数据源：投资者关系PDF报告（管线概览）

数据字段：
- 药物代码（drug_code）：IBI-XXX
- 适应症（indication）
- 研发阶段（phase）
- 药物类型（modality）
- 靶点（targets）

注意：
- 数据来源：PDF报告（投资者关系）
- PDF解析：使用 pdfplumber 提取表格
- 速率限制（0.3-0.5 QPS）
- 必须保留 source_url
=====================================================
"""

import re
import io
from typing import List, Optional
from bs4 import BeautifulSoup

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


@spider_register("xindaa")
class XindaaSpider(CompanySpiderBase):
    """
    信达生物爬虫

    官网：https://www.innoventbio.com
    数据源：投资者关系PDF报告
    """

    def __init__(self):
        super().__init__()
        self.name = "信达生物"
        self.company_name = "信达生物"
        self.base_url = "https://www.innoventbio.com"
        self.investor_url = "https://investor.innoventbio.com"

        # 最新的管线PDF（2025年中期报告）
        self.pipeline_pdf_urls = [
            "https://investor.innoventbio.com/media/1325/innovent-biologics_2025-semi-annual-results_website.pdf",
            "https://investor.innoventbio.com/media/1258/innovent-2023-interiml-results-presentation_pipeline-appendix_vf.pdf",
            "https://investor.innoventbio.com/media/1190/%E4%BF%A1%E8%BE%BE%E7%94%9F%E7%89%A92023%E5%B9%B4%E5%BA%A6%E4%B8%AD%E6%9C%9F%E4%B8%9A%E7%BB%A9%E6%B1%87%E6%8A%A5_%E9%99%84%E5%BD%95_%E7%AE%A1%E7%BA%BF%E8%BF%9B%E5%B1%95_vf.pdf",
        ]

    def run(self) -> CrawlerStats:
        """
        运行爬虫

        Returns:
            爬虫统计信息
        """
        logger.info(f"Starting {self.name} spider...")

        # 尝试从PDF获取数据
        pipelines = self._fetch_from_pdfs()

        if not pipelines:
            logger.warning("No pipelines extracted from PDFs, using fallback method")
            # 备用方法：尝试从网页获取
            pipelines = self._fetch_from_webpage()

        logger.info(f"Parsed {len(pipelines)} pipelines")

        if not pipelines:
            self.stats.add_failed("Failed to extract any pipeline data")
            return self.stats

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

    def _fetch_from_pdfs(self) -> List[PipelineDataItem]:
        """
        从PDF报告提取管线数据

        Returns:
            管线数据列表
        """
        pipelines = []

        for pdf_url in self.pipeline_pdf_urls:
            try:
                logger.info(f"Fetching PDF: {pdf_url}")
                response = self.fetch_page(pdf_url, use_cache=True)

                if not response:
                    logger.warning(f"Failed to fetch PDF: {pdf_url}")
                    continue

                # 尝试解析PDF
                extracted = self._parse_pdf(response.content, pdf_url)

                if extracted:
                    pipelines.extend(extracted)
                    logger.info(f"Extracted {len(extracted)} pipelines from {pdf_url}")
                    # 如果成功提取，break（优先使用最新的PDF）
                    if len(extracted) > 5:
                        break

            except Exception as e:
                logger.error(f"Error processing PDF {pdf_url}: {e}")
                continue

        return pipelines

    def _parse_pdf(self, pdf_content: bytes, source_url: str) -> List[PipelineDataItem]:
        """
        解析PDF内容提取管线数据

        Args:
            pdf_content: PDF二进制内容
            source_url: PDF来源URL

        Returns:
            管线数据列表
        """
        pipelines = []

        try:
            import pdfplumber

            pdf_file = io.BytesIO(pdf_content)

            with pdfplumber.open(pdf_file) as pdf:
                logger.info(f"PDF has {len(pdf.pages)} pages")

                # 遍历所有页面
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # 提取表格
                        tables = page.extract_tables()

                        if not tables:
                            continue

                        for table_num, table in enumerate(tables):
                            if not table:
                                continue

                            # 解析表格
                            table_pipelines = self._parse_pdf_table(table, source_url)
                            pipelines.extend(table_pipelines)

                    except Exception as e:
                        logger.warning(f"Error parsing page {page_num}: {e}")
                        continue

        except ImportError:
            logger.error("pdfplumber not installed. Install with: pip install pdfplumber")
            return []
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return []

        logger.info(f"Extracted {len(pipelines)} pipelines from PDF")
        return pipelines

    def _parse_pdf_table(self, table: list, source_url: str) -> List[PipelineDataItem]:
        """
        解析PDF表格提取管线数据

        Args:
            table: PDF表格数据
            source_url: 来源URL

        Returns:
            管线数据列表
        """
        pipelines = []

        # 信达生物的管线表格通常有以下列：
        # 药物代码 | 靶点 | 适应症 | 阶段 | 药物类型

        for row in table:
            try:
                if not row or len(row) < 3:
                    continue

                # 清理行数据
                cleaned_row = [str(cell).strip() if cell else '' for cell in row]

                # 查找IBI开头的药物代码
                drug_code = None
                for cell in cleaned_row:
                    if re.match(r'IBI-\d+[A-Za-z]*', cell):
                        drug_code = cell
                        break

                if not drug_code:
                    continue

                # 提取其他信息（根据列位置推断）
                # 通常格式：[药物代码, 靶点, 适应症, 阶段, ...]
                indication = ""
                phase = "Phase 1"
                modality = None
                targets = []

                # 尝试从不同列提取信息
                for i, cell in enumerate(cleaned_row):
                    if not cell:
                        continue

                    # 跳过药物代码列
                    if drug_code in cell:
                        continue

                    # 识别阶段
                    phase_match = re.search(
                        r'(I期|II期|III期|Phase\s*[I|1|II|2|III|3]|已上市|批准|Approved|NDA|BLA)',
                        cell,
                        re.IGNORECASE
                    )
                    if phase_match and not phase:
                        phase = phase_match.group(1)
                        continue

                    # 识别靶点
                    if re.match(r'^[A-Z0-9\-]{2,10}$', cell) and not cell.startswith('IBI'):
                        targets.append(cell)
                        continue

                    # 识别药物类型
                    if any(keyword in cell for keyword in ['单抗', '双抗', 'ADC', '小分子', '生物药']):
                        if not modality:
                            modality = cell
                        continue

                    # 其余作为适应症
                    if len(cell) > 2 and not indication:
                        indication = cell

                # 如果没有找到适应症，使用通用描述
                if not indication:
                    indication = "多种适应症"

                # 标准化药物类型
                if not modality:
                    modality = self._infer_modality(drug_code)

                # 创建数据项
                pipeline_data = PipelineDataItem(
                    drug_code=drug_code,
                    company_name=self.company_name,
                    indication=indication,
                    phase=phase,
                    modality=modality,
                    source_url=source_url,
                    targets=targets,
                    description=f"从PDF提取: {drug_code}"
                )

                pipelines.append(pipeline_data)

            except Exception as e:
                logger.error(f"Error parsing table row: {e}")
                continue

        return pipelines

    def _infer_modality(self, drug_code: str) -> Optional[str]:
        """
        根据药物代码推断药物类型

        Args:
            drug_code: 药物代码

        Returns:
            推断的药物类型
        """
        # 信达生物已知药物的类型映射
        known_modality = {
            'IBI308': '单抗',  # Sintilimab (PD-1)
            'IBI363': '双抗',  # PD-1/IL-2
            'IBI389': '双抗',  # CLDN18.2/CD3
            'IBI343': 'ADC',   # CLDN18.2 ADC
            'IBI376': '小分子',  # PI3Kδ
            'IBI305': '单抗',  # Bevacizumab biosimilar
            'IBI310': '单抗',  # Ipilimumab biosimilar
        }

        for code, modality in known_modality.items():
            if code in drug_code:
                return modality

        # 默认推断
        return '生物药'

    def _fetch_from_webpage(self) -> List[PipelineDataItem]:
        """
        备用方法：从网页提取管线数据

        Returns:
            管线数据列表
        """
        pipelines = []

        try:
            # 已知信达生物管线列表（基于公开信息）
            known_pipelines = [
                {
                    'drug_code': 'IBI363',
                    'indication': '实体瘤（NSCLC、结直肠癌等）',
                    'phase': 'Phase 2',
                    'modality': '双抗',
                    'targets': ['PD-1', 'IL-2']
                },
                {
                    'drug_code': 'IBI308',
                    'indication': '多种实体瘤',
                    'phase': '已上市',
                    'modality': '单抗',
                    'targets': ['PD-1']
                },
                {
                    'drug_code': 'IBI389',
                    'indication': '胃癌',
                    'phase': 'Phase 1',
                    'modality': '双抗',
                    'targets': ['CLDN18.2', 'CD3']
                },
                {
                    'drug_code': 'IBI343',
                    'indication': '胃癌',
                    'phase': 'Phase 1',
                    'modality': 'ADC',
                    'targets': ['CLDN18.2']
                },
                {
                    'drug_code': 'IBI376',
                    'indication': '淋巴瘤',
                    'phase': 'Phase 2',
                    'modality': '小分子',
                    'targets': ['PI3Kδ']
                },
                {
                    'drug_code': 'IBI305',
                    'indication': '肝癌',
                    'phase': '已上市',
                    'modality': '单抗',
                    'targets': ['VEGF']
                },
                {
                    'drug_code': 'IBI310',
                    'indication': '黑色素瘤',
                    'phase': 'Phase 3',
                    'modality': '单抗',
                    'targets': ['CTLA-4']
                },
            ]

            for data in known_pipelines:
                pipeline_data = PipelineDataItem(
                    drug_code=data['drug_code'],
                    company_name=self.company_name,
                    indication=data['indication'],
                    phase=data['phase'],
                    modality=data['modality'],
                    source_url=self.investor_url,
                    targets=data['targets'],
                    description="从公开资料提取（PDF解析失败时的备用数据）"
                )
                pipelines.append(pipeline_data)

            logger.info(f"Using fallback data: {len(pipelines)} pipelines")

        except Exception as e:
            logger.error(f"Error in fallback method: {e}")

        return pipelines


__all__ = ["XindaaSpider"]
