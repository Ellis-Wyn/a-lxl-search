"""
=====================================================
PubMed API 客户端
=====================================================

功能：
- ESearch: 搜索 PubMed 文献（获取 PMID 列表）
- EFetch: 获取文献详细信息
- ESummary: 获取文献摘要信息
- 智能查询构建（关键词 + MeSH）

API 限制：
- 每秒最多 3 次请求（无 API key）
- 每秒最多 10 次请求（有 API key）
- 参考：https://www.ncbi.nlm.nih.gov/books/NBK25501/

使用示例：
    client = PubmedClient()

    # 搜索 EGFR 相关文献
    pmids = await client.search("EGFR inhibitor lung cancer", max_results=100)

    # 获取详细信息
    publications = await client.fetch_details(pmids)
=====================================================
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from core.http_client import HttpClient
from core.logger import get_logger

logger = get_logger(__name__)


# PubMed API 基础 URL
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_ESEARCH = f"{PUBMED_BASE_URL}/esearch.fcgi"
PUBMED_EFETCH = f"{PUBMED_BASE_URL}/efetch.fcgi"
PUBMED_ESUMMARY = f"{PUBMED_BASE_URL}/esummary.fcgi"


# 默认查询配置
DEFAULT_RETMAX = 100  # 每次最多返回结果数
DEFAULT_RETMODE = "json"  # 返回格式
DEFAULT_DB = "pubmed"  # 数据库名称


class PubmedClient:
    """
    PubMed API 客户端

    核心功能：
    1. search(): 搜索文献（返回 PMID 列表）
    2. fetch_details(): 获取文献详情（返回完整的 Publication 数据）
    3. build_smart_query(): 构建智能查询（关键词 + MeSH 同义词扩展）
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        delay: float = 0.35,  # 默认每秒约 3 次请求
        timeout: float = 30.0,
    ):
        """
        初始化 PubMed 客户端

        Args:
            api_key: NCBI API Key（可选，有 key 可提升速率限制）
            delay: 请求间隔（秒），避免超限
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.delay = delay
        self.last_request_time: Optional[float] = None

        # 创建 HTTP 客户端
        self.http_client = HttpClient(
            base_url=PUBMED_BASE_URL,
            timeout=timeout,
            max_retries=3,
            circuit_breaker=True,
            circuit_breaker_name="pubmed_api",
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60.0,
        )

        # 默认查询参数
        self.default_params = {
            "db": DEFAULT_DB,
            "retmax": DEFAULT_RETMAX,
            "retmode": DEFAULT_RETMODE,
        }

        if api_key:
            self.default_params["api_key"] = api_key

    async def _rate_limit(self) -> None:
        """
        速率限制控制

        确保请求间隔符合 NCBI 要求
        """
        if self.last_request_time:
            import time
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)

        import time
        self.last_request_time = time.time()

    async def _request_esearch(
        self,
        query: str,
        retmax: int = DEFAULT_RETMAX,
        retstart: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 ESearch 请求

        Args:
            query: 搜索关键词
            retmax: 最大返回结果数
            retstart: 起始位置（用于分页）
            **kwargs: 其他查询参数

        Returns:
            ESearch API 响应数据
        """
        await self._rate_limit()

        params = {
            **self.default_params,
            "term": query,
            "retmax": retmax,
            "retstart": retstart,
            **kwargs
        }

        logger.info(
            f"PubMed ESearch request",
            extra={
                "query": query[:100],
                "retmax": retmax,
                "retstart": retstart,
            }
        )

        response = await self.http_client.get(
            "/esearch.fcgi",
            params=params,
        )

        response.raise_for_status()
        data = response.json()

        # 解析结果
        result = data.get("esearchresult", {})
        count = int(result.get("count", 0))
        pmids = result.get("idlist", [])
        retmax_actual = int(result.get("retmax", 0))
        retstart_actual = int(result.get("retstart", 0))

        logger.info(
            f"PubMed ESearch completed",
            extra={
                "query": query[:100],
                "total_count": count,
                "returned_ids": len(pmids),
                "retstart": retstart_actual,
            }
        )

        return {
            "count": count,
            "pmids": pmids,
            "retmax": retmax_actual,
            "retstart": retstart_actual,
        }

    async def _request_efetch(
        self,
        pmids: List[str],
        **kwargs
    ) -> str:
        """
        执行 EFetch 请求（返回 XML）

        Args:
            pmids: PMID 列表
            **kwargs: 其他查询参数

        Returns:
            XML 响应文本
        """
        await self._rate_limit()

        params = {
            **self.default_params,
            "id": ",".join(pmids),
            "retmode": "xml",  # EFetch 必须用 XML
            **kwargs
        }

        logger.info(
            f"PubMed EFetch request",
            extra={
                "pmid_count": len(pmids),
            }
        )

        response = await self.http_client.get(
            "/efetch.fcgi",
            params=params,
        )

        response.raise_for_status()
        return response.text

    async def search(
        self,
        query: str,
        max_results: int = 100,
        date_range: Optional[tuple[str, str]] = None,
        publication_types: Optional[List[str]] = None,
    ) -> List[str]:
        """
        搜索 PubMed 文献（返回 PMID 列表）

        Args:
            query: 搜索关键词，如 "EGFR inhibitor lung cancer"
            max_results: 最大返回结果数
            date_range: 日期范围，如 ("2020/01/01", "2024/12/31")
            publication_types: 文献类型过滤，如 ["Clinical Trial", "Review"]

        Returns:
            PMID 列表

        Example:
            >>> client = PubmedClient()
            >>> pmids = await client.search("EGFR inhibitor", max_results=50)
            >>> print(len(pmids))
            50
        """
        all_pmids = []
        retstart = 0
        retmax = min(DEFAULT_RETMAX, max_results)

        # 构建查询字符串
        final_query = self._build_filtered_query(
            query,
            date_range=date_range,
            publication_types=publication_types,
        )

        # 分页获取
        while len(all_pmids) < max_results:
            result = await self._request_esearch(
                final_query,
                retmax=retmax,
                retstart=retstart,
            )

            pmids = result["pmids"]
            if not pmids:
                break

            all_pmids.extend(pmids)

            # 检查是否已获取足够数据
            if len(all_pmids) >= max_results:
                all_pmids = all_pmids[:max_results]
                break

            # 检查是否已获取所有数据
            total_count = result["count"]
            if len(all_pmids) >= total_count:
                break

            retstart += retmax

        logger.info(
            f"PubMed search completed",
            extra={
                "query": query[:100],
                "total_pmids": len(all_pmids),
                "requested_max": max_results,
            }
        )

        return all_pmids

    def _build_filtered_query(
        self,
        base_query: str,
        date_range: Optional[tuple[str, str]] = None,
        publication_types: Optional[List[str]] = None,
    ) -> str:
        """
        构建带过滤条件的查询字符串

        Args:
            base_query: 基础查询
            date_range: 日期范围
            publication_types: 文献类型

        Returns:
            查询字符串
        """
        query_parts = [f"({base_query})"]

        # 添加日期过滤
        if date_range:
            start_date, end_date = date_range
            query_parts.append(f'("{start_date}"[Date - Publication] : "{end_date}"[Date - Publication])')

        # 添加文献类型过滤
        if publication_types:
            type_filter = " OR ".join([f'"{pt}"[Publication Type]' for pt in publication_types])
            query_parts.append(f"({type_filter})")

        return " AND ".join(query_parts)

    async def fetch_details(
        self,
        pmids: List[str],
        batch_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取文献详细信息

        Args:
            pmids: PMID 列表
            batch_size: 每批获取的文献数量（最多 100）

        Returns:
            文献详情列表

        Example:
            >>> client = PubmedClient()
            >>> publications = await client.fetch_details(["12345678", "23456789"])
            >>> print(publications[0]["title"])
        """
        all_publications = []

        # 分批获取
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            xml_text = await self._request_efetch(batch_pmids)

            # 解析 XML
            from .pubmed_parser import PubmedParser
            parser = PubmedParser()
            batch_publications = parser.parse_xml(xml_text)
            all_publications.extend(batch_publications)

            logger.info(
                f"PubMed EFetch batch completed",
                extra={
                    "batch_index": i // batch_size + 1,
                    "batch_size": len(batch_pmids),
                    "parsed_count": len(batch_publications),
                }
            )

        logger.info(
            f"PubMed fetch_details completed",
            extra={
                "total_pmids": len(pmids),
                "total_publications": len(all_publications),
            }
        )

        return all_publications

    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 100,
        date_range: Optional[tuple[str, str]] = None,
        publication_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索并获取文献详情（一步完成）

        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            date_range: 日期范围
            publication_types: 文献类型

        Returns:
            文献详情列表
        """
        pmids = await self.search(
            query=query,
            max_results=max_results,
            date_range=date_range,
            publication_types=publication_types,
        )

        if not pmids:
            return []

        return await self.fetch_details(pmids)

    def build_smart_query(
        self,
        target_name: str,
        keywords: Optional[List[str]] = None,
        mesh_terms: Optional[List[str]] = None,
        use_synonyms: bool = True,
    ) -> str:
        """
        构建智能查询（关键词 + MeSH 扩展）

        Args:
            target_name: 靶点名称，如 "EGFR"
            keywords: 额外关键词，如 ["inhibitor", "lung cancer"]
            mesh_terms: MeSH 主题词，如 ["Carcinoma, Non-Small Cell Lung"]
            use_synonyms: 是否使用同义词扩展

        Returns:
            PubMed 查询字符串

        Example:
            >>> client = PubmedClient()
            >>> query = client.build_smart_query(
            ...     "EGFR",
            ...     keywords=["inhibitor", "tyrosine kinase"],
            ...     mesh_terms=["Carcinoma, Non-Small Cell Lung"]
            ... )
            >>> print(query)
            'EGFR[Ti/Ab] AND (inhibitor[Ti/Ab] OR tyrosine kinase[Ti/Ab])'
        """
        query_parts = []

        # 1. 靶点搜索（标题 + 摘要）
        target_query = f'"{target_name}"[Ti/Ab]'
        query_parts.append(target_query)

        # 2. 关键词搜索
        if keywords:
            keyword_query = " OR ".join([f'"{kw}"[Ti/Ab]' for kw in keywords])
            query_parts.append(f"({keyword_query})")

        # 3. MeSH 主题词搜索
        if mesh_terms:
            mesh_query = " OR ".join([f'"{mesh}"[MeSH Terms]' for mesh in mesh_terms])
            query_parts.append(f"({mesh_query})")

        # 组合查询
        if not query_parts:
            return target_name

        return " AND ".join(query_parts)

    async def close(self) -> None:
        """关闭客户端"""
        await self.http_client.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


__all__ = [
    "PubmedClient",
]
