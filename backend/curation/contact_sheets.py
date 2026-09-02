"""
backend/curation/contact_sheets.py

Milestone 18A: Private Visual Contact Sheet Generator.
Renders responsive HTML contact sheet galleries with tile cards showing
image thumbnails, dimensions, page provenance, proposed triage class,
and candidate decision status for rapid human review.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import Any, Dict, List

from backend.curation.image_inventory import ImageRecord
from backend.curation.image_triage import DecisionStatus, TriageResult

logger = logging.getLogger(__name__)


class ContactSheetGenerator:
    """Renders HTML review contact sheets for extracted reference images."""

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _status_color(status: DecisionStatus | str) -> str:
        s = status.value if hasattr(status, "value") else str(status)
        if s == DecisionStatus.AUTO_KEEP_CANDIDATE.value:
            return "#10b981"  # Emerald
        elif s == DecisionStatus.AUTO_REJECT_CANDIDATE.value:
            return "#ef4444"  # Rose/Red
        elif s == DecisionStatus.HUMAN_REVIEW_REQUIRED.value:
            return "#f59e0b"  # Amber
        return "#64748b"  # Slate

    def render_contact_sheet(
        self,
        records: List[ImageRecord],
        triage_results: List[TriageResult],
        title: str = "Milestone 18A — Image Curation Contact Sheet",
        sheet_filename: str = "contact_sheet_index.html",
        max_images: int = 300,
    ) -> Path:
        """
        Renders a self-contained HTML gallery for the given records and triage results.
        """
        output_file = self.output_dir / sheet_filename
        triage_map = {t.extraction_id: t for t in triage_results}

        # Slice to max_images for responsiveness
        selected_records = records[:max_images]

        tiles_html = []
        for rec in selected_records:
            triage = triage_map.get(rec.extraction_id)
            status_val = triage.decision_status.value if triage else "UNKNOWN"
            triage_cls = triage.triage_class.value if triage else "UNKNOWN"
            color = self._status_color(status_val)

            # Build relative image source path from contact_sheet location to image file
            img_rel_path = f"../{rec.filename}"

            tile = f"""
            <div class="tile" style="border-top: 4px solid {color};">
                <div class="thumb-container">
                    <a href="{html.escape(img_rel_path)}" target="_blank" title="Click to view full image">
                        <img src="{html.escape(img_rel_path)}" alt="{html.escape(rec.filename)}" loading="lazy" />
                    </a>
                </div>
                <div class="info">
                    <div class="badge-row">
                        <span class="badge" style="background-color: {color}22; color: {color}; border: 1px solid {color}88;">
                            {html.escape(status_val)}
                        </span>
                        <span class="badge badge-class">
                            {html.escape(triage_cls)}
                        </span>
                    </div>
                    <div class="filename" title="{html.escape(rec.filename)}">{html.escape(rec.filename)}</div>
                    <div class="meta-row">
                        <span><strong>PDF:</strong> p.{rec.pdf_page or '?'}</span>
                        <span><strong>Textbook:</strong> p.{rec.textbook_page or '?'}</span>
                        <span><strong>Fig:</strong> #{rec.figure_index or '?'}</span>
                    </div>
                    <div class="meta-row">
                        <span>{rec.width} &times; {rec.height} px</span>
                        <span>{round(rec.file_size_bytes / 1024, 1)} KB</span>
                        <span>Entropy: {rec.entropy}</span>
                    </div>
                </div>
            </div>
            """
            tiles_html.append(tile)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }}
        header {{
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }}
        h1 {{
            margin: 0 0 8px 0;
            font-size: 24px;
        }}
        .legend {{
            display: flex;
            gap: 16px;
            margin-top: 12px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
        }}
        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}
        .tile {{
            background: var(--surface);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
        }}
        .thumb-container {{
            height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #090d16;
            padding: 8px;
            border-bottom: 1px solid var(--border);
        }}
        .thumb-container img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
        .info {{
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
        }}
        .badge-row {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
        }}
        .badge-class {{
            background: #3b82f622;
            color: #60a5fa;
            border: 1px solid #3b82f688;
        }}
        .filename {{
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: #e2e8f0;
        }}
        .meta-row {{
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p style="color: var(--text-muted); margin: 0;">Showing {len(selected_records):,} sampled images (Generated by Milestone 18A curation suite)</p>
        <div class="legend">
            <div class="legend-item"><span class="dot" style="background: #10b981;"></span> AUTO_KEEP_CANDIDATE</div>
            <div class="legend-item"><span class="dot" style="background: #ef4444;"></span> AUTO_REJECT_CANDIDATE</div>
            <div class="legend-item"><span class="dot" style="background: #f59e0b;"></span> HUMAN_REVIEW_REQUIRED</div>
            <div class="legend-item"><span class="dot" style="background: #64748b;"></span> QUARANTINED_CORRUPT</div>
        </div>
    </header>
    <main class="gallery">
        {"".join(tiles_html)}
    </main>
</body>
</html>
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"🖼️ Rendered contact sheet with {len(selected_records)} tiles to {output_file}")
        return output_file
