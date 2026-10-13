"""Export a transcript to TXT, SRT, VTT, JSON and DOCX.

DOCX is written directly as Office Open XML with the standard library, so no
extra package is needed.
"""

import io
import json
import re
import zipfile
from xml.sax.saxutils import escape

FORMATS = {
    "txt": "text/plain; charset=utf-8",
    "timestamps.txt": "text/plain; charset=utf-8",
    "srt": "application/x-subrip; charset=utf-8",
    "vtt": "text/vtt; charset=utf-8",
    "json": "application/json",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def clock(seconds, sep=".", always_hours=True):
    """12.5 -> '00:00:12.500' (or '00:00:12,500' for SRT)."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def short_clock(seconds):
    """12.5 -> '0:12', 3725 -> '1:02:05'."""
    s = int(seconds)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def paragraphs(segments, pause=2.0, max_chars=600):
    """Group segments into readable paragraphs, breaking at long pauses."""
    result, current, last_end = [], [], None
    for seg in segments:
        long_pause = last_end is not None and seg["start"] - last_end > pause
        too_long = sum(len(s["text"]) for s in current) > max_chars
        if current and (long_pause or too_long):
            result.append(current)
            current = []
        current.append(seg)
        last_end = seg["end"]
    if current:
        result.append(current)
    return [{"start": p[0]["start"], "text": " ".join(s["text"] for s in p)} for p in result]


def to_txt(segments):
    return "\n\n".join(p["text"] for p in paragraphs(segments)) + "\n"


def to_timestamped_txt(segments):
    return "\n".join(f"[{short_clock(s['start'])}] {s['text']}" for s in segments) + "\n"


def to_srt(segments):
    blocks = []
    for i, s in enumerate(segments, 1):
        blocks.append(f"{i}\n{clock(s['start'], ',')} --> {clock(s['end'], ',')}\n{s['text']}\n")
    return "\n".join(blocks)


def to_vtt(segments):
    cues = [f"{clock(s['start'])} --> {clock(s['end'])}\n{s['text']}\n" for s in segments]
    return "WEBVTT\n\n" + "\n".join(cues)


def to_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------ DOCX ----

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="320" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="Meta"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="666666"/><w:sz w:val="18"/></w:rPr></w:style>
</w:styles>"""


def _run(text, bold=False, color=None):
    props = ("<w:b/>" if bold else "") + (f'<w:color w:val="{color}"/>' if color else "")
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _para(runs, style=None, indent=False):
    ppr = ""
    if style or indent:
        ppr = "<w:pPr>"
        ppr += f'<w:pStyle w:val="{style}"/>' if style else ""
        ppr += '<w:ind w:left="360" w:hanging="360"/>' if indent else ""
        ppr += "</w:pPr>"
    return f"<w:p>{ppr}{''.join(runs)}</w:p>"


def _markdown_paragraphs(markdown):
    """Very small Markdown to DOCX: '## heading', '- bullet', '**bold**', text."""
    out = []
    for line in markdown.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line.startswith("#"):
            out.append(_para([_run(line.lstrip("# ").strip())], "Heading2"))
            continue
        bullet = re.match(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)", line)
        text = bullet.group(1) if bullet else line
        runs = [
            _run(part, bold=(i % 2 == 1)) for i, part in enumerate(text.split("**")) if part
        ]
        if bullet:
            runs.insert(0, _run("•\t"))
        out.append(_para(runs, indent=bool(bullet)))
    return out


def to_docx(result):
    """result: {"title", "meta", "segments", "summary": {...}}"""
    body = [_para([_run(result.get("title", "Transcript"))], "Title")]
    if result.get("meta"):
        body.append(_para([_run(result["meta"])], "Meta"))

    summary = result.get("summary") or {}
    if summary.get("ai"):
        body.append(_para([_run("Summary")], "Heading1"))
        body += _markdown_paragraphs(summary["ai"])
    elif summary.get("key_points"):
        body.append(_para([_run("Key points")], "Heading1"))
        for point in summary["key_points"]:
            body.append(
                _para(
                    [_run("•\t"), _run(f"[{short_clock(point['start'])}] ", color="1F4E79"),
                     _run(point["text"])],
                    indent=True,
                )
            )
        if summary.get("keywords"):
            body.append(
                _para([_run("Keywords: ", bold=True), _run(", ".join(summary["keywords"]))])
            )

    body.append(_para([_run("Transcript")], "Heading1"))
    for p in paragraphs(result["segments"]):
        body.append(_para([_run(f"[{short_clock(p['start'])}]  ", color="1F4E79"), _run(p["text"])]))

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(body) +
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
        'w:header="709" w:footer="709" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/document.xml", document)
    return buffer.getvalue()


def export(result, fmt):
    """Return bytes for the requested format."""
    segments = result["segments"]
    if fmt == "txt":
        data = to_txt(segments)
    elif fmt == "timestamps.txt":
        data = to_timestamped_txt(segments)
    elif fmt == "srt":
        data = to_srt(segments)
    elif fmt == "vtt":
        data = to_vtt(segments)
    elif fmt == "json":
        data = to_json(result)
    elif fmt == "docx":
        return to_docx(result)
    else:
        raise ValueError("Unknown format: " + fmt)
    return data.encode("utf-8")
