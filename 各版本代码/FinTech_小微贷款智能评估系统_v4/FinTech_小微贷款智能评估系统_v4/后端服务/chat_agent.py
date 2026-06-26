"""
智能对话Agent — 基于知识库的小微贷款顾问
支持: 风险评估咨询 / 贷款要求解答 / 银行选择建议 / 政策解读
"""

import json
import os
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

# ============================================================
# 知识库加载
# ============================================================
KNOWLEDGE_BASE = {
    "bank_products": {},
    "policy_rules": [],
    "industry_rules": [],
    "rejection_factors": [],
    "credit_requirements": [],
    "tax_rules": [],
    "macro_stats": {},
    "training_cases": [],
    "feature_engineering": "",
    "data_semantics": "",
}

def load_knowledge_base(base_dir: str = None):
    """Load all knowledge base files."""
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), "..", "Agent整合构建", "Agent整合构建")

    # Try multiple paths — prioritize the corrected agent_kb
    paths_to_try = [
        os.path.join(os.path.dirname(__file__), "agent_kb"),
        base_dir,
        "E:/金融科技/Agent整合构建_修正版/Agent整合构建/Agent知识库",
        "E:/金融科技/Agent整合构建/Agent整合构建/Agent知识库",
    ]

    for path in paths_to_try:
        if os.path.exists(path):
            base_dir = path
            break

    # Load bank products JSON
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            full_path = os.path.join(root, f)
            try:
                if '银行产品数据库' in f and f.endswith('.json'):
                    with open(full_path, 'r', encoding='utf-8') as fh:
                        KNOWLEDGE_BASE["bank_products"] = json.load(fh)
                elif '宏观统计' in f and f.endswith('.json'):
                    with open(full_path, 'r', encoding='utf-8') as fh:
                        KNOWLEDGE_BASE["macro_stats"] = json.load(fh)
                elif '政策规则知识库' in f:
                    KNOWLEDGE_BASE["policy_rules"] = _read_csv_lines(full_path)
                elif '行业准入' in f:
                    KNOWLEDGE_BASE["industry_rules"] = _read_csv_lines(full_path)
                elif '贷款被拒因子' in f:
                    KNOWLEDGE_BASE["rejection_factors"] = _read_csv_lines(full_path)
                elif '征信要求分级' in f:
                    KNOWLEDGE_BASE["credit_requirements"] = _read_csv_lines(full_path)
                elif '纳税等级' in f:
                    KNOWLEDGE_BASE["tax_rules"] = _read_csv_lines(full_path)
                elif '教学案例库' in f:
                    KNOWLEDGE_BASE["training_cases"] = _read_csv_lines(full_path)
                elif '特征工程方案' in f:
                    with open(full_path, 'r', encoding='utf-8') as fh:
                        KNOWLEDGE_BASE["feature_engineering"] = fh.read()
                elif '数据语义' in f:
                    with open(full_path, 'r', encoding='utf-8') as fh:
                        KNOWLEDGE_BASE["data_semantics"] = fh.read()
                elif '2026政策补贴' in f:
                    KNOWLEDGE_BASE["policy_subsidies"] = _read_csv_lines(full_path)
            except Exception as e:
                pass  # Skip files that can't be read
    return KNOWLEDGE_BASE


def _read_csv_lines(path: str) -> List[str]:
    """Read CSV file and return line strings."""
    lines = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
    except:
        pass
    return lines


# ============================================================
# 核心对话引擎
# ============================================================

# 多轮对话上下文记忆
@dataclass
class ChatSession:
    session_id: str
    history: List[Dict[str, str]] = field(default_factory=list)
    enterprise_profile: Dict = field(default_factory=dict)
    last_topic: str = ""

# 存储活跃会话
_active_sessions: Dict[str, ChatSession] = {}


def get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _active_sessions:
        _active_sessions[session_id] = ChatSession(session_id=session_id)
    return _active_sessions[session_id]


# ============================================================
# 意图识别 + 知识检索
# ============================================================

TOPIC_KEYWORDS = {
    "风险评估": ["风险", "评分", "信用", "征信", "违约", "逾期", "评估", "通过率", "能不能贷", "贷不到"],
    "贷款条件": ["条件", "要求", "门槛", "资质", "需要什么", "准备什么", "材料", "手续", "营业执照"],
    "银行选择": ["哪家银行", "推荐", "选择", "哪个好", "对比", "利率", "额度", "期限"],
    "政策补贴": ["政策", "贴息", "补贴", "政府", "优惠", "担保", "支持", "创业贷"],
    "行业准入": ["行业", "能不能做", "限制", "禁止", "可以贷吗"],
    "利率额度": ["利率多少", "额度多少", "利息", "能贷多少", "多少钱"],
    "改善建议": ["怎么提高", "改善", "优化", "提升", "建议", "怎么办"],
    "纳税相关": ["纳税", "税务", "税", "发票", "A级", "B级"],
    "信用违约": ["失信", "黑名单", "被执行人", "处罚", "联合惩戒", "限制高消费", "失信名单", "违法", "公示", "不良记录", "违约记录"],
    "信用修复": ["修复", "移出", "移除", "恢复", "消除", "洗白", "宽限期", "删除", "信用恢复", "经营异常名录"],
    "企业自查": ["自查", "检查", "红灯", "预警", "隐患", "风险点", "贷款前", "整改", "怎么准备"],
    "还款测算": ["月供", "还款", "每月", "等额本息", "利息多少", "总共还", "还款压力", "能还上吗", "还不起", "月还款"],
    "贷款方案": ["方案", "策略", "规划", "分期", "先贷多少", "借多少合", "怎么借", "融资计划", "分几次", "组合"],
}


def identify_topic(query: str) -> str:
    """Identify the topic of the user query."""
    scores = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query)
        if score > 0:
            scores[topic] = score

    if not scores:
        return "综合咨询"

    return max(scores, key=scores.get)


def extract_enterprise_info(query: str, session: ChatSession) -> Dict:
    """Extract enterprise information from query and session context."""
    info = dict(session.enterprise_profile)

    # Extract amounts
    amount_match = re.search(r'(\d+)\s*[万元]', query)
    if amount_match:
        info['mentioned_amount'] = int(amount_match.group(1))

    # Extract years
    year_match = re.search(r'(\d+)\s*年', query)
    if year_match:
        info['mentioned_years'] = int(year_match.group(1))

    # Extract industry
    industries = ['制造', '零售', '餐饮', '建筑', '农业', '科技', '服务', '电商', '物流']
    for ind in industries:
        if ind in query:
            info['mentioned_industry'] = ind
            break

    # Check if asking about specific bank
    banks = ['工商', '建设', '农业', '中国银行', '交通', '邮储', '招商', '中信', '平安', '民生', '兴业', '浦发', '光大', '微众', '网商']
    for bank in banks:
        if bank in query:
            info['mentioned_bank'] = bank
            break

    # Update session
    session.enterprise_profile.update(info)
    return info


# ============================================================
# 响应生成
# ============================================================

def generate_response(query: str, session_id: str = "default") -> str:
    """Main entry point: generate AI response to user query."""
    session = get_or_create_session(session_id)
    session.history.append({"role": "user", "content": query})

    topic = identify_topic(query)
    info = extract_enterprise_info(query, session)
    session.last_topic = topic

    # Route to specific handler
    if topic == "风险评估":
        response = _handle_risk_assessment(query, info, session)
    elif topic == "贷款条件":
        response = _handle_loan_requirements(query, info, session)
    elif topic == "银行选择":
        response = _handle_bank_selection(query, info, session)
    elif topic == "政策补贴":
        response = _handle_policy_subsidies(query, info, session)
    elif topic == "行业准入":
        response = _handle_industry_access(query, info, session)
    elif topic == "利率额度":
        response = _handle_rate_amount(query, info, session)
    elif topic == "改善建议":
        response = _handle_improvement_advice(query, info, session)
    elif topic == "纳税相关":
        response = _handle_tax_related(query, info, session)
    elif topic == "信用违约":
        response = _handle_credit_default(query, info, session)
    elif topic == "信用修复":
        response = _handle_credit_repair(query, info, session)
    elif topic == "企业自查":
        response = _handle_preloan_check(query, info, session)
    elif topic == "还款测算":
        response = _handle_repayment_calc(query, info, session)
    elif topic == "贷款方案":
        response = _handle_loan_plan(query, info, session)
    else:
        response = _handle_general(query, info, session)

    session.history.append({"role": "assistant", "content": response})
    return response


def _handle_risk_assessment(query: str, info: Dict, session: ChatSession) -> str:
    """Handle risk assessment related queries."""
    lines = [
        "🔍 **风险评估分析**\n",
        "根据中国银行业小微企业贷款审批实践，影响您贷款通过率的核心风险因素包括：\n",
        "### 📊 五大核心风险维度\n",
        "1. **征信记录** (权重最高，约30%): 近2年逾期次数是最关键的指标。国有大行通常要求≤3次，股份行和中小银行≤6次。存在历史违约记录将导致通过率大幅降低。\n",
        "2. **经营流水** (约25%): 银行需要通过稳定的经营流水验证您的真实还款能力。建议保持至少6个月连续银行流水。\n",
        "3. **抵押/担保** (约20%): 拥有房产或其他有效抵押物可显著提升通过率。无抵押的纯信用贷款额度通常不超过年营收的40%。\n",
        "4. **经营年限** (约15%): 成立1年以上是大多数银行的底线要求，3年以上经营记录开始具备明显优势。\n",
        "5. **行业与纳税** (约10%): 纳税A/B级企业享受银税贷绿色通道；部分行业（如房地产、产能过剩）面临额外限制。\n",
    ]

    # Add contextual advice
    if info.get('mentioned_years'):
        years = info['mentioned_years']
        if years < 1:
            lines.append(f"⚠️ 您提到的{years}年经营时间不足1年，大多数国有大行无法准入。建议优先考虑邮储银行（门槛最低）或互联网银行（如网商银行仅需6个月）。\n")
        elif years < 3:
            lines.append(f"💡 {years}年经营时间处于银行审批的\"观察期\"。建议积累更长的经营记录，同时确保流水和征信良好，以提高通过率。\n")
        else:
            lines.append(f"✅ {years}年经营时间已越过银行\"三年敏感期\"，在经营年限维度具备良好优势。\n")

    if info.get('mentioned_industry'):
        ind = info['mentioned_industry']
        risky_industries = ['房地产', '娱乐', '采矿', '金融']
        if ind in risky_industries:
            lines.append(f"⚠️ {ind}行业在银行审批中属于审慎准入或限制行业，通过率可能偏低。\n")

    lines.append("\n💬 您可以告诉我更多关于您企业的具体情况（经营年限、月营收、是否有房产、征信状况等），我可以给出更精准的评估。")
    return "\n".join(lines)


def _handle_loan_requirements(query: str, info: Dict, session: ChatSession) -> str:
    """Handle loan requirement queries."""
    bank = info.get('mentioned_bank', '')

    lines = ["📋 **贷款申请核心要求**\n"]

    if bank:
        lines.append(f"### {bank}的小微企业贷款要求：\n")
        # Find bank info
        bank_data = None
        banks_list = KNOWLEDGE_BASE.get("bank_products", {}).get("banks", [])
        for b in banks_list:
            if bank in b.get('name', ''):
                bank_data = b
                break

        if bank_data:
            req = bank_data.get('requirements', {})
            lines.append(f"- **产品名称**: {bank_data.get('product_name', '小微贷款')}")
            lines.append(f"- **最低经营年限**: {req.get('min_business_years', 'N/A')}年")
            lines.append(f"- **最高额度**: 信用{bank_data.get('max_amount_credit', 'N/A')}万 / 抵押{bank_data.get('max_amount_mortgage', 'N/A')}万")
            lines.append(f"- **利率范围**: {bank_data.get('min_interest_rate', 'N/A')}%~{bank_data.get('max_interest_rate', 'N/A')}%")
            lines.append(f"- **适合对象**: {bank_data.get('target_enterprise', '各类小微企业')}")
        else:
            lines.append(f"暂无{bank}的详细数据，建议访问该行官网或咨询网点。\n")
    else:
        lines.append("### 小微企业贷款的通用申请条件：\n")
        lines.append("**基础材料（所有银行强制要求）:**")
        lines.append("1. 营业执照正副本（经营主体合规证明）")
        lines.append("2. 法定代表人及配偶身份证")
        lines.append("3. 经营场所租赁合同 + 近3个月水电费单据")
        lines.append("4. 近6个月对公账户或主要结算账户银行流水")
        lines.append("")
        lines.append("**加分材料（提高通过率）:**")
        lines.append("5. 近2年纳税证明（A/B级可走银税贷通道）")
        lines.append("6. 房产证/车辆登记证（抵押增信）")
        lines.append("7. 上下游大客户合作协议（证明业务稳定性）")
        lines.append("")
        lines.append("**关键红线（直接拒贷）:**")
        lines.append("- 当前存在逾期未结清记录")
        lines.append("- 贷款五级分类为关注/次级/可疑/损失类")
        lines.append("- 企业被列入失信被执行人名单")

    lines.append("\n💬 如果您想了解特定银行的具体要求，可以直接问我，如\"工商银行的要求是什么？\"")
    return "\n".join(lines)


def _handle_bank_selection(query: str, info: Dict, session: ChatSession) -> str:
    """Handle bank selection queries."""
    lines = ["🏦 **银行选择建议**\n"]

    # Determine user profile
    has_property = '房产' in query or '抵押' in query or '房子' in query
    is_startup = '初创' in query or '刚成立' in query or '新' in query
    is_ecommerce = '电商' in query or '淘宝' in query or '线上' in query or '网店' in query
    has_good_tax = '纳税' in query and ('A' in query or 'B' in query or '好' in query)
    has_bad_credit = '逾期' in query or '征信不好' in query or '信用差' in query

    lines.append("根据您的情况，推荐以下银行：\n")

    if has_property:
        lines.append("🏠 **有房产抵押 → 优先选择利率最低的银行:**")
        lines.append("- 🥇 中信银行 房抵e贷: 利率2.15%起，最高3000万，20年")
        lines.append("- 🥈 交通银行 经营贷: 利率2.20%起，最高1000万，10年")
        lines.append("- 🥉 招商银行 招捷贷: 利率2.35%起，最高3000万，20年（可二押）\n")

    if is_startup:
        lines.append("🌱 **初创企业 → 门槛最低的银行:**")
        lines.append("- 🥇 邮储银行: 门槛最亲民，0.5年起，县域覆盖强")
        lines.append("- 🥈 平安银行: 股份行中门槛最低，纯信用最高300万")
        lines.append("- 🥉 网商银行: 执照满6个月即可，支付宝生态整合\n")

    if is_ecommerce:
        lines.append("🛒 **电商/线上经营 → 互联网银行优势明显:**")
        lines.append("- 🥇 微众银行 微业贷: 通过率超80%，依托腾讯生态数据")
        lines.append("- 🥈 网商银行 网商贷: 支付宝生态，淘宝天猫商户首选\n")

    if has_good_tax:
        lines.append("📊 **纳税优质 → 银税贷通道:**")
        lines.append("- 建设银行 云税贷: 凭纳税记录最高500万，3.00%起")
        lines.append("- 中国银行 银税贷: 最高500万，≤3.6%\n")

    if has_bad_credit:
        lines.append("⚠️ **征信有瑕疵 → 选择容忍度高的银行:**")
        lines.append("- 建设银行: 接受历史逾期≤6次")
        lines.append("- 邮储银行: 对信用瑕疵相对包容")
        lines.append("- 建议先通过按时还款改善征信，6-12个月后再申请\n")

    if not any([has_property, is_startup, is_ecommerce, has_good_tax, has_bad_credit]):
        lines.append("💡 **综合推荐策略:**")
        lines.append("1. 同时向2-3家银行提交申请，提高整体获批概率")
        lines.append("2. 先申请通过率最高的（邮储/平安），积累信贷记录后再申请利率更低的")
        lines.append("3. 国有大行利率低但审批严，股份行/城商行更灵活\n")

    lines.append("💬 告诉我您企业的具体情况，我可以给出更精准的银行推荐。")
    return "\n".join(lines)


def _handle_policy_subsidies(query: str, info: Dict, session: ChatSession) -> str:
    """Handle policy and subsidy queries."""
    return """📜 **2026年小微企业贷款政策与补贴**

### 🔥 主要贴息政策
- **服务业贴息延长至2026年底**: 覆盖餐饮住宿、文旅、数字、绿色、零售等11个领域
- **单户贴息上限提高至1000万元** (原100万)
- **首年贴息1个百分点**: 部分行业利率可降至"1字头"

### 🎯 创业担保贷款
- **补贴后最低利率1.3%**: 额度300万，期限1-2年
- **适用对象**: 返乡农民工、大学生、退役军人、就业困难人员

### 🏛️ 政府增信机制
- **政府性融资担保**: 国家融担基金→省级再担保→市级担保三级体系
- **省农担**: 担保费率<1%，服务三农主体
- **风险补偿基金**: 多地设立小微贷款风险补偿池

### 💡 申请建议
- 联系当地工信局/金融办了解本地区具体政策
- 符合条件的先申请创业担保贷（利率最低）
- 关注当地财政贴息申报窗口期（通常每季度一次）

💬 如果您想了解特定行业或地区的政策，请告诉我。"""


def _handle_industry_access(query: str, info: Dict, session: ChatSession) -> str:
    """Handle industry access queries."""
    industry = info.get('mentioned_industry', '')

    lines = ["🏭 **行业准入分析**\n"]

    if industry:
        safe_industries = ['制造', '零售', '科技', '服务', '餐饮', '农业', '物流', '电商']
        restricted = ['房地产', '娱乐', '采矿', '金融', '钢铁', '水泥']

        if industry in safe_industries:
            lines.append(f"✅ **{industry}行业**属于银行积极支持的行业，无准入限制。\n")
            if industry == '制造':
                lines.append("制造业是普惠金融重点支持领域，享受专项贷款产品和利率优惠。")
            elif industry == '科技':
                lines.append("科技企业可申请\"专精特新\"专项贷款，建设银行善新贷最高1000万。")
            elif industry == '农业':
                lines.append("三农主体享受省农担增信、创业担保贷等政策红利。")
        elif industry in restricted:
            lines.append(f"⚠️ **{industry}行业**在银行审批中存在限制：\n")
            lines.append("- 属于审慎准入或严格限制行业")
            lines.append("- 通过率可能偏低，且利率上浮")
            lines.append("- 建议提供更多增信措施（抵押、担保）")
        else:
            lines.append(f"关于{industry}行业，银行一般根据具体子行业和经营模式评估。\n")

    lines.append("### 📋 银行行业准入分级:")
    lines.append("- ✅ **积极支持**: 制造业、批发零售、信息技术、农业、交通运输")
    lines.append("- ⚠️ **审慎准入**: 建筑业(需资质)、贸易(需真实背景)、文化体育")
    lines.append("- 🚫 **严格限制**: 房地产(非自用)、产能过剩、高污染")
    lines.append("- ❌ **禁止准入**: 非法行业(赌博、色情、毒品等)")

    return "\n".join(lines)


def _handle_rate_amount(query: str, info: Dict, session: ChatSession) -> str:
    """Handle rate and amount queries."""
    amount = info.get('mentioned_amount', 0)

    lines = ["💰 **利率与额度分析**\n"]
    lines.append("### 2026年市场行情:")
    lines.append("- **国有大行**: 2.20%~3.20% (利率最低)")
    lines.append("- **股份制银行**: 2.60%~5.00% (灵活度高)")
    lines.append("- **城商行**: 3.30%~6.00% (地域性强)")
    lines.append("- **互联网银行**: 3.60%~18.00% (大数据风控，利率区间大)")
    lines.append("")
    lines.append("### 额度计算公式 (银行通用):")
    lines.append("- **信用贷款**: ≤ 月营收 × 40% × 12个月")
    lines.append("- **抵押贷款**: ≤ 房产估值 × 65%")
    lines.append("- **最低额度**: 通常10万元起")
    lines.append("")

    if amount > 0:
        if amount <= 50:
            lines.append(f"💡 您提到的{amount}万属于小额贷款，纯信用即可覆盖。推荐：浦发银行(120万)、邮储银行(200万)、平安银行(300万)")
        elif amount <= 300:
            lines.append(f"💡 {amount}万额度的选择空间较大。有房产可选中信/招行（利率2.15%起），无房产可选建行/平安纯信用。")
        else:
            lines.append(f"💡 {amount}万属于较大额度，通常需要抵押物。推荐：中信/招行（最高3000万）、建行科创贷（1000万）")

    return "\n".join(lines)


def _handle_improvement_advice(query: str, info: Dict, session: ChatSession) -> str:
    """Handle improvement advice queries."""
    return """📈 **提高贷款通过率的系统方案**

### 🔧 短期改善 (1-3个月)
1. **归集经营流水**: 将微信/支付宝/现金收入统一存入对公账户
2. **结清小额逾期**: 优先处理近2年的逾期记录
3. **补办营业执照**: 无照经营是银行一票否决项
4. **规范发票管理**: 降低废票率，提高财务规范性

### 📊 中期优化 (3-12个月)
5. **提升纳税等级**: 按时申报纳税，争取A/B级
6. **建立征信记录**: 申请小额信用卡或贷款并按时还款
7. **积累对公流水**: 保持6个月以上连续稳定的对公流水记录
8. **分散客户结构**: 降低单一客户依赖度

### 🎯 长期战略 (1-3年)
9. **增加固定资产**: 购置可用于抵押的经营性房产
10. **拓展上下游**: 扩大供应商和客户数量，增强抗风险能力
11. **关注政策窗口**: 及时申请贴息、担保等政策支持

### 💡 针对性建议
- **缺抵押物** → 先申纯信用产品，积累记录后再申抵押贷
- **征信瑕疵** → 建设银行/邮储银行容忍度更高
- **经营时间短** → 互联网银行(6个月起)或农商行更友好
- **行业受限** → 多提供真实交易合同，证明业务合规

💬 告诉我您具体想改善哪个方面，我可以给出更详细的建议。"""


def _handle_tax_related(query: str, info: Dict, session: ChatSession) -> str:
    """Handle tax related queries."""
    return """📊 **纳税与贷款审批**

### 纳税等级评分规则
| 等级 | 评分 | 银行接受度 | 可申请产品 |
|------|------|-----------|-----------|
| **A级** | 优秀 | 所有银行欢迎 | 银税贷/科创贷/低息经营贷 |
| **B级** | 良好 | 绝大多数接受 | 银税贷/经营快贷/云税贷 |
| **M级** | 新设 | 部分接受 | 微业贷/网商贷/邮储小微贷 |
| **C级** | 一般 | 需要增信 | 需提供抵押或担保 |
| **D级** | 较差 | 很难通过 | 建议先改善纳税记录 |

### 🎯 银税贷产品推荐
- **建设银行 云税贷**: 纳税≥5000元可申请，最高500万，3.00%起
- **中国银行 银税贷**: 纳税A/B级，最高500万，≤3.6%
- **工商银行 经营快贷**: 纳税≥2万元，A/B/M级，最高300万

### 💡 改善纳税等级建议
1. 按时准确申报各项税种
2. 保持连续纳税记录
3. 控制废票率在5%以下
4. 配合税务稽查和评估

纳税A/B级企业在银行审批中享有明显的\"绿色通道\"优势。"""


def _handle_credit_default(query: str, info: Dict, session: ChatSession) -> str:
    """Handle credit default / blacklist related queries using official data."""
    from default_knowledge import (
        OFFICIAL_SOURCES, CREDIT_PENALTY_TIERS, TOP_PENALTIES,
        DEFAULT_ROOT_CAUSES, QUICK_STATS,
    )

    lines = ["🚨 **企业信用违约 — 官方数据与影响分析**\n"]
    lines.append("> 数据来源：最高人民法院 · 市场监管总局 · 央行征信中心 · 惠誉博华\n")

    # 关键统计数据
    lines.append("### 📊 核心数据速览\n")
    lines.append(f"- 2024年新纳入失信名单：**245.7万人次**（10年来首次下降）")
    lines.append(f"- 信用修复回归市场：**282.1万人次**（首次超过新纳入人数）")
    lines.append(f"- 经营异常名录：**1,138.8万户**（累计）")
    lines.append(f"- 严重违法失信企业：**1.34万户**")
    lines.append(f"- 联合惩戒：**44个部门 + 55项惩戒措施**")
    lines.append(f"- 2024年银行不良核销规模：**1.33万亿元**（创七年新高）\n")

    # 失信分级
    lines.append("### ⚖️ 失信行为三级分级（2025年4月起）\n")
    for t in CREDIT_PENALTY_TIERS:
        lines.append(f"**{t['级别']}**：{t['惩戒力度']}")
        lines.append(f"- 适用：{t['适用情形']}")
        if '宽限期' in t:
            lines.append(f"- 🟢 宽限期：{t['宽限期']}，可替代纳入名单")
        lines.append("")

    # 十大核心惩戒
    lines.append("### 🚫 十大核心惩戒措施\n")
    for i, p in enumerate(TOP_PENALTIES[:8], 1):
        lines.append(f"{i}. **{p['领域']}**：{p['措施']}")
    lines.append("")

    # 对企业贷款的具体影响
    lines.append("### 🔴 对贷款申请的直接影响\n")
    lines.append("- **被列入失信名单** → 所有银行直接拒贷，无一例外")
    lines.append("- **经营异常名录** → 国有大行直接拒贷，部分中小银行可能接受（需先移出）")
    lines.append("- **五级分类非正常** → 全部银行拒贷")
    lines.append("- **有未结清逾期** → 必须先结清才能申请")
    lines.append("- **近2年逾期>6次** → 多数银行拒贷（建行/邮储可能有例外）")
    lines.append("- **法定代表人被限高** → 企业贷款同样受影响\n")

    # 违约深层原因
    lines.append("### 📉 小微企业违约四大深层原因\n")
    for cause in DEFAULT_ROOT_CAUSES:
        lines.append(f"**{cause['大类']}**：{'、'.join(cause['具体原因'][:2])}")
        lines.append(f"  ⚠️ 预警：{cause['预警信号']}\n")

    # 官方查询入口
    lines.append("### 🔍 官方查询入口\n")
    lines.append("- 失信被执行人：zxgk.court.gov.cn（中国执行信息公开网）")
    lines.append("- 企业信用信息：gsxt.gov.cn（国家企业信用信息公示系统）")
    lines.append("- 企业信用报告：pbccrc.org.cn（央行征信中心）")
    lines.append("- 裁判文书：wenshu.court.gov.cn（中国裁判文书网）\n")

    lines.append("💬 如果您想了解具体的信用修复方法，可以问我\"如何修复企业信用？\"")

    return "\n".join(lines)


def _handle_credit_repair(query: str, info: Dict, session: ChatSession) -> str:
    """Handle credit repair related queries."""
    from default_knowledge import CREDIT_REPAIR_MECHANISMS, BUSINESS_ABNORMAL_TYPES

    lines = ["🔧 **企业信用修复 — 官方渠道操作指南**\n"]
    lines.append("> 根据最高人民法院2025年新规和市场监管总局信用修复机制\n")

    # 修复机制
    lines.append("### 📋 五大信用修复机制\n")
    for m in CREDIT_REPAIR_MECHANISMS:
        lines.append(f"**{m['机制']}**")
        lines.append(f"- 条件：{m['条件']}")
        lines.append(f"- 流程：{m['流程']}")
        lines.append(f"- 效果：{m['效果']}")
        if '宽限期' in m:
            lines.append(f"- 🟢 {m['宽限期']}")
        lines.append("")

    # 经营异常移出
    lines.append("### 📍 经营异常名录移出指南\n")
    for t in BUSINESS_ABNORMAL_TYPES:
        lines.append(f"**{t['类型']}**：{t['移出条件']}")
        lines.append(f"  风险提示：{t['风险提示']}\n")

    # 关键提醒
    lines.append("### ⚠️ 重要提醒\n")
    lines.append("- 🚫 **不存在\"征信修复\"中介**！征信领域没有\"修复\"概念，只有正规异议和投诉渠道")
    lines.append("- ✅ 所有信用修复必须通过**官方渠道**，不收取费用")
    lines.append("- ✅ 2024年已有**3207.2万户**经营主体成功修复信用")
    lines.append("- ✅ 2025年新规：有前景的困难企业可获**1-3个月宽限期**")
    lines.append("- ✅ 履行义务后法院须在**3个工作日内**删除失信信息")
    lines.append("- ✅ 信用等级**每半年动态调整**一次\n")

    lines.append("💬 如果您想了解贷款前的完整自查清单，可以问我\"贷款前需要自查什么？\"")

    return "\n".join(lines)


def _handle_preloan_check(query: str, info: Dict, session: ChatSession) -> str:
    """Handle pre-loan self-check and risk identification queries."""
    from default_knowledge import PRE_LOAN_CHECKLIST

    lines = ["📋 **贷款前企业自查清单 — 7大关键风险点**\n"]
    lines.append("> 在向银行提交贷款申请前，请逐项排查以下风险点。")
    lines.append("> 存在红灯信号的，建议**先整改后申请**，避免浪费征信查询次数。\n")

    for i, item in enumerate(PRE_LOAN_CHECKLIST, 1):
        lines.append(f"### {i}. {item['检查项']}")
        lines.append(f"📌 **自查路径**：{item['自查内容']}")

        for signal in item['红灯信号']:
            lines.append(f"  🔴 {signal}")

        lines.append(f"💡 **整改建议**：{item['整改建议']}")
        lines.append("")

    # 总结
    lines.append("---\n")
    lines.append("### 🎯 自查结果判断\n")
    lines.append("- **0个红灯** → ✅ 资质优异，可同时向2-3家银行提交申请")
    lines.append("- **1-2个红灯** → ⚠️ 建议先针对性整改，1-3个月后再申请")
    lines.append("- **3-4个红灯** → 🔴 通过率极低，建议按整改清单系统优化，3-6个月后再尝试")
    lines.append("- **5个以上红灯** → 🚫 当前不具备贷款条件，需要从根本上改善经营状况\n")

    lines.append("### 💡 贷款前策略建议\n")
    lines.append("1. **不要同时向多家银行申请**：每次申请都会产生征信查询记录，查询过多反而降低通过率")
    lines.append("2. **先自查后申请**：提前发现问题并整改，比被银行拒贷后再补救效果好得多")
    lines.append("3. **利用宽限期**：如被列入失信名单但企业有前景，可向法院申请1-3个月宽限期")
    lines.append("4. **善用信用修复**：2024年修复人数已超过新纳入人数，信用修复通道畅通")
    lines.append("5. **从小额贷款开始**：先申请小额信用贷款建立良好记录，再逐步申请大额\n")

    lines.append("💬 如果您发现具体问题需要解决建议，请直接告诉我，如\"征信有一次逾期怎么办？\"")

    return "\n".join(lines)


def _handle_repayment_calc(query: str, info: Dict, session: ChatSession) -> str:
    """Handle repayment calculation queries."""
    amount = info.get('mentioned_amount', 0)

    lines = ["💰 **还款测算分析**\n"]

    # 如果没有具体金额，用常见金额演示
    if amount == 0:
        # Check if there's enterprise data in session
        ep = session.enterprise_profile
        revenue = ep.get('monthly_revenue', 0)
        if isinstance(revenue, (int, float)) and revenue > 0:
            amount = int(revenue * 0.3)  # suggest 30% of monthly revenue as loan amount
        else:
            amount = 50000  # default 5万

    lines.append(f"以申请 **{amount/10000:.1f}万元** 贷款为例：\n")

    # 不同期限的还款测算
    rates = [3.5, 5.0, 8.0]
    terms = [12, 24, 36]
    lines.append("| 年利率 | 期限 | 月供(元) | 总利息(元) | 总还款(元) |")
    lines.append("|--------|------|----------|------------|------------|")
    for rate in rates:
        for term in terms:
            monthly_rate = rate / 100 / 12
            if monthly_rate > 0:
                emi = amount * monthly_rate * (1 + monthly_rate) ** term / ((1 + monthly_rate) ** term - 1)
            else:
                emi = amount / term
            total = emi * term
            interest = total - amount
            lines.append(f"| {rate}% | {term}个月 | {emi:,.0f} | {interest:,.0f} | {total:,.0f} |")

    lines.append("")
    lines.append("### 📊 还款安全线\n")
    lines.append("- **安全区间**：月供 < 月净收入的30%")
    lines.append("- **警戒区间**：月供占净收入30%-50%")
    lines.append("- **危险区间**：月供 > 净收入50%，银行大概率拒贷\n")

    lines.append("### 💡 降低月供的方法\n")
    lines.append("1. **拉长期限**：从12个月延至36个月，月供可降低约60%")
    lines.append("2. **降低额度**：减少申请金额，保留部分资金通过利润积累解决")
    lines.append("3. **找低利率银行**：国有大行利率比互联网银行低2-3个百分点")
    lines.append("4. **先息后本**：部分银行支持前6-12个月只还利息\n")

    lines.append("💬 告诉我具体的申请金额和期限，我可以帮您精确计算月供。")
    return "\n".join(lines)


def _handle_loan_plan(query: str, info: Dict, session: ChatSession) -> str:
    """Handle loan strategy/planning queries."""
    return """📋 **小微企业贷款策略方案**

### 🎯 根据企业阶段选择策略

**阶段一：初创期 (经营<1年)**
- 策略：先小额后大额，建立信用记录
- 推荐：网商/微众（线上纯信用）→ 邮储/平安（小额经营贷）
- 额度：先申请5-10万，按时还款后再提额
- 目标：积累6-12个月良好信贷记录

**阶段二：成长期 (经营1-3年)**
- 策略：多渠道组合融资
- 推荐组合：国有大行(低利率)+股份行(灵活)+城商行(本地化)
- 额度：申请年营收的20-30%
- 操作：同时向2-3家银行提交，但不超3家(避免征信查询过多)

**阶段三：成熟期 (经营3年+)**
- 策略：优化融资结构，降低综合成本
- 推荐：中信/招行(抵押贷，利率最低)+建行云税贷(纳税企业)
- 额度：可申请年营收的30-50%
- 操作：用房产抵押置换前期高利率信用贷款

### 🚫 融资红线
- 月还款总额不超过月净收入的40%
- 不同时向超过3家银行申请
- 不借高利贷/套路贷来偿还银行贷款
- 不被"资质包装"中介忽悠

### 📅 融资时间线建议
| 时间 | 行动 |
|------|------|
| T-6月 | 归集银行流水，规范发票管理 |
| T-3月 | 结清逾期，改善征信 |
| T-1月 | 自查7大风险点(问我"贷款前自查") |
| T时刻 | 向2-3家目标银行提交申请 |
| T+1月 | 获批后按时还款，建立良好记录 |

💬 告诉我您的企业当前处于哪个阶段，我可以给出更针对性的方案。"""


def _handle_general(query: str, info: Dict, session: ChatSession) -> str:
    """Handle general/unclassified queries."""
    # Check for greetings
    greetings = ['你好', '您好', 'hi', 'hello', '嗨', '在吗', '帮助', 'help']
    if any(g in query.lower() for g in greetings):
        return """👋 **您好！我是小微贷款智能顾问Agent**

基于官方权威数据（最高人民法院/市场监管总局/央行征信中心/惠誉博华），我可以帮您：

🏦 **风险评估** — 分析贷款通过概率，识别风险点
📋 **贷款条件** — 各银行的申请要求和所需材料
🏧 **银行选择** — 根据您的情况推荐最合适的银行
🚨 **信用违约** — 失信名单影响、处罚措施、违约原因分析
🔧 **信用修复** — 官方修复渠道、操作指南、宽限期政策
📋 **企业自查** — 贷款前7大风险点排查清单+整改建议
💰 **利率额度** — 市场行情和预期额度
📜 **政策补贴** — 最新贴息和补贴政策
📈 **改善建议** — 系统性提升通过率的方案

💬 **请直接告诉我您的需求，例如：**
- \"我的餐饮店有逾期记录，这对贷款有什么影响？\"
- \"被列入经营异常名录怎么移出？\"
- \"贷款前需要自查哪些方面？\""""

    # General knowledge response
    return """💡 根据您的咨询，以下是一些关键信息：

中国普惠小微贷款市场（2024年末数据）：
- 贷款余额: **32.93万亿元**
- 同比增速: **14.6%**
- 银行数量: 国有6家 + 股份12家 + 城商125家 + 农商约1600家

如果您有具体的贷款需求或疑问，请告诉我更多详情，例如：
- 您的企业经营年限、月营收、所在行业
- 是否有房产/抵押物
- 征信状况如何

这样我可以给出更有针对性的建议。"""


# ============================================================
# 初始化
# ============================================================

# 尝试加载知识库
try:
    load_knowledge_base()
except Exception as e:
    print(f"[ChatAgent] Knowledge base load warning: {e}")
