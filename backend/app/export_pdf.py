"""export_pdf(session_id) - renders the session via WeasyPrint (HTML/CSS ->
PDF), one page per topic (one session = one topic), and returns
{pdf_url}. PDFs land in EXPORT_DIR and are served under /static.

WeasyPrint is imported lazily inside export_session_pdf so the API still
boots on machines without the Pango/GTK libraries (common on Windows); only
the PDF export endpoint is affected in that case.
"""
import asyncio
import base64
import html as html_mod
import json
import os
import re

from . import db
from .config import settings

CSS = """
@page { size: A4; margin: 22mm 18mm; }
body { font-family: Georgia, 'Times New Roman', serif; color: #3d3929;
       font-size: 10.5pt; line-height: 1.55; }
h1 { font-size: 17pt; margin: 0 0 6pt; }
h2 { font-size: 12pt; margin: 16pt 0 4pt; color: #b4552f; }
h4 { margin: 4pt 0 2pt; font-size: 10pt; }
p { margin: 4pt 0; }
.card { border: 1pt solid #e5e2d9; border-radius: 6pt; padding: 6pt 8pt;
        margin: 4pt 0; page-break-inside: avoid; }
.card .q { font-weight: bold; }
.card .a { color: #6b6757; }
.cols { display: flex; gap: 16pt; }
.cols > div { flex: 1; }
ul { margin: 2pt 0 4pt; padding-left: 14pt; }
.band { display: inline-block; border: 1pt solid #999; border-radius: 8pt;
        padding: 1pt 7pt; font-size: 9pt; font-weight: bold; margin-bottom: 4pt; }
.flow { max-width: 100%; margin-top: 8pt; }
"""


def _mermaid_img_url(source: str) -> str:
    """mermaid.ink renders the flowchart server-side so WeasyPrint can embed
    it as an image (WeasyPrint cannot run the Mermaid JS client)."""
    state = json.dumps({"code": source, "mermaid": {"theme": "neutral"}})
    return "https://mermaid.ink/img/" + base64.urlsafe_b64encode(
        state.encode("utf-8")
    ).decode("ascii")


def _strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"[*_`#>]", "", text)
    return text.strip()


def _build_html(session: dict, messages: list[dict], assets: dict, evaluation: dict | None) -> str:
    topic = session.get("topic") or "Session"
    ai_texts = [m["content"] for m in messages if m["role"] == "ai"]
    explanation = _strip_markdown(max(ai_texts, key=len)) if ai_texts else ""

    analogy = assets.get("analogy") or {}
    flashcards = (assets.get("flashcards") or {}).get("cards") or []
    mermaid_src = (assets.get("mermaid") or {}).get("mermaid_source")

    fc_html = "".join(
        f"<div class='card'><p class='q'>{html_mod.escape(c['question'])}</p>"
        f"<p class='a'>A: {html_mod.escape(c['answer'])}</p></div>"
        for c in flashcards
    )

    if evaluation:
        covered = "".join(
            f"<li>{html_mod.escape(x)}</li>"
            for x in evaluation.get("covered_labels") or evaluation.get("covered") or []
        )
        missing = "".join(
            f"<li>{html_mod.escape(x)}</li>"
            for x in evaluation.get("missing_labels") or evaluation.get("missing") or []
        )
        ev_html = (
            f"<div class='band'>{html_mod.escape(evaluation['band'])}</div>"
            f"<div class='cols'><div><h4>Covered</h4><ul>{covered}</ul></div>"
            f"<div><h4>Missing</h4><ul>{missing}</ul></div></div>"
            f"<p>{html_mod.escape(evaluation['feedback'])}</p>"
        )
    else:
        ev_html = "<p>No teach-back attempt recorded for this session yet.</p>"

    flowchart = (
        f"<h2>Flowchart</h2><img class='flow' src='{_mermaid_img_url(mermaid_src)}'/>"
        if mermaid_src
        else ""
    )

    return f"""<!doctype html>
<html><head><meta charset='utf-8'><style>{CSS}</style></head>
<body>
  <h1>{html_mod.escape(topic)}</h1>
  <h2>Explanation</h2>
  <p>{html_mod.escape(explanation)}</p>
  <h2>Analogy</h2>
  <p>{html_mod.escape(analogy.get('analogy_text', ''))}</p>
  <h2>Flashcards</h2>
  {fc_html}
  <h2>Teach-back</h2>
  {ev_html}
  {flowchart}
</body></html>"""


async def export_session_pdf(session_id) -> dict:
    """Gather the session, render one page, return {pdf_url}."""
    from weasyprint import HTML  # lazy: needs Pango/GTK system libraries

    row = await db.fetchrow("SELECT * FROM sessions WHERE id=$1", session_id)
    if row is None:
        raise ValueError("session not found")
    session = dict(row)

    rows = await db.fetch(
        "SELECT role, content FROM session_messages WHERE session_id=$1 "
        "ORDER BY created_at, id",
        session_id,
    )
    messages = [dict(r) for r in rows]

    arows = await db.fetch(
        "SELECT asset_type, content FROM generated_assets WHERE session_id=$1 "
        "ORDER BY created_at",
        session_id,
    )
    assets: dict = {}
    for r in arows:
        content = r["content"]
        if content is None:
            continue
        assets[r["asset_type"]] = (
            json.loads(content) if isinstance(content, str) else content
        )

    html = _build_html(session, messages, assets, assets.get("evaluation"))

    os.makedirs(settings.export_dir, exist_ok=True)
    filename = f"{session_id}.pdf"
    path = os.path.join(settings.export_dir, filename)
    # WeasyPrint is synchronous; keep the event loop responsive.
    await asyncio.to_thread(lambda: HTML(string=html).write_pdf(path))
    return {"pdf_url": f"/static/exports/{filename}"}
