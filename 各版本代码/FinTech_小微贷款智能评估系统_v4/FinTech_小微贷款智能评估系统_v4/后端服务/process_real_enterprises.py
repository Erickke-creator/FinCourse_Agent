"""
从GitHub真实企业注册数据集提取中小微企业
来源: imhuster/Enterprise-Registration-Data-of-Chinese-Mainland (1000万+条)
提取目标: 1000家以上有代表性的中小微企业
"""

import csv
import json
import os
import random
import re
from collections import Counter
from typing import Dict, List

random.seed(42)

# ============================================================
# 行业关键词映射 (经营范围 → 行业分类)
# ============================================================
INDUSTRY_KEYWORDS = {
    "manufacturing": ["制造","加工","生产","组装","铸造","锻造","模具","机械","五金",
                      "电子","电器","纺织","服装","食品加工","塑料","金属","化工","印刷"],
    "wholesale_retail": ["批发","零售","销售","贸易","商贸","经销","百货","超市",
                         "商店","专卖","连锁"],
    "hospitality_food": ["餐饮","饭店","餐厅","酒店","宾馆","民宿","食堂","快餐",
                         "小吃","烧烤","火锅","烘焙","饮品","茶馆","咖啡馆"],
    "it_tech": ["科技","软件","信息技术","互联网","数据","网络","计算机","程序",
                "系统集成","人工智能","大数据","云计算","物联网","开发"],
    "agriculture": ["农业","种植","养殖","畜牧","水产","林业","农场","合作社",
                    "苗木","花卉","果蔬","茶叶","中药材"],
    "construction": ["建筑","装修","装饰","工程","施工","安装","幕墙","园林",
                     "防水","暖通","钢结构","土建"],
    "transportation": ["运输","物流","货运","快递","配送","仓储","搬家",
                       "冷链","货代","船务"],
    "culture_sports": ["文化","体育","广告","设计","摄影","影视","艺术","娱乐",
                       "传媒","演出","健身","培训","教育咨询"],
    "resident_service": ["家政","保洁","维修","美容","美发","洗染","汽车美容",
                         "宠物","干洗","开锁","家电维修"],
    "healthcare": ["医疗","医院","诊所","口腔","中医","药房","体检","康复",
                   "护理","保健","卫生"],
    "education": ["教育","培训","托管","托育","早教","辅导","技能培训"],
}

# SME注册资本阈值 (万元) — 不同行业的中小微企业标准
SME_CAPITAL_MAX = {
    "manufacturing": 4000, "wholesale_retail": 2000, "hospitality_food": 1000,
    "it_tech": 2000, "agriculture": 1000, "construction": 5000,
    "transportation": 3000, "culture_sports": 1000, "resident_service": 500,
    "healthcare": 1000, "education": 500,
}


def classify_industry(business_scope: str) -> str:
    """根据经营范围分类行业"""
    if not business_scope:
        return "other"
    scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in business_scope)
        if score > 0:
            scores[industry] = score
    if not scores:
        return "other"
    return max(scores, key=scores.get)


def parse_capital(capital_str: str) -> float:
    """解析注册资本字符串为万元"""
    if not capital_str:
        return 50
    try:
        # 去除"万元"等后缀，保留数字
        num_str = re.sub(r'[^0-9.]', '', str(capital_str))
        if not num_str:
            return 50
        val = float(num_str)
        # 如果原始字符串包含"万"，保持不变
        if '万' in str(capital_str):
            return min(val, 50000)
        # 如果原始是元为单位
        if '元' in str(capital_str) and '万' not in str(capital_str):
            return val / 10000
        # 默认视为万元
        return min(val, 50000)
    except:
        return 50


def is_sme(industry: str, capital_wan: float) -> bool:
    """判断是否为中小微企业"""
    max_cap = SME_CAPITAL_MAX.get(industry, 1000)
    return capital_wan <= max_cap


def estimate_revenue(capital_wan: float, industry: str) -> int:
    """根据注册资本估算月营收（基于行业特征）"""
    # 一般营收在资本的1-10倍/年，即0.08-0.8倍/月
    revenue_multipliers = {
        "manufacturing": 0.3, "wholesale_retail": 0.5, "hospitality_food": 0.2,
        "it_tech": 0.4, "agriculture": 0.1, "construction": 0.25,
        "transportation": 0.2, "culture_sports": 0.15, "resident_service": 0.1,
        "healthcare": 0.2, "education": 0.15,
    }
    multiplier = revenue_multipliers.get(industry, 0.2)
    base = capital_wan * multiplier
    # 加入随机波动
    revenue = base * random.uniform(0.5, 2.0)
    # 转为月营收(万元) → 元
    revenue_yuan = int(revenue * 10000)
    return max(10000, min(5000000, revenue_yuan))


def process_enterprise_csv(csv_dir: str) -> List[Dict]:
    """从CSV文件提取中小微企业"""
    smes = []
    used_names = set()
    industry_counts = Counter()

    # 查找CSV文件
    csv_files = []
    for root, _, files in os.walk(csv_dir):
        for f in files:
            if f.endswith('.csv') and not f.startswith('._'):
                csv_files.append(os.path.join(root, f))

    if not csv_files:
        print("No CSV files found!")
        return smes

    print(f"Found {len(csv_files)} CSV files")

    for csv_path in csv_files:
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 提取字段 (处理可能的列名变体)
                    name = row.get('name') or row.get('企业名称') or row.get('company_name', '')
                    if not name or len(name) < 4:
                        continue

                    capital_str = row.get('capital') or row.get('注册资金') or row.get('registered_capital', '50')
                    capital = parse_capital(capital_str)

                    scope = row.get('businessScope') or row.get('经营范围') or row.get('business_scope', '')
                    province = row.get('province') or row.get('所在省份') or row.get('province', '')
                    city = row.get('city') or row.get('地区') or row.get('city', '')
                    if not city and province:
                        city = province

                    # 分类行业
                    industry = classify_industry(scope)
                    if industry == "other":
                        continue

                    # 筛选中小微
                    if not is_sme(industry, capital):
                        continue

                    # 控制每行业数量
                    if industry_counts[industry] >= 120:
                        continue

                    # 避免重复
                    if name in used_names:
                        continue
                    used_names.add(name)

                    industry_counts[industry] += 1
                    revenue = estimate_revenue(capital, industry)

                    smes.append({
                        "name": name,
                        "industry": industry,
                        "region": city or province or "未知",
                        "capital_wan": capital,
                        "scope_snippet": scope[:100] if scope else "",
                        "revenue_monthly": revenue,
                        "years": random.randint(1, 20),
                        "employees": max(1, min(500, int(capital * random.uniform(0.05, 0.5)))),
                        "profit_margin": round(random.uniform(0.05, 0.30), 2),
                        "has_estate": capital > 100 and random.random() < 0.4,
                        "tax_level": random.choice(["A","B","B","M","M","C"]),
                        "has_license": True,
                        "has_bank_flow": random.random() < 0.75,
                        "is_tech": "科技" in (scope or ""),
                        "is_ecommerce": any(kw in (scope or "") for kw in ["电子商务","电商","网上","线上","互联网"]),
                        "credit_ok": random.random() < 0.88,
                        "overdue": int(random.expovariate(1.5)),
                    })

                    if len(smes) >= 1500:
                        break

        except Exception as e:
            print(f"Error processing {csv_path}: {e}")
            continue

        if len(smes) >= 1500:
            break

    return smes


def export_to_enterprise_format(smes: List[Dict], output_path: str):
    """导出为企业搜索数据库格式"""
    lines = []
    for sme in smes:
        # 清理企业名
        name = sme["name"].replace("'", "").replace('"', "").replace('\n', '')[:80]
        desc = f'注册资本{sme["capital_wan"]:.0f}万元，' + sme.get("scope_snippet", "")[:80]
        desc = desc.replace("'", "").replace('"', "")
        risks = []
        if sme["capital_wan"] < 30: risks.append("注册资金规模偏小")
        if sme["years"] < 1: risks.append("成立不足1年")
        if sme["overdue"] >= 3: risks.append(f'{sme["overdue"]}次逾期记录')
        if not sme["has_estate"]: risks.append("无房产抵押")
        if not sme["has_bank_flow"]: risks.append("无对公银行流水")
        if not risks: risks.append("经营正常，风险可控")

        risks_str = json.dumps(risks, ensure_ascii=False)

        lines.append(f'    "{name}": {{')
        lines.append(f'        "industry": "{sme["industry"]}", "region": "{sme["region"]}",')
        lines.append(f'        "years": {sme["years"]}, "employees": {sme["employees"]}, "revenue_monthly": {sme["revenue_monthly"]},')
        lines.append(f'        "profit_margin": {sme["profit_margin"]}, "has_estate": {str(sme["has_estate"])},')
        lines.append(f'        "tax_level": "{sme["tax_level"]}", "has_license": True, "has_bank_flow": {str(sme["has_bank_flow"])},')
        lines.append(f'        "is_tech": {str(sme["is_tech"])}, "is_ecommerce": {str(sme["is_ecommerce"])},')
        lines.append(f'        "credit_ok": {str(sme["credit_ok"])}, "overdue": {sme["overdue"]},')
        lines.append(f'        "description": "{desc}",')
        lines.append(f'        "risk_notes": {risks_str},')
        lines.append(f'    }},')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"Exported {len(smes)} SMEs to {output_path}")


if __name__ == "__main__":
    csv_dir = "real_enterprise_data"
    print(f"Processing CSV files from {csv_dir}...")
    smes = process_enterprise_csv(csv_dir)

    if len(smes) < 100:
        print(f"\nOnly {len(smes)} extracted from CSV — generating supplementary data...")
        # Fall back to generated data for remaining
        from generate_sme_database import generate_smes
        extra = generate_smes(1100 - len(smes))
        for e in extra:
            smes.append({
                "name": e["name"],
                "industry": e["industry"],
                "region": e["region"],
                "capital_wan": random.randint(10, 2000),
                "scope_snippet": "",
                "revenue_monthly": e["revenue_monthly"],
                "years": e["years"],
                "employees": e["employees"],
                "profit_margin": e["profit_margin"],
                "has_estate": e["has_estate"],
                "tax_level": e["tax_level"],
                "has_license": e["has_license"],
                "has_bank_flow": e["has_bank_flow"],
                "is_tech": e["is_tech"],
                "is_ecommerce": e["is_ecommerce"],
                "credit_ok": e["credit_ok"],
                "overdue": e["overdue"],
            })

    print(f"\nTotal SMEs: {len(smes)}")
    industries = Counter(s["industry"] for s in smes)
    for ind, count in sorted(industries.items(), key=lambda x: -x[1]):
        print(f"  {ind}: {count}")

    # Export
    export_to_enterprise_format(smes, "real_smes_output.py")
