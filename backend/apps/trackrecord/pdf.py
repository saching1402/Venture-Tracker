"""Marketing-sheet PDF (ReportLab, A4 landscape) in the Atlas navy / gold style."""
from __future__ import annotations

import datetime as dt
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (CondPageBreak, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

NAVY = colors.HexColor('#0f2347')
GOLD = colors.HexColor('#b38728')
RED = colors.HexColor('#b7282e')
GREEN = colors.HexColor('#1d7a47')
INK = colors.HexColor('#13203a')
MUTED = colors.HexColor('#5b6678')
LINE = colors.HexColor('#e4e8ef')
TINT = colors.HexColor('#f5f7fa')
SEV = {'high': RED, 'medium': GOLD, 'low': MUTED}

S = {
    'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.white),
    'sub': ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5, leading=12, textColor=colors.HexColor('#cfd6e1')),
    'h2': ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=4),
    'h3': ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=NAVY),
    'body': ParagraphStyle('body', fontName='Helvetica', fontSize=8.5, leading=11, textColor=INK),
    'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=7.4, leading=9.2, textColor=INK),
    'cellb': ParagraphStyle('cellb', fontName='Helvetica-Bold', fontSize=7.6, leading=9.4, textColor=NAVY),
    'num': ParagraphStyle('num', fontName='Helvetica', fontSize=7.4, leading=9.2, textColor=INK, alignment=TA_RIGHT),
    'head': ParagraphStyle('head', fontName='Helvetica-Bold', fontSize=6.6, leading=8, textColor=MUTED),
    'headr': ParagraphStyle('headr', fontName='Helvetica-Bold', fontSize=6.6, leading=8, textColor=MUTED, alignment=TA_RIGHT),
    'kpil': ParagraphStyle('kpil', fontName='Helvetica-Bold', fontSize=6.4, leading=8, textColor=MUTED),
    'kpiv': ParagraphStyle('kpiv', fontName='Helvetica-Bold', fontSize=14, leading=17, textColor=NAVY),
    'small': ParagraphStyle('small', fontName='Helvetica', fontSize=6.8, leading=8.6, textColor=MUTED),
}


def P(text, style='cell') -> Paragraph:
    return Paragraph(escape(str(text)) if text not in (None, '') else '—', S[style])


def money_m(v) -> str:
    if v is None:
        return '—'
    v = float(v)
    if v == 0:
        return '$0'
    if abs(v) >= 1000:
        return f'${v / 1000:,.2f}bn'
    if abs(v) >= 1:
        return f'${v:,.1f}m'
    return f'${v * 1000:,.0f}k'


def money_bn(v) -> str:
    if v is None:
        return '—'
    v = float(v)
    return f'${v:,.1f}bn' if v >= 1 else f'${v * 1000:,.0f}m'


def x(v) -> str:
    return '—' if v is None else f'{v:.2f}x'


def pct(v) -> str:
    return '—' if v is None else f'{v * 100:.1f}%'


def _kpis(summary: dict, settings) -> Table:
    items = [('Investments', str(summary.get('count', 0))), ('Invested', money_m(summary.get('invested_usd_m'))),
             ('Total value', money_m(summary.get('total_value_usd_m'))), ('Realised', money_m(summary.get('realised_usd_m'))),
             ('Gross MOIC', x(summary.get('gross_moic'))), ('Net MOIC', x(summary.get('net_moic'))),
             ('Gross IRR', pct(summary.get('gross_irr'))), ('Net IRR', pct(summary.get('net_irr'))),
             ('DPI', x(summary.get('dpi')))]
    if settings.show_capacity and summary.get('capacity_usd_m'):
        items.append(('Available capacity', money_m(summary.get('capacity_usd_m'))))
    cells = [[Paragraph(escape(k.upper()), S['kpil']), Paragraph(escape(v), S['kpiv'])] for k, v in items]
    t = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[(277 * mm) / len(items)] * len(items))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), TINT), ('BOX', (0, 0), (-1, -1), 0.6, LINE),
        ('LINEBEFORE', (1, 0), (-1, -1), 0.6, colors.white), ('LINEABOVE', (0, 0), (-1, 0), 2, GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def _table(header: list[tuple[str, bool]], rows: list[list], widths: list[float]) -> Table:
    data = [[Paragraph(escape(h.upper()), S['headr' if right else 'head']) for h, right in header]] + rows
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, NAVY), ('LINEBELOW', (0, 1), (-1, -1), 0.4, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 3.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafbfd')]),
    ]))
    return t


def _names(lst, n=3) -> str:
    lst = [s for s in (lst or []) if s]
    return ', '.join(lst[:n]) + (f' +{len(lst) - n}' if len(lst) > n else '')


def _direct_rows(rows) -> list[list]:
    out = []
    for inv, m in rows:
        net = x(m['net_moic']) + (' r' if m['net_basis'] == 'reported' else '')
        out.append([
            Paragraph(f'<b>{escape(inv.name)}</b><br/><font color="#5b6678">{escape(inv.sector or "")}</font>', S['cell']),
            Paragraph(f'{escape(inv.get_structure_display())}<br/><font color="#5b6678">{escape(inv.vehicle or "")}</font>', S['cell']),
            Paragraph(f'{escape(inv.round or "—")}<br/><font color="#5b6678">{inv.invest_date:%b %Y}</font>', S['cell']),
            P(money_bn(inv.entry_valuation_usd_bn), 'num'), P(money_m(m['invested_usd_m']), 'num'),
            P(money_m(m['current_usd_m']), 'num'), P(money_m(m['realised_usd_m']), 'num'),
            P(x(m['gross_moic']), 'num'), P(net, 'num'),
            Paragraph('n.m.' if m.get('irr_nm') else f'{pct(m["gross_irr"])}<br/><font color="#5b6678">{pct(m["net_irr"])} net</font>', S['num']),
            P(x(m['dpi']), 'num'),
            Paragraph(f'{escape(_names(inv.lead_investors, 2))}<br/><font color="#5b6678">{escape(_names(inv.co_investors, 3))}</font>', S['cell']),
            P(money_m(inv.capacity_usd_m) if inv.capacity_usd_m else '—', 'num'),
        ])
    return out


def _fund_rows(rows) -> list[list]:
    out = []
    for inv, m in rows:
        gp = inv.manager.name if inv.manager_id else ''
        out.append([
            Paragraph(f'<b>{escape(inv.vehicle or inv.name)}</b><br/><font color="#5b6678">{escape(gp)}</font>', S['cell']),
            P(inv.get_structure_display()), P(inv.vintage or inv.invest_date.year, 'num'),
            P(money_m(inv.commitment_usd_m), 'num'), P(money_m(m['invested_usd_m']), 'num'),
            P(money_m(m['realised_usd_m']), 'num'), P(money_m(m['current_usd_m']), 'num'),
            P(x(m['net_moic']) + (' r' if m['net_basis'] == 'reported' else ''), 'num'),
            P(pct(m['net_irr']), 'num'), P(x(m['net_dpi']), 'num'),
            P(money_m(m['unfunded_usd_m']), 'num'),
            P(money_m(inv.capacity_usd_m) if inv.capacity_usd_m else '—', 'num'),
        ])
    return out


def _points(title: str, pts: list[dict]) -> list:
    if not pts:
        return []
    items = [Paragraph(f'<b>{escape(title)}</b>', S['h3'])]
    for p in pts:
        c = SEV.get(p.get('severity'), MUTED).hexval()[2:]
        items.append(Paragraph(f'<font color="#{c}"><b>{escape(p.get("severity", "").upper())}</b></font>&nbsp; {escape(p.get("text", ""))}', S['body']))
    return items


def _commentary(inv, m) -> list:
    parts: list = [Paragraph(f'{escape(inv.name)} <font size="8" color="#5b6678">· {escape(inv.get_structure_display())} · '
                             f'{x(m["gross_moic"])} gross · {pct(m["gross_irr"])} IRR</font>', S['h2'])]
    if inv.thesis:
        parts.append(Paragraph(escape(inv.thesis), S['body']))
        parts.append(Spacer(1, 3))
    cols = [_points('Pros', inv.pros), _points('Cons', inv.cons), _points('Risks', inv.risks)]
    cols = [c for c in cols if c]
    if cols:
        t = Table([cols], colWidths=[(277 * mm) / len(cols)] * len(cols))
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 10)]))
        parts.append(t)
    comments = list(inv.comments.all()[:5])
    if comments:
        parts.append(Spacer(1, 3))
        parts.append(Paragraph('<b>Comments</b>', S['h3']))
        for c in comments:
            parts.append(Paragraph(f'<font color="#5b6678">{c.created_at:%d %b %Y} · {escape(c.author_name)}</font> &nbsp;{escape(c.text)}', S['body']))
    parts.append(Spacer(1, 6))
    return [KeepTogether(parts[:3]), *parts[3:]]


def render_pdf(rows: list[tuple], summary: dict, settings, commentary: bool = False) -> bytes:
    buf = io.BytesIO()
    today = dt.date.today()

    def footer(canvas, doc):
        w, h = landscape(A4)
        canvas.setFont('Helvetica', 6.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(10 * mm, 7 * mm, f'{settings.title} · {today:%d %B %Y}')
        canvas.drawRightString(w - 10 * mm, 7 * mm, f'Page {doc.page}')

    def first_page(canvas, doc):
        w, h = landscape(A4)
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 30 * mm, w, 30 * mm, stroke=0, fill=1)
        canvas.setFillColor(GOLD)
        canvas.rect(0, h - 31 * mm, w, 1 * mm, stroke=0, fill=1)
        footer(canvas, doc)
        canvas.restoreState()

    def later_pages(canvas, doc):
        w, h = landscape(A4)
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 3 * mm, w, 3 * mm, stroke=0, fill=1)
        canvas.setFillColor(GOLD)
        canvas.rect(0, h - 3.6 * mm, w, 0.6 * mm, stroke=0, fill=1)
        footer(canvas, doc)
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=8 * mm, bottomMargin=14 * mm, title=settings.title, author=settings.prepared_by or '')
    story: list = []
    meta = ' · '.join(filter(None, [settings.prepared_by, settings.contact, f'As of {today:%d %B %Y}']))
    head = Table([[Paragraph(escape(settings.title), S['title'])],
                  [Paragraph(escape(settings.subtitle or ''), S['sub'])],
                  [Paragraph(escape(meta), S['sub'])]], colWidths=[277 * mm])
    head.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0.5),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5)]))
    story += [head, Spacer(1, 12 * mm), _kpis(summary, settings), Spacer(1, 4)]

    directs = [r for r in rows if not r[0].is_fund]
    funds = [r for r in rows if r[0].is_fund]
    if directs:
        story.append(Paragraph('Direct investments, SPVs and co-investments', S['h2']))
        story.append(_table(
            [('Company', False), ('Structure', False), ('Round / date', False), ('Entry val.', True), ('Invested', True),
             ('Current', True), ('Realised', True), ('Gross MOIC', True), ('Net MOIC', True), ('IRR', True), ('DPI', True),
             ('Lead / invested with', False), ('Capacity', True)],
            _direct_rows(directs), [36, 24, 21, 16, 16, 16, 16, 15, 15, 17, 12, 55, 18]))
    if funds:
        story.append(CondPageBreak(40 * mm))
        story.append(Paragraph('Fund commitments', S['h2']))
        story.append(_table(
            [('Fund / GP', False), ('Type', False), ('Vintage', True), ('Commitment', True), ('Called', True),
             ('Distributed', True), ('NAV', True), ('Net TVPI', True), ('Net IRR', True), ('DPI', True), ('Unfunded', True),
             ('Capacity', True)],
            _fund_rows(funds), [56, 26, 15, 21, 19, 21, 19, 18, 18, 15, 21, 28]))
    if not rows:
        story.append(Paragraph('No investments are marked for the sheet yet.', S['body']))

    highlights = [(i, m) for i, m in rows if i.highlight]
    if highlights:
        story.append(CondPageBreak(30 * mm))
        story.append(Paragraph('Highlights', S['h2']))
        for inv, m in highlights:
            story.append(Paragraph(f'<b>{escape(inv.name)}</b> — {escape(inv.highlight)}', S['body']))
    if commentary:
        with_notes = [(i, m) for i, m in rows if i.thesis or i.pros or i.cons or i.risks or i.comments.exists()]
        if with_notes:
            story.append(CondPageBreak(60 * mm))
            story.append(Paragraph('Investment commentary', S['h2']))
            for inv, m in with_notes:
                story += _commentary(inv, m)

    story += [Spacer(1, 8), Paragraph('“r” = net figure reported by the GP; other net figures are estimated after the stated '
                                      'fees and carry. IRR is “n.m.” for positions held under a year. Amounts in USD.', S['small'])]
    if settings.disclaimer:
        story += [Spacer(1, 3), Paragraph(escape(settings.disclaimer), S['small'])]
    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    return buf.getvalue()
