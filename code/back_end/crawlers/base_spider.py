"""
=====================================================
药企爬虫基础类
=====================================================

定义爬虫的基类和共享组件：
- CompanySpiderBase: 所有药企爬虫的基类
- PipelineDataItem: 管线数据模型
- 爬虫工厂类

使用方式：
    class HengruiSpider(CompanySpiderBase):
        name = "hengrui"
        ...
=====================================================
"""

import time
import asyncio
import hashlib
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps

import re
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import or_
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from utils.database import SessionLocal
from models.pipeline import Pipeline
from models.target import Target
from models.relationships import TargetPipeline
from models.pipeline_event import PipelineEvent, EventType
from services.phase_mapper import PhaseMapper
from core.logger import get_logger

# 集成新工具模块
from utils.moa_recognizer import detect_moa
from utils.clinical_metrics_extractor import extract_clinical_metrics
from utils.pipeline_monitor import PipelineMonitor, ChangeType

logger = get_logger(__name__)


# =====================================================
# 数据模型
# =====================================================

@dataclass
class PipelineDataItem:
    """
    爬取的管线数据项

    属性：
        drug_code: 药物代码
        company_name: 公司名称
        indication: 适应症
        phase: 原始阶段文本
        modality: 药物类型
        source_url: 来源 URL
        targets: 相关靶点列表（可选）
        description: 描述（可选）
        is_combination: 是否联合用药（可选）
        combination_drugs: 联合用药列表（可选）
        status: 状态（可选）
    """
    drug_code: str
    company_name: str
    indication: str
    phase: str
    modality: Optional[str] = None
    source_url: Optional[str] = None
    targets: List[str] = field(default_factory=list)
    description: Optional[str] = None
    is_combination: bool = False
    combination_drugs: List[str] = field(default_factory=list)
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "drug_code": self.drug_code,
            "company_name": self.company_name,
            "indication": self.indication,
            "phase": self.phase,
            "phase_raw": self.phase,  # 保留原始阶段
            "modality": self.modality,
            "source_url": self.source_url,
            "targets": self.targets,
        }

    def __post_init__(self):
        """初始化后处理"""
        # 清理数据
        self.drug_code = self.drug_code.strip()
        self.indication = self.indication.strip()
        self.phase = self.phase.strip()

        if self.modality:
            self.modality = self.modality.strip()


@dataclass
class CrawlerStats:
    """爬虫统计信息"""
    total_fetched: int = 0  # 总共抓取数量
    success: int = 0          # 成功入库数量
    failed: int = 0           # 失败数量
    skipped: int = 0          # 跳过数量（重复等）
    errors: List[str] = field(default_factory=list)  # 错误列表

    def add_success(self):
        """增加成功计数"""
        self.success += 1
        self.total_fetched += 1

    def add_failed(self, error: str):
        """增加失败计数"""
        self.failed += 1
        self.total_fetched += 1
        self.errors.append(error)

    def add_skipped(self):
        """增加跳过计数"""
        self.skipped += 1
        self.total_fetched += 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_fetched": self.total_fetched,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
        }


# =====================================================
# 配置常量
# =====================================================

class CrawlerConfig:
    """爬虫配置"""

    # 请求配置
    DEFAULT_TIMEOUT: int = 30  # 秒
    DEFAULT_RETRY: int = 3     # 重试次数
    RETRY_BACKOFF: float = 0.5  # 重试退避（秒）
    RETRY_STATUS_CODES = [500, 502, 503, 504, 429]  # 需要重试的状态码

    # 速率限制（遵守 robots.txt）
    MIN_DELAY: float = 0.3     # 最小延迟（秒）
    MAX_DELAY: float = 0.5     # 最大延迟（秒）

    # 缓存配置
    ENABLE_CACHE: bool = True  # 是否启用缓存
    CACHE_TTL: int = 3600      # 缓存有效期（秒，1小时）

    # 熔断器配置
    CIRCUIT_BREAKER_THRESHOLD: int = 5  # 连续失败次数阈值
    CIRCUIT_BREAKER_TIMEOUT: int = 60   # 熔断器打开后的冷却时间（秒）

    # User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


# =====================================================
# 响应缓存
# =====================================================

class ResponseCache:
    """
    简单的响应缓存

    使用内存缓存，避免重复请求相同的URL
    """

    def __init__(self, ttl: int = CrawlerConfig.CACHE_TTL):
        """
        初始化缓存

        Args:
            ttl: 缓存有效期（秒）
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl
        logger.info(f"ResponseCache initialized with TTL={ttl}s")

    def _get_cache_key(self, url: str) -> str:
        """生成缓存键"""
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[str]:
        """
        从缓存获取响应

        Args:
            url: 请求URL

        Returns:
            缓存的响应内容或None
        """
        if not CrawlerConfig.ENABLE_CACHE:
            return None

        key = self._get_cache_key(url)

        if key in self._cache:
            cache_entry = self._cache[key]

            # 检查是否过期
            if datetime.now() - cache_entry['timestamp'] < timedelta(seconds=self._ttl):
                logger.debug(f"Cache HIT: {url}")
                return cache_entry['content']
            else:
                # 过期，删除
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {url}")

        logger.debug(f"Cache MISS: {url}")
        return None

    def set(self, url: str, content: str):
        """
        设置缓存

        Args:
            url: 请求URL
            content: 响应内容
        """
        if not CrawlerConfig.ENABLE_CACHE:
            return

        key = self._get_cache_key(url)
        self._cache[key] = {
            'content': content,
            'timestamp': datetime.now()
        }
        logger.debug(f"Cached: {url}")

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


# =====================================================
# 熔断器
# =====================================================

class CircuitBreaker:
    """
    熔断器

    当连续失败次数达到阈值时，熔断器打开，阻止后续请求
    一段时间后进入半开状态，尝试恢复
    """

    class State(Enum):
        CLOSED = "closed"      # 正常状态
        OPEN = "open"          # 熔断打开状态
        HALF_OPEN = "half_open"  # 半开状态（尝试恢复）

    def __init__(self, threshold: int = CrawlerConfig.CIRCUIT_BREAKER_THRESHOLD,
                 timeout: int = CrawlerConfig.CIRCUIT_BREAKER_TIMEOUT):
        """
        初始化熔断器

        Args:
            threshold: 连续失败次数阈值
            timeout: 熔断器打开后的冷却时间（秒）
        """
        self._threshold = threshold
        self._timeout = timeout
        self._failure_count = 0
        self._success_count = 0
        self._state = self.State.CLOSED
        self._last_failure_time: Optional[datetime] = None
        logger.info(f"CircuitBreaker initialized: threshold={threshold}, timeout={timeout}s")

    def _can_attempt(self) -> bool:
        """检查是否可以尝试请求"""
        if self._state == self.State.CLOSED:
            return True

        if self._state == self.State.OPEN:
            # 检查是否超过冷却时间
            if (datetime.now() - self._last_failure_time).total_seconds() >= self._timeout:
                self._state = self.State.HALF_OPEN
                logger.info("CircuitBreaker: OPEN -> HALF_OPEN")
                return True
            return False

        if self._state == self.State.HALF_OPEN:
            return True

        return False

    def record_success(self):
        """记录成功"""
        if self._state == self.State.HALF_OPEN:
            self._success_count += 1
            # 半开状态下连续成功则恢复
            if self._success_count >= 2:
                self._state = self.State.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info("CircuitBreaker: HALF_OPEN -> CLOSED")
        elif self._state == self.State.CLOSED:
            self._failure_count = 0

    def record_failure(self):
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self._threshold:
            if self._state != self.State.OPEN:
                self._state = self.State.OPEN
                logger.error(f"CircuitBreaker: CLOSED -> OPEN (failures={self._failure_count})")

    def get_state(self) -> State:
        """获取当前状态"""
        return self._state

    def reset(self):
        """重置熔断器"""
        self._failure_count = 0
        self._success_count = 0
        self._state = self.State.CLOSED
        logger.info("CircuitBreaker: RESET")


# =====================================================
# 性能监控
# =====================================================

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0
    total_response_time: float = 0.0  # 总响应时间（秒）
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    last_request_time: Optional[datetime] = None

    def record_request(self, success: bool, cached: bool, response_time: float):
        """
        记录请求

        Args:
            success: 是否成功
            cached: 是否来自缓存
            response_time: 响应时间（秒）
        """
        self.total_requests += 1
        self.last_request_time = datetime.now()

        if cached:
            self.cached_requests += 1
        elif success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        if not cached:
            self.total_response_time += response_time
            self.min_response_time = min(self.min_response_time, response_time)
            self.max_response_time = max(self.max_response_time, response_time)

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    def get_avg_response_time(self) -> float:
        """获取平均响应时间"""
        non_cached = self.total_requests - self.cached_requests
        if non_cached == 0:
            return 0.0
        return self.total_response_time / non_cached

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "cached_requests": self.cached_requests,
            "success_rate": f"{self.get_success_rate():.2f}%",
            "avg_response_time": f"{self.get_avg_response_time():.3f}s",
            "min_response_time": f"{self.min_response_time:.3f}s" if self.min_response_time != float('inf') else "N/A",
            "max_response_time": f"{self.max_response_time:.3f}s",
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None
        }


# =====================================================
# 基础爬虫类
# =====================================================

class CompanySpiderBase:
    """
    药企爬虫基类（增强版）

    提供通用的爬虫功能：
    - HTTP 请求（带重试、缓存、熔断器）
    - HTML 解析
    - 数据标准化
    - 数据库入库
    - 性能监控
    """

    def __init__(self):
        """初始化爬虫"""
        self.name: str = "base_spider"
        self.base_url: str = ""
        self.company_name: str = ""
        self.stats = CrawlerStats()

        # 初始化 Phase Mapper
        self.phase_mapper = PhaseMapper()

        # 初始化 Alert Service
        from services.alert_service import get_alert_service
        self.alert_service = get_alert_service()

        # 初始化缓存
        self.cache = ResponseCache()

        # 初始化熔断器
        self.circuit_breaker = CircuitBreaker()

        # 初始化性能监控
        self.metrics = PerformanceMetrics()

        # Session 配置（带重试机制）
        self.session = self._create_session()
        self.session.headers.update({
            "User-Agent": CrawlerConfig.USER_AGENT
        })

        logger.info(f"Initialized {self.name} spider with enhanced features")

    def _create_session(self) -> requests.Session:
        """
        创建带重试机制的Session

        Returns:
            配置好的Session对象
        """
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=CrawlerConfig.DEFAULT_RETRY,
            backoff_factor=CrawlerConfig.RETRY_BACKOFF,
            status_forcelist=CrawlerConfig.RETRY_STATUS_CODES,
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def fetch_page(self, url: str, timeout: int = None, use_cache: bool = True) -> Optional[requests.Response]:
        """
        获取页面内容（增强版：带缓存、熔断器、性能监控）

        Args:
            url: 页面 URL
            timeout: 超时时间（秒）
            use_cache: 是否使用缓存

        Returns:
            Response 对象或 None
        """
        timeout = timeout or CrawlerConfig.DEFAULT_TIMEOUT
        start_time = time.time()

        # 检查熔断器
        if not self.circuit_breaker._can_attempt():
            logger.error(f"Circuit breaker is OPEN, blocking request to: {url}")
            self.metrics.record_request(success=False, cached=False, response_time=0)
            return None

        # 检查缓存
        if use_cache:
            cached_content = self.cache.get(url)
            if cached_content is not None:
                # 创建一个伪造的Response对象
                response = requests.Response()
                response.status_code = 200
                response._content = cached_content.encode('utf-8')
                response.url = url

                response_time = time.time() - start_time
                self.metrics.record_request(success=True, cached=True, response_time=response_time)
                return response

        # 发起请求
        try:
            # 速率限制
            time.sleep(CrawlerConfig.MIN_DELAY)

            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()

            # 记录成功
            response_time = time.time() - start_time
            self.metrics.record_request(success=True, cached=False, response_time=response_time)
            self.circuit_breaker.record_success()

            # 缓存响应
            if use_cache and response.status_code == 200:
                self.cache.set(url, response.text)

            logger.debug(f"Fetched: {url} (status={response.status_code}, time={response_time:.3f}s)")
            return response

        except requests.RequestException as e:
            # 记录失败
            response_time = time.time() - start_time
            self.metrics.record_request(success=False, cached=False, response_time=response_time)
            self.circuit_breaker.record_failure()

            logger.error(f"Failed to fetch {url}: {e} (time={response_time:.3f}s)")
            return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """
        解析 HTML

        Args:
            html: HTML 内容

        Returns:
            BeautifulSoup 对象
        """
        return BeautifulSoup(html, "html.parser")

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        metrics = self.metrics.to_dict()
        metrics['circuit_breaker_state'] = self.circuit_breaker.get_state().value
        metrics['cache_size'] = self.cache.size()
        return metrics

    def reset_circuit_breaker(self):
        """重置熔断器"""
        self.circuit_breaker.reset()
        logger.info("Circuit breaker reset manually")

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()

    def _extract_targets_from_text(self, text: str) -> List[str]:
        """
        从文本中提取靶点信息（通用实现）

        Args:
            text: 文本内容（通常来自 indication）

        Returns:
            靶点列表（标准化后的名称）
        """
        if not text:
            return []

        targets = []

        # 常见靶点模式（涵盖大多数药企的靶点）
        target_patterns = [
            # 生长因子受体
            r'EGFR', r'HER2', r'HER3', r'HER4', r'VEGF', r'VEGFR1', r'VEGFR2', r'VEGFR3',
            r'FGFR', r'PDGFR', r'C-MET', r'MET', r'RON', r'IGF1R',

            # 免疫检查点
            r'PD-?1', r'PD-?L1', r'PD-?L2', r'CTLA-?4', r'LAG-?3', r'TIM-?3',
            r'TIGIT', r'CD47', r'SIRPα',

            # CD 系列靶点
            r'CD19', r'CD20', r'CD22', r'CD33', r'CD38', r'CD79[bB]', r'CD123',
            r'CD3', r'CD4', r'CD8', r'CD28', r'CD137', r'CD127', r'CD70',

            # 其他激酶
            r'ALK', r'ROS1', r'NTRK', r'BTK', r'JAK', r'SYK', r'BCL-?2',
            r'PI3K', r'AKT', r'mTOR', r'MAPK', r'ERK',

            # 其他靶点
            r'PARP', r'KRAS', r'NRAS', r'HRAS', r'BRAF', r'BRCA',
            r'IDH1', r'IDH2', r'FLT3', r'c-?KIT',
        ]

        # 提取靶点
        for pattern in target_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # 标准化靶点名称
                target = match.upper().replace('-', '').replace(' ', '')

                # 特殊处理
                if target == 'PDL1':
                    target = 'PD-L1'
                elif target == 'PDL2':
                    target = 'PD-L2'
                elif target == 'PDCD1':
                    target = 'PD-1'
                elif target == 'CD79B':
                    target = 'CD79b'
                elif target == 'SIRPA':
                    target = 'SIRPα'

                # 去重
                if target and target not in targets:
                    targets.append(target)

        return targets

    def normalize_phase(self, raw_phase: str) -> str:
        """
        标准化阶段名称

        Args:
            raw_phase: 原始阶段文本

        Returns:
            标准化的阶段名称
        """
        if not raw_phase:
            return "Unknown"

        # 使用 PhaseMapper 标准化
        return self.phase_mapper.normalize(raw_phase)

    def _is_phase_forward(self, old_phase: str, new_phase: str) -> bool:
        """
        判断phase是否是"前进"（用于Phase Jump告警）

        Args:
            old_phase: 旧的阶段（标准化后）
            new_phase: 新的阶段（标准化后）

        Returns:
            True如果新阶段比旧阶段更靠后，否则False

        Examples:
            _is_phase_forward("Phase 1", "Phase 2") → True
            _is_phase_forward("Phase 2", "Phase 1") → False
            _is_phase_forward("Phase 2", "Phase 2") → False
        """
        try:
            from services.phase_mapper import PHASE_ORDER, StandardPhase

            # 标准化输入
            old_standard = self.phase_mapper.normalize(old_phase)
            new_standard = self.phase_mapper.normalize(new_phase)

            # 转换为StandardPhase枚举
            old_enum = StandardPhase(old_standard)
            new_enum = StandardPhase(new_standard)

            # 获取阶段顺序值
            old_order = PHASE_ORDER.get(old_enum, -999)
            new_order = PHASE_ORDER.get(new_enum, -999)

            # 新阶段 > 旧阶段 = 前进
            is_forward = new_order > old_order

            logger.debug(
                f"Phase comparison: {old_phase}({old_order}) → "
                f"{new_phase}({new_order}), forward={is_forward}"
            )

            return is_forward

        except Exception as e:
            logger.warning(f"Failed to compare phases '{old_phase}' → '{new_phase}': {e}")
            # 如果无法比较，默认不是前进（避免误报）
            return False

    def discover_pipeline_url(self, homepage_url: str) -> Optional[str]:
        """
        从官网首页自动发现 Pipeline 页面 URL

        Args:
            homepage_url: 官网首页 URL

        Returns:
            Pipeline 页面 URL 或 None

        Examples:
            >>> url = spider.discover_pipeline_url("https://www.hengrui.com")
            >>> print(url)
            'https://www.hengrui.com/RD/pipeline.html'
        """
        from urllib.parse import urljoin

        try:
            logger.info(f"Discovering pipeline URL from: {homepage_url}")

            # 1. 获取首页
            response = self.fetch_page(homepage_url)
            if not response:
                logger.warning(f"Failed to fetch homepage: {homepage_url}")
                return None

            # 2. 解析HTML，查找包含关键词的链接
            keywords = [
                "Pipeline", "R&D", "Product Portfolio", "Research",
                "管线", "研发", "产品管线"
            ]

            soup = self.parse_html(response.text)

            # 查找所有链接
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text().strip()

                # 检查链接文本和href是否包含关键词
                text_lower = text.lower()
                href_lower = href.lower()

                # 匹配关键词（不区分大小写）
                if any(kw.lower() in text_lower or kw.lower() in href_lower for kw in keywords):
                    # 构造完整URL
                    full_url = urljoin(homepage_url, href)

                    logger.info(
                        f"✓ Discovered pipeline URL: {full_url} "
                        f"(link text: '{text[:50]}')"
                    )

                    return full_url

            # 未找到匹配的链接
            logger.warning(
                f"No pipeline URL found on homepage: {homepage_url}. "
                f"Searched for keywords: {', '.join(keywords)}"
            )
            return None

        except Exception as e:
            logger.error(f"Failed to discover pipeline URL from {homepage_url}: {e}")
            return None

    def _build_analysis_text(self, item: PipelineDataItem) -> str:
        """构建用于 MoA 识别和临床数据提取的文本"""
        return f"{item.indication} {item.description or ''}".strip()

    def _send_phase_jump_alert(self, item: PipelineDataItem, old_phase: str, new_phase: str) -> None:
        """发送 Phase Jump 告警"""
        logger.warning(
            f"⚠️  Phase Jump detected: {item.drug_code} ({item.company_name}) "
            f"{old_phase} → {new_phase}"
        )

        if not (hasattr(self, 'alert_service') and self.alert_service):
            return

        try:
            alert = self.alert_service.create_phase_jump_alert(
                company_name=item.company_name,
                drug_code=item.drug_code,
                old_phase=old_phase,
                new_phase=new_phase
            )
            self.alert_service.send_alert(alert)
            logger.info(f"✓ Phase Jump alert sent for {item.drug_code}")
        except Exception as e:
            logger.error(f"Failed to send phase jump alert: {e}")

    def _link_targets_to_pipeline(
        self,
        db: Session,
        pipeline: Pipeline,
        item: PipelineDataItem,
        targets: list
    ) -> int:
        """
        将靶点关联到管线，并记录靶点变更事件

        注意：此方法不自动提交，由调用方统一管理事务

        Args:
            db: 数据库会话
            pipeline: 管线对象
            item: 管线数据项
            targets: 靶点名称列表

        Returns:
            成功关联的靶点数量
        """
        # 获取现有靶点（用于变更检测）
        existing_target_names = {
            tp.target.standard_name
            for tp in pipeline.targets
        }

        linked_count = 0
        new_target_names = set()
        # 判断靶点来源：爬虫提取的非空列表 vs 文本回退提取
        evidence_source = "爬虫提取" if item.targets and len(item.targets) > 0 else "文本提取"

        # === 第一阶段：关联靶点 ===
        for target_name in targets:
            try:
                target = db.query(Target).filter(
                    or_(
                        Target.standard_name == target_name,
                        Target.aliases.contains([target_name])
                    )
                ).first()

                if not target:
                    # 创建新靶点（不立即提交）
                    target = Target(
                        standard_name=target_name,
                        aliases=[],
                        category="未知",
                        description=f"自动创建于管线爬虫: {item.drug_code}"
                    )
                    db.add(target)
                    # flush 获取 ID，但不提交事务
                    db.flush()
                    db.refresh(target)

                # 检查是否已存在关联
                existing_link = db.query(TargetPipeline).filter(
                    TargetPipeline.target_id == target.target_id,
                    TargetPipeline.pipeline_id == pipeline.pipeline_id
                ).first()

                if not existing_link:
                    link = TargetPipeline(
                        target_id=target.target_id,
                        pipeline_id=pipeline.pipeline_id,
                        relation_type="targets",
                        evidence_snippet=f"{evidence_source}: {item.indication[:100]}"
                    )
                    db.add(link)
                    linked_count += 1
                    new_target_names.add(target_name)

            except Exception as e:
                logger.error(f"Failed to link target {target_name} for {item.drug_code}: {e}", exc_info=True)

        # === 第二阶段：批量记录靶点变更事件 ===
        # 新增的靶点
        for target_name in (new_target_names - existing_target_names):
            self._record_event(
                db, pipeline, EventType.TARGET_ADDED,
                {
                    "target_name": target_name,
                    "evidence_source": evidence_source
                }
            )

        # 移除的靶点（存在于现有但不在新列表中）
        removed_targets = existing_target_names - set(targets)
        for removed_target in removed_targets:
            self._record_event(
                db, pipeline, EventType.TARGET_REMOVED,
                {
                    "target_name": removed_target,
                    "reason": "no_longer_extracted"
                }
            )

        return linked_count

    def _record_event(
        self,
        db: Session,
        pipeline: Pipeline,
        event_type: str,
        event_data: dict
    ) -> Optional[PipelineEvent]:
        """
        记录管线事件

        注意：此方法不自动提交，由调用方统一管理事务

        Args:
            db: 数据库会话
            pipeline: 管线对象
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            创建的事件对象，失败返回 None
        """
        try:
            event = PipelineEvent.create(
                db=db,
                pipeline_id=pipeline.pipeline_id,
                event_type=event_type,
                event_data=event_data,
                source="crawler",
                source_detail=self.name
            )
            logger.debug(
                f"Event recorded: {event_type} for {pipeline.drug_code} "
                f"- {event_data}"
            )
            return event
        except Exception as e:
            # 事件记录失败不应阻断主流程，但需要记录错误
            logger.error(
                f"Failed to record event {event_type} for {pipeline.drug_code}: {e}",
                exc_info=True
            )
            return None

    def _calculate_phase_duration_days(
        self,
        pipeline: Pipeline,
        old_phase: str
    ) -> Optional[int]:
        """
        计算在旧阶段持续的天数

        通过查询最后一次阶段变更事件来计算

        Args:
            pipeline: 管线对象
            old_phase: 旧阶段名称

        Returns:
            持续天数，无法计算返回 None
        """
        try:
            # 查询该管线最后一次 phase_changed 为 old_phase 的事件
            from models.pipeline_event import PipelineEvent
            db = SessionLocal()
            try:
                last_phase_event = db.query(PipelineEvent).filter(
                    PipelineEvent.pipeline_id == pipeline.pipeline_id,
                    PipelineEvent.event_type == EventType.PHASE_CHANGED
                ).order_by(PipelineEvent.occurred_at.desc()).first()

                if last_phase_event and last_phase_event.event_data.get("new_phase") == old_phase:
                    # 从上次变更到现在的时间
                    from datetime import datetime
                    return (datetime.utcnow() - last_phase_event.occurred_at).days

                # 如果没有历史事件，使用 first_seen_at 估算
                if pipeline.first_seen_at:
                    return (datetime.utcnow() - pipeline.first_seen_at).days

            finally:
                db.close()

        except Exception as e:
            logger.warning(f"Failed to calculate phase duration for {pipeline.drug_code}: {e}")

        return None

    def _detect_and_record_phase_change(
        self,
        db: Session,
        pipeline: Pipeline,
        old_phase: str,
        new_phase: str
    ) -> Optional[PipelineEvent]:
        """
        检测并记录 Phase 变更事件

        Args:
            db: 数据库会话
            pipeline: 管线对象
            old_phase: 旧阶段
            new_phase: 新阶段

        Returns:
            创建的事件对象，无变更返回 None
        """
        if old_phase == new_phase:
            return None

        # 计算在旧阶段的天数
        days_in_old_phase = self._calculate_phase_duration_days(pipeline, old_phase)

        # 判断是否是正向推进
        is_forward = self._is_phase_forward(old_phase, new_phase)

        # 检测是否跳过阶段
        phase_order = {"preclinical": 1, "I": 2, "II": 3, "III": 4, "filing": 5, "approved": 6}
        old_order = phase_order.get(old_phase.lower().replace("phase ", "").strip(), 0)
        new_order = phase_order.get(new_phase.lower().replace("phase ", "").strip(), 0)
        jumped = is_forward and (new_order - old_order) > 1

        # 记录事件
        return self._record_event(
            db=db,
            pipeline=pipeline,
            event_type=EventType.PHASE_CHANGED,
            event_data={
                "old_phase": old_phase,
                "new_phase": new_phase,
                "is_forward": is_forward,
                "jumped": jumped,
                "days_in_old_phase": days_in_old_phase
            }
        )

    def save_to_database(self, item: PipelineDataItem) -> bool:
        """
        保存管线数据到数据库

        Args:
            item: 管线数据项

        Returns:
            是否保存成功
        """
        db = None
        try:
            db = SessionLocal()
            import json

            # === 1. MoA 识别 ===
            detected_modality = None
            moa_confidence = None
            if not item.modality:
                try:
                    moa_result = detect_moa(
                        text=self._build_analysis_text(item),
                        title=item.drug_code
                    )
                    detected_modality = moa_result.modality
                    moa_confidence = moa_result.confidence
                    if moa_confidence >= 0.7:
                        item.modality = detected_modality
                        logger.info(
                            f"MoA detected for {item.drug_code}: {detected_modality} "
                            f"(confidence: {moa_confidence:.2f})"
                        )
                except Exception as e:
                    logger.warning(f"MoA detection failed for {item.drug_code}: {e}")

            # === 2. 临床数据提取 ===
            clinical_metrics_dict = None
            try:
                clinical_metrics_dict = extract_clinical_metrics(self._build_analysis_text(item))
                if clinical_metrics_dict and any(clinical_metrics_dict.values()):
                    logger.info(
                        f"Clinical metrics for {item.drug_code}: "
                        f"ORR={clinical_metrics_dict.get('ORR')}, "
                        f"PFS={clinical_metrics_dict.get('PFS')}, "
                        f"n={clinical_metrics_dict.get('Sample_Size')}"
                    )
            except Exception as e:
                logger.warning(f"Clinical data extraction failed for {item.drug_code}: {e}")

            # === 3. 查找或创建管线 ===
            phase_normalized = self.normalize_phase(item.phase)
            existing = db.query(Pipeline).filter(
                Pipeline.drug_code == item.drug_code,
                Pipeline.company_name == item.company_name,
                Pipeline.indication == item.indication,
            ).first()

            if existing:
                # === 更新现有管线 ===
                old_phase = existing.phase
                pipeline = existing

                # 检测 Phase 变更
                if old_phase != phase_normalized:
                    # Phase 变化：检测是否是 Phase Jump 并发送告警
                    if self._is_phase_forward(old_phase, phase_normalized):
                        self._send_phase_jump_alert(item, old_phase, phase_normalized)
                    # 记录 Phase 变更事件
                    self._detect_and_record_phase_change(
                        db, pipeline, old_phase, phase_normalized
                    )

                pipeline.phase = phase_normalized
                pipeline.phase_raw = item.phase
                pipeline.last_seen_at = datetime.utcnow()

                # 检测重新激活（从 discontinued 恢复为 active）
                if pipeline.status == 'discontinued' and item.status == 'active':
                    pipeline.status = 'active'
                    days_discontinued = (
                        (datetime.utcnow() - pipeline.discontinued_at).days
                        if pipeline.discontinued_at else None
                    )
                    pipeline.discontinued_at = None
                    # 记录重新激活事件
                    self._record_event(
                        db, pipeline, EventType.REACTIVATED,
                        {"days_discontinued": days_discontinued}
                    )
                    logger.info(f"Re-activated pipeline: {item.drug_code}")

                # 检测新终止（从 active 变为 discontinued）
                if pipeline.status == 'active' and item.status == 'discontinued':
                    pipeline.status = 'discontinued'
                    pipeline.discontinued_at = datetime.utcnow()
                    # 记录终止事件
                    self._record_event(
                        db, pipeline, EventType.DISCONTINUED,
                        {
                            "reason": "crawler_marked_discontinued",
                            "last_phase": old_phase,
                            "days_active": (
                                datetime.utcnow() - pipeline.first_seen_at
                            ).days if pipeline.first_seen_at else None
                        }
                    )
                    logger.warning(f"Marked as discontinued: {item.drug_code}")

                # 检测 Modality 变更
                if detected_modality and moa_confidence >= 0.7:
                    if pipeline.modality != detected_modality:
                        old_modality = pipeline.modality
                        pipeline.modality = detected_modality
                        # 记录 Modality 变更事件
                        self._record_event(
                            db, pipeline, EventType.MODALITY_CHANGED,
                            {"old_modality": old_modality, "new_modality": detected_modality}
                        )
            else:
                # === 创建新管线 ===
                pipeline = Pipeline(
                    drug_code=item.drug_code,
                    company_name=item.company_name,
                    indication=item.indication,
                    phase=phase_normalized,
                    phase_raw=item.phase,
                    modality=item.modality or detected_modality,
                    source_url=item.source_url,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                    status=item.status,
                    is_combination=item.is_combination,
                    combination_drugs=json.dumps(item.combination_drugs) if item.combination_drugs else None,
                )
                db.add(pipeline)
                # flush 获取 ID，但不提交事务
                db.flush()

                # 记录创建事件（在同一事务内）
                self._record_event(
                    db, pipeline, EventType.CREATED,
                    {
                        "initial_phase": phase_normalized,
                        "initial_indication": item.indication,
                        "initial_modality": pipeline.modality,
                        "initial_targets": item.targets or []
                    }
                )

            # === 4. 处理靶点关联 ===
            targets_extracted = [t for t in (item.targets or []) if t and t.strip()]
            if not targets_extracted:
                targets_extracted = self._extract_targets_from_text(item.indication)
                targets_extracted = [t for t in targets_extracted if t and t.strip()]

            if targets_extracted:
                linked_count = self._link_targets_to_pipeline(db, pipeline, item, targets_extracted)
                logger.info(f"Extracted {len(targets_extracted)} targets from {item.drug_code}: {targets_extracted}")

            # === 5. 统一提交事务 ===
            # 所有关联操作完成后，一次性提交，确保原子性
            db.commit()

            # === 6. 记录保存日志 ===
            logger.info(
                f"Saved pipeline: {item.drug_code} ({phase_normalized})" +
                (f" [MoA: {detected_modality}]" if detected_modality else "") +
                (f" [Clinical: ORR={clinical_metrics_dict.get('ORR')}]" if clinical_metrics_dict and clinical_metrics_dict.get('ORR') else "") +
                (f" [Targets: {len(targets_extracted)}]" if targets_extracted else "")
            )
            return True

        except Exception as e:
            # 按错误类型分类处理
            error_type = type(e).__name__

            # 数据库连接错误
            if 'operational' in str(type(e)).lower() or 'connection' in str(e).lower():
                logger.error(f"Database connection error for {item.drug_code}: {e}")
            # 唯一约束冲突（并发插入）
            elif 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                logger.warning(f"Duplicate pipeline {item.drug_code}: {e}")
            # 其他错误
            else:
                logger.error(f"Failed to save pipeline {item.drug_code} ({error_type}): {e}")

            # 尝试回滚
            if db:
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback: {rollback_error}")

            return False

        finally:
            # 确保数据库连接关闭
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.warning(f"Failed to close database connection: {close_error}")

    def check_discontinued_pipelines(
        self,
        seen_drug_codes: List[str],
        threshold_days: int = None
    ) -> List[str]:
        """
        检测消失的管线（竞品退场）

        Args:
            seen_drug_codes: 本次爬虫看到的药物代码列表
            threshold_days: 阈值天数（默认从配置读取）

        Returns:
            消失的药物代码列表
        """
        from config import settings

        # 检查是否启用竞品退场检测
        if not settings.PIPELINE_DISAPPEARED_CHECK_ENABLED:
            logger.debug("Pipeline discontinued check is disabled")
            return []

        # 使用配置的阈值或传入的阈值
        threshold = threshold_days or settings.PIPELINE_DISAPPEARED_THRESHOLD_DAYS

        db = SessionLocal()

        try:
            # 查询该公司所有活跃管线
            existing_pipelines = db.query(Pipeline).filter(
                Pipeline.company_name == self.company_name,
                Pipeline.status == 'active'
            ).all()

            existing_codes = set(p.drug_code for p in existing_pipelines)
            seen_codes = set(seen_drug_codes)

            # 找出消失的管线
            disappeared_codes = existing_codes - seen_codes

            if disappeared_codes:
                logger.warning(
                    f"Detected {len(disappeared_codes)} disappeared pipelines: {disappeared_codes}"
                )

                # 标记为 discontinued（只标记超过阈值的）
                discontinued_count = 0
                cutoff_time = datetime.utcnow() - timedelta(days=threshold)

                for pipeline in existing_pipelines:
                    if pipeline.drug_code in disappeared_codes:
                        # 检查是否超过阈值
                        days_since_last_seen = (
                            datetime.utcnow() - pipeline.last_seen_at
                        ).days if pipeline.last_seen_at else 999

                        if days_since_last_seen >= threshold:
                            pipeline.status = 'discontinued'
                            pipeline.discontinued_at = datetime.utcnow()
                            discontinued_count += 1

                            # 创建预警
                            alert = self.alert_service.create_discontinued_alert(
                                company_name=pipeline.company_name,
                                drug_code=pipeline.drug_code,
                                indication=pipeline.indication,
                                phase=pipeline.phase,
                                reason=f"未在官网抓取到（超过{threshold}天未更新）"
                            )
                            self.alert_service.send_alert(alert)

                            logger.warning(
                                f"⚠️  Pipeline discontinued: {pipeline.drug_code} "
                                f"(last seen {days_since_last_seen} days ago)"
                            )
                        else:
                            logger.info(
                                f"Pipeline {pipeline.drug_code} not seen but "
                                f"only {days_since_last_seen} days ago (threshold: {threshold})"
                            )

                db.commit()
                logger.info(
                    f"Marked {discontinued_count}/{len(disappeared_codes)} "
                    f"pipelines as discontinued (threshold: {threshold} days)"
                )

            return list(disappeared_codes)

        except Exception as e:
            logger.error(f"Error detecting disappeared pipelines: {e}")
            db.rollback()
            return []
        finally:
            db.close()

    def detect_phase_jumps(
        self,
        old_pipelines: List[Dict[str, Any]],
        new_pipelines: List[Dict[str, Any]]
    ) -> None:
        """
        检测Phase Jump并记录日志（可以在子类的run()方法中调用）

        Args:
            old_pipelines: 旧管线数据列表（从数据库获取）
            new_pipelines: 新管线数据列表（刚爬取的）

        Example:
            在子类的run()方法中：
                # 获取旧数据
                old_data = self._get_old_pipelines_from_db()

                # 爬取新数据
                new_data = self.fetch_pipelines()

                # 保存新数据
                for item in new_data:
                    self.save_to_database(item)

                # 检测Phase Jump
                self.detect_phase_jumps(old_data, new_data)
        """
        try:
            monitor = PipelineMonitor(disappeared_threshold_days=90)

            # 分析变化
            events = monitor.analyze_pipeline_changes(old_pipelines, new_pipelines)

            # 处理Phase Jump事件
            phase_jumps = [e for e in events if isinstance(e, type(events[0])) and hasattr(e, 'change_type') and e.change_type == ChangeType.PHASE_JUMP]

            for event in events:
                if hasattr(event, 'change_type') and event.change_type == ChangeType.PHASE_JUMP:
                    logger.warning(
                        f"Phase Jump detected: {event.drug_code} ({event.company_name}) "
                        f"{event.old_phase} → {event.new_phase} "
                        f"[Level: {event.phase_jump_level}]"
                    )

                    # 发送预警（如果配置了alert_service）
                    if hasattr(self, 'alert_service'):
                        alert = self.alert_service.create_phase_jump_alert(
                            company_name=event.company_name,
                            drug_code=event.drug_code,
                            old_phase=event.old_phase,
                            new_phase=event.new_phase
                        )
                        self.alert_service.send_alert(alert)

            # 处理新进场
            for event in events:
                if hasattr(event, 'is_new') and event.is_new:
                    logger.info(
                        f"New pipeline detected: {event.drug_code} ({event.company_name}) "
                        f"in {event.phase}"
                    )

            # 处理消失管线
            for event in events:
                if hasattr(event, 'is_disappeared') and event.is_disappeared:
                    logger.warning(
                        f"Pipeline disappeared: {event.drug_code} ({event.company_name}) "
                        f"- last seen {event.days_since_update} days ago"
                    )

            if events:
                logger.info(f"Detected {len(events)} pipeline events")

        except Exception as e:
            logger.error(f"Failed to detect phase jumps: {e}")

    def run(self) -> CrawlerStats:
        """
        运行爬虫

        子类需要实现此方法

        Returns:
            爬虫统计信息
        """
        raise NotImplementedError("Subclass must implement run() method")


# =====================================================
# 爬虫工厂
# =====================================================

class CompanySpiderFactory:
    """爬虫工厂类"""

    # 爬虫注册表
    _spiders: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, spider_class: type):
        """
        注册爬虫

        Args:
            name: 爬虫名称（公司标识）
            spider_class: 爬虫类
        """
        cls._spiders[name] = spider_class
        logger.info(f"Registered spider: {name}")

    @classmethod
    def create(cls, name: str) -> Optional[CompanySpiderBase]:
        """
        创建爬虫实例

        Args:
            name: 爬虫名称

        Returns:
            爬虫实例或 None
        """
        spider_class = cls._spiders.get(name)
        if spider_class:
            return spider_class()

        logger.error(f"Spider not found: {name}")
        return None

    @classmethod
    def list_spiders(cls) -> List[str]:
        """获取所有已注册的爬虫名称"""
        return list(cls._spiders.keys())


# =====================================================
# 装饰器
# =====================================================

def spider_register(name: str):
    """
    爬虫注册装饰器

    使用方式：
        @spider_register("hengrui")
        class HengruiSpider(CompanySpiderBase):
            ...
    """
    def decorator(spider_class: type):
        CompanySpiderFactory.register(name, spider_class)
        # 添加 _spider_name 属性供自动发现使用
        spider_class._spider_name = name
        return spider_class
    return decorator


# =====================================================
# 导出
# =====================================================

__all__ = [
    # 数据模型
    "PipelineDataItem",
    "CrawlerStats",
    "PerformanceMetrics",
    # 配置
    "CrawlerConfig",
    # 基础爬虫类
    "CompanySpiderBase",
    "CompanySpiderFactory",
    "spider_register",
    # 功能组件
    "ResponseCache",
    "CircuitBreaker",
]
