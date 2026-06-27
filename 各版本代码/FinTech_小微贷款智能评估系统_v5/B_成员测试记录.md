# 成员 B — Chat Agent / 知识库工具测试记录

## 本次范围

- 统一 `evaluate_loan` 工具与 `LoanInput` 的字段和单位。
- 修复异步 Agent 工具未被 `await` 的问题。
- 修复中文政策问句、中文行业别名的检索。
- 删除会产生误导性结果的无 Key 降级回答；未配置 Key 时返回 503。
- PDF 工具暂不对 Agent 暴露，等 PDF 模块统一修复后再接入。

## 字段口径

| Agent 字段 | 单位 | 后端字段 |
|---|---:|---|
| `requested_amount` | 元 | `LoanInput.requested_amount` |
| `loan_term` | 月 | `LoanInput.loan_term` |
| `operating_years` | 年 | `LoanInput.operating_years` |
| `monthly_revenue` | 元/月 | `LoanInput.monthly_revenue` |
| `monthly_fixed_cost` | 元/月 | `LoanInput.monthly_fixed_cost` |
| `overdue_count_2yr` | 次 | `LoanInput.overdue_count_2yr` |

旧字段仅在后端保留过渡兼容，不再出现在 Agent Tool Schema 中。

## 知识库真实口径

- 银行产品知识库：15 家。
- 银行评估引擎：30 家。
- 国家级政策：18 条。
- 地方政策：24 条。
- 教学案例：30 个基础案例 + 20 个增强案例。
- 企业画像库：1100 家教学画像，不是真实征信数据。

## 固定问题对应工具

1. “我开餐饮店2年，月流水6万，想贷20万，可以吗？” → `evaluate_loan`
2. “A级纳税企业适合推荐什么银行？” → `search_banks` + `evaluate_loan`
3. “有过逾期还能贷款吗？” → `get_credit_tolerance` + `search_cases`
4. “广东制造业小微企业有什么政策支持？” → `search_policies`
5. “帮我查某企业贷款可行性。” → `search_enterprise`

## 自动测试

```bash
cd 后端服务
python -m unittest discover -s tests -p "test_*.py" -v
```

测试覆盖：字段 Schema、贷款评估输出、同步/异步工具执行、中文政策检索、行业别名、无 Key 报错以及模拟 LLM Function Call 完整循环。

当前回归测试共 11 项，全部通过。包含前端优先使用的 `/api/chat/stream` 必须复用 Function Call Agent 的集成测试。真实 DeepSeek 端到端测试需在本地 `.env` 配置有效 Key 后运行。
