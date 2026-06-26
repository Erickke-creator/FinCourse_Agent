"""
程序化生成1000+家真实可搜索的中国中小微企业
基于真实城市/行业分布/经营模式构建
"""

import json
import random
import numpy as np
from typing import Dict, List

random.seed(42)
np.random.seed(42)

# ============================================================
# 1. 真实城市+区县数据 (覆盖全国各省)
# ============================================================
CITIES = [
    ("北京市", ["朝阳区","海淀区","丰台区","通州区","大兴区","昌平区"]),
    ("上海市", ["浦东新区","闵行区","嘉定区","松江区","宝山区","青浦区"]),
    ("广州市", ["天河区","白云区","番禺区","黄埔区","花都区","增城区"]),
    ("深圳市", ["南山区","宝安区","龙岗区","龙华区","光明区","坪山区"]),
    ("杭州市", ["余杭区","滨江区","西湖区","萧山区","拱墅区","临平区"]),
    ("成都市", ["武侯区","高新区","锦江区","青羊区","金牛区","双流区","龙泉驿区"]),
    ("武汉市", ["洪山区","东湖高新区","江岸区","武昌区","江夏区","东西湖区"]),
    ("南京市", ["江宁区","鼓楼区","建邺区","栖霞区","浦口区","雨花台区"]),
    ("苏州市", ["工业园区","昆山市","吴江区","吴中区","虎丘区","相城区"]),
    ("重庆市", ["渝中区","渝北区","江北区","南岸区","沙坪坝区","九龙坡区"]),
    ("西安市", ["雁塔区","碑林区","未央区","长安区","高新区","莲湖区"]),
    ("长沙市", ["岳麓区","开福区","天心区","雨花区","芙蓉区","望城区"]),
    ("郑州市", ["二七区","金水区","郑东新区","中原区","管城区","高新区"]),
    ("天津市", ["南开区","河西区","滨海新区","东丽区","西青区","北辰区"]),
    ("济南市", ["历城区","历下区","市中区","天桥区","槐荫区","章丘区"]),
    ("青岛市", ["市南区","崂山区","黄岛区","城阳区","即墨区","胶州市"]),
    ("合肥市", ["包河区","蜀山区","庐阳区","瑶海区","肥西县","肥东县"]),
    ("福州市", ["鼓楼区","台江区","仓山区","晋安区","马尾区","闽侯县"]),
    ("厦门市", ["思明区","湖里区","集美区","海沧区","同安区","翔安区"]),
    ("东莞市", ["长安镇","虎门镇","塘厦镇","厚街镇","寮步镇","大朗镇"]),
    ("佛山市", ["顺德区","南海区","禅城区","三水区","高明区"]),
    ("宁波市", ["北仑区","鄞州区","海曙区","镇海区","慈溪市","余姚市"]),
    ("温州市", ["鹿城区","龙湾区","瓯海区","乐清市","瑞安市","永嘉县"]),
    ("石家庄市", ["长安区","桥西区","裕华区","新华区","鹿泉区","正定县"]),
    ("昆明市", ["官渡区","五华区","盘龙区","西山区","呈贡区","安宁市"]),
    ("贵阳市", ["云岩区","南明区","花溪区","观山湖区","白云区","清镇市"]),
    ("南昌市", ["东湖区","西湖区","青山湖区","红谷滩区","南昌县","进贤县"]),
    ("南宁市", ["青秀区","兴宁区","江南区","良庆区","西乡塘区","武鸣区"]),
    ("临沂市", ["兰山区","罗庄区","河东区","费县","沂水县","莒南县"]),
    ("金华市", ["义乌市","永康市","东阳市","婺城区","金东区","浦江县"]),
]

# ============================================================
# 2. 行业模板：名称后缀 + 营收范围 + 利润率 + 员工范围
# ============================================================
INDUSTRY_TEMPLATES = {
    "manufacturing": {
        "label": "制造业",
        "suffixes": ["五金加工厂","机械配件厂","模具制造厂","电子元器件厂","塑料制品厂",
                     "金属制品加工厂","纺织加工厂","包装材料厂","食品加工厂","家具制造厂",
                     "汽车配件厂","精密机械厂","铸造厂","钣金加工厂","印刷包装厂"],
        "revenue_range": (80000, 2000000),
        "margin_range": (0.06, 0.25),
        "employees_range": (10, 200),
        "has_estate_pct": 0.55,
        "tax_levels": ["A","B","B","C","C","M"],
        "credit_ok_pct": 0.85,
        "descriptions": [
            "为本地产业集群提供配套加工服务",
            "承接国内外订单，部分产品出口",
            "服务周边制造业企业，供应链配套",
            "自有设备和厂房，多年代工经验",
        ],
    },
    "wholesale_retail": {
        "label": "批发零售业",
        "suffixes": ["商贸行","批发部","商行","百货店","综合超市","数码商行",
                     "服装批发店","建材经营部","文具批发部","食品商行","家电专卖店",
                     "化妆品店","五金店","茶叶商行","酒类批发部"],
        "revenue_range": (25000, 800000),
        "margin_range": (0.07, 0.30),
        "employees_range": (2, 50),
        "has_estate_pct": 0.30,
        "tax_levels": ["B","B","M","M","C"],
        "credit_ok_pct": 0.88,
        "descriptions": [
            "服务周边社区居民和商户",
            "线上线下结合经营",
            "区域代理品牌销售",
            "批发零售兼营",
        ],
    },
    "hospitality_food": {
        "label": "住宿餐饮",
        "suffixes": ["小吃店","面馆","餐厅","火锅店","快餐店","烧烤店",
                     "饺子馆","川菜馆","酒楼","烘焙坊","饮品店","农家乐",
                     "小吃铺","早点铺","卤味店","私房菜馆"],
        "revenue_range": (20000, 400000),
        "margin_range": (0.15, 0.35),
        "employees_range": (2, 30),
        "has_estate_pct": 0.20,
        "tax_levels": ["M","M","B","B","C"],
        "credit_ok_pct": 0.82,
        "descriptions": [
            "服务周边居民和上班族",
            "口碑老店，回头客多",
            "主打地方特色美食",
            "外卖+堂食双线经营",
        ],
    },
    "it_tech": {
        "label": "信息技术",
        "suffixes": ["科技工作室","软件开发部","网络服务部","数据服务部",
                     "信息技术服务部","电商运营部","小程序开发工作室",
                     "技术服务部","数字营销工作室","IT外包服务部"],
        "revenue_range": (20000, 600000),
        "margin_range": (0.20, 0.50),
        "employees_range": (3, 60),
        "has_estate_pct": 0.10,
        "tax_levels": ["B","M","B","M","A"],
        "credit_ok_pct": 0.90,
        "descriptions": [
            "为本地企业提供数字化服务",
            "承接外包项目开发",
            "SAAS产品代理和技术支持",
            "面向中小企业提供IT解决方案",
        ],
    },
    "agriculture": {
        "label": "农业",
        "suffixes": ["种植合作社","养殖场","家庭农场","农业基地","果蔬合作社",
                     "养殖专业合作社","种植基地","苗木场","水产养殖场","畜牧养殖场"],
        "revenue_range": (10000, 300000),
        "margin_range": (0.08, 0.25),
        "employees_range": (2, 50),
        "has_estate_pct": 0.25,
        "tax_levels": ["M","M","A","B","M"],
        "credit_ok_pct": 0.88,
        "descriptions": [
            "从事经济作物种植/畜禽养殖",
            "供应本地农贸市场和商超",
            "获得当地农业部门政策扶持",
            "通过合作社模式联合经营",
        ],
    },
    "construction": {
        "label": "建筑业",
        "suffixes": ["装饰工程部","建筑工程队","安装工程部","装修公司","施工队",
                     "园林工程部","防水工程部","钢结构工程部","暖通工程部","水电安装部"],
        "revenue_range": (40000, 800000),
        "margin_range": (0.08, 0.20),
        "employees_range": (5, 80),
        "has_estate_pct": 0.35,
        "tax_levels": ["B","B","C","C","M"],
        "credit_ok_pct": 0.80,
        "descriptions": [
            "承接各类建筑装饰工程项目",
            "服务房地产开发和市政工程",
            "有专业施工资质和技术团队",
        ],
    },
    "transportation": {
        "label": "交通运输",
        "suffixes": ["货运部","物流站","配送中心","运输车队","快运部",
                     "仓储服务部","搬家服务部","冷链运输部","快递网点","配送站"],
        "revenue_range": (30000, 500000),
        "margin_range": (0.06, 0.18),
        "employees_range": (3, 40),
        "has_estate_pct": 0.30,
        "tax_levels": ["B","B","M","C"],
        "credit_ok_pct": 0.87,
        "descriptions": [
            "从事公路货运/城市配送",
            "服务本地工商企业物流需求",
            "与快递/物流平台合作",
        ],
    },
    "culture_sports": {
        "label": "文化体育",
        "suffixes": ["设计工作室","摄影工作室","健身房","培训中心","广告设计部",
                     "画室","琴行","文化传媒工作室","体育用品店","图文快印店"],
        "revenue_range": (10000, 150000),
        "margin_range": (0.20, 0.45),
        "employees_range": (2, 20),
        "has_estate_pct": 0.15,
        "tax_levels": ["M","M","B","M"],
        "credit_ok_pct": 0.90,
        "descriptions": [
            "从事创意设计和艺术培训",
            "服务本地社区和企业客户",
            "通过线上平台获客",
        ],
    },
    "resident_service": {
        "label": "居民服务",
        "suffixes": ["家政服务部","汽车美容店","家电维修部","洗染店","美发店",
                     "干洗店","清洁服务部","汽车维修店","宠物店","锁具服务部"],
        "revenue_range": (15000, 200000),
        "margin_range": (0.15, 0.40),
        "employees_range": (2, 25),
        "has_estate_pct": 0.15,
        "tax_levels": ["M","M","M","B"],
        "credit_ok_pct": 0.90,
        "descriptions": [
            "服务周边社区居民的日常需求",
            "社区口碑好，回头客多",
            "多年从业经验，技术熟练",
        ],
    },
    "healthcare": {
        "label": "卫生医疗",
        "suffixes": ["口腔诊所","中医馆","社区诊所","推拿理疗馆","药房",
                     "视光中心","康复理疗中心","体检中心","妇幼保健站","牙科诊所"],
        "revenue_range": (30000, 300000),
        "margin_range": (0.20, 0.40),
        "employees_range": (3, 20),
        "has_estate_pct": 0.25,
        "tax_levels": ["B","B","B","M"],
        "credit_ok_pct": 0.93,
        "descriptions": [
            "持证执业医师坐诊",
            "服务周边社区居民",
            "医保定点/商业保险合作",
        ],
    },
    "education": {
        "label": "教育",
        "suffixes": ["培训中心","托管中心","托育机构","早教中心",
                     "艺术培训班","课外辅导中心","职业技能培训部","书法培训班"],
        "revenue_range": (25000, 250000),
        "margin_range": (0.15, 0.35),
        "employees_range": (3, 25),
        "has_estate_pct": 0.15,
        "tax_levels": ["B","B","M","M"],
        "credit_ok_pct": 0.90,
        "descriptions": [
            "持证办学，合规经营",
            "服务周边学生和家庭",
            "小班教学，口碑招生",
        ],
    },
}

# ============================================================
# 3. 姓氏+品牌名
# ============================================================
SURNAMES = ["鑫达","恒达","宏达","振海","永利","华美","泰和","安泰","恒源",
            "金运","鑫旺","顺达","丰源","汇智","极光","瑞丰","明泰","德力",
            "金盛","天宇","博源","长信","中联","正大","华美","力恒","诚信",
            "匠心","通达","宏业","安恒","独角兽","数据魔方","彩虹","时光",
            "动力","蜂鸟","鲜达","利民","康泰","雪域","海之鲜","同仁","贝乐"]

MALE_NAMES = ["建国","志强","伟明","海涛","永刚","建军","国强","文博",
              "志远","明辉","晓东","建华","振华","国栋","志刚","大伟"]

FEMALE_NAMES = ["秀英","桂兰","玉珍","秀珍","凤英","美玲","丽华","淑芬",
                "秀芳","桂英","玉兰","秀云","秀梅","丽萍","雪梅","春梅"]

# ============================================================
# 4. 生成器主函数
# ============================================================
def generate_smes(n: int = 1000) -> List[Dict]:
    """Generate n realistic Chinese SME profiles."""
    smes = []
    used_names = set()

    # 行业分配权重(接近真实比例)
    industry_weights = {
        "wholesale_retail": 0.22,
        "manufacturing": 0.18,
        "hospitality_food": 0.15,
        "agriculture": 0.10,
        "construction": 0.08,
        "it_tech": 0.08,
        "transportation": 0.05,
        "resident_service": 0.05,
        "culture_sports": 0.04,
        "healthcare": 0.03,
        "education": 0.02,
    }

    industries = []
    weights = []
    for ind, w in industry_weights.items():
        industries.append(ind)
        weights.append(w)

    for i in range(n):
        # 选择行业
        industry = random.choices(industries, weights=weights, k=1)[0]
        template = INDUSTRY_TEMPLATES[industry]

        # 选择城市
        city_data = random.choice(CITIES)
        city = city_data[0]
        district = random.choice(city_data[1])

        # 生成企业名
        suffix = random.choice(template["suffixes"])
        brand = random.choice(SURNAMES)
        owner = random.choice(MALE_NAMES + FEMALE_NAMES)

        # 三种命名模式
        name_style = random.random()
        if name_style < 0.35:
            name = f"{city}{district}{brand}{suffix}"
        elif name_style < 0.65:
            name = f"{district}{brand}{suffix}"
        else:
            name = f"{city}{brand}{suffix}"

        # 避免重名
        if name in used_names:
            name = f"{name}({district})"
        used_names.add(name)

        # 财务参数
        rev_min, rev_max = template["revenue_range"]
        revenue = int(np.random.lognormal(
            mean=np.log((rev_min + rev_max) / 2),
            sigma=0.8
        ))
        revenue = max(rev_min, min(rev_max, revenue))

        margin_min, margin_max = template["margin_range"]
        profit_margin = round(random.uniform(margin_min, margin_max), 2)

        emp_min, emp_max = template["employees_range"]
        employees = random.randint(emp_min, emp_max)

        # 资产
        has_estate = random.random() < template["has_estate_pct"]

        # 税务
        tax_level = random.choice(template["tax_levels"])

        # 征信
        credit_ok = random.random() < template["credit_ok_pct"]
        if credit_ok:
            overdue = int(np.random.exponential(0.5))
            overdue = min(overdue, 2)
        else:
            overdue = random.randint(1, 6)

        # 经营年数(对数正态分布)
        years = max(0.5, round(np.random.lognormal(mean=1.0, sigma=0.8), 1))
        years = min(years, 25)

        # 其他标签
        has_license = random.random() < 0.90
        has_bank_flow = random.random() < (0.70 if revenue > 50000 else 0.35)
        is_tech = industry == "it_tech" or random.random() < 0.08
        is_ecommerce = (industry in ["wholesale_retail", "it_tech"]) or random.random() < 0.12

        # 描述
        desc = random.choice(template["descriptions"])

        # 风险提示
        risks = []
        if not has_license:
            risks.append("无营业执照，银行一票否决")
        if not has_bank_flow:
            risks.append("无对公银行流水")
        if overdue >= 3:
            risks.append(f"近2年逾期{overdue}次，征信风险较高")
        elif overdue >= 1:
            risks.append(f"有过{overdue}次轻微逾期")
        if not has_estate and revenue > 100000:
            risks.append("无自有房产，纯信用贷款额度受限")
        if revenue < 30000:
            risks.append("经营规模偏小，抗风险能力弱")
        if years < 1:
            risks.append("经营时间不足1年")
        if industry == "construction":
            risks.append("行业受政策周期影响较大")
        if industry == "agriculture":
            risks.append("受天气和市场价格波动影响")
        if not risks:
            risks.append("经营状况总体良好")

        smes.append({
            "name": name,
            "industry": industry,
            "region": city,
            "years": years,
            "employees": employees,
            "revenue_monthly": revenue,
            "profit_margin": profit_margin,
            "has_estate": has_estate,
            "tax_level": tax_level,
            "has_license": has_license,
            "has_bank_flow": has_bank_flow,
            "is_tech": is_tech,
            "is_ecommerce": is_ecommerce,
            "credit_ok": credit_ok,
            "overdue": overdue,
            "description": desc,
            "risk_notes": risks,
        })

    return smes


# ============================================================
# 5. 导出为Enterprise DB格式
# ============================================================
def export_to_python_code(smes: List[Dict]) -> str:
    """Generate Python code that can be appended to enterprise_search.py."""
    lines = ['\n    # === 程序化生成的1000+中小微企业 ===\n']
    for sme in smes:
        name = sme["name"].replace("'", "\\'")
        desc = sme["description"].replace("'", "\\'")
        risks_str = json.dumps(sme["risk_notes"], ensure_ascii=False)

        lines.append(f'    "{name}": {{')
        lines.append(f'        "industry": "{sme["industry"]}", "region": "{sme["region"]}",')
        lines.append(f'        "years": {sme["years"]}, "employees": {sme["employees"]}, "revenue_monthly": {sme["revenue_monthly"]},')
        lines.append(f'        "profit_margin": {sme["profit_margin"]}, "has_estate": {str(sme["has_estate"])},')
        lines.append(f'        "tax_level": "{sme["tax_level"]}", "has_license": {str(sme["has_license"])}, "has_bank_flow": {str(sme["has_bank_flow"])},')
        lines.append(f'        "is_tech": {str(sme["is_tech"])}, "is_ecommerce": {str(sme["is_ecommerce"])},')
        lines.append(f'        "credit_ok": {str(sme["credit_ok"])}, "overdue": {sme["overdue"]},')
        lines.append(f'        "description": "{desc}",')
        lines.append(f'        "risk_notes": {risks_str},')
        lines.append(f'    }},')

    return '\n'.join(lines)


if __name__ == "__main__":
    print("Generating 1000+ Chinese SMEs...")
    smes = generate_smes(1000)

    # 统计
    from collections import Counter
    industries = Counter(s["industry"] for s in smes)
    print(f"\nTotal: {len(smes)} SMEs")
    for ind, count in sorted(industries.items(), key=lambda x: -x[1]):
        print(f"  {ind}: {count}")

    # 导出为JSON (避免编码问题)
    import json
    db = {}
    for s in smes:
        name = s["name"]
        db[name] = {
            "industry": s["industry"], "region": s["region"],
            "years": s["years"], "employees": s["employees"],
            "revenue_monthly": s["revenue_monthly"],
            "profit_margin": round(s["profit_margin"], 2),
            "has_estate": s["has_estate"], "tax_level": s["tax_level"],
            "has_license": s["has_license"], "has_bank_flow": s["has_bank_flow"],
            "is_tech": s["is_tech"], "is_ecommerce": s["is_ecommerce"],
            "credit_ok": s["credit_ok"], "overdue": s["overdue"],
            "description": s["description"],
            "risk_notes": s["risk_notes"],
        }

    with open("sme_database.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    size_kb = len(json.dumps(db, ensure_ascii=False)) / 1024
    print(f"Saved: sme_database.json ({size_kb:.0f}KB)")
