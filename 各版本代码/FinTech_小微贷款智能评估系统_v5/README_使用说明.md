# 小微贷款智能评估助手 v5.0 — FinTech期末项目

> **帮助小微企业主在申请贷款前进行自我风险评估 + 30家银行匹配 + LLM Agent 智能对话顾问**
>
> 前后端全栈 · ML驱动 · DeepSeek V4 Function Call · RAG 语义检索 · 多 Agent 协作

---

## 快速开始

### 环境要求
- Python >= 3.10
- Node.js >= 18
- npm >= 9

### 一键安装

1. 双击 `一键安装启动.bat`（自动安装依赖+训练模型）
2. 双击 `启动后端.bat`（自动检测 ML 模型 → 缺失则训练 → 启动 API）
3. 双击 `启动前端.bat`（启动前端，端口3000）
4. 浏览器访问 `http://localhost:3000`

---

## 系统功能

### 核心模块

| 模块 | 功能 |
|------|------|
| 智能对话 | AI贷款顾问，13个对话领域（风险评估/银行选择/信用违约/信用修复/企业自查/还款测算/贷款方案等） |
| 企业信息 | 18字段经营数据录入 + 8个预置案例一键填入 |
| 企业搜索 | 输入企业名称自动搜索1159家企业数据库，生成贷款可行性报告 |
| 风险评估 | 五维信用评分仪表盘 + AI报告 + 财务压力测算 |
| 银行匹配 | 30家银行通过概率排序 + TOP5雷达图对比 |
| 关系网络 | 供应链风险热力图 + 集中度预警 |
| 材料清单 | 智能申贷材料检查表 + 勾选进度 |
| 普惠金融 | FinTech理论展示 |

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + Vite 6 + TypeScript + TailwindCSS 4 + ECharts 5 |
| 后端 | Python FastAPI |
| ML | XGBoost + GradientBoosting + RandomForest（9000行真实数据训练） |
| 知识库 | 18条政策规则 + 30个教学案例 + 行业准入/征信/纳税规则 |

### 数据规模

| 数据 | 数量 |
|------|------|
| 银行数据库 | 30家（6国有+7股份+10城商+2农商+3互联网+2外资） |
| 企业数据库 | 1159家（371城市 × 11行业） |
| ML训练样本 | 9000行（UCI真实 + CUMCM合成） |
| 知识库规则 | 18条政策法规 + 7大被拒因子 + 6类补贴政策 |

---

## 项目结构

```
FinTech_小微贷款智能评估系统_v5/
├── 一键安装启动.bat
├── 启动后端.bat
├── 启动前端.bat
├── README_使用说明.md
│
├── 前端源码/              React+Vite+TS前端
│   ├── src/
│   │   ├── App.tsx        主应用（7模块仪表盘）
│   │   ├── types.ts       类型定义
│   │   ├── utils/calculator.ts  核心引擎
│   │   └── components/    9个组件
│   └── package.json
│
├── 后端服务/              Python FastAPI后端
│   ├── main.py            API服务入口
│   ├── bank_engine.py     30行匹配引擎
│   ├── chat_agent.py      AI对话Agent（13领域）
│   ├── enterprise_search.py  1159企业搜索
│   ├── data_loader.py     训练数据加载
│   ├── ml_inference.py    ML推理
│   ├── train_ml_enhanced.py   ML训练
│   ├── agent_kb/          知识库文件
│   ├── cumcm_data/        训练数据
│   └── models/            已训练模型
│
└── 数据文件/              报告与参考数据
    ├── banks_sme_loan_data.json
    └── 银行端小微企业贷款数据_完整报告.md
```

---

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/banks | 获取30家银行数据 |
| POST | /api/evaluate | 提交企业数据，返回完整评估+银行匹配 |
| POST | /api/chat | AI对话接口（13领域） |
| POST | /api/enterprise/search | 企业名称搜索（1159家） |

---

## 数据来源

- 中国人民银行《中国普惠金融指标分析报告(2024-2025年)》
- 2020年全国大学生数学建模竞赛C题
- 最高人民法院失信被执行人数据
- 国家企业信用信息公示系统
- 惠誉博华小微贷款NPAS报告
- GitHub Enterprise-Registration-Data-of-Chinese-Mainland

---

**© 2026 FinTech 课程项目组**
