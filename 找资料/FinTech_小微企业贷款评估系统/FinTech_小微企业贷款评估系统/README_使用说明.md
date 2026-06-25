# 🏦 小微贷款智能评估助手 — FinTech期末项目

> **帮助小微企业主在申请贷款前进行自我风险评估 + 26家银行匹配**
>
> 比赛获奖级 · 实践可部署 · 前后端全栈 · ML驱动

---

## 📋 项目概述

### 🎯 解决的核心问题

传统小微贷款存在严重的信息不对称：银行不了解小微企业的真实经营状况，小微企业也不清楚自己符合哪些银行的条件。本系统从**小微企业视角**出发，提供：

1. **自我风险评估** — 输入经营数据，获得信用评分和风险诊断
2. **银行智能匹配** — 自动预测26家银行的贷款通过概率、利率、额度
3. **供应链网络分析** — 可视化上下游关系，识别集中度风险
4. **材料清单准备** — 智能生成申贷所需材料检查表

### 🏆 技术创新点

| 创新维度 | 实现内容 |
|----------|----------|
| **ML模型** | XGBoost违约预测 + GradientBoosting信用评级 + RandomForest风险分类 (3模型集成) |
| **银行数据** | 26家银行真实产品参数（6国有+7股份+8城商+3互联网+2外资） |
| **供应链图谱** | ECharts力导向图 + 风险热力色谱 |
| **8个真实案例** | 覆盖制造/零售/餐饮/农业/建筑/IT/自由职业/批发 |
| **雷达图对比** | TOP5银行5维指标可视化对比 |

---

## 📁 项目结构

```
FinTech_小微企业贷款评估系统/
│
├── README_使用说明.md              ← 本文件
├── 一键安装.bat                    ← Windows一键安装
├── 启动后端.bat                    ← 启动Python后端 (端口8000)
│
├── 前端源码/                       ← React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx                 ← 主应用 (仪表盘布局)
│   │   ├── types.ts                ← TypeScript类型定义
│   │   ├── utils/calculator.ts     ← 核心引擎 (评分+银行匹配)
│   │   └── components/
│   │       ├── BankMatchPanel.tsx  ← 银行匹配面板
│   │       ├── BankRadarChart.tsx  ← ECharts雷达图
│   │       ├── ScoreGauge.tsx      ← 评分仪表盘
│   │       ├── AdvisorReport.tsx   ← AI顾问报告
│   │       ├── FinancialMetrics.tsx← 财务指标分析
│   │       ├── MaterialChecklist.tsx← 材料清单
│   │       ├── SupplyChainGraph.tsx← 供应链风险网络图
│   │       └── InclusiveFinanceSlide.tsx ← 普惠金融理论
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── 后端服务/                       ← Python FastAPI
│   ├── main.py                     ← API服务入口
│   ├── bank_engine.py              ← 26行匹配引擎
│   ├── models.py                   ← Pydantic数据模型
│   ├── data_loader.py              ← 数据加载器(支持CUMCM 2020)
│   ├── ml_inference.py             ← ML模型推理
│   ├── train_ml_enhanced.py        ← 增强ML训练脚本
│   ├── requirements.txt            ← Python依赖
│   └── models/                     ← 已训练模型文件 (.pkl)
│       ├── xgb_default_predictor.pkl   ← XGBoost违约预测
│       ├── gb_rating_classifier.pkl    ← GradientBoosting评级
│       ├── rf_risk_classifier.pkl      ← RandomForest风险分类
│       ├── feature_scaler.pkl
│       ├── label_encoders.pkl
│       └── model_metadata.json
│
└── 数据与报告/
    ├── banks_sme_loan_data.json    ← 26行结构化数据 (可导入程序)
    ├── 银行端小微企业贷款数据_完整报告.md ← 完整调研报告
    └── bank_matcher_prototype.py   ← Python原型演示 (4例测试)
```

---

## 🚀 快速开始

### 方式一：一键安装 (推荐)

双击 `一键安装.bat`，自动完成：
1. 安装Python依赖
2. 安装Node.js依赖
3. 训练ML模型
4. 启动后端服务
5. 启动前端开发服务器

### 方式二：手动安装

#### 1. 环境要求

- **Python** ≥ 3.10
- **Node.js** ≥ 18
- **npm** ≥ 9

#### 2. 安装后端

```bash
cd 后端服务
pip install -r requirements.txt

# 训练ML模型 (首次必须执行)
python train_ml_enhanced.py

# 启动API服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看API文档。

#### 3. 安装前端

```bash
cd 前端源码
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000 使用系统。

---

## 🎮 使用指南

### 基本流程

1. 打开 http://localhost:3000
2. 左侧选择 **📋 企业信息**，填入经营数据
3. 或从底部8个案例中点击一个快速体验
4. 点击 **"开始智能评估 + 银行匹配"**
5. 系统自动跳转到 **📊 风险评估**，展示评分结果
6. 切换左侧导航查看：
   - **🏦 银行匹配** — 26家银行排序 + TOP5雷达图 + 展开看详情
   - **🔗 关系网络** — 供应链风险热力图
   - **📁 材料清单** — 申贷材料检查表
   - **🎓 普惠金融** — 理论展示

### 8个预置案例

| 案例 | 行业 | 特征 |
|------|------|------|
| 奶茶店 | 餐饮 | 2年·有流水·无抵押 |
| 制造业 | 制造 | 5年·A级纳税·有房产·科创 |
| 电商卖家 | 零售 | 3年·纯线上·无抵押 |
| 农业合作社 | 农业 | 4年·有担保·三农 |
| 建筑承包商 | 建筑 | 6年·有房·高负债·逾期 |
| 科技初创 | IT | 0.5年·亏损·科创标签 |
| 自由职业 | 文体 | 1.5年·无执照·无流水 |
| 批发老店 | 零售 | 10年·征信瑕疵·有房 |

---

## 🔧 API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/banks` | 获取全部银行数据 |
| POST | `/api/evaluate` | 提交企业数据，返回完整评估+银行匹配 |
| POST | `/api/evaluate/quick` | 快速评估，仅返回评分+TOP5银行 |

### 评估接口示例

```bash
curl -X POST http://localhost:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_type": "individual",
    "operating_years": 2,
    "industry": "hospitality_food",
    "region": "广东省",
    "monthly_revenue": 60000,
    "monthly_fixed_cost": 35000,
    "existing_liabilities": 20000,
    "requested_amount": 100000,
    "loan_term": 12,
    "annual_rate": 6.0,
    "tax_level": "B",
    "has_business_license": true,
    "has_stable_bank_flow": true,
    "has_overdue_record": false,
    "overdue_count_2yr": 0,
    "has_collateral_or_guarantor": false,
    "has_real_estate": false,
    "real_estate_value": 0,
    "is_ecommerce": false,
    "is_tech_enterprise": false
  }'
```

---

## 📊 数据来源

| 数据 | 来源 |
|------|------|
| 银行产品参数 | 央行普惠金融报告(2024-2025)、各银行官网、证券时报/界面新闻 |
| ML训练特征 | 山东大学学报(2024)、运筹与管理(2025)、Heliyon(2024)等学术论文 |
| 信用评估框架 | 5C原则 + CUMCM 2020建模竞赛指标体系 |
| 训练数据集 | CUMCM 2020国赛C题 (425家企业, 1,096,012条发票) + ChinaZJB (IEEE DataPort) |

---

## 🧠 使用真实数据训练

如果要获得更好的ML模型效果，可以下载CUMCM 2020真实数据：

1. 访问 http://www.mcm.edu.cn/ 历年竞赛试题 → 2020年C题
2. 下载附件1和附件2的Excel文件
3. 放入 `后端服务/cumcm_data/` 目录
4. 重新运行 `python train_ml_enhanced.py`

使用真实数据训练后，模型AUC预计可达 **0.90+**（论文报告值0.964）。

---

## ⚙️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | React 19 + Vite 6 + TypeScript 5.8 |
| UI样式 | TailwindCSS 4 |
| 动画 | Motion (Framer Motion) |
| 图表 | ECharts 5 |
| 图标 | Lucide React |
| 后端框架 | FastAPI (Python) |
| ML框架 | XGBoost + scikit-learn + imbalanced-learn |
| 数据处理 | pandas + numpy |

---

## 📝 许可与致谢

本项目为金融科技课程期末作业，仅供学习交流使用。

数据来源：
- 中国人民银行《中国普惠金融指标分析报告(2024-2025年)》
- 2020年全国大学生数学建模竞赛C题
- 各大银行公开产品信息

---

**© 2026 FinTech 课程项目组**
