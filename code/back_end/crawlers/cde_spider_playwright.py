"""
=====================================================
CDE Spider (Playwright版本) - 药审中心爬虫
=====================================================

使用 Playwright 浏览器自动化工具获取 CDE 网站数据
解决 JavaScript 动态渲染和反爬虫问题

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
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

from bs4 import BeautifulSoup

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


@spider_register("cde_playwright")
class CDESpiderPlaywright(CompanySpiderBase):
    """
    CDE（药审中心）爬虫 - Playwright版本

    使用浏览器自动化工具解决 JavaScript 动态渲染问题
    """

    def __init__(self):
        """初始化 CDE 爬虫"""
        super().__init__()

        # 基本信息
        self.name = "CDE药审中心(Playwright)"
        self.base_url = settings.CDE_CRAWLER_BASE_URL
        self.info_disclosure_url = settings.CDE_CRAWLER_INFO_URL

        # CDE 网站特定的 URL 列表
        self.list_page_urls = [
            "https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d",
        ]

        logger.info(f"CDESpider(Playwright) initialized: {self.base_url}")

    def run(self) -> CrawlerStats:
        """
        运行爬虫主流程

        流程：
        1. 获取列表页（使用 Playwright）
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

        # 使用同步包装器运行异步方法
        try:
            import asyncio
            asyncio.run(self._run_async(crawler_run_id))
        except Exception as e:
            logger.error(f"Spider run failed: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"{self.name} spider completed. Stats: {self.stats.to_dict()}")
        return self.stats

    async def _run_async(self, crawler_run_id: str):
        """异步运行爬虫"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                # 遍历所有列表页
                for list_url in self.list_page_urls:
                    try:
                        logger.info(f"Fetching list page: {list_url}")

                        # 1. 获取事件列表
                        events = await self.fetch_event_list(page, list_url)
                        logger.info(f"Found {len(events)} events from list page")

                        if not events:
                            logger.warning(f"No events found on {list_url}")
                            continue

                        # 2. 逐个处理事件
                        for event_data in events:
                            try:
                                # 3. 抓取详情页
                                detail = await self.fetch_event_detail(page, event_data.public_page_url)

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

            finally:
                await browser.close()

    async def fetch_event_list(self, page, list_url: str) -> List[CDEEventData]:
        """
        使用 Playwright 获取事件列表（从列表页）

        Args:
            page: Playwright Page 对象
            list_url: 列表页 URL

        Returns:
            CDEEventData 列表
        """
        all_events = []

        try:
            # 访问页面
            await page.goto(list_url, wait_until="networkidle", timeout=30000)

            # 等待表格加载
            try:
                await page.wait_for_selector('table, tbody, .table', timeout=10000)
            except:
                # 如果没有找到表格，可能数据是通过其他方式加载的
                logger.warning("No table found, trying alternative selectors")
                # 等待任意内容加载
                await page.wait_for_load_state("networkidle", timeout=10000)

            # 获取页面 HTML
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # 尝试多种方式查找表格
            tables = soup.find_all('table')
            if not tables:
                # 尝试查找 div 表格
                tables = soup.find_all('div', class_=re.compile(r'table|list|grid'))

            if not tables:
                logger.warning("No tables found on page, checking for data in other formats")
                # 保存 HTML 用于调试
                debug_file = "debug_playwright_page.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"Page HTML saved to {debug_file} for debugging")
                return []

            # 使用第一个找到的表格
            table = tables[0]
            rows = table.find_all('tr')

            logger.info(f"Found table with {len(rows)} rows")

            for row in rows[1:]:  # 跳过表头
                cols = row.find_all(['td', 'th'])
                if len(cols) < 7:
                    continue

                try:
                    # 提取数据
                    seq_no = cols[0].get_text(strip=True)  # 序号
                    acceptance_no = cols[1].get_text(strip=True)  # 受理号
                    drug_name = cols[2].get_text(strip=True)  # 药品名称
                    drug_type = cols[3].get_text(strip=True)  # 药品类型
                    application_type = cols[4].get_text(strip=True)  # 申请类型
                    registration_class = cols[5].get_text(strip=True)  # 注册分类
                    applicant = cols[6].get_text(strip=True)  # 企业名称
                    undertake_date_str = cols[7].get_text(strip=True) if len(cols) > 7 else None  # 承办日期

                    # 从受理号提取事件类型
                    event_type = self._parse_acceptance_no_type(acceptance_no, application_type)

                    # 解析日期
                    undertake_date = None
                    if undertake_date_str:
                        try:
                            undertake_date = datetime.strptime(undertake_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            logger.warning(f"Invalid date format: {undertake_date_str}")

                    # 查找详情页链接
                    detail_link = cols[1].find('a')
                    if detail_link and detail_link.get('href'):
                        public_page_url = urljoin(self.base_url, detail_link['href'])
                    else:
                        public_page_url = list_url

                    # 构建事件数据
                    event = CDEEventData(
                        acceptance_no=acceptance_no,
                        event_type=event_type,
                        drug_name=drug_name,
                        applicant=applicant,
                        public_page_url=public_page_url,
                        source_urls=[list_url, public_page_url],
                        drug_type=drug_type,
                        registration_class=registration_class,
                        undertake_date=undertake_date
                    )

                    all_events.append(event)
                    logger.debug(f"Parsed event: {acceptance_no} - {drug_name}")

                except Exception as e:
                    logger.error(f"Error parsing row: {e}")
                    continue

            logger.info(f"Total events fetched from {list_url}: {len(all_events)}")
            return all_events

        except Exception as e:
            logger.error(f"Failed to fetch list page with Playwright: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def fetch_event_detail(self, page, detail_url: str) -> Optional[Dict[str, Any]]:
        """
        使用 Playwright 获取事件详情（从详情页）

        Args:
            page: Playwright Page 对象
            detail_url: 详情页 URL

        Returns:
            详情字段字典，如果失败返回 None
        """
        try:
            # 访问详情页
            await page.goto(detail_url, wait_until="networkidle", timeout=30000)

            # 等待页面加载
            await page.wait_for_load_state("networkidle", timeout=10000)

            # 获取页面 HTML
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            detail = {}

            # 尝试提取适应症
            indication_selectors = [
                '.indication',
                '.adapter-indication',
                'td:contains("适应症") + td',
                'div:contains("适应症") + div',
                'label:contains("适应症") ~ *',
            ]
            for selector in indication_selectors:
                try:
                    elem = soup.select_one(selector)
                    if elem:
                        detail['indication'] = elem.get_text(strip=True)
                        break
                except:
                    continue

            # 尝试提取审评状态
            review_status_selectors = [
                '.review-status',
                '.status',
                'td:contains("审评状态") + td',
                'td:contains("办理状态") + td',
            ]
            for selector in review_status_selectors:
                try:
                    elem = soup.select_one(selector)
                    if elem:
                        detail['review_status'] = elem.get_text(strip=True)
                        break
                except:
                    continue

            # 提取所有附件 URL
            attachment_urls = []
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                    full_url = urljoin(self.base_url, href)
                    attachment_urls.append(full_url)

            if attachment_urls:
                detail['attachment_urls'] = attachment_urls

            logger.debug(f"Fetched detail for {detail_url}: {len(detail)} fields")
            return detail

        except Exception as e:
            logger.error(f"Failed to fetch detail page {detail_url}: {e}")
            return {}

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
            f"[CDE新事件] {event_data.drug_name} - {event_data.event_type}\n"
            f"申请人: {event_data.applicant}\n"
            f"受理号: {event_data.acceptance_no}\n"
            f"适应症: {event_data.indication or 'N/A'}"
        )

        # 创建告警（使用现有的 alert service）
        logger.warning(
            f"New CDE event alert: {event_data.event_type} - {event_data.drug_name} "
            f"(severity: {severity.value})"
        )

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
            if '补充申请' in application_type or '补充资料' in application_type:
                return '补充资料'
            else:
                return 'IND'
        elif acceptance_no.startswith('CYHS'):
            # 化药仿制申请
            return 'NDA'
        elif acceptance_no.startswith('S') or '生物制品' in application_type:
            # 生物制品
            if 'SL' in acceptance_no or '临床试验' in application_type:
                return 'CTA'
            else:
                return 'BLA'
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

__all__ = ["CDESpiderPlaywright", "CDEEventData"]
