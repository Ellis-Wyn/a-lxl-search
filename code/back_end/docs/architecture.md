# 系统架构文档

## 项目概述

**病理AI药研情报库** 是一个医药研发情报收集与分析系统，专注于：
- 竞品管线监控
- 靶点-文献关联分析
- PubMed智能检索
- Phase Jump检测

### 技术栈

- **后端框架**: FastAPI
- **ORM**: SQLAlchemy
- **数据库**: SQLite（开发）/ PostgreSQL（生产）
- **爬虫**: BeautifulSoup4 + requests
- **测试**: pytest
- **文档**: FastAPI自动生成 + Sphinx

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Targets  │  │Pipeline  │  │ Publications│ │ PubMed  │   │
│  │   API    │  │   API    │  │    API     │ │   API   │   │
│  └────┬─────┘  └────┬─────┘  └────┬───────┘  └────┬────┘   │
└───────┼────────────┼─────────────┼────────────────┼────────┘
        │            │             │                │
┌───────┼────────────┼─────────────┼────────────────┼────────┐
│       ▼            ▼             ▼                ▼        │
│                     Service Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Database  │  │ Pipeline │  │ Phase    │  │ Pubmed   │ │
│  │ Service  │  │ Service  │  │ Mapper   │  │ Service  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
└───────┼────────────┼─────────────┼────────────────┼───────┘
        │            │             │                │
┌───────┼────────────┼─────────────┼────────────────┼───────┐
│       ▼            ▼             ▼                ▼       │
│                    Data Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │  Target  │  │Pipeline  │  │Publication│  │Relation- ││
│  │  Model   │  │  Model   │  │  Model    │  │  ships   ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
└───────┼────────────┼─────────────┼────────────────┼──────┘
        │            │             │                │
┌───────┼────────────┼─────────────┼────────────────┼───────┐
│       ▼            ▼             ▼                ▼       │
│              External Services                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ PubMed   │  │ Company  │  │ Database │             │
│  │   API    │  │ Websites │  │   (DB)   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└───────────────────────────────────────────────────────┘
```

---

## 模块说明

### 1. API Layer（`api/`）

#### 职责
- 接收HTTP请求
- 验证输入数据（Pydantic）
- 调用Service层
- 返回响应

#### 主要模块

##### Targets API (`api/targets.py`)
- `GET /api/v1/targets` - 获取靶点列表（支持搜索、分页）
- `GET /api/v1/targets/{id}` - 获取靶点详情
- `POST /api/v1/targets` - 创建靶点
- `GET /api/v1/targets/{id}/publications` - 获取靶点相关文献
- `GET /api/v1/targets/{id}/pipelines` - 获取靶点相关管线
- `GET /api/v1/targets/stats` - 获取靶点统计信息

##### Pipeline API (`api/pipeline.py`)
- `POST /api/pipeline` - 创建管线
- `GET /api/pipeline/search` - 搜索管线
- `GET /api/pipeline/company/{name}` - 获取公司管线
- `POST /api/pipeline/update-and-detect` - 更新并检测变化
- `GET /api/pipeline/statistics` - 获取管线统计

##### Publications API (`api/publications.py`)
- `GET /api/v1/publications` - 获取文献列表
- `POST /api/v1/publications` - 创建文献
- `GET /api/v1/publications/{pmid}` - 获取文献详情
- `POST /api/v1/publications/{pmid}/link` - 关联文献到靶点

##### PubMed API (`api/pubmed.py`)
- `POST /api/pubmed/search` - 搜索PubMed文献
- `GET /api/pubmed/publication/{pmid}` - 获取文献详情

---

### 2. Service Layer（`services/`）

#### 职责
- 业务逻辑处理
- 数据转换
- 外部服务调用
- 事务协调

#### DatabaseService (`services/database_service.py`)

**功能**: 数据库CRUD操作的统一入口

**主要方法**:
```python
# Target 操作
create_target(data: Dict) -> Target
get_target_by_name(name: str) -> Target
get_target_by_id(id: str) -> Target
search_targets(keyword: str, limit: int) -> List[Target]

# Publication 操作
create_publication(data: Dict) -> Publication
get_publication_by_pmid(pmid: str) -> Publication
get_publications_by_target(target_id: str) -> List[Publication]

# Pipeline 操作
create_pipeline(data: Dict) -> Pipeline
get_pipeline_by_id(id: str) -> Pipeline
get_pipelines_by_company(name: str) -> List[Pipeline]
get_pipelines_by_target(target_id: str) -> List[Pipeline]

# 关联操作
link_target_publication(target_id, pmid, relation_type, evidence_snippet)
link_target_pipeline(target_id, pipeline_id, relation_type, is_primary)
```

**特性**:
- 自动重试（3次）
- 事务管理（自动回滚）
- 错误分类（连接错误、重复键错误）

#### PubmedService (`services/pubmed_service.py`)

**功能**: PubMed智能查询服务

**主要方法**:
```python
async def search_by_target(
    target_name: str,
    config: QueryConfig,
    custom_keywords: List[str],
    diseases: List[str]
) -> List[Dict]
```

**特性**:
- 智能查询构建（同义词扩展）
- 文献排序算法（相关性 + 时效性 + 临床数据）
- 自动重试（5次）
- 缓存支持

#### PhaseMapper (`services/phase_mapper.py`)

**功能**: 标准化研发阶段

**支持阶段**:
- Preclinical（临床前）
- Phase 1（I期）
- Phase 2（II期）
- Phase 3（III期）
- Filing（申报中）
- Approved（已上市）

**映射能力**:
- 30+种阶段变体
- 中英文混合
- 大小写不敏感
- 特殊字符处理

---

### 3. Data Layer（`models/`）

#### 数据模型

##### Target (`models/target.py`)
```python
class Target(Base):
    """靶点模型"""

    target_id: str (UUID, PK)
    standard_name: str (唯一)
    aliases: List[str]
    gene_id: str
    uniprot_id: str
    category: str
    description: str
    created_at: DateTime

    # ORM 关系
    publications: relationship(TargetPublication)
    pipelines: relationship(TargetPipeline)
```

##### Publication (`models/publication.py`)
```python
class Publication(Base):
    """文献模型"""

    pmid: str (PK)
    title: str
    abstract: Text
    pub_date: Date
    journal: String
    publication_type: String
    authors: List[str]
    mesh_terms: List[str]
    clinical_data_tags: List[dict]
    created_at: DateTime

    # ORM 关系
    targets: relationship(TargetPublication)
```

##### Pipeline (`models/pipeline.py`)
```python
class Pipeline(Base):
    """管线模型"""

    pipeline_id: int (PK, AutoIncrement)
    drug_code: str
    company_name: str
    indication: str
    phase: str
    phase_raw: str
    modality: str
    source_url: str
    status: Enum(active, discontinued)
    is_combination: bool
    combination_drugs: JSON
    first_seen_at: DateTime
    last_seen_at: DateTime

    # ORM 关系
    targets: relationship(TargetPipeline)

    # 方法
    is_disappeared(threshold_days: int = 90) -> bool
    get_phase_order() -> int
    has_phase_changed(new_phase: str) -> bool
```

##### 关联表

**TargetPublication** (`models/relationships.py`):
```python
class TargetPublication(Base):
    """靶点-文献关联表"""
    __tablename__ = "target_publications"

    target_id: str (FK)
    pmid: str (FK)
    relation_type: str
    evidence_snippet: Text
    created_at: DateTime

    __table_args__ = (
        PrimaryKeyConstraint(target_id, pmid),
        ForeignKeyConstraint(...)
    )
```

**TargetPipeline** (`models/relationships.py`):
```python
class TargetPipeline(Base):
    """靶点-管线关联表"""
    __tablename__ = "target_pipelines"

    target_id: str (FK)
    pipeline_id: int (FK)
    relation_type: str
    is_primary: bool
    evidence_snippet: Text
    created_at: DateTime

    __table_args__ = (
        PrimaryKeyConstraint(target_id, pipeline_id),
        ForeignKeyConstraint(...)
    )
```

---

### 4. Crawlers Layer（`crawlers/`）

#### CompanySpiderBase (`crawlers/company_spider.py`)

**功能**: 爬虫基类，提供通用爬虫功能

**特性**:
- 重试机制（指数退避）
- 缓存支持（TTL缓存）
- 熔断器（失败率阈值）
- 性能监控（响应时间、成功率）
- 消失管线检测

**主要方法**:
```python
def fetch_page(url: str, timeout: int) -> Optional[Response]
def parse_from_text(html: str) -> List[PipelineDataItem]
def save_to_database(item: PipelineDataItem) -> bool
def check_discontinued_pipelines(seen_drugs: List[str]) -> List[str]
```

**爬虫列表**:
- `HengruiSpider` - 恒瑞医药官网爬虫
- `BeiGeneSpider` - 百济神州官网爬虫

---

### 5. Utils Layer（`utils/`）

#### Validators (`utils/validators.py`)

**功能**: Pydantic数据验证模型

**主要模型**:
- `TargetCreateRequest` - 靶点创建验证
- `PublicationCreateRequest` - 文献创建验证
- `PipelineCreateRequest` - 管线创建验证
- `TargetPublicationLinkRequest` - 靶点-文献关联验证
- `TargetPipelineLinkRequest` - 靶点-管线关联验证

**验证规则**:
- 正则表达式验证（格式）
- 业务规则验证（联合用药逻辑）
- 自动数据清理（去重）
- 类型安全（Enum）

#### Retry (`core/retry.py`)

**功能**: 统一重试机制

**策略**:
- `DATABASE` - 3次重试，指数退避
- `HTTP_REQUEST` - 3次重试
- `EXTERNAL_API` - 5次重试
- `CRAWLER` - 3次重试

**特性**:
- 指数退避（base_delay * 2^attempt）
- 随机抖动（±50%）
- 支持同步/异步函数

---

## 数据流

### 创建管线流程

```
┌─────────┐
│ 用户请求 │
└────┬────┘
     │
     ▼
┌─────────────────┐
│ API Layer       │
│ - 验证输入       │
│ - Pydantic模型  │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Service Layer   │
│ - PhaseMapper   │
│ - 标准化阶段    │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Data Layer      │
│ - ORM操作       │
│ - 事务管理      │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Database       │
└─────────────────┘
```

### PubMed智能查询流程

```
┌──────────────┐
│ 用户查询请求  │
│ - target_name │
│ - keywords   │
│ - diseases   │
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│ 构建智能查询    │
│ - 同义词扩展    │
│ - MeSH术语      │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ PubMed API      │
│ - 重试机制      │
│ - 速率限制      │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ 解析响应        │
│ - 提取字段      │
│ - 临床数据标签  │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ 排序算法        │
│ - 时效性得分    │
│ - 临床得分      │
│ - 来源得分      │
│ - 关键词匹配    │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ 返回排序结果    │
└─────────────────┘
```

---

## 核心功能

### 1. Phase Jump检测

**原理**: 监控管线阶段变化，检测研发进度

**实现**:
```python
# services/pipeline_service.py

def detect_phase_jumps(pipeline, new_phase):
    """
    检测Phase Jump

    阶段顺序: preclinical → Phase 1 → Phase 2 → Phase 3 → filing → approved
    """
    old_order = pipeline.get_phase_order()
    new_order = PhaseMapper.get_phase_order(new_phase)

    if new_order > old_order:
        return PhaseJump(
            pipeline_id=pipeline.pipeline_id,
            old_phase=pipeline.phase,
            new_phase=new_phase,
            jump_days=(datetime.now() - pipeline.last_seen_at).days
        )
```

### 2. 消失管线检测

**原理**: 比较上次爬取结果，检测竞品退场

**实现**:
```python
# crawlers/company_spider.py

def check_discontinued_pipelines(self, seen_drugs: List[str]) -> List[str]:
    """
    检测消失的管线

    阈值: 90天未在官网出现 → 判定为消失
    """
    from_db = self.get_all_drug_codes()
    disappeared = set(from_db) - set(seen_drugs)

    for drug_code in disappeared:
        pipeline = self.get_pipeline(drug_code)
        if pipeline.is_disappeared(threshold_days=90):
            pipeline.status = 'discontinued'

    return list(disappeared)
```

### 3. 联合用药识别

**原理**: 从适应症描述中识别联合用药方案

**实现**:
```python
# utils/pipeline_parser.py

class CombinationTherapyDetector:
    """
    联合用药检测器

    规则:
    1. 关键词: "联合", "combination", "+", "with"
    2. 药物代码模式: [A-Z]+-[0-9]+
    3. 最少2个药物
    """

    @staticmethod
    def detect_combination(
        indication: str,
        current_drug: str
    ) -> Tuple[bool, List[str]]:
        # 提取所有药物代码
        drugs = extract_drug_codes(indication)
        drugs.append(current_drug)

        if len(drugs) >= 2:
            return True, list(set(drugs))
        return False, []
```

---

## 安全性

### 输入验证
- Pydantic模型验证所有API输入
- 正则表达式验证格式
- SQL参数化查询防止注入

### 错误处理
- 分类错误处理（连接、重复、业务）
- 自动重试机制
- 详细错误日志

### 数据保护
- 事务管理保证一致性
- 级联删除防止孤立数据
- 外键约束保证引用完整性

---

## 性能优化

### 缓存策略
- HTTP响应缓存（TTL=1小时）
- PubMed查询缓存
- 数据库查询结果缓存

### 批量操作
- 批量插入管线数据
- 批量创建关联关系

### 索引优化
- 标准名称索引（Target.standard_name）
- PMID索引（Publication.pmid）
- 复合唯一索引（Pipeline: drug_code + company_name + indication）

---

## 监控与日志

### 日志级别
- DEBUG: 详细调试信息
- INFO: 重要操作记录
- WARNING: 警告信息
- ERROR: 错误信息

### 监控指标
- 爬虫性能（响应时间、成功率）
- API调用次数
- 数据库查询时间
- 错误率统计

---

## 部署架构

### 开发环境
```
┌─────────────────┐
│  FastAPI Server │
│   (localhost)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │
│  (本地文件)      │
└─────────────────┘
```

### 生产环境
```
┌─────────────────┐
│  Nginx (反向代理)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gunicorn       │
│  (多进程)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  (主从复制)      │
└─────────────────┘
```

---

## 测试策略

### 单元测试
- 模型测试（58个）
- 服务层测试（46个）
- 总计104个测试
- 覆盖率≥85%

### 集成测试
- API端到端测试
- 数据库集成测试
- 外部API集成测试

### 测试工具
- pytest - 测试框架
- pytest-cov - 覆盖率
- factory_boy - 测试数据工厂

---

## 未来规划

### Phase 3: 长期优化
1. **日志和监控**
   - 结构化日志（JSON）
   - 性能监控（Prometheus）
   - 告警机制（钉钉、企业微信）

2. **性能优化**
   - Redis缓存层
   - 批量API接口
   - 数据库查询优化

3. **安全性**
   - JWT认证
   - API速率限制
   - HTTPS强制

4. **可扩展性**
   - 消息队列（Celery）
   - 微服务拆分
   - 容器化部署

---

## 文档索引

- [API文档](http://localhost:8000/docs) - FastAPI自动生成
- [测试文档](../tests/README.md) - 测试指南
- [Phase 1完成报告](../PHASE1_COMPLETION_REPORT.md) - 改进总结
- [配置说明](../config.example.py) - 配置示例

---

**最后更新**: 2026-02-02
**维护者**: Claude Code Assistant
