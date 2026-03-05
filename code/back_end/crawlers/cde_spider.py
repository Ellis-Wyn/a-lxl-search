"""
=====================================================
CDE Spider（药审中心爬虫）
=====================================================

爬取 CDE（药审中心）网站的 IND/NDA 受理与审评信息

官网：https://www.cde.org.cn
目标：
- IND/CTA 受理
- NDA/BLA 受理
- 补充资料
- 审评状态

数据存储：
- models.CDEEvent 表
- 增量更新（基于 acceptance_no）
- 数据可追溯性（source_urls 存储所有相关URL）
=====================================================
"""

import re
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from urllib.parse import urljoin
from dataclasses import dataclass

from bs4 import BeautifulSoup
from requests import Response

from crawlers.base_spider import CompanySpiderBase, spider_register, CrawlerStats
from core.logger import get_logger
from config import settings

logger = get_logger(__name__)


@dataclass
class CDEEventData:
    """
    CDE 事件数据类（中间数据结构）

    用于在爬取过程中传递数据，确保类型安全
    """
    acceptance_no: str  # 受理号（唯一）
    event_type: str  # IND/CTA/NDA/BLA/补充资料
    drug_name: str  # 药品名称
    applicant: str  # 申请人
    public_page_url: str  # 公示页面URL
    source_urls: List[str]  # 所有相关URL

    # 可选字段
    drug_type: Optional[str] = None  # 化药/生物制品/中药
    registration_class: Optional[str] = None  # 1类/2类/3类
    indication: Optional[str] = None  # 适应症
    undertake_date: Optional[date] = None  # 承办日期
    acceptance_date: Optional[date] = None  # 受理日期
    public_date: Optional[date] = None  # 公示日期
    review_status: Optional[str] = None  # 审评状态


@spider_register("cde")
class CDESpider(CompanySpiderBase):
    """
    CDE（药审中心）爬虫

    设计原则：
    - 继承 CompanySpiderBase 复用通用功能
    - 专注 CDE 网站特定解析逻辑
    - 模块化：列表页解析、详情页解析、数据入库分离
    - 健壮性：完善的错误处理和日志记录
    """

    def __init__(self):
        """初始化 CDE 爬虫"""
        super().__init__()

        # 基本信息
        self.name = "CDE药审中心"
        self.base_url = settings.CDE_CRAWLER_BASE_URL
        self.info_disclosure_url = settings.CDE_CRAWLER_INFO_URL

        # CDE 网站特定的 URL 列表
        # 根据实际探索结果更新为真实的 CDE 信息公开页面 URL
        self.list_page_urls = [
            # 化药新药/仿制/补充申请受理列表
            "https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d",
            # 如有其他类别的列表页，可在此添加
            # f"{self.base_url}/main/xxgk/listpage/xxxxxxxx",  # 生物制品
            # f"{self.base_url}/main/xxgk/listpage/yyyyyyyy",  # 中药
        ]

        logger.info(f"CDESpider initialized: {self.base_url}")

    def run(self) -> CrawlerStats:
        """
        运行爬虫主流程

        流程：
        1. 获取列表页
        2. 解析事件列表
        3. 逐个抓取详情页
        4. 入库（增量更新）
        5. 触发告警（新 NDA/BLA）

        Returns:
            CrawlerStats: 爬虫统计信息
        """
        logger.info(f"Starting {self.name} spider...")

        # 生成爬虫运行ID
        crawler_run_id = f"cde_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # 遍历所有列表页
        for list_url in self.list_page_urls:
            try:
                logger.info(f"Fetching list page: {list_url}")

                # 1. 获取事件列表
                events = self.fetch_event_list(list_url)
                logger.info(f"Found {len(events)} events from list page")

                if not events:
                    logger.warning(f"No events found on {list_url}")
                    continue

                # 2. 逐个处理事件
                for event_data in events:
                    try:
                        # 3. 抓取详情页
                        detail = self.fetch_event_detail(event_data.public_page_url)

                        if detail:
                            # 合并数据
                            event_data.drug_type = detail.get('drug_type')
                            event_data.registration_class = detail.get('registration_class')
                            event_data.indication = detail.get('indication')
                            event_data.review_status = detail.get('review_status')

                            # 4. 保存到数据库
                            success = self.save_to_database(event_data, crawler_run_id)

                            if success:
                                self.stats.add_success()
                            else:
                                self.stats.add_failed(f"Failed to save: {event_data.acceptance_no}")
                        else:
                            self.stats.add_failed(f"Failed to fetch detail: {event_data.public_page_url}")

                    except Exception as e:
                        logger.error(f"Error processing event {event_data.acceptance_no}: {e}")
                        self.stats.add_failed(f"Error: {event_data.acceptance_no}")
                        continue

                # 遵守速率限制
                import time
                time.sleep(settings.CDE_CRAWLER_RATE_LIMIT)

            except Exception as e:
                logger.error(f"Error processing list page {list_url}: {e}")
                self.stats.add_failed(f"List page error: {list_url}")
                continue

        logger.info(f"{self.name} spider completed. Stats: {self.stats.to_dict()}")
        return self.stats

    def fetch_event_list(self, list_url: str) -> List[CDEEventData]:
        """
        获取事件列表（从列表页）

        Args:
            list_url: 列表页 URL

        Returns:
            CDEEventData 列表

        基于 CDE 实际网站结构实现：
        - 表格格式：<table class="table">
        - 列：序号、受理号、药品名称、药品类型、申请类型、注册分类、企业名称、承办日期
        - 支持分页：遍历所有页面
        """
        all_events = []
        page = 1
        max_pages = 100  # 防止无限循环

        while page <= max_pages:
            # 构建分页 URL（如果有的话）
            page_url = f"{list_url}?page={page}" if page > 1 else list_url

            logger.info(f"Fetching page {page}: {page_url}")
            response = self.fetch_page(page_url)

            if not response:
                logger.error(f"Failed to fetch list page: {page_url}")
                break

            soup = self.parse_html(response.text)

            # 解析表格（CDE 网站使用 <table class="table"> 结构）
            # 查找表格行，跳过表头
            table = soup.select_one('table')
            if not table:
                logger.warning(f"No table found on page {page}")
                break

            rows = table.select('tr')
            if len(rows) <= 1:  # 只有表头，没有数据
                logger.info(f"No more data rows on page {page}")
                break

            page_events = []
            for row in rows[1:]:  # 跳过表头行
                cols = row.select('td')
                if len(cols) < 7:  # 至少需要7列：序号、受理号、药品名称、药品类型、申请类型、注册分类、企业名称、承办日期
                    continue

                try:
                    # 提取数据
                    seq_no = cols[0].text.strip()  # 序号
                    acceptance_no = cols[1].text.strip()  # 受理号（如：CXHS2600023）
                    drug_name = cols[2].text.strip()  # 药品名称
                    drug_type = cols[3].text.strip()  # 药品类型（化药/生物制品/中药）
                    application_type = cols[4].text.strip()  # 申请类型（新药/仿制/补充申请）
                    registration_class = cols[5].text.strip()  # 注册分类（1/2.2/4等）
                    applicant = cols[6].text.strip()  # 企业名称
                    undertake_date_str = cols[7].text.strip() if len(cols) > 7 else None  # 承办日期

                    # 从受理号提取事件类型
                    # CXHS=化药新药(IND), JXHB=化药补充申请, CYHS=化药仿制, CXSL=化药临床试验申请(IND)
                    event_type = self._parse_acceptance_no_type(acceptance_no, application_type)

                    # 解析日期
                    undertake_date = None
                    if undertake_date_str:
                        try:
                            undertake_date = datetime.strptime(undertake_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            logger.warning(f"Invalid date format: {undertake_date_str}")

                    # 查找详情页链接（通常在受理号这一列有链接）
                    detail_link = cols[1].select_one('a')
                    public_page_url = urljoin(self.base_url, detail_link['href']) if detail_link else list_url

                    # 构建事件数据
                    event = CDEEventData(
                        acceptance_no=acceptance_no,
                        event_type=event_type,
                        drug_name=drug_name,
                        applicant=applicant,
                        public_page_url=public_page_url,
                        source_urls=[list_url, public_page_url],  # 包含列表页和详情页URL
                        drug_type=drug_type,
                        registration_class=registration_class,
                        undertake_date=undertake_date
                    )

                    page_events.append(event)

                except Exception as e:
                    logger.error(f"Error parsing row: {e}, row content: {row}")
                    continue

            if not page_events:
                logger.info(f"No events found on page {page}, stopping pagination")
                break

            logger.info(f"Found {len(page_events)} events on page {page}")
            all_events.extend(page_events)

            # 检查是否还有下一页
            # 查找"下一页"或分页控件
            next_button = soup.select_one('a.pagination-next') or soup.select_one('li.next a')
            if not next_button or 'disabled' in next_button.get('class', []):
                logger.info("No more pages available")
                break

            page += 1
            # 遵守速率限制
            import time
            time.sleep(settings.CDE_CRAWLER_RATE_LIMIT)

        logger.info(f"Total events fetched from {list_url}: {len(all_events)}")
        return all_events

    def fetch_event_detail(self, detail_url: str) -> Optional[Dict[str, Any]]:
        """
        获取事件详情（从详情页）

        Args:
            detail_url: 详情页 URL

        Returns:
            详情字段字典，如果失败返回 None

        基于 CDE 实际网站结构实现：
        - 详情页可能包含：适应症、审评状态、受理日期、公示日期等
        - 提取所有 PDF 附件 URL
        """
        response = self.fetch_page(detail_url)

        if not response:
            logger.error(f"Failed to fetch detail page: {detail_url}")
            return None

        soup = self.parse_html(response.text)
        detail = {}

        try:
            # CDE 详情页可能的结构：
            # 1. 使用 key-value 表格显示详细信息
            # 2. 使用 div 布局显示字段

            # 尝试提取适应症（可能在不同位置）
            indication_selectors = [
                '.indication',
                '.adapter-indication',
                'td:contains("适应症") + td',
                'div:contains("适应症") + div',
                'label:contains("适应症") + *',
            ]
            for selector in indication_selectors:
                elem = soup.select_one(selector)
                if elem:
                    detail['indication'] = elem.text.strip()
                    break

            # 尝试提取审评状态
            review_status_selectors = [
                '.review-status',
                '.status',
                'td:contains("审评状态") + td',
                'td:contains("办理状态") + td',
                'div:contains("审评状态") + div',
            ]
            for selector in review_status_selectors:
                elem = soup.select_one(selector)
                if elem:
                    detail['review_status'] = elem.text.strip()
                    break

            # 尝试提取受理日期
            acceptance_date_selectors = [
                'td:contains("受理日期") + td',
                'td:contains("受理时间") + td',
                'div:contains("受理日期") + div',
            ]
            for selector in acceptance_date_selectors:
                elem = soup.select_one(selector)
                if elem:
                    date_str = elem.text.strip()
                    try:
                        detail['acceptance_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                    break

            # 尝试提取公示日期
            public_date_selectors = [
                'td:contains("公示日期") + td',
                'td:contains("公示时间") + td',
                'div:contains("公示日期") + div',
            ]
            for selector in public_date_selectors:
                elem = soup.select_one(selector)
                if elem:
                    date_str = elem.text.strip()
                    try:
                        detail['public_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                    break

            # 提取所有附件 URL（PDF、图片等）
            attachment_urls = []
            for link in soup.select('a[href]'):
                href = link.get('href', '')
                # 检查是否是附件链接（PDF、图片等）
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png']):
                    full_url = urljoin(self.base_url, href)
                    attachment_urls.append(full_url)

            if attachment_urls:
                detail['attachment_urls'] = attachment_urls

            # 如果详情页和列表页URL不同，记录详情页URL
            if detail_url != detail_url:
                detail['detail_page_url'] = detail_url

            logger.debug(f"Fetched detail for {detail_url}: {len(detail)} fields")

        except Exception as e:
            logger.error(f"Error parsing detail page {detail_url}: {e}")
            # 即使出错也返回空字典，而不是 None
            return {}

        return detail

    def save_to_database(self, event_data: CDEEventData, crawler_run_id: str) -> bool:
        """
        保存到数据库（增量更新）

        Args:
            event_data: 事件数据
            crawler_run_id: 爬虫运行ID

        Returns:
            是否成功
        """
        from utils.database import SessionLocal
        from models.cde_event import CDEEvent

        db = SessionLocal()

        try:
            # 检查是否已存在（通过 acceptance_no）
            existing = db.query(CDEEvent).filter_by(
                acceptance_no=event_data.acceptance_no
            ).first()

            if existing:
                # 更新现有记录
                existing.drug_name = event_data.drug_name
                existing.applicant = event_data.applicant
                existing.drug_type = event_data.drug_type
                existing.registration_class = event_data.registration_class
                existing.indication = event_data.indication
                existing.review_status = event_data.review_status
                existing.undertake_date = event_data.undertake_date
                existing.acceptance_date = event_data.acceptance_date
                existing.public_date = event_data.public_date
                existing.last_seen_at = datetime.utcnow()
                existing.crawler_run_id = crawler_run_id

                # 合并 source_urls（去重）
                existing_urls = set(existing.get_source_urls())
                existing_urls.update(event_data.source_urls)
                existing.source_urls = list(existing_urls)

                logger.info(f"Updated existing CDE event: {event_data.acceptance_no}")

            else:
                # 创建新记录
                new_event = CDEEvent(
                    id=event_data.acceptance_no,  # 使用 acceptance_no 作为主键
                    acceptance_no=event_data.acceptance_no,
                    event_type=event_data.event_type,
                    drug_name=event_data.drug_name,
                    applicant=event_data.applicant,
                    public_page_url=event_data.public_page_url,
                    source_urls=event_data.source_urls,
                    drug_type=event_data.drug_type,
                    registration_class=event_data.registration_class,
                    indication=event_data.indication,
                    review_status=event_data.review_status,
                    undertake_date=event_data.undertake_date,
                    acceptance_date=event_data.acceptance_date,
                    public_date=event_data.public_date,
                    crawler_run_id=crawler_run_id,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow()
                )

                db.add(new_event)

                logger.info(f"Created new CDE event: {event_data.acceptance_no}")

                # 触发新事件告警
                self._trigger_new_event_alert(event_data)

            db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save event {event_data.acceptance_no}: {e}")
            db.rollback()
            return False

        finally:
            db.close()

    def _trigger_new_event_alert(self, event_data: CDEEventData) -> None:
        """
        触发新事件告警

        策略：
        - NDA/BLA 受理 → 高危
        - Phase 3 相关 IND → 中危
        - 其他 IND/CTA → 低危

        Args:
            event_data: 事件数据
        """
        if not self.alert_service:
            return

        from services.alert_service import AlertSeverity, AlertType

        # 判断严重程度
        if 'NDA' in event_data.event_type or 'BLA' in event_data.event_type:
            severity = AlertSeverity.HIGH
        elif '补充资料' in event_data.event_type:
            severity = AlertSeverity.MEDIUM
        elif event_data.indication and 'Phase 3' in event_data.indication:
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW

        # 构建消息
        message = (
            f"🆕 CDE新事件: {event_data.drug_name} - {event_data.event_type}\n"
            f"申请人: {event_data.applicant}\n"
            f"受理号: {event_data.acceptance_no}\n"
            f"适应症: {event_data.indication or 'N/A'}"
        )

        # 创建告警（使用现有的 alert service）
        # 注意：由于 alert_service 可能是为 pipeline 设计的，
        # 这里可能需要根据实际情况调整
        logger.warning(
            f"New CDE event alert: {event_data.event_type} - {event_data.drug_name} "
            f"(severity: {severity.value})"
        )

    def _extract_event_type(self, text: str) -> str:
        """
        从文本中提取事件类型

        Args:
            text: 原始文本

        Returns:
            标准化的事件类型
        """
        text = text.strip()

        # 映射表
        type_mapping = {
            'IND': 'IND',
            'CTA': 'CTA',
            '临床试验申请': 'IND',
            'NDA': 'NDA',
            'BLA': 'BLA',
            '新药申请': 'NDA',
            '生物制品申请': 'BLA',
            '补充资料': '补充资料',
            '补充申请': '补充资料',
        }

        for key, value in type_mapping.items():
            if key in text:
                return value

        return text

    def _parse_acceptance_no_type(self, acceptance_no: str, application_type: str) -> str:
        """
        从受理号和申请类型解析事件类型

        受理号编码规则：
        - CX**: 化药新药（**=HS为新药，**=SL为临床试验申请IND）
        - CY**: 化药仿制（**=HS为仿制申请）
        - JX**: 化药补充申请（**=HB为补充资料）
        - SX**: 生物制品相关
        - Z**: 中药相关

        Args:
            acceptance_no: 受理号（如：CXHS2600023, JXHB2600014）
            application_type: 申请类型（新药/仿制/补充申请）

        Returns:
            标准化的事件类型（IND/NDA/BLA/补充资料）
        """
        if not acceptance_no:
            return 'IND'  # 默认值

        acceptance_no = acceptance_no.upper().strip()

        # 根据受理号前缀判断
        if acceptance_no.startswith('JX'):
            # 化药补充申请
            return '补充资料'
        elif acceptance_no.startswith('CXSL'):
            # 化药临床试验申请 = IND
            return 'IND'
        elif acceptance_no.startswith('CXHS'):
            # 化药新药申请
            # 根据注册分类判断是 IND 还是 NDA
            # 1类、2类通常需要临床试验（IND）
            # 3类、4类、5类可能是直接申请 NDA
            if '补充申请' in application_type or '补充资料' in application_type:
                return '补充资料'
            else:
                # 默认认为是 IND，如果是 NDA 阶段，通常会有后续的受理号
                return 'IND'
        elif acceptance_no.startswith('CYHS'):
            # 化药仿制申请
            # 仿制药一般不需要做临床试验，直接申请上市
            return 'NDA'
        elif acceptance_no.startswith('S') or '生物制品' in application_type:
            # 生物制品
            if 'SL' in acceptance_no or '临床试验' in application_type:
                return 'CTA'  # Clinical Trial Application（生物制品）
            else:
                return 'BLA'  # Biologics License Application
        elif acceptance_no.startswith('Z'):
            # 中药
            if 'SL' in acceptance_no or '临床试验' in application_type:
                return 'IND'
            else:
                return 'NDA'
        else:
            # 未知类型，根据申请类型判断
            if '补充' in application_type:
                return '补充资料'
            elif '仿制' in application_type:
                return 'NDA'
            else:
                return 'IND'


# =====================================================
# 导出
# =====================================================

__all__ = ["CDESpider", "CDEEventData"]
