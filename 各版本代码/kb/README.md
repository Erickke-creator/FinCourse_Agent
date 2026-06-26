# 普惠金融小微企业融资诊断 Agent — 统一知识库

> 版本 1.0.0 | 2026-06-25
> 本目录是小微企业贷款评估系统的**唯一权威知识库**。所有评估逻辑应从此读取数据，禁止在代码中硬编码知识库内容。

## 目录结构

```
kb/
├── VERSION                        ← 版本号
├── README.md                      ← 本文件（组员使用指南）
├── schema/                        ← JSON Schema 校验定义（7个）
├── data/                          ← 知识库数据文件（16个）
│   ├── policies/                  ← 政策规则（国家级18条 + 地方级24条）
│   ├── banks/                     ← 银行产品（28家 + 地域可用性）
│   ├── industries/                ← 行业准入（18行业 + 地域调整）
│   ├── credit_tax/                ← 征信与纳税（分级表 + 评分规则）
│   ├── risk_control/              ← 风控规则（被拒因子 + 补贴政策 + 宏观数据）
│   ├── cases/                     ← 教学案例（30条基础 + 20条增强）
│   └── governance/                ← 数据治理（来源登记 + 语义层 + 字段映射）
├── loader/                        ← Python 加载器（pip installable）
└── tests/                         ← 单元测试
```

## 快速开始（组员使用）

### 1. 安装 loader 包

```bash
cd 找资料/kb/loader
pip install -e .
```

### 2. 在代码中使用

```python
from kb_loader import KnowledgeBase, KBQuery

# 加载知识库
kb = KnowledgeBase()

# 创建查询会话（自动记录溯源）
query = KBQuery(kb)

# 查询银行产品
banks = query.get_all_banks()
print(f"加载了 {len(banks)} 家银行产品")

# 查询行业准入
info = query.get_industry_acceptance("manufacturing")
print(f"制造业接受度系数: {info['接受度系数']}")

# 查询纳税评分
score = query.get_tax_score("A")
print(f"A级纳税评分: {score}")

# 查询广东省制造业适用的政策
policies = query.get_relevant_policies(["制造业", "科创"], province="广东省")
print(f"匹配了 {len(policies)} 条政策")

# 查看本次评估使用了哪些知识库（溯源）
for src in query.get_accessed_sources():
    print(f"  [{src.domain}] {src.description}")

# 查看 KB 版本
print(query.get_kb_version())
```

### 3. 直接读写数据文件

不需要写代码，也可以用任何工具直接读取 `data/` 下的 CSV/JSON 文件：

```python
import pandas as pd
df = pd.read_csv("kb/data/industries/industry_acceptance.csv")
```

## 数据文件说明

| 文件 | 行数 | 说明 |
|------|------|------|
| `policies/national_policies.csv` | 18 | 国家级监管政策法规（22列，含 rule_id, key_condition, risk_warning 等） |
| `policies/provincial_policies.csv` | 24 | 省市级普惠金融细则（18列，含 province, city, subsidy_content 等） |
| `banks/bank_products.json` | 28 | 银行产品参数（含 requirements, preferences, rejection_sensitivity） |
| `banks/bank_regional_availability.csv` | 30 | 银行地域覆盖（含 覆盖范围, 重点服务区域, 线上化程度） |
| `industries/industry_acceptance.csv` | 18 | 行业准入等级与接受度系数 |
| `industries/regional_adjustments.csv` | 23 | 行业准入的地域差异化调整系数 |
| `credit_tax/credit_tolerance.csv` | 4 | 银行层级征信容忍度 |
| `credit_tax/tax_level_scoring.csv` | 5 | 纳税等级 A/B/M/C/D 评分映射 |
| `risk_control/rejection_factors.csv` | 7 | 贷款被拒因子与权重 |
| `risk_control/subsidy_policies.csv` | 6 | 2026政策补贴与贴息规则 |
| `risk_control/macro_statistics.json` | 1 | 普惠小微贷款宏观统计 |
| `cases/teaching_cases_basic.csv` | 30 | 原始教学案例 |
| `cases/teaching_cases_enhanced.csv` | 20 | 增强版案例（含 diagnosis_chain, improvement_advice） |
| `governance/data_source_registry.csv` | — | 所有数据来源的URL/许可证/下载状态 |
| `governance/data_semantics.md` | — | 字段定义、标签口径、使用边界 |
| `governance/field_mapping_ml_kb.csv` | 35 | 输入字段→ML模型→知识库的三方映射关系 |

## 数据更新流程

1. 修改 `kb/data/` 下的 CSV/JSON 文件
2. 同步更新 `kb/VERSION` 中的版本号和日期
3. 运行 `python kb/tests/test_loader.py` 验证数据完整性
4. 重启后端服务使新数据生效

## 边界声明

- 模型数据为德国历史个人信贷（UCI）+ 统计模拟数据（CUMCM 2020），不可解释为中国小微企业违约总体
- 所有教学案例 is_synthetic=1，非真实客户或裁判案例
- 政策资料为公开资料整理摘要，非官方全文或法律意见
- 银行产品参数基于公开信息整理，可能变化
- 所有输出仅用于课程展示，不构成真实授信审批依据
