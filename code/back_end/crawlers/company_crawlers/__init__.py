"""
=====================================================
药企官网爬虫包
=====================================================

支持从药企官网爬取管线数据：
- 恒瑞医药
- 百济神州
- 信达生物
- 君实生物
- 康方生物
- 等 12 家种子公司

技术栈：
- Scrapy 爬虫框架
- 数据标准化（Phase 映射）
- 自动入库

使用方式：
    from crawlers.company_spider import CompanySpiderFactory

    spider = CompanySpiderFactory.create("hengrui")
    results = spider.run()
=====================================================
"""

__version__ = "1.0.0"
