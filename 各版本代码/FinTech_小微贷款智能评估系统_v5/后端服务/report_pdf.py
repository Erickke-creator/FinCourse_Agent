"""
v5 PDF 报告 — reportlab + SimHei 黑体（registerFontFamily 修复）
专业商业风格：封面 + 评分可视化 + 银行排名 + 页眉页脚
"""

import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# ============================================================
# 字体注册（关键：registerFontFamily 才能让 Paragraph 正常渲染）
# ============================================================
_CN_FONT = "SimHei"

def _init_font():
    for path in [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]:
        if os.path.exists(path):
            try:
                is_ttc = path.endswith('.ttc')
                pdfmetrics.registerFont(TTFont(_CN_FONT, path, subfontIndex=0) if is_ttc else TTFont(_CN_FONT, path))
                registerFontFamily(_CN_FONT, normal=_CN_FONT, bold=_CN_FONT)
                print(f"[PDF] Font: {_CN_FONT} ({os.path.basename(path)})")
                return
            except Exception:
                continue
    print("[PDF] WARNING: No CJK font found")

_init_font()

# ============================================================
# 品牌色彩
# ============================================================
C_PRIMARY   = HexColor('#1e3a5f')
C_ACCENT    = HexColor('#2563eb')
C_SUCCESS   = HexColor('#16a34a')
C_WARNING   = HexColor('#f59e0b')
C_DANGER    = HexColor('#dc2626')
C_BG_LIGHT  = HexColor('#f8fafc')
C_BORDER    = HexColor('#e2e8f0')
C_TEXT      = HexColor('#1e293b')
C_MUTED     = HexColor('#64748b')
C_WHITE     = HexColor('#ffffff')
C_ROW_ALT   = HexColor('#f1f5f9')

# ============================================================
# 进度条 Flowable
# ============================================================
class ScoreBar(Flowable):
    def __init__(self, label, score, max_score, width=260):
        Flowable.__init__(self)
        self.label = label
        self.score = score
        self.max_score = max_score
        self._width = width
        self.height = 16

    def draw(self):
        ratio = min(self.score / self.max_score, 1.0)
        color = C_SUCCESS if ratio >= 0.8 else (C_WARNING if ratio >= 0.5 else C_DANGER)
        # label
        self.canv.setFont(_CN_FONT, 9)
        self.canv.setFillColor(C_TEXT)
        self.canv.drawString(0, 2, self.label)
        score_txt = f"{self.score:.0f}/{self.max_score:.0f}"
        self.canv.drawRightString(self._width, 2, score_txt)
        # bar bg
        bar_y, bar_h = -1, 4.5
        self.canv.setFillColor(C_BORDER)
        self.canv.roundRect(0, bar_y, self._width, bar_h, 2.25, fill=1, stroke=0)
        self.canv.setFillColor(color)
        self.canv.roundRect(0, bar_y, self._width * ratio, bar_h, 2.25, fill=1, stroke=0)


# ============================================================
# 样式
# ============================================================
def _style(name, **kw):
    base = kw.pop('parent', None)
    defaults = {'fontName': _CN_FONT, 'textColor': C_TEXT}
    defaults.update(kw)
    return ParagraphStyle(name, parent=base, **defaults)

ST = {
    'cover_title': _style('cover_title', fontSize=26, leading=34, alignment=TA_CENTER, textColor=C_WHITE),
    'cover_sub':   _style('cover_sub',   fontSize=10, leading=16, alignment=TA_CENTER, textColor=HexColor('#93c5fd')),
    'cover_info':  _style('cover_info',  fontSize=9,  leading=14, alignment=TA_CENTER, textColor=HexColor('#cbd5e1')),
    'h1':          _style('h1',          fontSize=14, leading=20, textColor=C_PRIMARY, spaceBefore=10, spaceAfter=2),
    'body':        _style('body',        fontSize=10, leading=16, textColor=C_TEXT),
    'body_sm':     _style('body_sm',     fontSize=8,  leading=12, textColor=C_MUTED),
    'score_big':   _style('score_big',   fontSize=38, leading=44, alignment=TA_CENTER, textColor=C_ACCENT),
    'verdict':     _style('verdict',     fontSize=12, leading=18, alignment=TA_CENTER),
    'disclaimer':  _style('disclaimer',  fontSize=7,  leading=10, textColor=C_MUTED),
}


# ============================================================
# 表格
# ============================================================
def _table(data, col_widths, header_rows=1):
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), C_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, header_rows - 1), C_WHITE),
        ('FONTNAME', (0, 0), (-1, -1), _CN_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4, C_BORDER),
        ('LINEBELOW', (0, 0), (-1, header_rows - 1), 1, C_ACCENT),
    ]
    for i in range(header_rows, len(data)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), C_ROW_ALT))
    t.setStyle(TableStyle(cmds))
    return t


def _divider():
    return HRFlowable(width="100%", thickness=0.4, color=C_BORDER, spaceBefore=2, spaceAfter=2)


# ============================================================
# 页眉页脚
# ============================================================
def _on_page(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(C_PRIMARY)
    canvas_obj.setLineWidth(1)
    canvas_obj.line(20*mm, A4[1] - 15*mm, A4[0] - 20*mm, A4[1] - 15*mm)
    canvas_obj.setFont(_CN_FONT, 7)
    canvas_obj.setFillColor(C_MUTED)
    canvas_obj.drawString(20*mm, A4[1] - 13*mm, "FinTech 小微贷款智能评估系统 v5.0")
    canvas_obj.drawRightString(A4[0] - 20*mm, A4[1] - 13*mm, "CONFIDENTIAL")
    canvas_obj.setFont(_CN_FONT, 8)
    canvas_obj.drawCentredString(A4[0] / 2, 12*mm, f"— {canvas_obj.getPageNumber()} —")
    canvas_obj.restoreState()

def _on_first_page(canvas_obj, doc):
    pass


# ============================================================
# 主生成
# ============================================================
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


def _build_story(result, enterprise, doc_width):
    s = ST
    story = []
    e = enterprise

    # ====== 封面 ======
    story.append(Spacer(1, 30*mm))
    story.append(HRFlowable(width="35%", thickness=2.5, color=C_ACCENT, spaceAfter=10))
    story.append(Paragraph("小微企业贷款", s['cover_title']))
    story.append(Paragraph("可行性评估报告", s['cover_title']))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("FinTech SME Loan Assessment Report", s['cover_sub']))
    story.append(Spacer(1, 18*mm))
    story.append(HRFlowable(width="35%", thickness=1, color=C_ACCENT, spaceAfter=10))
    story.append(Paragraph(f"评估日期：{datetime.now().strftime('%Y 年 %m 月 %d 日')}", s['cover_info']))
    story.append(Paragraph(f"企业名称：{e.get('name', '未指定')}", s['cover_info']))
    story.append(Paragraph("评估引擎：FinTech v5.0 · LLM Agent + ML + RAG", s['cover_info']))
    story.append(Spacer(1, 12*mm))
    story.append(Paragraph("— CONFIDENTIAL —", s['cover_info']))
    story.append(PageBreak())

    # ====== 一、评分总览 ======
    story.append(Paragraph("一、综合评分总览", s['h1']))
    story.append(_divider())
    story.append(Spacer(1, 4*mm))

    score = result.get('score', 0)
    risk_str = str(result.get('risk_level', '')).lower()
    if 'high' in risk_str:
        risk_label, risk_color = '高风险 — 建议调整条件后重新申请', C_DANGER
    elif 'medium' in risk_str:
        risk_label, risk_color = '中等风险 — 建议谨慎放款', C_WARNING
    else:
        risk_label, risk_color = '低风险 — 建议放款', C_SUCCESS

    story.append(Paragraph(f"{score:.0f}", s['score_big']))
    story.append(Paragraph("综合信用评分 / 100", _style('sc', parent=s['body_sm'], alignment=TA_CENTER)))
    story.append(Spacer(1, 3*mm))

    v_style = ParagraphStyle('v', parent=s['verdict'], textColor=risk_color)
    story.append(Paragraph(risk_label, v_style))
    story.append(Spacer(1, 6*mm))

    # 指标表
    info = [
        ["评估指标", "数值", "评估指标", "数值"],
        ["企业健康度", f"{result.get('enterprise_health_score', 0):.0f} / 100",
         "建议贷款金额", f"{result.get('suggested_amount', 0):.0f} 元"],
        ["预计月供", f"{result.get('monthly_repayment', 0):.0f} 元",
         "建议期限", f"{result.get('suggested_term', 12)} 个月"],
        ["还款压力比", f"{result.get('repayment_pressure_ratio', 0):.1f}%",
         "DTI 比率", f"{result.get('dti_ratio', 0):.1f}%"],
    ]
    if result.get('ml_enhanced'):
        info.append(["ML 违约概率", f"{result.get('ml_default_prob', 0):.1%}",
                     "ML 信用评级", str(result.get('ml_credit_rating', 'N/A'))])
    story.append(_table(info, [38*mm, 38*mm, 38*mm, 38*mm]))
    story.append(Spacer(1, 8*mm))

    # ====== 二、五维分解 ======
    story.append(Paragraph("二、五维信用评分分解", s['h1']))
    story.append(_divider())
    story.append(Spacer(1, 2*mm))
    bd = result.get('breakdown', {})
    dims = [
        ('经营实力', bd.get('operating_strength', 0), 20),
        ('现金流覆盖', bd.get('cash_flow_coverage', 0), 20),
        ('征信合规', bd.get('credit_compliance', 0), 20),
        ('信用增强', bd.get('credit_enhancement', 0), 20),
        ('杠杆风险', bd.get('leverage_risk', 0), 20),
    ]
    for label, val, mx in dims:
        story.append(ScoreBar(label, val, mx, width=doc_width * 0.82))
        story.append(Spacer(1, 1*mm))
    story.append(Spacer(1, 6*mm))

    # ====== 三、银行匹配 ======
    story.append(Paragraph("三、银行匹配推荐 TOP 5", s['h1']))
    story.append(_divider())
    story.append(Spacer(1, 2*mm))
    banks = result.get('bank_matches', [])[:5]
    if banks:
        rows = [[str(i+1), b.get('bank_name', ''), b.get('product_name', b.get('loan_type', '')),
                 f"{b.get('approval_probability', 0):.0%}", f"{b.get('estimated_interest_rate', 0):.2f}%"]
                for i, b in enumerate(banks)]
        story.append(_table([["#", "银行名称", "产品", "审批概率", "利率"], *rows],
                           [10*mm, 42*mm, 48*mm, 28*mm, 28*mm]))
    else:
        story.append(Paragraph("暂未匹配到合适的银行产品。", s['body']))

    story.append(PageBreak())

    # ====== 四、优势 ======
    story.append(Paragraph("四、核心优势分析", s['h1']))
    story.append(_divider())
    for strength in result.get('strengths', [])[:6]:
        story.append(Paragraph(f"<font color='#16a34a'>✓</font>  {strength}", s['body']))
    story.append(Spacer(1, 6*mm))

    # ====== 五、风险 ======
    story.append(Paragraph("五、风险因素识别", s['h1']))
    story.append(_divider())
    for risk in result.get('risks', [])[:6]:
        story.append(Paragraph(f"<font color='#dc2626'>!</font>  {risk}", s['body']))
    story.append(Spacer(1, 6*mm))

    # ====== 六、改进建议 ======
    tips = result.get('improvement_tips', [])
    if tips:
        story.append(Paragraph("六、改进建议与行动计划", s['h1']))
        story.append(_divider())
        for i, tip in enumerate(tips[:6], 1):
            story.append(Paragraph(f"<b>{i}.</b>  {tip}", s['body']))
        story.append(Spacer(1, 6*mm))

    # ====== 七、材料 ======
    materials = result.get('recommended_materials', result.get('materials', []))[:8]
    if materials:
        story.append(Paragraph("七、建议准备材料清单", s['h1']))
        story.append(_divider())
        cat_map = {'basic': '基础', 'financial': '财务', 'enhancement': '增强'}
        for m in materials:
            name = m.get('name', '')
            cat = cat_map.get(m.get('category', ''), '')
            req = '●' if m.get('is_required', True) else '○'
            story.append(Paragraph(f"{req} [{cat}] {name}", s['body']))

    story.append(Spacer(1, 15*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "免责声明：本报告由 AI 辅助生成，仅供内部参考，不构成贷款承诺或投资建议。",
        s['disclaimer']))
    return story


def generate_pdf_bytes(evaluation_result: dict, enterprise_info: dict = None) -> io.BytesIO:
    enterprise = enterprise_info or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm,
                            topMargin=22*mm, bottomMargin=22*mm,
                            title="小微企业贷款可行性评估报告")
    story = _build_story(evaluation_result, enterprise, doc.width)
    doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_page)
    buf.seek(0)
    return buf


def generate_pdf_file(evaluation_result: dict, enterprise_info: dict = None) -> str:
    enterprise = enterprise_info or {}
    name = enterprise.get('name', '企业')
    filename = f"贷款评估报告_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_DIR, filename)
    buf = generate_pdf_bytes(evaluation_result, enterprise_info)
    with open(filepath, 'wb') as f:
        f.write(buf.read())
    return filepath


generate_pdf_report = generate_pdf_file
