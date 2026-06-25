"""Migrate knowledge base files from 普惠金融Agent_知识库 to kb/data/"""
import shutil, os

SRC_BASE = r'c:\Users\Eric\Desktop\Programs\FinCourse_Agent\找资料\普惠金融Agent_知识库'
DST_BASE = r'c:\Users\Eric\Desktop\Programs\FinCourse_Agent\找资料\kb\data'

FILES = [
    (r'01_政策规则\政策规则知识库_国家级.csv',     r'policies\national_policies.csv'),
    (r'01_政策规则\政策规则知识库_地方级.csv',     r'policies\provincial_policies.csv'),
    (r'02_银行产品\银行产品数据库_统一版.json',    r'banks\bank_products.json'),
    (r'02_银行产品\银行地域可用性.csv',            r'banks\bank_regional_availability.csv'),
    (r'03_行业准入\行业准入与限制规则.csv',        r'industries\industry_acceptance.csv'),
    (r'03_行业准入\行业准入地域调整系数.csv',      r'industries\regional_adjustments.csv'),
    (r'04_征信与纳税\征信要求分级表.csv',          r'credit_tax\credit_tolerance.csv'),
    (r'04_征信与纳税\纳税等级评分规则.csv',        r'credit_tax\tax_level_scoring.csv'),
    (r'05_风控规则\贷款被拒因子与权重.csv',        r'risk_control\rejection_factors.csv'),
    (r'05_风控规则\2026政策补贴与贴息规则.csv',    r'risk_control\subsidy_policies.csv'),
    (r'05_风控规则\宏观统计数据.json',             r'risk_control\macro_statistics.json'),
    (r'06_教学案例\教学案例库_原始版.csv',          r'cases\teaching_cases_basic.csv'),
    (r'06_教学案例\教学案例库_增强版.csv',          r'cases\teaching_cases_enhanced.csv'),
    (r'07_数据治理\数据来源登记表.csv',             r'governance\data_source_registry.csv'),
    (r'07_数据治理\数据语义层与口径说明.md',        r'governance\data_semantics.md'),
    (r'07_数据治理\输入字段_ML模型_知识库映射表.csv', r'governance\field_mapping_ml_kb.csv'),
]

for src_rel, dst_rel in FILES:
    src = os.path.join(SRC_BASE, src_rel)
    dst = os.path.join(DST_BASE, dst_rel)
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        dst_size = os.path.getsize(dst)
        print(f'OK ({dst_size:>6d} bytes): {dst_rel}')
    else:
        print(f'MISSING: {src_rel}')
print('Done!')
