# File: utils/document_preview.py
# Purpose: Render the case model as a document-style HTML/text preview.
# Encoding: UTF-8
"""On-screen rendering of the complaint before export.

The exported Word file remains authoritative. This module renders the same
model content for review, using the shared party/agent formatting from
:mod:`utils.doc_generator` so the preview and the DOCX cannot drift apart.
Every user-provided value is HTML-escaped before it reaches the preview.
"""

import html

from utils.doc_generator import DocumentGenerator


def _escape(value):
    return html.escape(str(value or ""))


def _party_label(role, index, total):
    return role if total == 1 else f"{role}{index}"


def _party_blocks(model, plaintiff_label="原告", defendant_label="被告",
                  agent_label="诉讼代理人"):
    """Return ``[(label, line), ...]`` for plaintiffs, agent and defendants."""
    blocks = []
    plaintiffs = list(model.party_manager.plaintiffs)
    for index, party in enumerate(plaintiffs, 1):
        blocks.append(
            (
                _party_label(plaintiff_label, index, len(plaintiffs)),
                DocumentGenerator.format_party_line(party),
            )
        )

    agent_text = DocumentGenerator.format_agent_text(getattr(model, "agent", None))
    if agent_text:
        blocks.append((agent_label, agent_text))

    defendants = list(model.party_manager.defendants)
    for index, party in enumerate(defendants, 1):
        blocks.append(
            (
                _party_label(defendant_label, index, len(defendants)),
                DocumentGenerator.format_party_line(party),
            )
        )
    return blocks


def _appendix_text(model, copy_label="本状"):
    defendant_count = len(model.party_manager.defendants)
    if defendant_count <= 0:
        return ""
    return f"附：{copy_label}副本{defendant_count}份。"


def _build_text(title, party_blocks, claim_heading, claims, facts, appendix,
                destination, signer_label):
    lines = [title, ""]
    for label, line in party_blocks:
        lines.append(f"{label}：{line}")

    lines.extend(["", claim_heading])
    for index, claim in enumerate(claims, 1):
        lines.append(f"{index}. {claim}")

    lines.extend(["", "事实与理由：", facts])

    if appendix:
        lines.extend(["", appendix])

    lines.extend(["", "此致", str(destination or ""), "", f"{signer_label}：", "年   月   日"])
    return "\n".join(lines)


def build_complaint_text(model):
    """Return a plain-text rendering of the complaint for tests/fallbacks."""
    return _build_text(
        "民 事 起 诉 状",
        _party_blocks(model),
        "诉讼请求：",
        model.all_claims(),
        model.all_facts(),
        _appendix_text(model),
        model.court_name,
        "具状人",
    )


def build_arbitration_text(model):
    """Return a plain-text rendering of the labour arbitration application."""
    return _build_text(
        "劳 动 仲 裁 申 请 书",
        _party_blocks(model, "申请人", "被申请人", "委托代理人"),
        "仲裁请求：",
        model.all_arbitration_claims(),
        model.all_arbitration_facts(),
        _appendix_text(model, "本申请书"),
        getattr(model, "arb_commission", ""),
        "申请人",
    )


def _build_html(title, party_blocks, claim_heading, claims, facts, appendix,
                destination, signer_label):
    party_html = "\n".join(
        f'<p class="party"><span class="label">{_escape(label)}：</span>{_escape(line)}</p>'
        for label, line in party_blocks
    )

    # Qt's HTML engine does not apply the CSS ``text-indent`` property, so the
    # conventional two-character first-line indent is rendered with ideographic
    # spaces. This affects the preview only; the DOCX keeps real paragraph
    # indentation.
    indent = "&#12288;&#12288;"
    claims_html = "\n".join(
        f'<p class="claim">{indent}{index}. {_escape(claim)}</p>'
        for index, claim in enumerate(claims, 1)
    )

    fact_paragraphs = [
        part.strip() for part in str(facts).split("\n\n") if part.strip()
    ]
    facts_html = "\n".join(
        f'<p class="body">{indent}{_escape(part).replace(chr(10), "<br/>")}</p>'
        for part in fact_paragraphs
    )
    appendix_html = f'<p class="appendix">{indent}{_escape(appendix)}</p>' if appendix else ""
    destination = _escape(destination)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
    body {{
        margin: 0;
        padding: 0;
        background-color: #ffffff;
        color: #000000;
        font-family: "FangSong", "FangSong_GB2312", "STFangsong", "SimSun", serif;
        font-size: 12pt;
        line-height: 1.9;
    }}
    .page {{
        padding: 32px 48px 40px 48px;
    }}
    h1 {{
        margin: 0 0 28px 0;
        font-family: "SimSun", "Songti SC", serif;
        font-size: 22pt;
        font-weight: normal;
        text-align: center;
        letter-spacing: 2px;
    }}
    p {{
        margin: 0 0 6px 0;
    }}
    .party {{
        text-indent: 0;
    }}
    .label, .heading {{
        font-family: "SimHei", "Microsoft YaHei", sans-serif;
    }}
    .heading {{
        margin-top: 18px;
        margin-bottom: 8px;
    }}
    .claim, .body, .appendix {{
        text-align: justify;
    }}
    .appendix {{
        margin-top: 14px;
    }}
    .court {{
        text-indent: 0;
    }}
    .signature {{
        margin-top: 28px;
        text-align: right;
    }}
    .signature p {{
        margin-bottom: 10px;
    }}
</style>
</head>
<body>
<div class="page">
    <h1>{_escape(title)}</h1>
    {party_html}
    <p class="heading">{_escape(claim_heading)}</p>
    {claims_html}
    <p class="heading">事实与理由：</p>
    <p class="body">{facts_html}</p>
    {appendix_html}
    <p class="court">此致</p>
    <p class="court">{destination}</p>
    <div class="signature">
        <p>{_escape(signer_label)}：</p>
        <p>年&nbsp;&nbsp;&nbsp;月&nbsp;&nbsp;&nbsp;日</p>
    </div>
</div>
</body>
</html>"""


def build_complaint_html(model):
    """Return a self-contained HTML rendering with an A4-like page frame."""
    return _build_html(
        "民 事 起 诉 状",
        _party_blocks(model),
        "诉讼请求：",
        model.all_claims(),
        model.all_facts(),
        _appendix_text(model),
        model.court_name,
        "具状人",
    )


def build_arbitration_html(model):
    """Return a self-contained HTML rendering of the arbitration application."""
    return _build_html(
        "劳 动 仲 裁 申 请 书",
        _party_blocks(model, "申请人", "被申请人", "委托代理人"),
        "仲裁请求：",
        model.all_arbitration_claims(),
        model.all_arbitration_facts(),
        _appendix_text(model, "本申请书"),
        getattr(model, "arb_commission", ""),
        "申请人",
    )
