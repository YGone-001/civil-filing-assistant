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


def _party_blocks(model):
    """Return ``[(label, line), ...]`` for plaintiffs, agent and defendants."""
    blocks = []
    plaintiffs = list(model.party_manager.plaintiffs)
    for index, party in enumerate(plaintiffs, 1):
        blocks.append(
            (
                _party_label("原告", index, len(plaintiffs)),
                DocumentGenerator.format_party_line(party),
            )
        )

    agent_text = DocumentGenerator.format_agent_text(getattr(model, "agent", None))
    if agent_text:
        blocks.append(("诉讼代理人", agent_text))

    defendants = list(model.party_manager.defendants)
    for index, party in enumerate(defendants, 1):
        blocks.append(
            (
                _party_label("被告", index, len(defendants)),
                DocumentGenerator.format_party_line(party),
            )
        )
    return blocks


def _appendix_text(model):
    defendant_count = len(model.party_manager.defendants)
    if defendant_count <= 0:
        return ""
    return f"附：本状副本{defendant_count}份。"


def build_complaint_text(model):
    """Return a plain-text rendering of the complaint for tests/fallbacks."""
    lines = ["民 事 起 诉 状", ""]
    for label, line in _party_blocks(model):
        lines.append(f"{label}：{line}")

    lines.extend(["", "诉讼请求："])
    for index, claim in enumerate(model.render_claims(), 1):
        lines.append(f"{index}. {claim}")

    lines.extend(["", "事实与理由：", model.render_facts()])

    appendix = _appendix_text(model)
    if appendix:
        lines.extend(["", appendix])

    lines.extend(["", "此致", str(model.court_name or ""), "", "具状人：", "年   月   日"])
    return "\n".join(lines)


def build_complaint_html(model):
    """Return a self-contained HTML rendering with an A4-like page frame."""
    party_html = "\n".join(
        f'<p class="party"><span class="label">{_escape(label)}：</span>{_escape(line)}</p>'
        for label, line in _party_blocks(model)
    )

    # Qt's HTML engine does not apply the CSS ``text-indent`` property, so the
    # conventional two-character first-line indent is rendered with ideographic
    # spaces. This affects the preview only; the DOCX keeps real paragraph
    # indentation.
    indent = "&#12288;&#12288;"
    claims_html = "\n".join(
        f'<p class="claim">{indent}{index}. {_escape(claim)}</p>'
        for index, claim in enumerate(model.render_claims(), 1)
    )

    facts_html = indent + _escape(model.render_facts()).replace("\n", "<br/>")
    appendix = _appendix_text(model)
    appendix_html = f'<p class="appendix">{indent}{_escape(appendix)}</p>' if appendix else ""
    court = _escape(model.court_name)

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
    <h1>民 事 起 诉 状</h1>
    {party_html}
    <p class="heading">诉讼请求：</p>
    {claims_html}
    <p class="heading">事实与理由：</p>
    <p class="body">{facts_html}</p>
    {appendix_html}
    <p class="court">此致</p>
    <p class="court">{court}</p>
    <div class="signature">
        <p>具状人：</p>
        <p>年&nbsp;&nbsp;&nbsp;月&nbsp;&nbsp;&nbsp;日</p>
    </div>
</div>
</body>
</html>"""
