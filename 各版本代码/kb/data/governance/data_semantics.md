# 普惠金融 Agent 数据语义层

## 稳定数据源

- 模型样本：`data/processed/贷款风险模型训练数据_已清洗.csv`，粒度为“一行一个历史个人信贷样本”。
- 规则知识：`data/processed/普惠金融政策规则知识库_已整理.csv`，粒度为“一行一个可检索规则主题”。
- 教学案例：`data/processed/小微企业融资教学案例库_模拟数据.csv`，粒度为“一行一个教学模拟案例”。
- 来源登记：`data/metadata/数据来源登记表.csv`。

## 核心定义

- `risk_label=1`：UCI 原标签 `credit_risk=0`，表示 bad credit risk。
- `risk_label=0`：UCI 原标签 `credit_risk=1`，表示 good credit risk。
- `is_synthetic=1`：该案例为课程教学模拟，不是真实客户、银行授信记录或裁判案例。
- 空白企业经营字段：公开源没有该字段；空白不等于 0。
- `rule_id`：Agent 最小规则检索单元；输出时应同时返回 `source_url` 与 `last_verified_at`。

## 使用边界

- 模型数据为德国历史个人信贷，不可解释为中国小微企业违约总体。
- 规则文件用于 RAG/规则解释，不进入贷款风险模型训练表。
- 模型概率、案例匹配和政策摘要均只用于课程展示，不构成真实授信或法律意见。
