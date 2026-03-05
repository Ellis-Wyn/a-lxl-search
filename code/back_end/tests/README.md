# 测试文档

## 概述

本项目使用 pytest 进行单元测试和集成测试，目标覆盖率 ≥80%。

## 测试结构

```
tests/
├── __init__.py
├── test_models/              # 模型单元测试
│   ├── __init__.py
│   ├── test_target.py        # Target 模型测试
│   ├── test_publication.py   # Publication 模型测试
│   └── test_pipeline.py      # Pipeline 模型测试
├── test_services/            # 服务层测试
│   ├── __init__.py
│   ├── test_database_service.py  # DatabaseService 测试
│   └── test_phase_mapper.py      # PhaseMapper 测试
└── unit/                     # 其他单元测试
    ├── test_retry.py
    ├── test_circuit_breaker.py
    └── test_exceptions.py
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行特定模块

```bash
# 运行模型测试
pytest tests/test_models/

# 运行服务层测试
pytest tests/test_services/

# 运行单个测试文件
pytest tests/test_models/test_target.py

# 运行单个测试类
pytest tests/test_models/test_target.py::TestTargetModel

# 运行单个测试方法
pytest tests/test_models/test_target.py::TestTargetModel::test_create_target_minimal
```

### 运行带标记的测试

```bash
# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 运行需要数据库的测试
pytest -m database

# 排除慢速测试
pytest -m "not slow"
```

### 生成覆盖率报告

```bash
# 生成 HTML 覆盖率报告
pytest --cov=. --cov-report=html

# 生成终端覆盖率报告
pytest --cov=. --cov-report=term-missing

# 生成 XML 覆盖率报告（用于 CI）
pytest --cov=. --cov-report=xml
```

## 测试覆盖

### 模型测试 (test_models/)

- **test_target.py**: 16 个测试
  - 靶点创建（最小/完整）
  - 别名功能
  - 序列化
  - ORM 关系
  - 唯一约束
  - 查询方法

- **test_publication.py**: 17 个测试
  - 文献创建
  - 作者列表处理
  - 时效性计算
  - 临床数据标签
  - ORM 关系
  - 查询和排序

- **test_pipeline.py**: 25 个测试
  - 管线创建
  - 时间戳方法
  - Phase 映射
  - 消失检测
  - 联合用药
  - 序列化
  - ORM 关系

### 服务层测试 (test_services/)

- **test_database_service.py**: 28 个测试
  - CRUD 操作
  - 事务管理
  - 关联表操作
  - 错误处理
  - 单例模式

- **test_phase_mapper.py**: 18 个测试
  - 30+ 种阶段映射
  - 中英文混合
  - 边界情况
  - 特殊字符
  - 大小写不敏感

## 编写新测试

### 测试模板

```python
"""
=====================================================
[模块名称] 测试
=====================================================
"""

import pytest
from sqlalchemy.orm import Session

from [module_path] import [ClassName]


class Test[ClassName]:
    """[ClassName] 测试类"""

    def test_[test_name](self, db_session: Session):
        """测试描述"""
        # Arrange（准备）
        service = [ClassName]()
        service._db = db_session

        # Act（执行）
        result = service.method_to_test()

        # Assert（断言）
        assert result is not None
```

### 最佳实践

1. **使用 Fixture**: 复用 conftest.py 中的测试数据
2. **测试隔离**: 每个测试独立，不依赖其他测试
3. **清晰命名**: 测试方法名应描述测试内容
4. **AAA 模式**: Arrange（准备）→ Act（执行）→ Assert（断言）
5. **边界测试**: 测试正常情况和边界情况
6. **错误测试**: 测试错误处理和异常情况

## 持续集成

测试会在以下情况自动运行：
- 每次提交代码
- 每个 Pull Request
- 每日定时任务

## 覆盖率目标

| 模块 | 目标覆盖率 | 当前覆盖率 |
|------|----------|----------|
| models/ | 90% | - |
| services/ | 85% | - |
| crawlers/ | 75% | - |
| api/ | 80% | - |
| **总计** | **≥80%** | - |

## 故障排查

### 常见问题

**Q: 测试失败，提示 "No module named 'tests'"**
```bash
# 从项目根目录运行测试
cd D:\26初寒假实习\A_lxl_search\code\back_end
pytest
```

**Q: 数据库连接错误**
```bash
# 测试使用内存数据库，不需要真实数据库
# 确保已安装 pytest 和 pytest-cov
pip install pytest pytest-cov
```

**Q: 覆盖率报告生成失败**
```bash
# 安装 pytest-cov
pip install pytest-cov
```

## 贡献指南

提交代码前请确保：
1. 所有测试通过：`pytest`
2. 覆盖率不下降：`pytest --cov=.`
3. 新功能有对应测试

## 参考资料

- [pytest 文档](https://docs.pytest.org/)
- [Pydantic 测试](https://docs.pydantic.dev/latest/concepts/tests/)
- [SQLAlchemy 测试](https://docs.sqlalchemy.org/en/20/orm/testing.html)
