# FinCourse_Agent — Git 协作手册

> 适用：金融科技课程项目组 | 仓库：`FinCourse_Agent`

---

## 一、环境准备（每人一次）

### 1. 克隆仓库

```bash
git clone https://github.com/Erickke-creator/FinCourse_Agent.git
cd FinCourse_Agent
```

### 2. 安装依赖

```bash
# Python 后端
cd "找资料/FinTech_小微企业贷款评估系统/FinTech_小微企业贷款评估系统/后端服务"
pip install -r requirements.txt

# 训练 ML 模型（首次必须）
python train_ml_enhanced.py

# Node 前端
cd "../前端源码"
npm install
```

### 3. 验证

```bash
# 启动后端
cd "../后端服务"
python -m uvicorn main:app --port 8000

# 另开终端，启动前端
cd "../前端源码"
npm run dev
```

打开 `http://localhost:3000`，点击"开始评估"确认一切正常。

---

## 二、日常工作流

### 每次开始工作前

```bash
git pull        # 拉取最新代码
```

### 修改知识库数据

知识库文件在 `找资料/kb/data/` 下，都是 CSV/JSON，直接用编辑器改。

```bash
# 示例：更新制造业准入系数
# 编辑 找资料/kb/data/industries/industry_acceptance.csv
# 同步更新 找资料/kb/VERSION 中的日期

git add "找资料/kb/data/industries/industry_acceptance.csv" "找资料/kb/VERSION"
git commit -m "kb: 制造业准入系数 1.0→1.05，依据2026年央行指导文件"
git push
```

### 修改代码（后端/前端）

```bash
git add .
git commit -m "feat: 银行匹配引擎增加地域加权"
git push
```

### 冲突处理

如果 push 被拒绝（别人先推了）：

```bash
git pull --rebase   # 把别人的改动拉下来，自己的放在上面
git push            # 再推
```

如果 rebase 过程中有冲突：手动编辑冲突文件 → `git add .` → `git rebase --continue` → `git push`。

---

## 三、Commit 信息规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `kb:` | 知识库数据更新 | `kb: 更新广东省地方政策规则` |
| `feat:` | 新功能 | `feat: 增加供应链关系图谱组件` |
| `fix:` | Bug 修复 | `fix: 修正纳税等级D的评分错误` |
| `refactor:` | 代码重构 | `refactor: 抽取银行匹配为独立模块` |
| `docs:` | 文档更新 | `docs: 更新 README 使用说明` |
| `chore:` | 杂项 | `chore: 清理旧文件` |

---

## 四、知识库协作规则

### 谁改什么

- **数据文件**（`kb/data/*.csv`, `*.json`）：任何人都可以改，改完后 commit 标注 `kb:`
- **Loader 代码**（`kb/loader/*.py`）：至少一个人 review 后再合并
- **后端**（`后端服务/*.py`）：同上
- **前端**（`前端源码/src/*`）：同上
- **旧知识库目录**（`Agent整合构建/`、`普惠金融Agent_知识库/`、`金融科技agent/`）：**归档只读，不要修改**

### 改知识库的 check list

1. 改 CSV/JSON 数据
2. 更新 `找资料/kb/VERSION` 中的 `date:` 为当天日期
3. `git commit -m "kb: <改了什么>"` 
4. `git push`

---

## 五、紧急情况处理

### 改错了，想撤销

```bash
# 撤销未 commit 的修改
git restore <文件名>

# 撤销已 commit 但未 push 的 commit
git reset --soft HEAD~1    # 保留修改
git reset --hard HEAD~1    # 丢弃修改（危险）
```

### 上传了不该上传的大文件

```bash
# 从 Git 中删除但保留本地文件
git rm --cached <文件路径>
git commit -m "chore: 移除大文件"
# 别忘了更新 .gitignore
```

### 本地改乱了，想回到最新版本

```bash
git stash       # 暂存当前修改
git pull        # 拉取最新
git stash pop   # 恢复暂存的修改
```

---

## 六、目录结构速查

```
FinCourse_Agent/
├── .gitignore
├── 找资料/
│   ├── kb/                              ← ★ 统一知识库（权威来源）
│   │   ├── data/                        ← 知识库数据文件
│   │   └── loader/                      ← Python 加载器
│   ├── FinTech_小微企业贷款评估系统/      ← ★ 应用代码
│   │   └── FinTech_小微企业贷款评估系统/
│   │       ├── 后端服务/
│   │       └── 前端源码/
│   ├── Agent整合构建/                    ← 归档（只读）
│   ├── 普惠金融Agent_知识库/              ← 归档（只读）
│   └── 金融科技agent/                    ← 归档（只读）
└── README.md
```
