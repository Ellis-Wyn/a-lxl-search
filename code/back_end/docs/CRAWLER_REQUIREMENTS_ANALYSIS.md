# 爬虫需求分析与改进方案

## 甲方要求 vs 当前实现

### 1. 联合用药识别 ❌ 未实现

**甲方要求：**
- 识别 `[Drug A] + [Drug B]` 或 `in combination with` 模式
- 标记为联用，而不是两个独立的单药管线

**当前实现：**
```python
# company_spider.py line 246-252
existing = db.query(Pipeline).filter(
    Pipeline.drug_code == item.drug_code,
    Pipeline.company_name == item.company_name,
    Pipeline.indication == item.indication,
).first()
```
- ❌ 没有联合用药字段
- ❌ 没有识别联合用药的逻辑
- ❌ 没有标记联用疗法

**改进方案：**

#### 1.1 添加数据库字段

```sql
ALTER TABLE pipeline ADD COLUMN IF NOT EXISTS is_combination BOOLEAN DEFAULT FALSE;
ALTER TABLE pipeline ADD COLUMN IF NOT EXISTS combination_drugs TEXT;  -- JSON array: ["HRS-1234", "HRS-5678"]
```

#### 1.2 更新Pipeline模型

```python
# models/pipeline.py
class Pipeline(Base):
    # ...existing fields...
    is_combination = Column(Boolean, default=False, nullable=False, comment="是否为联合用药")
    combination_drugs = Column(Text, nullable=True, comment="联合用药列表(JSON)")
```

#### 1.3 实现识别逻辑

```python
# utils/pipeline_parser.py
import re
from typing import List, Optional, Tuple

class CombinationTherapyDetector:
    """联合用药检测器"""

    # 联合用药模式
    COMBINATION_PATTERNS = [
        r'\+\s*',                      # "Drug A + Drug B"
        r'\b(?:in\s+)?combination\s+(?:with|of)\b',  # "in combination with"
        r'\b(?:plus|&|and)\b',          # "Drug A plus Drug B"
        r'联合',                        # 中文
        r'联用',                        # 中文
    ]

    @classmethod
    def detect_combination(cls, text: str, drug_list: List[str]) -> Tuple[bool, List[str]]:
        """
        检测是否为联合用药

        Args:
            text: 待检测文本
            drug_list: 已识别的药物列表

        Returns:
            (是否联合用药, 联合药物列表)
        """
        if not text:
            return False, []

        text_lower = text.lower()

        # 检查联合用药关键词
        for pattern in cls.COMBINATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True, cls._extract_drugs(text, drug_list)

        return False, []

    @classmethod
    def _extract_drugs(cls, text: str, known_drugs: List[str]) -> List[str]:
        """从文本中提取药物代码"""
        # 提取所有药物代码模式 (如 HRS-1234, SHR-5678)
        drug_pattern = r'\b([A-Z]{2,}-\d{4,})\b'
        found_drugs = re.findall(drug_pattern, text)

        # 去重并过滤已知的药物
        combination_drugs = list(set(found_drugs) - set(known_drugs))

        return combination_drugs
```

#### 1.4 在爬虫中集成

```python
# hengrui_spider.py parse_pipeline_page 方法
from utils.pipeline_parser import CombinationTherapyDetector

# ...existing code...
if pop_div:
    pop_ps = pop_div.find_all('p')

    if len(pop_ps) >= 1:
        indication_text = pop_ps[0].get_text(separator=' ', strip=True)

        # 检测联合用药
        is_combination, combo_drugs = CombinationTherapyDetector.detect_combination(
            indication_text,
            [drug_code]
        )

        indication = re.sub(r'\s+', ' ', indication_text).strip()
        # 移除治疗方式信息（已在is_combination中标记）
        indication = indication.replace('单 药', '').replace('单药', '')
        indication = indication.replace('药或联合', '').replace('联合', '').strip()

# 创建数据项
pipeline_data = PipelineDataItem(
    drug_code=drug_code,
    company_name=self.company_name,
    indication=indication,
    phase=phase,
    source_url=self.pipeline_url,
    targets=[target] if target else [],
    is_combination=is_combination,  # 新增字段
    combination_drugs=combo_drugs   # 新增字段
)
```

---

### 2. 适应症区分 ⚠️ 部分实现

**甲方要求：**
- 同一药物可能针对不同疾病（如胃癌、肺癌）
- 应以 **"药物+靶点+适应症"** 为唯一主键
- 避免数据覆盖

**当前实现：**
```python
# company_spider.py line 246-252
existing = db.query(Pipeline).filter(
    Pipeline.drug_code == item.drug_code,
    Pipeline.company_name == item.company_name,
    Pipeline.indication == item.indication,  # ✅ 包含适应症
).first()
```

✅ **当前逻辑正确**：使用 `drug_code + company_name + indication` 作为唯一性检查

**验证：**
```python
# 同一个药物针对不同适应症会创建多条记录
HRS-9815 + 恒瑞医药 + 前列腺癌 = Record 1
HRS-9815 + 恒瑞医药 + 肺癌     = Record 2
```

**潜在问题：**
- ⚠️ 如果适应症文本不完全一致（如"非小细胞肺癌" vs "肺癌"），会创建重复记录
- ⚠️ 需要适应症标准化

**改进方案 - 适应症标准化：**

```python
# utils/indication_mapper.py
from typing import Optional

class IndicationMapper:
    """适应症标准化器"""

    # 适应症映射表
    INDICATION_MAPPING = {
        # 肺癌
        "非小细胞肺癌": "非小细胞肺癌",
        "NSCLC": "非小细胞肺癌",
        "小细胞肺癌": "小细胞肺癌",
        "SCLC": "小细胞肺癌",
        "肺癌": "肺癌",

        # 乳腺癌
        "乳腺癌": "乳腺癌",
        "三阴性乳腺癌": "三阴性乳腺癌",
        "HER2阳性乳腺癌": "HER2阳性乳腺癌",

        # 实体瘤
        "实体瘤": "实体瘤",
        "晚期实体瘤": "实体瘤",
        "Solid Tumor": "实体瘤",

        # 血液瘤
        "淋巴瘤": "淋巴瘤",
        "非霍奇金淋巴瘤": "非霍奇金淋巴瘤",
        "白血病": "白血病",
        "多发性骨髓瘤": "多发性骨髓瘤",
    }

    @classmethod
    def normalize(cls, indication: str) -> str:
        """
        标准化适应症名称

        Args:
            indication: 原始适应症文本

        Returns:
            标准化的适应症名称
        """
        if not indication:
            return "Unknown"

        indication = indication.strip()

        # 精确匹配
        if indication in cls.INDICATION_MAPPING:
            return cls.INDICATION_MAPPING[indication]

        # 模糊匹配（包含关键词）
        for key, value in cls.INDICATION_MAPPING.items():
            if key.lower() in indication.lower():
                return value

        # 如果没有匹配，返回原文（但截断到50字符）
        return indication[:50] if len(indication) > 50 else indication
```

在爬虫中使用：
```python
from utils.indication_mapper import IndicationMapper

indication_normalized = IndicationMapper.normalize(indication)

pipeline_data = PipelineDataItem(
    # ...
    indication=indication_normalized,  # 使用标准化后的适应症
)
```

---

### 3. 终止研发识别 ❌ 未实现

**甲方要求：**
- 官网更新中药物消失
- 出现 Discontinued / Terminated / Dropped 字样
- 自动发出**"竞品退场"**预警

**当前实现：**
```python
# company_spider.py line 252-259
if existing:
    existing.last_seen_at = datetime.utcnow()
    db.commit()
    logger.debug(f"Updated existing pipeline: {item.drug_code}")
    db.close()
    return True
```

✅ 有 `last_seen_at` 字段追踪
❌ 没有检测消失的逻辑
❌ 没有识别终止状态
❌ 没有预警机制

**改进方案：**

#### 3.1 识别终止状态

```python
# utils/pipeline_parser.py
class DiscontinuationDetector:
    """终止研发检测器"""

    # 终止关键词
    DISCONTINUED_KEYWORDS = [
        'discontinued',
        'terminated',
        'dropped',
        'suspended',
        'withdrawn',
        '终止',
        '暂停',
        '放弃',
        '已终止',
        '已暂停',
    ]

    @classmethod
    def is_discontinued(cls, text: str) -> bool:
        """
        检测是否已终止研发

        Args:
            text: 待检测文本

        Returns:
            是否已终止
        """
        if not text:
            return False

        text_lower = text.lower()

        for keyword in cls.DISCONTINUED_KEYWORDS:
            if keyword in text_lower:
                return True

        return False
```

#### 3.2 检测消失的管线

```python
# company_spider.py add method
def check_discontinued_pipelines(self, seen_drug_codes: List[str]) -> List[str]:
    """
    检测消失的管线

    Args:
        seen_drug_codes: 本次爬虫看到的药物代码列表

    Returns:
        消失的药物代码列表
    """
    db = SessionLocal()

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

        # 标记为 discontinued
        for pipeline in existing_pipelines:
            if pipeline.drug_code in disappeared_codes:
                pipeline.status = 'discontinued'
                pipeline.discontinued_at = datetime.utcnow()

        db.commit()
        logger.info(f"Marked {len(disappeared_codes)} pipelines as discontinued")

    db.close()
    return list(disappeared_codes)
```

#### 3.3 预警机制

```python
# services/alert_service.py
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

class AlertType(str, Enum):
    COMPETITOR_WITHDRAWN = "competitor_withdrawn"  # 竞品退场
    PIPELINE_DISCONTINUED = "pipeline_discontinued"  # 管线终止
    NEW_COMPETITOR = "new_competitor"              # 新竞品

@dataclass
class Alert:
    """预警信息"""
    alert_type: AlertType
    company_name: str
    drug_code: str
    indication: str
    phase: str
    message: str
    severity: str  # "high", "medium", "low"
    metadata: Dict = None

class AlertService:
    """预警服务"""

    def __init__(self):
        self.alerts: List[Alert] = []

    def create_discontinued_alert(self, pipeline_data: Dict) -> Alert:
        """创建终止预警"""
        return Alert(
            alert_type=AlertType.COMPETITOR_WITHDRAWN,
            company_name=pipeline_data['company_name'],
            drug_code=pipeline_data['drug_code'],
            indication=pipeline_data['indication'],
            phase=pipeline_data['phase'],
            message=f"⚠️ 竞品退场预警: {pipeline_data['company_name']} 的 {pipeline_data['drug_code']} 已终止研发",
            severity="high",
            metadata=pipeline_data
        )

    def send_alert(self, alert: Alert):
        """发送预警（可扩展为邮件/钉钉/企业微信）"""
        self.alerts.append(alert)

        # TODO: 实现实际的发送逻辑
        logger.warning(
            f"🚨 ALERT: {alert.message}",
            extra={
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "company": alert.company_name,
                "drug_code": alert.drug_code,
            }
        )

    def get_alerts(self, alert_type: AlertType = None) -> List[Alert]:
        """获取预警列表"""
        if alert_type:
            return [a for a in self.alerts if a.alert_type == alert_type]
        return self.alerts
```

#### 3.4 集成到爬虫

```python
# company_spider.py
from services.alert_service import AlertService
from utils.pipeline_parser import DiscontinuationDetector

class CompanySpiderBase:
    def __init__(self):
        # ...existing code...
        self.alert_service = AlertService()

    def run(self) -> CrawlerStats:
        """运行爬虫"""
        # ...existing code...

        # 收集本次看到的药物代码
        seen_drug_codes = []

        for item in pipelines:
            seen_drug_codes.append(item.drug_code)

            # 检查是否已终止
            if DiscontinuationDetector.is_discontinued(item.indication):
                # 创建终止预警
                alert = self.alert_service.create_discontinued_alert({
                    'company_name': item.company_name,
                    'drug_code': item.drug_code,
                    'indication': item.indication,
                    'phase': item.phase,
                })
                self.alert_service.send_alert(alert)

                # 标记为已终止
                item.status = 'discontinued'

            # 保存到数据库
            self.save_to_database(item)

        # 检测消失的管线
        disappeared = self.check_discontinued_pipelines(seen_drug_codes)

        if disappeared:
            # 为每个消失的管线创建预警
            for drug_code in disappeared:
                # 查询详细信息
                db = SessionLocal()
                pipeline = db.query(Pipeline).filter(
                    Pipeline.drug_code == drug_code,
                    Pipeline.company_name == self.company_name
                ).first()

                if pipeline:
                    alert = self.alert_service.create_discontinued_alert({
                        'company_name': pipeline.company_name,
                        'drug_code': pipeline.drug_code,
                        'indication': pipeline.indication,
                        'phase': pipeline.phase,
                    })
                    self.alert_service.send_alert(alert)

                db.close()

        return self.stats
```

---

## 实施计划

### Phase 1: 高优先级（立即实施）

1. **终止研发识别** (2-3小时)
   - [ ] 添加 `status`, `discontinued_at` 字段到Pipeline模型
   - [ ] 实现 `DiscontinuationDetector`
   - [ ] 实现 `check_discontinued_pipelines` 方法
   - [ ] 实现 `AlertService` 基础功能
   - [ ] 测试竞品退场检测

### Phase 2: 中优先级（本周完成）

2. **联合用药识别** (3-4小时)
   - [ ] 添加 `is_combination`, `combination_drugs` 字段
   - [ ] 实现 `CombinationTherapyDetector`
   - [ ] 在爬虫中集成检测逻辑
   - [ ] 更新API返回联合用药信息
   - [ ] 测试联合用药识别

3. **适应症标准化** (2-3小时)
   - [ ] 实现 `IndicationMapper`
   - [ ] 添加常见适应症映射
   - [ ] 在爬虫中应用标准化
   - [ ] 测试去重逻辑

### Phase 3: 低优先级（可选）

4. **预警增强** (按需)
   - [ ] 邮件通知
   - [ ] 钉钉/企业微信机器人
   - [ ] 预警历史记录
   - [ ] 预警统计报表

---

## 验证测试

### 测试场景1: 联合用药

```python
# 输入
text = "HRS-1234 + HRS-5678 用于治疗非小细胞肺癌"
# 期望输出
is_combination = True
combination_drugs = ["HRS-5678"]
```

### 测试场景2: 适应区区分

```python
# 场景：同一药物不同适应症
pipeline1 = {
    "drug_code": "HRS-1234",
    "indication": "非小细胞肺癌"
}
pipeline2 = {
    "drug_code": "HRS-1234",
    "indication": "乳腺癌"
}
# 期望：创建2条记录，不覆盖
```

### 测试场景3: 竞品退场

```python
# 第一次爬取
crawl_1 = ["HRS-1234", "HRS-5678", "HRS-9012"]
# 第二次爬取（HRS-5678消失）
crawl_2 = ["HRS-1234", "HRS-9012"]
# 期望：HRS-5678 标记为 discontinued，发送预警
```

---

## 总结

| 需求 | 当前状态 | 优先级 | 预计工时 |
|------|---------|--------|---------|
| 联合用药识别 | ❌ 未实现 | 高 | 3-4h |
| 适应症区分 | ⚠️ 部分实现 | 中 | 2-3h |
| 终止检测/预警 | ❌ 未实现 | **最高** | 2-3h |

**建议优先实现终止检测功能，因为这是竞品分析的核心需求。**
