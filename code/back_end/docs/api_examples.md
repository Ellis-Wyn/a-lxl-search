# API 使用示例文档

## 概述

本文档提供所有API端点的详细使用示例，包括请求格式、响应格式和常见场景。

---

## Targets API

### 1. 创建靶点

**端点**: `POST /api/v1/targets`

**请求示例**:
```json
{
  "standard_name": "EGFR",
  "aliases": ["ERBB1", "HER1"],
  "gene_id": "1956",
  "uniprot_id": "P00533",
  "category": "Tyrosine Kinase",
  "description": "Epidermal Growth Factor Receptor"
}
```

**响应示例** (201 Created):
```json
{
  "target_id": "123e4567-e89b-12d3-a456-426614174000",
  "standard_name": "EGFR",
  "aliases": ["ERBB1", "HER1"],
  "gene_id": "1956",
  "uniprot_id": "P00533",
  "category": "Tyrosine Kinase",
  "description": "Epidermal Growth Factor Receptor",
  "created_at": "2026-02-02T12:00:00"
}
```

**验证规则**:
- `standard_name`: 必填，1-100字符，只能包含字母、数字和连字符，必须以字母开头
- `aliases`: 可选，列表自动去重，每个别名格式同标准名称
- `gene_id`: 可选，必须是数字
- `uniprot_id`: 可选，1-50字符

**错误示例**:
```json
// 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "standard_name"],
      "msg": "标准名称只能包含字母、数字和连字符",
      "type": "value_error"
    }
  ]
}

// 409 Conflict
{
  "detail": "Target already exists: EGFR"
}
```

### 2. 获取靶点列表

**端点**: `GET /api/v1/targets`

**查询参数**:
- `keyword`: 搜索关键词（标准名称模糊匹配）
- `category`: 分类过滤
- `limit`: 返回数量限制（1-200，默认50）
- `offset`: 偏移量（分页，默认0）

**请求示例**:
```bash
GET /api/v1/targets?keyword=EGF&limit=10&offset=0
```

**响应示例** (200 OK):
```json
{
  "total": 25,
  "items": [
    {
      "target_id": "123e4567-e89b-12d3-a456-426614174000",
      "standard_name": "EGFR",
      "aliases": ["ERBB1", "HER1"],
      "category": "Tyrosine Kinase"
    },
    {
      "target_id": "223e4567-e89b-12d3-a456-426614174001",
      "standard_name": "EGFR2",
      "aliases": ["HER2"],
      "category": "Tyrosine Kinase"
    }
  ]
}
```

### 3. 获取靶点详情

**端点**: `GET /api/v1/targets/{target_id}`

**响应示例** (200 OK):
```json
{
  "target_id": "123e4567-e89b-12d3-a456-426614174000",
  "standard_name": "EGFR",
  "aliases": ["ERBB1", "HER1"],
  "gene_id": "1956",
  "uniprot_id": "P00533",
  "category": "Tyrosine Kinase",
  "description": "Epidermal Growth Factor Receptor",
  "created_at": "2026-02-02T12:00:00",
  "publications": [
    {
      "pmid": "12345678",
      "title": "EGFR inhibitor in NSCLC",
      "journal": "J Clin Oncol",
      "pub_date": "2024-01-15"
    }
  ],
  "pipelines": [
    {
      "pipeline_id": 1,
      "drug_code": "SHR-1210",
      "company_name": "恒瑞医药",
      "indication": "非小细胞肺癌",
      "phase": "Phase 3"
    }
  ]
}
```

### 4. 获取靶点相关文献

**端点**: `GET /api/v1/targets/{target_id}/publications`

**查询参数**:
- `limit`: 返回数量限制（1-200，默认50）
- `offset`: 偏移量（默认0）

**响应示例** (200 OK):
```json
{
  "total": 15,
  "items": [
    {
      "pmid": "12345678",
      "title": "EGFR inhibitor in NSCLC: A phase III trial",
      "abstract": "This study evaluates...",
      "journal": "Journal of Clinical Oncology",
      "pub_date": "2024-01-15",
      "publication_type": "Clinical Trial",
      "relation_type": "focus_on"
    }
  ]
}
```

---

## Publications API

### 1. 创建文献

**端点**: `POST /api/v1/publications`

**请求示例**:
```json
{
  "pmid": "12345678",
  "title": "EGFR inhibitor in NSCLC: A phase III trial",
  "abstract": "This study evaluates the efficacy of EGFR inhibitor...",
  "pub_date": "2024-01-15",
  "journal": "Journal of Clinical Oncology",
  "publication_type": "Clinical Trial",
  "authors": ["Zhang San", "Li Si", "Wang Wu"],
  "mesh_terms": [
    "Carcinoma, Non-Small Cell Lung",
    "Receptor, Epidermal Growth Factor"
  ],
  "clinical_data_tags": [
    "ORR: 65%",
    "PFS: 12.3 months",
    "OS: 28.5 months"
  ]
}
```

**响应示例** (201 Created):
```json
{
  "pmid": "12345678",
  "title": "EGFR inhibitor in NSCLC: A phase III trial",
  "abstract": "This study evaluates...",
  "pub_date": "2024-01-15",
  "journal": "Journal of Clinical Oncology",
  "publication_type": "Clinical Trial",
  "authors": ["Zhang San", "Li Si", "Wang Wu"],
  "mesh_terms": [
    "Carcinoma, Non-Small Cell Lung",
    "Receptor, Epidermal Growth Factor"
  ],
  "clinical_data_tags": [
    "ORR: 65%",
    "PFS: 12.3 months",
    "OS: 28.5 months"
  ],
  "created_at": "2026-02-02T12:00:00"
}
```

**验证规则**:
- `pmid`: 必填，必须是数字，最多10位，唯一
- `title`: 必填，1-500字符
- `authors`: 自动去重
- `clinical_data_tags`: 临床数据标签列表

**错误示例**:
```json
// 422 Validation Error
{
  "detail": [
    {
      "loc": ["body", "pmid"],
      "msg": "PMID 必须是数字",
      "type": "value_error"
    }
  ]
}
```

### 2. 获取文献列表

**端点**: `GET /api/v1/publications`

**查询参数**:
- `keyword`: 搜索关键词（标题/摘要）
- `journal`: 期刊过滤
- `publication_type`: 文献类型过滤
- `date_from`: 起始日期（YYYY-MM-DD）
- `date_to`: 结束日期（YYYY-MM-DD）
- `limit`: 返回数量限制（1-200，默认50）
- `offset`: 偏移量（默认0）

**请求示例**:
```bash
GET /api/v1/publications?keyword=EGFR&journal=J%20Clin%20Oncol&date_from=2023-01-01&limit=20
```

**响应示例** (200 OK):
```json
{
  "total": 150,
  "items": [
    {
      "pmid": "12345678",
      "title": "EGFR inhibitor in NSCLC",
      "journal": "J Clin Oncol",
      "pub_date": "2024-01-15",
      "publication_type": "Clinical Trial"
    }
  ]
}
```

### 3. 关联文献到靶点

**端点**: `POST /api/v1/publications/{pmid}/link`

**请求示例**:
```json
{
  "target_id": "123e4567-e89b-12d3-a456-426614174000",
  "relation_type": "focus_on",
  "evidence_snippet": "This paper focuses on EGFR inhibition in NSCLC"
}
```

**响应示例** (200 OK):
```json
{
  "success": true,
  "message": "Successfully linked publication to target",
  "target_id": "123e4567-e89b-12d3-a456-426614174000",
  "pmid": "12345678"
}
```

**relation_type 可选值**:
- `mentioned_in` - 提及
- `focus_on` - 重点讨论

---

## Pipeline API

### 1. 创建管线

**端点**: `POST /api/pipeline`

**请求示例**:
```json
{
  "drug_code": "SHR-1210",
  "company_name": "恒瑞医药",
  "indication": "非小细胞肺癌",
  "phase": "Phase 3",
  "phase_raw": "III期",
  "modality": "Monoclonal Antibody",
  "source_url": "https://www.hengrui.com/pipeline.html",
  "targets": ["PD-1"]
}
```

**响应示例** (201 Created):
```json
{
  "pipeline_id": 1,
  "drug_code": "SHR-1210",
  "company_name": "恒瑞医药",
  "indication": "非小细胞肺癌",
  "phase": "Phase 3",
  "phase_normalized": "Phase 3",
  "modality": "Monoclonal Antibody",
  "source_url": "https://www.hengrui.com/pipeline.html",
  "status": "active",
  "first_seen_at": "2026-02-01T10:00:00",
  "last_seen_at": "2026-02-02T12:00:00"
}
```

**验证规则**:
- `drug_code`: 必填，1-255字符，只能包含大写字母、数字和连字符，必须以字母开头
- `phase`: 必填，必须是有效阶段值
- `source_url`: 必填，必须以 http:// 或 https:// 开头

### 2. 搜索管线

**端点**: `GET /api/pipeline/search`

**查询参数**:
- `keyword`: 关键词（药物代码/适应症）
- `target_name`: 靶点名称
- `company_name`: 公司名称
- `phase`: 阶段过滤
- `limit`: 返回数量限制（1-500，默认50）

**请求示例**:
```bash
GET /api/pipeline/search?keyword=SHR&phase=Phase%203&limit=20
```

**响应示例** (200 OK):
```json
{
  "total": 37,
  "items": [
    {
      "pipeline_id": 1,
      "drug_code": "SHR-1210",
      "company_name": "恒瑞医药",
      "indication": "非小细胞肺癌",
      "phase": "Phase 3",
      "modality": "Monoclonal Antibody",
      "targets": [
        {
          "target_id": "123e4567-e89b-12d3-a456-426614174000",
          "standard_name": "PD-1",
          "relation_type": "inhibits"
        }
      ]
    }
  ]
}
```

### 3. 批量更新并检测变化

**端点**: `POST /api/pipeline/update-and-detect`

**功能**:
- 批量更新管线数据
- 检测 Phase Jump（阶段变化）
- 检测消失管线（竞品退场）
- 生成变化报告

**请求示例**:
```json
{
  "company_name": "恒瑞医药",
  "new_pipelines": [
    {
      "drug_code": "SHR-1210",
      "indication": "非小细胞肺癌",
      "phase": "Phase 3",
      "source_url": "https://www.hengrui.com/pipeline.html"
    },
    {
      "drug_code": "SHR-1501",
      "indication": "实体瘤",
      "phase": "Phase 2",
      "source_url": "https://www.hengrui.com/pipeline.html"
    }
  ],
  "disappeared_threshold_days": 180
}
```

**响应示例** (200 OK):
```json
{
  "total_changes": 5,
  "new_pipelines": [
    {
      "drug_code": "SHR-1501",
      "company_name": "恒瑞医药",
      "indication": "实体瘤",
      "phase": "Phase 2"
    }
  ],
  "phase_jumps": [
    {
      "pipeline_id": 1,
      "drug_code": "SHR-1210",
      "company_name": "恒瑞医药",
      "indication": "非小细胞肺癌",
      "old_phase": "Phase 2",
      "new_phase": "Phase 3",
      "jump_days": 45,
      "confidence": 0.95,
      "detected_at": "2026-02-02T12:00:00"
    }
  ],
  "disappeared_pipelines": [
    {
      "drug_code": "OLD-001",
      "company_name": "恒瑞医药",
      "last_seen_at": "2025-07-15T10:00:00",
      "days_since_last_seen": 201
    }
  ],
  "reappeared_pipelines": [],
  "info_updates": 2,
  "scan_date": "2026-02-02T12:00:00"
}
```

---

## PubMed API

### 1. 智能搜索文献

**端点**: `POST /api/pubmed/search`

**功能**:
- 智能查询构建（同义词扩展）
- 自动排序（相关性 + 时效性 + 临床数据）
- 支持 MeSH 术语

**请求示例**:
```json
{
  "target_name": "EGFR",
  "keywords": ["inhibitor", "TKI"],
  "diseases": ["lung cancer"],
  "max_results": 50,
  "date_range_days": 365,
  "include_clinical_trials": true,
  "include_reviews": false,
  "min_relevance_score": 60.0
}
```

**响应示例** (200 OK):
```json
{
  "total": 50,
  "publications": [
    {
      "pmid": "12345678",
      "title": "EGFR inhibitor in NSCLC: A phase III trial",
      "abstract": "This study evaluates...",
      "journal": "Journal of Clinical Oncology",
      "pub_date": "2024-01-15",
      "publication_type": "Clinical Trial",
      "mesh_terms": ["Lung Neoplasms"],
      "clinical_data_tags": [
        {"ORR": "65%"},
        {"PFS": "12.3 months"},
        {"OS": "28.5 months"}
      ],
      "relevance_score": 87.5,
      "recency_score": 80,
      "clinical_score": 40,
      "source_score": 25,
      "keyword_match_score": 82.0
    }
  ]
}
```

**相关性得分计算**:
- 时效性得分（40%权重）: 0-100分
- 临床数据得分（25%权重）: 0-50分
- 来源期刊得分（15%权重）: 0-30分
- 关键词匹配得分（20%权重）: 0-100分

---

## 错误处理

### 通用错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### HTTP 状态码

- `200 OK` - 请求成功
- `201 Created` - 资源创建成功
- `400 Bad Request` - 请求参数错误
- `404 Not Found` - 资源不存在
- `409 Conflict` - 资源冲突（如重复创建）
- `422 Unprocessable Entity` - 数据验证失败
- `500 Internal Server Error` - 服务器内部错误

### 错误示例

**400 Bad Request**:
```json
{
  "detail": "Invalid date_from format: 2024/01/01"
}
```

**404 Not Found**:
```json
{
  "detail": "Target not found: 123e4567-e89b-12d3-a456-426614174000"
}
```

**422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "drug_code"],
      "msg": "药物代码只能包含大写字母、数字和连字符",
      "type": "value_error",
      "ctx": {
        "pattern": "^[A-Z0-9\\-]+$"
      }
    }
  ]
}
```

---

## Python 客户端示例

### 使用 requests 库

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 创建靶点
response = requests.post(
    f"{BASE_URL}/api/v1/targets",
    json={
        "standard_name": "EGFR",
        "aliases": ["ERBB1"],
        "gene_id": "1956"
    }
)
target = response.json()
print(f"Created target: {target['target_id']}")

# 2. 搜索文献
response = requests.post(
    f"{BASE_URL}/api/pubmed/search",
    json={
        "target_name": "EGFR",
        "max_results": 20
    }
)
results = response.json()
print(f"Found {results['total']} publications")

# 3. 创建管线
response = requests.post(
    f"{BASE_URL}/api/pipeline",
    json={
        "drug_code": "SHR-1210",
        "company_name": "恒瑞医药",
        "indication": "非小细胞肺癌",
        "phase": "Phase 3",
        "source_url": "https://example.com"
    }
)
pipeline = response.json()
print(f"Created pipeline: {pipeline['pipeline_id']}")
```

### 异步客户端（aiohttp）

```python
import aiohttp
import asyncio

async def search_publications():
    BASE_URL = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/pubmed/search",
            json={
                "target_name": "EGFR",
                "max_results": 50
            }
        ) as response:
            results = await response.json()
            print(f"Found {results['total']} publications")

            for pub in results['publications']:
                print(f"- {pub['title']} ({pub['relevance_score']})")

asyncio.run(search_publications())
```

---

## 最佳实践

### 1. 错误处理

```python
import requests
from requests.exceptions import RequestException

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/targets",
        json={"standard_name": "EGFR"},
        timeout=10
    )
    response.raise_for_status()

    # 检查业务逻辑错误
    if response.status_code == 409:
        print("Target already exists")
    else:
        target = response.json()
        print(f"Created: {target['target_id']}")

except requests.exceptions.Timeout:
    print("Request timeout")
except requests.exceptions.ConnectionError:
    print("Connection error")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
except RequestException as e:
    print(f"Request failed: {e}")
```

### 2. 分页处理

```python
def get_all_targets(keyword: str):
    """获取所有匹配的靶点（自动分页）"""
    offset = 0
    limit = 100
    all_targets = []

    while True:
        response = requests.get(
            f"{BASE_URL}/api/v1/targets",
            params={"keyword": keyword, "limit": limit, "offset": offset}
        )
        data = response.json()

        all_targets.extend(data['items'])

        if len(data['items']) < limit:
            break

        offset += limit

    return all_targets
```

### 3. 批量操作

```python
def batch_create_pipelines(pipelines_data: list):
    """批量创建管线"""
    created = []
    failed = []

    for pipeline_data in pipelines_data:
        try:
            response = requests.post(
                f"{BASE_URL}/api/pipeline",
                json=pipeline_data,
                timeout=30
            )
            response.raise_for_status()
            created.append(response.json())

        except Exception as e:
            failed.append({
                "data": pipeline_data,
                "error": str(e)
            })

    return {
        "created": len(created),
        "failed": len(failed),
        "failed_items": failed
    }
```

---

**最后更新**: 2026-02-02
