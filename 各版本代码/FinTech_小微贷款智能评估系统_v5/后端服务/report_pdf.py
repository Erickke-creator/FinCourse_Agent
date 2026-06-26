"""
v5 PDF 报告导出模块
将贷款评估结果生成正式 PDF 报告，可直接打印提交银行。
"""

import os
import io
from datetime import datetime
from typing import Optional

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


def generate_pdf_report(evaluation_result: dict, enterprise_info: dict = None) -> str:
    """
    生成 PDF 评估报告，返回文件路径。

    evaluation_result: evaluate_loan() 返回的 EvaluationResult.model_dump()
    enterprise_info: 企业基本信息 {name, industry, amount, ...}
    """
    enterprise = enterprise_info or {}
    result = evaluation_result

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, HRFlowable
        )
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus.flowables import KeepTogether
    except ImportError:
        raise ImportError("reportlab 未安装。pip install reportlab")

    # 尝试注册中文字体
    _register_chinese_fonts()

    filename = f"贷款评估报告_{enterprise.get('name', '企业')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # 标题
    story.append(Paragraph("小微企业贷款可行性评估报告", styles['Title']))
    story.append(Spacer(1, 5*mm))

    # 元信息
    meta_style = styles['Normal']
    story.append(Paragraph(f"评估日期：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}", meta_style))
    story.append(Paragraph(f"评估引擎版本：v5.0 (含ML增强)", meta_style))
    story.append(Spacer(1, 5*mm))

    # 企业信息
    story.append(Paragraph("一、企业基本信息", styles['Heading2']))
    info_data = [
        ["项目", "内容"],
        ["企业名称", enterprise.get('name', '未提供')],
        ["所属行业", enterprise.get('industry', '未提供')],
        ["申请金额", f"{enterprise.get('amount', 0)} 万元"],
        ["申请期限", f"{enterprise.get('term_years', 1)} 年"],
        ["经营年限", f"{enterprise.get('business_years', 0)} 年"],
        ["纳税等级", enterprise.get('tax_level', '未提供')],
    ]
    t = Table(info_data, colWidths=[60*mm, 80*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a56db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    # 评分总览
    story.append(Paragraph("二、综合评分总览", styles['Heading2']))

    score = result.get('score', 0)
    risk_level = result.get('risk_level', 'N/A')
    risk_color = '#ef4444' if 'high' in str(risk_level) else '#f59e0b' if 'medium' in str(risk_level) else '#22c55e'

    score_data = [
        ["评估指标", "得分/等级"],
        ["综合信用评分", f"{score:.0f} / 100"],
        ["风险等级", str(risk_level)],
        ["企业健康度", f"{result.get('enterprise_health_score', 0):.0f} / 100"],
        ["建议贷款金额", f"{result.get('suggested_amount', 0):.0f} 元"],
        ["建议贷款期限", f"{result.get('suggested_term', 12)} 个月"],
        ["预计月供", f"{result.get('monthly_repayment', 0):.0f} 元"],
        ["DTI 比率", f"{result.get('dti_ratio', 0):.1f}%"],
        ["还款压力比", f"{result.get('repayment_pressure_ratio', 0):.1f}%"],
    ]
    if result.get('ml_enhanced'):
        score_data.append(["ML违约概率", f"{result.get('ml_default_prob', 0):.1%}"])
        score_data.append(["ML信用评级", str(result.get('ml_credit_rating', 'N/A'))])

    t2 = Table(score_data, colWidths=[60*mm, 80*mm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a56db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
    ]))
    story.append(t2)
    story.append(Spacer(1, 5*mm))

    # 五维分解
    breakdown = result.get('breakdown', {})
    if breakdown:
        story.append(Paragraph("五维评分分解", styles['Heading3']))
        bd = [
            ["维度", "得分", "满分"],
            ["经营实力", str(breakdown.get('operating_strength', 0)), "20"],
            ["现金流覆盖", str(breakdown.get('cash_flow_coverage', 0)), "20"],
            ["征信合规", str(breakdown.get('credit_compliance', 0)), "20"],
            ["信用增强", str(breakdown.get('credit_enhancement', 0)), "20"],
            ["杠杆风险", str(breakdown.get('leverage_risk', 0)), "20"],
        ]
        t3 = Table(bd, colWidths=[60*mm, 35*mm, 35*mm])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(t3)

    story.append(Spacer(1, 8*mm))

    # 银行匹配
    story.append(Paragraph("三、银行匹配推荐 TOP 5", styles['Heading2']))
    bank_matches = result.get('bank_matches', [])[:5]
    if bank_matches:
        bank_data = [["银行", "审批概率", "预估利率", "匹配理由"]]
        for bm in bank_matches:
            bank_data.append([
                bm.get('bank_name', bm.get('name', '')),
                f"{bm.get('approval_probability', 0):.0%}",
                f"{bm.get('estimated_rate', 0):.2f}%",
                (bm.get('match_reasons', [''])[0] if bm.get('match_reasons') else '')[:40]
            ])
        t4 = Table(bank_data, colWidths=[35*mm, 25*mm, 25*mm, 55*mm])
        t4.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a56db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(t4)
    else:
        story.append(Paragraph("暂未匹配到合适的银行产品。", meta_style))

    story.append(Spacer(1, 8*mm))

    # 优势与风险
    story.append(Paragraph("四、优势分析", styles['Heading2']))
    for s in result.get('strengths', [])[:5]:
        story.append(Paragraph(f"• {s}", meta_style))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("五、风险提示", styles['Heading2']))
    for r in result.get('risks', [])[:5]:
        story.append(Paragraph(f"• {r}", meta_style))

    story.append(Spacer(1, 5*mm))

    # 改进建议
    story.append(Paragraph("六、改进建议", styles['Heading2']))
    for i, tip in enumerate(result.get('improvement_tips', [])[:5], 1):
        story.append(Paragraph(f"{i}. {tip}", meta_style))

    story.append(Spacer(1, 10*mm))

    # 材料清单
    story.append(Paragraph("七、建议准备材料", styles['Heading2']))
    for m in result.get('recommended_materials', [])[:8]:
        story.append(Paragraph(f"• [{m.get('category', '')}] {m.get('name', '')} — {m.get('description', '')}", meta_style))

    story.append(Spacer(1, 15*mm))

    # 免责声明
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#cccccc')))
    story.append(Spacer(1, 3*mm))
    disclaimer = Paragraph(
        "<i>免责声明：本报告由 AI 辅助生成，仅供参考。实际贷款审批以银行终审为准。"
        "报告中涉及的银行产品信息来源于公开渠道，可能存在滞后。ML 模型基于历史数据训练，"
        "不代表对未来表现的任何保证。</i>",
        ParagraphStyle('disclaimer', parent=styles['Normal'], fontSize=7, textColor=HexColor('#999999'))
    )
    story.append(disclaimer)

    doc.build(story)
    return filepath


def _register_chinese_fonts():
    """尝试注册中文字体（Windows/Mac/Linux 常见路径）"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        # Windows
        ("C:/Windows/Fonts/msyh.ttc", "ChineseYaHei"),
        ("C:/Windows/Fonts/msyhbd.ttc", "ChineseYaHeiBold"),
        ("C:/Windows/Fonts/simsun.ttc", "ChineseSong"),
        # Mac
        ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
        ("/Library/Fonts/Arial Unicode.ttf", "ArialUnicode"),
        # Linux
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "WenQuanYi"),
    ]

    registered = False
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                registered = True
            except Exception:
                pass

    # 如果都找不到，使用内置 Helvetica（仅支持英文）
    if not registered:
        print("[PDF] 未找到中文字体，报告将以英文/拼音显示。")


# ============================================================
# Agent Tool 接口
# ============================================================
def export_report_tool(evaluation_result: dict, enterprise_name: str = "") -> str:
    """供 Agent 调用的报告导出工具"""
    try:
        path = generate_pdf_report(evaluation_result, {"name": enterprise_name})
        return f"PDF 报告已生成：{path}"
    except Exception as e:
        return f"报告生成失败：{str(e)}"
