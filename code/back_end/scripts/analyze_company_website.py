"""
=====================================================
药企官网分析工具
=====================================================

帮助分析药企官网结构，指导爬虫开发：
1. 访问官网
2. 查找管线页面
3. 分析 HTML 结构
4. 生成爬虫代码

使用方式：
    python scripts/analyze_company_website.py --company hengrui
    python scripts/analyze_company_website.py --url https://www.hengrui.com/Product
=====================================================
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from bs4 import BeautifulSoup
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="website_analyzer", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


# =====================================================
# 公司配置
# =====================================================

COMPANY_CONFIGS = {
    "hengrui": {
        "name": "恒瑞医药",
        "base_url": "https://www.hengrui.com",
        "pipeline_paths": [
            "/Product",           # 产品中心
            "/rd/pipeline",        # 研发管线（可能）
            "/Investor-Relations", # 投资者关系
        ],
        "company_type": "制药",
        "focus_areas": ["肿瘤", "自身免疫", "代谢疾病"],
    },
    "beigene": {
        "name": "百济神州",
        "base_url": "https://www.beigene.com",
        "pipeline_paths": [
            "/pipeline",
            "/our-science/clinical-trials",
        ],
        "company_type": "生物制药",
        "focus_areas": ["肿瘤", "血液瘤"],
    },
    "inda": {
        "name": "信达生物",
        "base_url": "https://www.innoventbio.com",
        "pipeline_paths": [
            "/pipeline",
            "/research-development",
        ],
        "company_type": "生物制药",
        "focus_areas": ["肿瘤", "代谢疾病"],
    },
}


# =====================================================
# 分析工具
# =====================================================

class WebsiteAnalyzer:
    """网站分析器"""

    def __init__(self, company_name: str):
        """
        初始化分析器

        Args:
            company_name: 公司名称代码
        """
        self.config = COMPANY_CONFIGS.get(company_name)
        if not self.config:
            raise ValueError(f"Unknown company: {company_name}")

        self.company_name = self.config["name"]
        self.base_url = self.config["base_url"]

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        logger.info(f"Initialized analyzer for {self.company_name}")

    def analyze(self) -> Dict[str, Any]:
        """
        分析网站

        Returns:
            分析结果
        """
        results = {
            "company": self.company_name,
            "base_url": self.base_url,
            "accessible_pages": [],
            "pipeline_pages": [],
            "html_structure": {},
        }

        # 1. 检查网站可访问性
        logger.info("Checking website accessibility...")
        results["accessible"] = self.check_accessibility()

        if not results["accessible"]:
            return results

        # 2. 查找管线页面
        logger.info("Searching for pipeline pages...")
        results["pipeline_pages"] = self.find_pipeline_pages()

        # 3. 分析管线页面结构
        if results["pipeline_pages"]:
            logger.info("Analyzing pipeline page structure...")
            results["html_structure"] = self.analyze_pipeline_page(
                results["pipeline_pages"][0]["url"]
            )

        return results

    def check_accessibility(self) -> bool:
        """检查网站可访问性"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ Website accessible: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"❌ Website not accessible: {e}")
            return False

    def find_pipeline_pages(self) -> List[Dict[str, Any]]:
        """查找管线页面"""
        found_pages = []

        for path in self.config.get("pipeline_paths", []):
            url = self.base_url + path

            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"✅ Found page: {url}")
                    found_pages.append({
                        "url": url,
                        "path": path,
                        "title": self.extract_title(response.text),
                    })
                else:
                    logger.warning(f"⚠️  Page returned {response.status_code}: {url}")

            except Exception as e:
                logger.error(f"❌ Error accessing {url}: {e}")

        return found_pages

    def extract_title(self, html: str) -> str:
        """提取页面标题"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            title = soup.find("title")
            return title.text.strip() if title else "No title"
        except:
            return "Unknown"

    def analyze_pipeline_page(self, url: str) -> Dict[str, Any]:
        """
        分析管线页面结构

        Args:
            url: 页面 URL

        Returns:
            HTML 结构分析结果
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 分析页面结构
            structure = {
                "url": url,
                "title": self.extract_title(response.text),
                "possible_containers": self.find_pipeline_containers(soup),
                "sample_items": self.extract_sample_items(soup),
                "forms": self.analyze_forms(soup),
                "tables": self.analyze_tables(soup),
                "recommendations": self.generate_recommendations(soup),
            }

            return structure

        except Exception as e:
            logger.error(f"Error analyzing pipeline page: {e}")
            return {}

    def find_pipeline_containers(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        查找可能的管线容器

        Args:
            soup: BeautifulSoup 对象

        Returns:
            容器列表
        """
        containers = []

        # 常见的容器类名
        possible_classes = [
            "pipeline-list",
            "product-list",
            "drug-list",
            "rd-pipeline",
            "pipeline-table",
            "table-pipeline",
        ]

        for class_name in possible_classes:
            elements = soup.find_all(class_=class_name)
            for elem in elements[:3]:  # 只取前3个
                containers.append({
                    "class": class_name,
                    "tag": elem.name,
                    "id": elem.get("id", ""),
                    "preview": str(elem)[:200],  # 前200个字符
                })

        return containers

    def extract_sample_items(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        提取示例管线项目

        Args:
            soup: BeautifulSoup 对象

        Returns:
            示例项目列表
        """
        items = []

        # 查找表格行
        tables = soup.find_all("table")
        for table in tables[:2]:  # 只看前2个表格
            rows = table.find_all("tr")
            for row in rows[1:4]:  # 前3行数据
                cells = row.find_all(["td", "th"])
                if cells:
                    items.append({
                        "type": "table_row",
                        "cells_count": len(cells),
                        "preview": "|".join([cell.text.strip()[:30] for cell in cells[:3]]),
                    })

        # 查找列表项
        lists = soup.find_all(["ul", "ol"])
        for lst in lists[:2]:
            items_list = lst.find_all("li")
            for item in items_list[:3]:
                items.append({
                    "type": "list_item",
                    "text": item.text.strip()[:100],
                })

        return items

    def analyze_forms(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """分析表单"""
        forms = soup.find_all("form")
        return [
            {
                "action": form.get("action", ""),
                "method": form.get("method", "GET"),
                "inputs_count": len(form.find_all("input")),
            }
            for form in forms
        ]

    def analyze_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """分析表格"""
        tables = soup.find_all("table")
        return [
            {
                "rows_count": len(table.find_all("tr")),
                "has_headers": bool(table.find("th")),
                "caption": table.find("caption").text if table.find("caption") else "",
            }
            for table in tables
        ]

    def generate_recommendations(self, soup: BeautifulSoup) -> List[str]:
        """
        生成爬虫开发建议

        Args:
            soup: BeautifulSoup 对象

        Returns:
            建议列表
        """
        recommendations = []

        # 检查是否有表格
        tables = soup.find_all("table")
        if tables:
            recommendations.append("✅ 页面包含表格，可以解析 <table> 元素")
        else:
            recommendations.append("⚠️  页面没有表格，可能需要解析 <div> 列表")

        # 检查是否有列表
        lists = soup.find_all(["ul", "ol"])
        if lists:
            recommendations.append("✅ 页面包含列表，可以解析 <ul>/<ol> 元素")

        # 检查是否有 JavaScript 渲染
        scripts = soup.find_all("script")
        js_frameworks = ["react", "vue", "angular", "jquery"]
        for script in scripts:
            script_text = script.string or ""
            if any(fw in script_text.lower() for fw in js_frameworks):
                recommendations.append("⚠️  页面使用 JavaScript 框架，可能需要使用 Selenium 或 Playwright")
                break

        # 检查是否有分页
        pagination_keywords = ["next", "pagination", "page", "更多"]
        page_text = soup.get_text().lower()
        if any(kw in page_text for kw in pagination_keywords):
            recommendations.append("ℹ️  页面可能包含分页，需要处理多页数据")

        # 检查 robots.txt
        recommendations.append("ℹ️  请检查 robots.txt 确认爬取规则")
        recommendations.append("ℹ️  建议设置 0.3-0.5 秒的请求间隔")

        return recommendations


# =====================================================
# 主程序
# =====================================================

def main():
    """主程序"""
    parser = argparse.ArgumentParser(description="分析药企官网")
    parser.add_argument("--company", choices=list(COMPANY_CONFIGS.keys()),
                       help="公司名称代码")
    parser.add_argument("--url", help="直接分析指定 URL")
    parser.add_argument("--output", help="保存分析结果到文件")

    args = parser.parse_args()

    if args.url:
        # 直接分析指定 URL
        logger.info(f"Analyzing URL: {args.url}")
        # TODO: 实现直接分析 URL 的逻辑
        logger.info("直接 URL 分析功能待实现")
        return

    if not args.company:
        logger.error("请指定公司名称，使用 --company 参数")
        parser.print_help()
        return 1

    # 分析公司网站
    logger.info("=" * 60)
    logger.info(f"分析药企官网: {args.company}")
    logger.info("=" * 60)

    analyzer = WebsiteAnalyzer(args.company)
    results = analyzer.analyze()

    # 输出结果
    print()
    print("=" * 60)
    print("分析结果")
    print("=" * 60)
    print(f"公司: {results['company']}")
    print(f"官网: {results['base_url']}")
    print(f"可访问: {'✅ 是' if results['accessible'] else '❌ 否'}")
    print()

    if results["pipeline_pages"]:
        print("找到的管线页面:")
        for page in results["pipeline_pages"]:
            print(f"  - {page['url']}")
            print(f"    标题: {page['title']}")
        print()

    if results.get("html_structure"):
        structure = results["html_structure"]
        print("页面结构分析:")
        print(f"  容器数量: {len(structure.get('possible_containers', []))}")
        print(f"  表格数量: {len(structure.get('tables', []))}")
        print(f"  表单数量: {len(structure.get('forms', []))}")
        print()

        if structure.get("recommendations"):
            print("开发建议:")
            for rec in structure["recommendations"]:
                print(f"  {rec}")
            print()

    # 保存结果
    if args.output:
        import json
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 结果已保存到: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
