"""Build a complete ten-slide English PDF from verified reports and actual screenshots."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
W, H = 1280, 720
INK = HexColor("#23372f")
MUTED = HexColor("#65706a")
PAPER = HexColor("#f5f4ee")
GREEN = HexColor("#244e3d")
RED = HexColor("#a8472d")
LINE = HexColor("#dce0d8")


def load(name):
    path = ROOT / "evals" / name
    return json.loads(path.read_text()) if path.exists() else {}


def build(target: Path, stage="draft"):
    team = json.loads((ROOT / "submission/team.json").read_text())
    evidence = load("results.json")
    live = load("live-pipeline.json")
    semantic = load("live-semantic.json")
    browser = load("browser.json")
    xml = ROOT / "evals/unit-tests.xml"
    test_count = 0
    test_failures = 0
    if xml.exists():
        tree = ET.parse(xml)
        for suite in tree.iter("testsuite"):
            test_count += int(suite.get("tests", "0"))
            test_failures += int(suite.get("failures", "0")) + int(suite.get("errors", "0"))
    target.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(target), pagesize=(W, H))
    c.setTitle("RenderGuard — Blue Bands Collectors — AI Control Layer")
    c.setAuthor(", ".join(team["members"]))
    c.setSubject("HackYeah 2026 Goldman Sachs AI Control Layer. Prepared for team review; not submitted.")

    def text(x, y, content, size=18, font="Helvetica", color=INK):
        c.setFillColor(color)
        c.setFont(font, size)
        c.drawString(x, y, content)

    def paragraph(x, y, content, width=520, size=20, leading=30, color=MUTED):
        words = content.split()
        line = ""
        for word in words:
            if c.stringWidth((line + " " + word).strip(), "Helvetica", size) > width:
                text(x, y, line, size, color=color)
                y -= leading
                line = word
            else:
                line = (line + " " + word).strip()
        if line:
            text(x, y, line, size, color=color)
            y -= leading
        return y

    def frame(n, category, title, subtitle=""):
        c.setFillColor(PAPER)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        text(60, 675, "RENDERGUARD / AI CONTROL LAYER", 11, "Helvetica-Bold", MUTED)
        text(1115, 675, f"{n:02d} / 10", 11, color=MUTED)
        text(60, 610, category.upper(), 12, "Helvetica-Bold", MUTED)
        text(60, 548, title, 42, "Times-Roman")
        if subtitle:
            paragraph(60, 510, subtitle, 1100, 16, 24)
        c.setStrokeColor(LINE)
        c.line(60, 50, 1220, 50)
        text(60, 27, team["team"] + "  /  HackYeah 2026  /  English", 10, color=MUTED)
        text(865, 27, stage.upper() + " - PREPARED FOR REVIEW, NOT SUBMITTED", 9, color=MUTED)

    def rule(y):
        c.setStrokeColor(LINE)
        c.line(60, y, 1220, y)

    def shot(filename, x, y, width, height):
        p = ROOT / "output/playwright" / filename
        if not p.exists():
            return False
        image = ImageReader(str(p))
        iw, ih = image.getSize()
        scale = min(width / iw, height / ih)
        c.drawImage(image, x, y + (height - ih * scale), width=iw * scale, height=ih * scale, mask="auto")
        return True

    frame(1, "Blue Bands Collectors", "The invoice looks right. Does the payment?")
    text(60, 420, "RenderGuard", 76, "Times-Roman", GREEN)
    paragraph(
        60,
        360,
        "An evidence-bound release gate for AI-prepared repeat-supplier EUR payments.",
        780,
        26,
        38,
        color=INK,
    )
    paragraph(60, 250, "Viktor Vitovec  /  Jan Sebastian Rosicky  /  Krystof Bigas", 1060, 20, 30)
    text(60, 176, "LIVE DEMO", 11, "Helvetica-Bold", MUTED)
    text(60, 148, team["demo_url"], 21, color=GREEN)
    c.linkURL(team["demo_url"], (60, 140, 730, 168), relative=0)
    text(60, 109, team["repository_url"], 16, color=GREEN)
    c.linkURL(team["repository_url"], (60, 103, 830, 128), relative=0)
    text(940, 155, "SANDBOX ONLY", 15, "Helvetica-Bold", GREEN)
    paragraph(940, 120, "No bank connected. No money moved.", 260, 13, 20)
    c.showPage()

    frame(
        2,
        "The specific failure",
        "One invoice can carry two payment instructions.",
        "User: an accounts-payable operator preparing a repeat-supplier payment against an approved purchase order.",
    )
    values = [
        ("Visible page", "Account ...1001", "EUR 1,240.00", INK),
        ("Hidden PDF text / QR", "Account ...9999", "Same-looking invoice", RED),
        ("Approved supplier", "Account ...1001", "Independent authority", GREEN),
    ]
    for index, (title, a, b, color) in enumerate(values):
        x = 60 + index * 390
        text(x, 385, title, 23, "Times-Roman", color)
        text(x, 330, a, 26, "Helvetica-Bold", color)
        text(x, 292, b, 18, color=MUTED)
    rule(248)
    paragraph(
        60,
        200,
        "Payment changes must be independently verified using a saved supplier contact. Document agreement alone cannot authorize a new bank account.",
        1100,
        23,
        34,
    )
    text(
        60,
        83,
        "Research: FBI business email compromise guidance; Microsoft vendor-bank approval workflow.",
        11,
        color=MUTED,
    )
    c.showPage()

    frame(3, "Purpose-built workflow", "AI prepares. Independent evidence decides.")
    steps = [
        ("01", "Select authority", "Approved repeat supplier + PO"),
        ("02", "Establish evidence", "Raster / OCR / PDF text / EPC QR"),
        ("03", "Constrain the AI", "Semantic guard + bank handles"),
        ("04", "Approve exact intent", "Reviewer-bound action + evidence"),
        ("05", "Release once", "Protected sandbox ledger receipt"),
    ]
    for index, (number, title, body) in enumerate(steps):
        x = 60 + index * 235
        text(x, 400, number, 40, "Times-Roman", GREEN)
        paragraph(x, 333, title, 200, 21, 28, color=INK)
        paragraph(x, 265, body, 190, 16, 24)
    rule(190)
    paragraph(
        60,
        144,
        "Bank verification is a separate administrator workflow. The assistant cannot change supplier authority, approve itself or execute a payment.",
        1120,
        20,
        30,
    )
    c.showPage()

    frame(
        4,
        "A complete positive path",
        "A legitimate invoice reaches a saved receipt.",
        "Actual rendered PDF -> local model proposal -> human reviewer -> immutable sandbox ledger.",
    )
    shot("release.png", 580, 80, 640, 380)
    y = paragraph(
        60,
        415,
        "The AI receives opaque account handles and evidence-grounded structured fields.",
        440,
        22,
        33,
        color=INK,
    )
    y = paragraph(
        60,
        y - 25,
        "The reviewer sees the exact recipient, EUR amount, invoice and approved obligation.",
        440,
        19,
        29,
    )
    paragraph(
        60,
        y - 25,
        "Execution rechecks authority and records one receipt. A retry returns that same receipt.",
        440,
        19,
        29,
    )
    c.showPage()

    frame(
        5,
        "Concrete adversarial evidence",
        "The page and the payment QR disagree.",
        "The actual QR-swap PDF is blocked before any model dispatch.",
    )
    shot("qr-swap.png", 550, 80, 670, 380)
    y = paragraph(
        60,
        420,
        "Visible recipient: ...1001. Decoded EPC recipient: ...9999. Approved supplier: ...1001.",
        420,
        23,
        34,
        color=RED,
    )
    paragraph(
        60,
        y - 25,
        "Also tested: hidden text recipient / total, QR amount swap, unverified account change, ambiguity and overbilling.",
        420,
        19,
        29,
    )
    c.showPage()

    frame(6, "Hybrid control layer", "Deterministic authority. Semantic interpretation.")
    text(60, 413, "DETERMINISTIC RELEASE CONTROLS", 13, "Helvetica-Bold", GREEN)
    paragraph(
        60,
        377,
        "Identity, models, tools, privacy patterns, literal attack signatures, evidence agreement, supplier/PO, action schema and budget reservations.",
        520,
        21,
        32,
    )
    text(690, 413, "REAL LOCAL SEMANTIC GUARD", 13, "Helvetica-Bold", GREEN)
    paragraph(
        690,
        377,
        "Qwen2.5:3b classifies behavioral overrides in untrusted document content. The proposal model is constrained to evidence-grounded fields.",
        520,
        21,
        32,
    )
    rule(234)
    paragraph(
        60,
        190,
        "Policy and literal signature catalog can be edited live. Historical probes inspect CVE-2025-6514 unsafe MCP authorization endpoints and unsafe pickle formats; they never execute supplied code.",
        1110,
        19,
        29,
    )
    c.showPage()

    frame(7, "Protected execution", "An approval means one exact action.")
    left = [
        "Payment hash",
        "Source PDF + rendered-image hashes",
        "Structured evidence hash",
        "Approved supplier + obligation hashes",
        "Policy version + signature catalog",
        "Workspace, reviewer capability and expiry",
    ]
    for index, value in enumerate(left):
        text(60, 415 - index * 44, value, 20, color=INK)
    paragraph(750, 412, "A change invalidates the approval.", 420, 33, 43, color=GREEN)
    paragraph(
        750,
        290,
        "A single transaction revalidates, consumes approval and inserts the receipt. Unique proposal / invoice constraints prevent duplicate effects.",
        420,
        20,
        31,
    )
    text(750, 140, "8 concurrent retries -> 1 receipt", 24, "Times-Roman", GREEN)
    text(750, 102, "Executable concurrency test; actual SQLite ledger.", 12, color=MUTED)
    c.showPage()

    frame(8, "Reporting and resource control", "Show the decision. Account for the cost.")
    shot("register.png", 620, 80, 600, 380)
    y = paragraph(
        60,
        420,
        "Actual decision trail, policy versions, model tokens, stage latency, bound hashes and immutable receipts.",
        500,
        22,
        33,
        color=INK,
    )
    y = paragraph(
        60,
        y - 25,
        "Export redacted JSONL and sandbox release CSV. Approval tokens never enter exports.",
        500,
        19,
        29,
    )
    paragraph(
        60,
        y - 25,
        "Reserve call / token / cost / concurrency limits before dispatch. Unknown interrupted usage consumes its reservation.",
        500,
        19,
        29,
    )
    c.showPage()

    frame(
        9,
        "Reproducible evidence",
        "Positive cases matter as much as attacks.",
        "Finite synthetic corpus and stated prompts. No universal fraud or prompt-injection guarantee.",
    )
    stats = [
        (
            f"{test_count - test_failures}/{test_count}",
            "Control / integration checks",
            "Actual OCR + labelled provider double",
        ),
        (
            f"{live.get('passed', 0)}/{live.get('total', 0)}",
            "Full live PDF workflows",
            "Real local AI, worker, approval, release",
        ),
        (
            f"{semantic.get('passed', 0)}/{semantic.get('total', 0)}",
            "Real semantic prompt checks",
            "Benign terms and behavioral overrides",
        ),
        (
            f"{browser.get('passed', 0)}/{browser.get('total', 0)}",
            "Headless browser workflows",
            "No mocked network; desktop + mobile",
        ),
    ]
    for index, (number, title, note) in enumerate(stats):
        x = 60 + index * 300
        text(x, 365, number, 58, "Times-Roman", GREEN)
        paragraph(x, 286, title, 270, 19, 28, color=INK)
        paragraph(x, 215, note, 270, 15, 23)
    text(
        60,
        116,
        f"Evidence expectations: {evidence.get('passed', 0)}/{evidence.get('total', 0)}. Full workflow: seven legitimate variants + nine blocked cases.",
        15,
        color=MUTED,
    )
    text(
        60,
        86,
        "Recorded reports include source-content hashes; commands and expected cases are packaged.",
        13,
        color=MUTED,
    )
    c.showPage()

    frame(10, "Ready to inspect and change", "A complete gate, with an explicit boundary.")
    y = paragraph(
        60,
        417,
        "Robustness: exact protected release and adversarial checks. Architecture: isolated worker, modular gateway and provider. Reporting: actual audit and export. Tests: executable positive and negative suite. Scale: bounded resources and a documented migration path.",
        670,
        21,
        32,
        color=INK,
    )
    paragraph(
        60,
        y - 24,
        "Deployed on always-on hosts. No paid key required. Team and submission materials are fully English.",
        670,
        20,
        30,
    )
    text(860, 410, "SUPPORTED", 12, "Helvetica-Bold", GREEN)
    paragraph(
        860,
        377,
        "Repeat supplier / approved EUR obligation / labelled PDF / EPC QR / sandbox ledger.",
        340,
        17,
        26,
    )
    text(860, 246, "PRODUCTION INTEGRATION", 12, "Helvetica-Bold", MUTED)
    paragraph(
        860,
        214,
        "External identity, independently managed ERP authority, disposable workers and an idempotent bank adapter.",
        340,
        17,
        26,
    )
    text(60, 95, team["demo_url"], 22, color=GREEN)
    c.linkURL(team["demo_url"], (60, 87, 760, 119), relative=0)
    c.showPage()
    c.save()
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="submission/presentation.pdf")
    parser.add_argument("--stage", default="draft")
    args = parser.parse_args()
    print(build(ROOT / args.output, args.stage))
