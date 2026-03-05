"""
=====================================================
PubMed 文献解析器
=====================================================

功能：
- 解析 EFetch 返回的 XML 数据
- 提取文献字段（标题、摘要、MeSH 等）
- 提取临床数据标签（ORR、PFS 等）
- 识别文献来源类型（ASCO、AACR、NEJM 等）

使用示例：
    parser = PubmedParser()
    publications = parser.parse_xml(xml_string)

    for pub in publications:
        print(f"PMID: {pub['pmid']}")
        print(f"Title: {pub['title']}")
        print(f"Clinical Data: {pub['clinical_data_tags']}")
=====================================================
"""

from typing import Optional, List, Dict, Any
import re
from datetime import datetime
from xml.etree import ElementTree as ET

from core.logger import get_logger

logger = get_logger(__name__)


# 已知的高质量来源期刊/会议
PRESTIGIOUS_SOURCES = {
    "ASCO": ["ASCO", "American Society of Clinical Oncology"],
    "AACR": ["AACR", "American Association for Cancer Research"],
    "ESMO": ["ESMO", "European Society for Medical Oncology"],
    "NEJM": ["N Engl J Med", "New England Journal of Medicine"],
    "LANCET": ["Lancet", "Lancet Oncol", "Lancet Respir Med"],
    "JAMA": ["JAMA", "JAMA Oncol"],
    "JCO": ["J Clin Oncol", "Journal of Clinical Oncology"],
    "NATURE": ["Nature", "Nature Med", "Nature Cancer"],
    "SCIENCE": ["Science"],
}


# 临床数据指标正则表达式
CLINICAL_METRICS_PATTERNS = {
    "ORR": r"(?:objective response rate|ORR)[:\s]*([0-9]+\.?[0-9]*\s*%|\d+)",
    "PFS": r"(?:progression[- ]?free survival|PFS)[:\s]*([0-9]+\.?[0-9]*\s*(?:months?|mos?|m))",
    "OS": r"(?:overall survival|OS)[:\s]*([0-9]+\.?[0-9]*\s*(?:months?|mos?|m))",
    "DCR": r"(?:disease control rate|DCR)[:\s]*([0-9]+\.?[0-9]*\s*%|\d+)",
    "n": r"(?:n\s*=\s*(\d+))",
}


class PubmedParser:
    """
    PubMed 文献解析器

    核心功能：
    1. parse_xml(): 解析 XML 文本，返回文献列表
    2. _parse_article(): 解析单篇文章
    3. _extract_clinical_data(): 提取临床数据标签
    4. _identify_source_type(): 识别文献来源类型
    """

    def __init__(self):
        """初始化解析器"""
        self.clinical_patterns = self._compile_clinical_patterns()

    def _compile_clinical_patterns(self) -> Dict[str, re.Pattern]:
        """
        编译临床数据正则表达式

        Returns:
            编译后的正则表达式字典
        """
        compiled = {}
        for metric, pattern in CLINICAL_METRICS_PATTERNS.items():
            try:
                compiled[metric] = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                logger.warning(f"Failed to compile pattern for {metric}: {e}")

        return compiled

    def parse_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        解析 PubMed EFetch XML 数据

        Args:
            xml_text: XML 文本

        Returns:
            文献字典列表

        Example:
            >>> parser = PubmedParser()
            >>> publications = parser.parse_xml(xml_string)
            >>> print(len(publications))
            10
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            return []

        publications = []

        # PubMed XML 使用 PubmedArticleSet 作为根节点
        for article in root.findall(".//PubmedArticle"):
            try:
                pub = self._parse_article(article)
                if pub:
                    publications.append(pub)
            except Exception as e:
                logger.warning(f"Failed to parse article: {e}")
                continue

        logger.info(
            f"Parsed PubMed XML",
            extra={
                "total_articles": len(root.findall(".//PubmedArticle")),
                "parsed_successfully": len(publications),
            }
        )

        return publications

    def _parse_article(self, article_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """
        解析单篇文章元素

        Args:
            article_elem: 文章 XML 元素

        Returns:
            文献字典
        """
        # PMID
        pmid_elem = article_elem.find(".//PMID")
        if pmid_elem is None:
            return None

        pmid = pmid_elem.text

        # 标题
        title = self._extract_text(article_elem, ".//ArticleTitle")
        if not title:
            title = self._extract_text(article_elem, ".//Article/ArticleTitle")

        # 摘要
        abstract = self._extract_abstract(article_elem)

        # 期刊信息
        journal = self._extract_journal(article_elem)

        # 发布日期
        pub_date = self._extract_pub_date(article_elem)

        # MeSH 主题词
        mesh_terms = self._extract_mesh_terms(article_elem)

        # 文献类型
        publication_type = self._extract_publication_type(article_elem)

        # 来源类型（ASCO/AACR 等）
        source_type = self._identify_source_type(journal)

        # 临床数据标签
        clinical_data_tags = self._extract_clinical_data(abstract, title)

        return {
            "pmid": pmid,
            "title": title or "",
            "abstract": abstract or "",
            "journal": journal,
            "pub_date": pub_date,
            "mesh_terms": mesh_terms,
            "publication_type": publication_type,
            "source_type": source_type,
            "clinical_data_tags": clinical_data_tags,
        }

    def _extract_text(self, elem: ET.Element, xpath: str) -> Optional[str]:
        """
        提取元素的文本内容

        Args:
            elem: XML 元素
            xpath: XPath 表达式

        Returns:
            文本内容
        """
        found = elem.find(xpath)
        if found is not None and found.text:
            return found.text.strip()
        return None

    def _extract_abstract(self, article_elem: ET.Element) -> Optional[str]:
        """
        提取摘要文本

        Args:
            article_elem: 文章 XML 元素

        Returns:
            摘要文本（合并多个段落）
        """
        abstract_elem = article_elem.find(".//Abstract")
        if abstract_elem is None:
            return None

        # 提取所有 AbstractText 段落
        abstract_texts = []
        for text_elem in abstract_elem.findall(".//AbstractText"):
            if text_elem.text:
                label = text_elem.get("Label", "")
                if label:
                    abstract_texts.append(f"{label}: {text_elem.text}")
                else:
                    abstract_texts.append(text_elem.text)

        return " ".join(abstract_texts) if abstract_texts else None

    def _extract_journal(self, article_elem: ET.Element) -> Optional[str]:
        """
        提取期刊名称

        Args:
            article_elem: 文章 XML 元素

        Returns:
            期刊名称
        """
        # 尝试多种 XPath 路径
        journal_elem = article_elem.find(".//Journal/Title")
        if journal_elem is not None and journal_elem.text:
            return journal_elem.text.strip()

        journal_elem = article_elem.find(".//ISOAbbreviation")
        if journal_elem is not None and journal_elem.text:
            return journal_elem.text.strip()

        return None

    def _extract_pub_date(self, article_elem: ET.Element) -> Optional[str]:
        """
        提取发布日期

        Args:
            article_elem: 文章 XML 元素

        Returns:
            日期字符串（YYYY-MM-DD 格式）
        """
        date_elem = article_elem.find(".//PubMedPubDate[@PubStatus='pubmed']")
        if date_elem is None:
            date_elem = article_elem.find(".//PubDate")

        if date_elem is None:
            return None

        # 提取年份
        year_elem = date_elem.find("Year")
        if year_elem is None or year_elem.text is None:
            return None

        year = year_elem.text

        # 提取月份
        month_elem = date_elem.find("Month")
        month = month_elem.text if month_elem is not None else "01"

        # 提取日期
        day_elem = date_elem.find("Day")
        day = day_elem.text if day_elem is not None else "01"

        # 标准化月份名称
        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
        }
        month = month_map.get(month, month)

        # 格式化日期
        try:
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except (ValueError, AttributeError):
            return f"{year}-01-01"

    def _extract_mesh_terms(self, article_elem: ET.Element) -> List[str]:
        """
        提取 MeSH 主题词

        Args:
            article_elem: 文章 XML 元素

        Returns:
            MeSH 主题词列表
        """
        mesh_terms = []

        for mesh_elem in article_elem.findall(".//MeshHeading"):
            descriptor_elem = mesh_elem.find("DescriptorName")
            if descriptor_elem is not None and descriptor_elem.text:
                mesh_terms.append(descriptor_elem.text)

        return mesh_terms

    def _extract_publication_type(self, article_elem: ET.Element) -> Optional[str]:
        """
        提取文献类型

        Args:
            article_elem: 文章 XML 元素

        Returns:
            文献类型（如 Clinical Trial, Review）
        """
        # PubMed 中的第一个 PublicationType 通常是主要类型
        pub_type_elem = article_elem.find(".//PublicationType")
        if pub_type_elem is not None and pub_type_elem.text:
            return pub_type_elem.text.strip()

        return None

    def _identify_source_type(self, journal: Optional[str]) -> Optional[str]:
        """
        识别文献来源类型

        Args:
            journal: 期刊名称

        Returns:
            来源类型（ASCO、AACR、NEJM 等）
        """
        if not journal:
            return None

        journal_lower = journal.lower()

        for source_type, patterns in PRESTIGIOUS_SOURCES.items():
            for pattern in patterns:
                if pattern.lower() in journal_lower:
                    return source_type

        return None

    def _extract_clinical_data(
        self,
        abstract: Optional[str],
        title: Optional[str],
    ) -> List[Dict[str, str]]:
        """
        提取临床数据标签

        Args:
            abstract: 摘要文本
            title: 标题文本

        Returns:
            临床数据标签列表，如 [{"metric": "ORR", "value": "45.2%"}]
        """
        clinical_data = []

        # 合并标题和摘要进行搜索
        text = " ".join(filter(None, [title, abstract]))

        if not text:
            return clinical_data

        # 提取各项指标
        for metric, pattern in self.clinical_patterns.items():
            match = pattern.search(text)
            if match:
                value = match.group(1) if match.lastindex else match.group(0)
                clinical_data.append({
                    "metric": metric,
                    "value": value.strip(),
                })

        return clinical_data


__all__ = [
    "PubmedParser",
]
