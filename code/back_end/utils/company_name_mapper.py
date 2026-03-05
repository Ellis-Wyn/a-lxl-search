"""
=====================================================
公司名称映射器（Company Name Mapper）
=====================================================

功能：
1. 简称 → 全称（恒瑞 → 江苏恒瑞医药股份有限公司）
2. 中文 → 英文（百济神州 → BeiGene）
3. 同义词映射（多个名称指向同一公司）
4. 模糊匹配（支持部分匹配）
5. 批量转换

设计原则：
- 单例模式（全局唯一实例）
- 面向对象（封装映射逻辑）
- 对外暴露简洁接口
- 易于维护和扩展

使用示例：
    from utils.company_name_mapper import get_company_mapper

    mapper = get_company_mapper()

    # 标准化（简称→全称）
    full_name = mapper.normalize("恒瑞")
    # 输出: 江苏恒瑞医药股份有限公司

    # 扩展（获取所有变体）
    variants = mapper.expand("百济")
    # 输出: ['百济神州', 'BeiGene', '百济神州（北京）生物科技有限公司']

    # 搜索匹配（模糊匹配）
    matched = mapper.find_match("百济神州生物")
    # 输出: 百济神州（北京）生物科技有限公司
=====================================================
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from functools import lru_cache
import re
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CompanyMapping:
    """公司映射数据结构"""
    # 标准全称（数据库中的正式名称）
    standard_name: str

    # 英文名
    english_name: Optional[str] = None

    # 简称列表（用户可能搜索的简称）
    aliases: List[str] = field(default_factory=list)

    # 拼音缩写（可选）
    pinyin_abbr: Optional[str] = None

    # 股票代码（可选）
    stock_code: Optional[str] = None

    def __post_init__(self):
        """数据验证和清洗"""
        # 确保简称列表不包含标准名称本身
        self.aliases = [a for a in self.aliases if a != self.standard_name]

        # 去重
        self.aliases = list(set(self.aliases))


class CompanyNameMapper:
    """
    公司名称映射器

    功能：
    1. normalize(): 标准化公司名称（简称→全称）
    2. expand(): 扩展公司名称（获取所有变体）
    3. find_match(): 模糊匹配公司名称
    4. add_mapping(): 动态添加映射
    5. get_all_companies(): 获取所有公司列表
    """

    # 类变量：单例实例
    _instance: Optional['CompanyNameMapper'] = None

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化映射器"""
        if self._initialized:
            return

        self._initialized = True

        # 构建映射字典
        self._mappings: Dict[str, CompanyMapping] = {}
        self._alias_to_standard: Dict[str, str] = {}
        self._fuzzy_index: Dict[str, Set[str]] = {}

        # 加载初始数据
        self._load_initial_mappings()
        self._build_indexes()

        logger.info(f"公司名称映射器初始化完成，已加载 {len(self._mappings)} 家公司")

    def _load_initial_mappings(self) -> None:
        """加载初始公司映射数据"""

        # ==================== 国内药企 ====================
        companies = [
            # 百济神州
            {
                "standard_name": "百济神州",
                "english_name": "BeiGene",
                "aliases": ["百济", "BeiGene", "百济神州生物科技", "百济神州（北京）生物科技有限公司"],
                "pinyin_abbr": "BJ",
                "stock_code": "688235.SH"
            },

            # 信达生物
            {
                "standard_name": "信达生物",
                "english_name": "Innovent",
                "aliases": ["信达生物制药（苏州）有限公司", "Innovent Biologics", "信达制药"],
                "pinyin_abbr": "XD",
                "stock_code": "01801.HK"
            },

            # 再鼎医药
            {
                "standard_name": "再鼎医药",
                "english_name": "Zai Lab",
                "aliases": ["Zai Lab", "再鼎医药（上海）有限公司", "ZaiLab"],
                "pinyin_abbr": "ZD",
                "stock_code": "9688.HK"
            },

            # 嘉和生物
            {
                "standard_name": "嘉和生物",
                "english_name": "Genor",
                "aliases": ["Genor Biopharma", "嘉和生物药业有限公司"],
                "pinyin_abbr": "JH",
                "stock_code": "6998.HK"
            },

            # 基石药业
            {
                "standard_name": "基石药业",
                "english_name": "CStone",
                "aliases": ["CStone Pharmaceuticals", "基石药业（苏州）有限公司"],
                "pinyin_abbr": "JS",
                "stock_code": "2616.HK"
            },

            # 君实生物
            {
                "standard_name": "君实生物",
                "english_name": "Junshi",
                "aliases": ["Junshi Biosciences", "Top Alliance", "上海君实生物医药科技股份有限公司"],
                "pinyin_abbr": "JS",
                "stock_code": "688180.SH"
            },

            # 康方生物
            {
                "standard_name": "康方生物",
                "english_name": "Akeso",
                "aliases": ["Akeso Inc", "中山康方生物医药有限公司"],
                "pinyin_abbr": "KF",
                "stock_code": "9926.HK"
            },

            # 复宏汉霖
            {
                "standard_name": "复宏汉霖",
                "english_name": "Henlius",
                "aliases": ["Henlius Biotech", "上海复宏汉霖生物技术股份有限公司"],
                "pinyin_abbr": "FH",
                "stock_code": "6966.HK"
            },

            # 荣昌生物
            {
                "standard_name": "荣昌生物",
                "english_name": "RemeGen",
                "aliases": ["RemeGen Co", "荣昌生物制药（烟台）股份有限公司"],
                "pinyin_abbr": "RC",
                "stock_code": "688331.SH"
            },

            # 石药集团
            {
                "standard_name": "石药集团",
                "english_name": "CSPC",
                "aliases": ["CSPC Pharmaceutical", "CSPC Pharmaceutical Group"],
                "pinyin_abbr": "SY",
                "stock_code": "01093.HK"
            },

            # 药明生物
            {
                "standard_name": "药明生物",
                "english_name": "WuXi Bio",
                "aliases": ["WuXi AppTec", "无锡药明康德新药开发股份有限公司"],
                "pinyin_abbr": "YMKD",
                "stock_code": "603259.SH"
            },

            # 恒瑞医药
            {
                "standard_name": "恒瑞医药",
                "english_name": "Hengrui",
                "aliases": ["江苏恒瑞医药股份有限公司", "Jiangsu Hengrui", "Hengrui Medicine"],
                "pinyin_abbr": "HR",
                "stock_code": "600276.SH"
            },

            # 百奥泰
            {
                "standard_name": "百奥泰",
                "english_name": "Bio-Thera",
                "aliases": ["BioThera", "百奥泰生物制药股份有限公司"],
                "pinyin_abbr": "BAT",
                "stock_code": "688177.SH"
            },

            # 神州细胞
            {
                "standard_name": "神州细胞",
                "english_name": "ShenZhen Cell",
                "aliases": ["北京神州细胞生物技术集团股份公司"],
                "pinyin_abbr": "SZ",
                "stock_code": "688520.SH"
            },

            # 康宁杰瑞
            {
                "standard_name": "康宁杰瑞",
                "english_name": "Alphamab",
                "aliases": ["Alphamab Oncology", "苏州康宁杰瑞生物科技有限公司"],
                "pinyin_abbr": "KNJR",
                "stock_code": "9966.HK"
            },

            # 金迪克
            {
                "standard_name": "金迪克",
                "english_name": "Jindike",
                "aliases": ["江苏金迪克生物技术股份有限公司"],
                "pinyin_abbr": "JDK",
                "stock_code": "688670.SH"
            },

            # 沃森生物
            {
                "standard_name": "沃森生物",
                "english_name": "Walvax",
                "aliases": ["Walvax Biotechnology", "云南沃森生物技术股份有限公司"],
                "pinyin_abbr": "WS",
                "stock_code": "300142.SZ"
            },

            # 智飞生物
            {
                "standard_name": "智飞生物",
                "english_name": "Zhifei",
                "aliases": ["Zhifei Biological", "重庆智飞生物制品股份有限公司"],
                "pinyin_abbr": "ZF",
                "stock_code": "300122.SZ"
            },

            # 康泰生物
            {
                "standard_name": "康泰生物",
                "english_name": "BioKangtai",
                "aliases": ["Kangtai", "深圳康泰生物制品股份有限公司"],
                "pinyin_abbr": "KT",
                "stock_code": "300601.SZ"
            },

            # 华兰生物
            {
                "standard_name": "华兰生物",
                "english_name": "Hualan",
                "aliases": ["Hualan Biological Engineering", "华兰生物工程股份有限公司"],
                "pinyin_abbr": "HL",
                "stock_code": "002007.SZ"
            },

            # 天坛生物
            {
                "standard_name": "天坛生物",
                "english_name": "BPL",
                "aliases": ["Beijing Tiantan Biological", "北京天坛生物制品股份有限公司"],
                "pinyin_abbr": "TT",
                "stock_code": "600161.SH"
            },

            # 复星医药
            {
                "standard_name": "复星医药",
                "english_name": "Fosun",
                "aliases": ["Fosun Pharma", "上海复星医药（集团）股份有限公司"],
                "pinyin_abbr": "FX",
                "stock_code": "600196.SH"
            },

            # 先声药业
            {
                "standard_name": "先声药业",
                "english_name": "Simcere",
                "aliases": ["Simcere Pharmaceutical", "先声药业集团有限公司"],
                "pinyin_abbr": "XSY",
                "stock_code": "02096.HK"
            },

            # 和黄医药
            {
                "standard_name": "和黄医药",
                "english_name": "Hutchmed",
                "aliases": ["Chi-Med", "和黄中国医药科技有限公司"],
                "pinyin_abbr": "HHYY",
                "stock_code": "00013.HK"
            },

            # 亚盛医药
            {
                "standard_name": "亚盛医药",
                "english_name": "Ascentage",
                "aliases": ["Ascentage Pharma", "苏州亚盛药业有限公司"],
                "pinyin_abbr": "YSYY",
                "stock_code": "6855.HK"
            },

            # 辉瑞（国外）
            {
                "standard_name": "辉瑞制药",
                "english_name": "Pfizer",
                "aliases": ["辉瑞", "Pfizer", "辉瑞制药有限公司"],
                "pinyin_abbr": "ZR",
                "stock_code": "PFE.US"
            },

            # 默沙东（国外）
            {
                "standard_name": "默沙东",
                "english_name": "Merck",
                "aliases": ["MSD", "默克", "默沙东（中国）有限公司"],
                "pinyin_abbr": "MSD",
                "stock_code": "MRK.US"
            },

            # 罗氏（国外）
            {
                "standard_name": "罗氏",
                "english_name": "Roche",
                "aliases": ["F. Hoffmann-La Roche", "罗氏（中国）有限公司"],
                "pinyin_abbr": "LS",
                "stock_code": "ROG.SW"
            },

            # 诺华（国外）
            {
                "standard_name": "诺华",
                "english_name": "Novartis",
                "aliases": ["诺华制药", "诺华（中国）有限公司"],
                "pinyin_abbr": "NH",
                "stock_code": "NVS.US"
            },

            # 百时美施贵宝（国外）
            {
                "standard_name": "百时美施贵宝",
                "english_name": "BMS",
                "aliases": ["Bristol Myers Squibb", "施贵宝", "百时美施贵宝（中国）有限公司"],
                "pinyin_abbr": "BMS",
                "stock_code": "BMY.US"
            },

            # 阿斯利康（国外）
            {
                "standard_name": "阿斯利康",
                "english_name": "AstraZeneca",
                "aliases": ["AZ", "阿斯利康制药", "阿斯利康（中国）有限公司"],
                "pinyin_abbr": "ASLK",
                "stock_code": "AZN.L"
            },

            # 葛兰素史克（国外）
            {
                "standard_name": "葛兰素史克",
                "english_name": "GSK",
                "aliases": ["GlaxoSmithKline", "葛兰素", "葛兰素史克（中国）有限公司"],
                "pinyin_abbr": "GLS",
                "stock_code": "GSK.L"
            },

            # 赛诺菲（国外）
            {
                "standard_name": "赛诺菲",
                "english_name": "Sanofi",
                "aliases": ["赛诺菲安万特", "赛诺菲（中国）有限公司"],
                "pinyin_abbr": "SNF",
                "stock_code": "SAN.PA"
            },

            # 礼来（国外）
            {
                "standard_name": "礼来",
                "english_name": "Eli Lilly",
                "aliases": ["Lilly", "礼来制药", "礼来（中国）有限公司"],
                "pinyin_abbr": "LL",
                "stock_code": "LLY.US"
            },

            # 强生（国外）
            {
                "standard_name": "强生",
                "english_name": "J&J",
                "aliases": ["Johnson & Johnson", "杨森", "强生（中国）有限公司"],
                "pinyin_abbr": "QS",
                "stock_code": "JNJ.US"
            },
        ]

        # 创建映射对象
        for company_data in companies:
            mapping = CompanyMapping(**company_data)
            standard_name = mapping.standard_name
            self._mappings[standard_name] = mapping

    def _build_indexes(self) -> None:
        """构建索引，加速查询"""
        for standard_name, mapping in self._mappings.items():
            # 索引标准名称
            self._alias_to_standard[standard_name] = standard_name

            # 索引英文名
            if mapping.english_name:
                self._alias_to_standard[mapping.english_name] = standard_name

            # 索引所有别名
            for alias in mapping.aliases:
                self._alias_to_standard[alias] = standard_name

            # 构建模糊索引（用于部分匹配）
            all_names = [standard_name]
            if mapping.english_name:
                all_names.append(mapping.english_name)
            all_names.extend(mapping.aliases)

            # 为每个名称生成关键词（用于模糊搜索）
            for name in all_names:
                # 提取中文字符（去除常见后缀）
                keywords = self._extract_keywords(name)
                for keyword in keywords:
                    if keyword not in self._fuzzy_index:
                        self._fuzzy_index[keyword] = set()
                    self._fuzzy_index[keyword].add(standard_name)

    def _extract_keywords(self, name: str) -> List[str]:
        """
        从公司名称中提取关键词

        例如：
        - "江苏恒瑞医药股份有限公司" → ["恒瑞", "恒瑞医药"]
        - "BeiGene" → ["beigene"]
        """
        keywords = []

        # 移除常见后缀
        suffixes = [
            "有限公司", "股份有限公司", "集团有限公司",
            "生物科技", "生物技术", "制药", "生物医药",
            "（中国）", "（北京）", "（上海）", "（苏州）", "（烟台）",
            "(China)", "(Beijing)", "(Shanghai)", "(Suzhou)"
        ]

        clean_name = name
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, "")

        # 提取中文关键词（2-4个字的连续片段）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]{2,4}', clean_name)
        keywords.extend(chinese_chars)

        # 提取英文关键词（小写）
        english_words = re.findall(r'[a-zA-Z]{2,}', clean_name)
        keywords.extend([w.lower() for w in english_words])

        return keywords

    # ==================== 公共接口 ====================

    def normalize(self, name: str) -> Optional[str]:
        """
        标准化公司名称

        Args:
            name: 用户输入的公司名称（可以是简称、英文名等）

        Returns:
            标准全称，如果未找到返回None

        Example:
            >>> mapper = CompanyNameMapper()
            >>> mapper.normalize("恒瑞")
            '江苏恒瑞医药股份有限公司'
            >>> mapper.normalize("BeiGene")
            '百济神州（北京）生物科技有限公司'
        """
        if not name or not name.strip():
            return None

        # 精确匹配
        if name in self._alias_to_standard:
            return self._alias_to_standard[name]

        # 尝试大小写不敏感匹配（针对英文名）
        name_lower = name.lower()
        for alias, standard in self._alias_to_standard.items():
            if alias.lower() == name_lower:
                return standard

        return None

    def expand(self, name: str, include_standard: bool = True) -> List[str]:
        """
        扩展公司名称，返回所有可能的变体

        Args:
            name: 用户输入的公司名称
            include_standard: 是否包含标准名称

        Returns:
            所有变体列表（简称、英文名、标准名称等）

        Example:
            >>> mapper = CompanyNameMapper()
            >>> mapper.expand("百济")
            ['百济神州', 'BeiGene', '百济神州（北京）生物科技有限公司']
        """
        standard = self.normalize(name)

        if not standard or standard not in self._mappings:
            # 未找到映射，返回原名称
            return [name] if name else []

        mapping = self._mappings[standard]
        variants = []

        # 添加简称
        variants.extend(mapping.aliases)

        # 添加英文名
        if mapping.english_name:
            variants.append(mapping.english_name)

        # 添加标准名称
        if include_standard:
            variants.append(standard)

        # 去重并保持顺序
        seen = set()
        result = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                result.append(v)

        return result

    def find_match(self, name: str, threshold: float = 0.6) -> Optional[str]:
        """
        模糊匹配公司名称

        Args:
            name: 用户输入的公司名称
            threshold: 匹配阈值（0-1）

        Returns:
            最佳匹配的标准名称，未找到返回None

        Example:
            >>> mapper = CompanyNameMapper()
            >>> mapper.find_match("百济神州生物")
            '百济神州（北京）生物科技有限公司'
        """
        if not name or not name.strip():
            return None

        # 先尝试精确匹配
        exact = self.normalize(name)
        if exact:
            return exact

        # 提取关键词进行模糊匹配
        keywords = self._extract_keywords(name)

        # 统计每个标准名称的匹配次数
        scores = {}
        for keyword in keywords:
            if keyword in self._fuzzy_index:
                for standard_name in self._fuzzy_index[keyword]:
                    scores[standard_name] = scores.get(standard_name, 0) + 1

        # 返回得分最高的
        if scores:
            best_match = max(scores.items(), key=lambda x: x[1])
            # 检查是否达到阈值
            if best_match[1] >= len(keywords) * threshold:
                return best_match[0]

        return None

    def add_mapping(self, standard_name: str, **kwargs) -> None:
        """
        动态添加公司映射

        Args:
            standard_name: 标准全称
            **kwargs: 其他属性（english_name, aliases等）

        Example:
            >>> mapper = CompanyNameMapper()
            >>> mapper.add_mapping(
            ...     "新公司制药有限公司",
            ...     english_name="New Company",
            ...     aliases=["新公司", "NC"]
            ... )
        """
        # 如果已存在，更新
        if standard_name in self._mappings:
            logger.warning(f"公司 {standard_name} 已存在，将被覆盖")

        mapping = CompanyMapping(standard_name=standard_name, **kwargs)
        self._mappings[standard_name] = mapping

        # 重建索引
        self._build_indexes()

        logger.info(f"添加公司映射: {standard_name}")

    def get_all_companies(self) -> List[str]:
        """获取所有标准公司名称列表"""
        return list(self._mappings.keys())

    def get_company_info(self, name: str) -> Optional[Dict]:
        """
        获取公司详细信息

        Args:
            name: 公司名称（任意形式）

        Returns:
            公司信息字典，未找到返回None
        """
        standard = self.normalize(name)

        if not standard or standard not in self._mappings:
            return None

        mapping = self._mappings[standard]

        return {
            "standard_name": mapping.standard_name,
            "english_name": mapping.english_name,
            "aliases": mapping.aliases,
            "pinyin_abbr": mapping.pinyin_abbr,
            "stock_code": mapping.stock_code,
        }

    def is_valid_company(self, name: str) -> bool:
        """
        验证是否是有效的公司名称

        Args:
            name: 公司名称

        Returns:
            True表示有效，False表示无效
        """
        return self.normalize(name) is not None


# ==================== 全局访问函数 ====================

@lru_cache(maxsize=1)
def get_company_mapper() -> CompanyNameMapper:
    """
    获取公司名称映射器单例

    使用 lru_cache 确保全局唯一实例

    Example:
        >>> mapper1 = get_company_mapper()
        >>> mapper2 = get_company_mapper()
        >>> mapper1 is mapper2  # True
    """
    return CompanyNameMapper()


# ==================== 导出 ====================

__all__ = [
    "CompanyNameMapper",
    "CompanyMapping",
    "get_company_mapper",
]
