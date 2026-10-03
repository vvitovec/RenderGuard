"""Build ten English slides from scoped reports and native browser evidence captures."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
W, H = 1280, 720
INK = HexColor('#23372f')
MUTED = HexColor('#65706a')
PAPER = HexColor('#f5f4ee')
GREEN = HexColor('#244e3d')
RED = HexColor('#a8472d')
LINE = HexColor('#dce0d8')
PALE = HexColor('#edf2e7')


def load(name):
    path = ROOT / 'evals' / name
    return json.loads(path.read_text()) if path.exists() else {}


def build(target: Path, stage='draft'):
    team = json.loads((ROOT / 'submission/team.json').read_text())
    evidence, live = load('results.json'), load('live-pipeline.json')
    semantic, browser = load('live-semantic.json'), load('browser.json')
    performance = load('performance.json')
    if stage == 'final':
        hashes = [report.get('source_sha') for report in (live, semantic, browser, performance)]
        if not hashes[0] or any(value != hashes[0] for value in hashes):
            raise ValueError('Final deck requires matching source hashes in live, semantic, browser and performance reports')
        if not isinstance(performance.get('gateway', {}).get('p95_ms'), (int, float)):
            raise ValueError('Final deck requires a measured deterministic gateway p95')
    test_count = test_failures = 0
    xml = ROOT / 'evals/unit-tests.xml'
    if xml.exists():
        for suite in ET.parse(xml).iter('testsuite'):
            test_count += int(suite.get('tests', '0'))
            test_failures += int(suite.get('failures', '0')) + int(suite.get('errors', '0'))
    target.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(target), pagesize=(W, H))
    c.setTitle('RenderGuard — Blue Bands Collectors — AI Control Layer')
    c.setAuthor(', '.join(team['members']))
    c.setSubject('HackYeah 2026. Prepared for team review; not submitted.')

    def text(x, y, content, size=18, font='Helvetica', color=INK):
        c.setFillColor(color)
        c.setFont(font, size)
        c.drawString(x, y, str(content))

    def paragraph(x, y, content, width=520, size=20, leading=30, color=MUTED):
        line = ''
        for word in content.split():
            candidate = (line + ' ' + word).strip()
            if line and c.stringWidth(candidate, 'Helvetica', size) > width:
                text(x, y, line, size, color=color)
                y -= leading
                line = word
            else:
                line = candidate
        if line:
            text(x, y, line, size, color=color)
            y -= leading
        return y

    def frame(n, category, title, subtitle=''):
        c.setFillColor(PAPER)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        text(60, 675, 'RENDERGUARD / AI CONTROL LAYER', 11, 'Helvetica-Bold', MUTED)
        text(1115, 675, f'{n:02d} / 10', 11, color=MUTED)
        text(60, 610, category.upper(), 12, 'Helvetica-Bold', MUTED)
        size = min(42, 1160 / max(1, c.stringWidth(title, 'Times-Roman', 42)) * 42)
        text(60, 548, title, size, 'Times-Roman')
        if subtitle:
            paragraph(60, 510, subtitle, 1130, 16, 24)
        c.setStrokeColor(LINE)
        c.line(60, 50, 1220, 50)
        text(60, 27, team['team'] + ' / HackYeah 2026 / English', 10, color=MUTED)
        text(865, 27, stage.upper() + ' — PREPARED FOR REVIEW', 9, color=MUTED)

    def rule(y):
        c.setStrokeColor(LINE)
        c.line(60, y, 1220, y)

    def shot(filename, x, y, width, height):
        path = ROOT / 'output/playwright' / filename
        if not path.exists():
            raise FileNotFoundError(f'Capture native browser evidence before building the deck: {path}')
        image = ImageReader(str(path))
        iw, ih = image.getSize()
        scale = min(width / iw, height / ih)
        dw, dh = iw * scale, ih * scale
        c.drawImage(image, x + (width - dw) / 2, y + (height - dh) / 2, width=dw, height=dh, mask='auto')

    def box(x, y, width, height, title, body, accent=False):
        c.setFillColor(PALE if accent else HexColor('#fffef9'))
        c.setStrokeColor(GREEN if accent else LINE)
        c.roundRect(x, y, width, height, 4, fill=1, stroke=1)
        text(x + 14, y + height - 25, title, 16, 'Helvetica-Bold', GREEN if accent else INK)
        paragraph(x + 14, y + height - 47, body, width - 28, 12, 17)

    def arrow(x1, y1, x2, y2):
        c.setStrokeColor(GREEN)
        c.setLineWidth(1.2)
        c.line(x1, y1, x2, y2)
        if x2 > x1:
            c.line(x2, y2, x2 - 6, y2 + 4)
            c.line(x2, y2, x2 - 6, y2 - 4)
        elif y2 < y1:
            c.line(x2, y2, x2 - 4, y2 + 6)
            c.line(x2, y2, x2 + 4, y2 + 6)

    frame(1, 'Blue Bands Collectors', 'The invoice looks right. Does the payment?')
    text(60, 418, 'RenderGuard', 76, 'Times-Roman', GREEN)
    paragraph(60, 355, 'Release controls for AI-prepared repeat-supplier EUR payments.', 850, 28, 40, INK)
    paragraph(60, 245, 'Viktor Vitovec / Jan Sebastian Rosicky / Krystof Bigas', 1100, 20, 30)
    text(60, 171, 'LIVE DEMO / SOURCE', 11, 'Helvetica-Bold', MUTED)
    text(60, 141, team['demo_url'], 22, color=GREEN)
    c.linkURL(team['demo_url'], (60, 135, 770, 165), relative=0)
    text(60, 103, team['repository_url'], 17, color=GREEN)
    c.linkURL(team['repository_url'], (60, 95, 830, 122), relative=0)
    text(935, 156, 'SANDBOX ONLY', 15, 'Helvetica-Bold', GREEN)
    paragraph(935, 121, 'No bank connected. No money moved.', 280, 15, 22)
    c.showPage()

    frame(2, 'The concrete failure', 'One invoice can carry two payment instructions.', 'Accounts payable: prepare a repeat-supplier payment against an independently approved obligation.')
    for index, (title, account, caption, color) in enumerate([
        ('Visible page', '...1001', 'EUR 1,240.00', INK),
        ('PDF text / payment QR', '...9999', 'Machine-readable instructions', RED),
        ('Approved supplier', '...1001', 'Independent payment authority', GREEN),
    ]):
        x = 60 + index * 390
        text(x, 393, title, 22, 'Times-Roman', color)
        text(x, 331, account, 43, 'Helvetica-Bold', color)
        text(x, 292, caption, 16, color=MUTED)
    rule(251)
    paragraph(60, 204, 'Agreement is necessary, but an invoice cannot approve its own new bank account. A saved supplier contact and approved obligation remain the authority.', 1100, 23, 34)
    text(60, 87, 'Grounded in FBI payment-change guidance and existing Microsoft / SAP supplier-master workflows.', 12, color=MUTED)
    c.showPage()

    frame(3, 'Architecture / reusable gateway + payment adapter', 'The control layer sits before the effect.', 'The UI inspects decisions. Enforcement lives in the gateway and protected executor.')
    box(60, 335, 195, 100, 'Untrusted PDF', 'Operator selects approved supplier + obligation first.')
    box(285, 335, 230, 100, 'Isolated worker', 'Pixels / OCR / PDF text / EPC QR. No network, ledger or signing secret.')
    box(545, 335, 270, 100, 'Policy gateway', 'Identity, privacy, literal feed, resource reservations and evidence checks.', True)
    box(845, 335, 370, 100, 'Local AI boundary', 'Semantic guard + constrained proposal assistant. Opaque account handles; no approval or release authority.')
    arrow(255, 385, 285, 385)
    arrow(515, 385, 545, 385)
    arrow(815, 385, 845, 385)
    box(60, 180, 350, 105, 'Registered proposal / SDK', 'Exact action grounding. Reusable model/tool/resource policy hooks; payment evidence is the specialized adapter.', True)
    box(445, 180, 335, 105, 'Authenticated reviewer', 'Approves the exact evidence, payment, supplier, obligation and configuration versions.')
    box(815, 180, 400, 105, 'Protected executor + ledger', 'Revalidate + atomically consume approval and obligation. One sandbox effect; safe retry.', True)
    arrow(410, 232, 445, 232)
    arrow(780, 232, 815, 232)
    arrow(1020, 335, 1020, 300)
    c.line(1020, 300, 235, 300)
    arrow(235, 300, 235, 285)
    paragraph(60, 132, 'Audit and stage telemetry span both boundaries. The PDF worker sees only the document queue; the AI never receives a reviewer capability.', 1140, 16, 24)
    c.showPage()

    frame(4, 'Complete positive path', 'A real local proposal reaches one saved receipt.', 'Actual browser captures: the model receives account_1; the reviewer releases the exact synthetic action.')
    text(60, 458, 'MINIMIZED OUTGOING MODEL INPUT', 12, 'Helvetica-Bold', GREEN)
    shot('model-input.png', 60, 132, 695, 300)
    text(795, 458, 'EXACT ACTION / SANDBOX RECEIPT', 12, 'Helvetica-Bold', GREEN)
    shot('release-detail.png', 795, 100, 425, 332)
    paragraph(60, 91, 'The agent prepares; the human approves. Retrying returns the existing receipt.', 710, 17, 25, INK)
    c.showPage()

    frame(5, 'Adversarial evidence', 'A conflicting QR never reaches the model.', 'Visible / approved ...1001 vs decoded EPC ...9999. Final block and zero dispatch are observable.')
    shot('qr-detail.png', 60, 125, 1160, 345)
    paragraph(60, 92, 'Hidden recipients / totals, unverified changes, ambiguous evidence and reusing an obligation are held or blocked.', 1140, 17, 25)
    c.showPage()

    frame(6, 'Hybrid, configurable controls', 'Change the policy. Observe the real decision.')
    shot('controls.png', 595, 98, 625, 366)
    y = paragraph(60, 435, 'Deterministic controls protect identity, data, tools, budgets and exact release authority.', 485, 22, 32, INK)
    y = paragraph(60, y - 17, 'The real Qwen2.5:3b semantic guard recognizes behavioral instructions in untrusted content. Risk and review/block thresholds are visible.', 485, 18, 27)
    paragraph(60, y - 17, 'Live literal feed: allowed → add canary → blocked → restore → allowed. Supplied data never becomes executable code.', 485, 18, 27)
    text(60, 95, 'POST /api/sdk/propose  {document_id, payment: {account_ref, ...}}', 11, 'Courier', GREEN)
    c.showPage()

    frame(7, 'Protected execution', 'An approval means one exact action.')
    for index, value in enumerate([
        'Payment hash + source / rendered-image hashes',
        'Structured evidence hash',
        'Approved supplier + obligation versions',
        'Policy + literal signature catalog versions',
        'Workspace, reviewer, expiry and approval audience',
    ]):
        text(60, 418 - index * 44, value, 20)
    paragraph(740, 415, 'A change invalidates the approval.', 460, 32, 43, GREEN)
    paragraph(740, 285, 'One transaction revalidates intent, consumes approval and the approved obligation, and inserts the sandbox receipt.', 460, 20, 31)
    text(740, 133, 'Concurrent retries → one receipt', 24, 'Times-Roman', GREEN)
    paragraph(60, 145, 'Changing the invoice number cannot pay the same full obligation again.', 600, 18, 27)
    text(60, 93, 'Synthetic ledger only; a real bank adapter would need equivalent external idempotency.', 13, color=MUTED)
    c.showPage()

    frame(8, 'Reporting / performance', 'Report the final decision and the remaining budget.')
    shot('audit-detail.png', 60, 273, 1160, 185)
    p95 = performance.get('gateway', {}).get('p95_ms')
    gateway_text = f'{p95:,.2f} ms' if isinstance(p95, (int, float)) else 'Not measured'
    text(60, 233, 'DETERMINISTIC GATEWAY p95', 11, 'Helvetica-Bold', GREEN)
    text(60, 183, gateway_text, 34, 'Times-Roman', GREEN)
    paragraph(350, 232, f"{performance.get('requests', 0)} sequential measured requests, including policy lookup and audit persistence. No model, OCR or network; not a throughput benchmark.", 855, 17, 25)
    workflow = live.get('p95_end_to_end_ms')
    workflow_text = f'{workflow:,.0f} ms' if isinstance(workflow, (int, float)) else 'not measured'
    paragraph(60, 130, f'Full workflow p95: {workflow_text}. The UI reports OCR, semantic inference, proposal inference, queue and executor separately. Redacted JSONL and sandbox CSV are exportable.', 1140, 17, 25)
    c.showPage()

    frame(9, 'Reproducible evidence', 'Positive cases matter as much as attacks.', 'Finite synthetic cases and stated prompts. Probabilistic detection is not a universal guarantee.')
    stats = [
        (f'{test_count - test_failures}/{test_count}', 'Control / integration checks', 'Actual OCR; labelled provider doubles'),
        (f"{live.get('passed', 0)}/{live.get('total', 0)}", 'Full hosted PDF workflows', 'Real local AI, human approval, ledger'),
        (f"{semantic.get('passed', 0)}/{semantic.get('total', 0)}", 'Real semantic prompt checks', 'Benign, role / delimiter and language variants'),
        (f"{browser.get('passed', 0)}/{browser.get('total', 0)}", 'Headless browser checks', 'Actual API, model, feed and exports'),
    ]
    for index, (value, title, note) in enumerate(stats):
        x = 60 + index * 300
        text(x, 365, value, 56, 'Times-Roman', GREEN)
        paragraph(x, 286, title, 270, 19, 28, INK)
        paragraph(x, 215, note, 270, 15, 23)
    counts = {verdict: sum(item.get('expected') == verdict for item in live.get('cases', [])) for verdict in ('allow', 'block', 'review')}
    text(60, 116, f"Hosted corpus: {counts['allow']} permitted / {counts['block']} blocked / {counts['review']} held. Evidence-only checks: {evidence.get('passed', 0)}/{evidence.get('total', 0)}.", 15, color=MUTED)
    text(60, 86, 'Source / release hashes and exact commands are packaged. Recorded evidence is clearly separated from live probes.', 13, color=MUTED)
    c.showPage()

    frame(10, 'Ready to inspect', 'Useful at one boundary. Honest about the rest.')
    paragraph(60, 415, 'Developer integration: scoped evidence and proposal API. Operations: isolated worker, bounded local model, persistent approval / ledger state. Judges: mutate policy and feeds, submit new prompts, inspect actual audit and replay tests.', 680, 22, 33, INK)
    paragraph(60, 225, 'The contribution is the evidence-to-execution chain: representations, independent authority, minimized AI, exact human approval and one protected effect.', 680, 21, 31)
    text(860, 415, 'SUPPORTED', 12, 'Helvetica-Bold', GREEN)
    paragraph(860, 382, 'Repeat supplier / approved full EUR obligation / labelled PDF / optional EPC QR / sandbox ledger.', 340, 17, 26)
    text(860, 242, 'PRODUCTION INTEGRATION', 12, 'Helvetica-Bold', MUTED)
    paragraph(860, 210, 'External identity, independent ERP master data, disposable workers and bank-side idempotency. No claim of invoice authenticity.', 340, 17, 26)
    text(60, 95, team['demo_url'], 22, color=GREEN)
    c.linkURL(team['demo_url'], (60, 87, 760, 119), relative=0)
    c.showPage()
    c.save()
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='submission/presentation.pdf')
    parser.add_argument('--stage', default='draft')
    args = parser.parse_args()
    print(build(ROOT / args.output, args.stage))
