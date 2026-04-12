#!/usr/bin/env python3
"""
Captain's Log Academy — Log Reader (Casey's Interface)

Generates daily digests, filters by vessel/score/tags, and produces
human-readable markdown output.
"""

import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class LogEntry:
    """A parsed captain's log entry."""
    path: str
    vessel_id: str
    vessel_type: str
    sequence: int
    date: date
    title: str
    body: str
    frontmatter: dict = field(default_factory=dict)

    @property
    def score(self) -> Optional[float]:
        return self.frontmatter.get("score")

    @property
    def rubric(self) -> Optional[dict]:
        return self.frontmatter.get("rubric")


def parse_log_file(path: str) -> Optional[LogEntry]:
    """Parse a markdown log file with YAML frontmatter."""
    content = Path(path).read_text()

    # Extract frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)
    frontmatter = {}
    for line in fm_text.strip().split('\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip().lower()
            value = value.strip()
            # Try to parse as number
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            frontmatter[key] = value

    body = content[fm_match.end():].strip()

    # Extract title (first # heading)
    title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled"

    # Parse path: logs/YYYY-MM-DD/[vessel-id].[sequence].md
    filename = os.path.basename(path)
    stem = filename.replace('.md', '')
    parts = stem.split('.', 1)
    vessel_id = parts[0] if parts else "unknown"
    sequence = int(parts[1]) if len(parts) > 1 else 0

    date_str = os.path.basename(os.path.dirname(path))
    try:
        log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        log_date = date.today()

    vessel_type = frontmatter.get("type", "unknown")

    return LogEntry(
        path=path,
        vessel_id=vessel_id,
        vessel_type=vessel_type,
        sequence=sequence,
        date=log_date,
        title=title,
        body=body,
        frontmatter=frontmatter,
    )


def reading_time_minutes(text: str) -> float:
    """Estimate reading time in minutes (238 wpm average)."""
    words = len(text.split())
    return words / 238.0


class LogReader:
    """Casey's interface for reading captain's logs."""

    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)

    def get_logs(
        self,
        target_date: Optional[date] = None,
        vessel_id: Optional[str] = None,
        vessel_type: Optional[str] = None,
        min_score: float = 0.0,
        max_score: float = 10.0,
    ) -> list[LogEntry]:
        """Get logs matching filters."""
        logs = []

        if target_date:
            date_dir = self.logs_dir / target_date.strftime("%Y-%m-%d")
            if not date_dir.exists():
                return logs
            dirs = [date_dir]
        else:
            dirs = sorted(self.logs_dir.glob("????-??-??"), reverse=True)

        for d in dirs:
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                entry = parse_log_file(str(f))
                if entry is None:
                    continue
                if vessel_id and entry.vessel_id != vessel_id:
                    continue
                if vessel_type and entry.vessel_type != vessel_type:
                    continue
                if entry.score is not None and (entry.score < min_score or entry.score > max_score):
                    continue
                logs.append(entry)

        return logs

    def generate_digest(
        self,
        target_date: Optional[date] = None,
        min_score: float = 7.0,
    ) -> str:
        """Generate Casey's daily digest as markdown.

        Only includes logs scoring >= min_score.
        """
        if target_date is None:
            target_date = date.today()

        logs = self.get_logs(target_date=target_date, min_score=min_score)
        logs.sort(key=lambda l: l.score or 0, reverse=True)

        lines = [
            f"# Captain's Digest — {target_date.isoformat()}",
            f"",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"Logs included: {len(logs)} (score >= {min_score})",
            f"",
        ]

        if not logs:
            lines.append("_No logs met the quality threshold today. The fleet was quiet._")
            lines.append("")
            return "\n".join(lines)

        # Group by vessel
        by_vessel: dict[str, list[LogEntry]] = {}
        for log in logs:
            by_vessel.setdefault(log.vessel_id, []).append(log)

        for vessel_id, vessel_logs in by_vessel.items():
            vtype = vessel_logs[0].vessel_type
            lines.append(f"## {vessel_id} ({vtype})")
            lines.append("")

            for log in vessel_logs:
                rt = reading_time_minutes(log.body)
                score_str = f"{log.score:.1f}" if log.score else "?"
                lines.append(f"### {log.title}")
                lines.append(f"")
                lines.append(f"Score: {score_str}/10 · ~{rt:.1f} min read · Seq #{log.sequence}")
                lines.append(f"")

                # Include the implication line (last paragraph with "Implication" or bold)
                body_lines = log.body.split('\n')
                for line in body_lines:
                    if 'implication' in line.lower() or line.startswith('**'):
                        lines.append(f"> {line}")
                        break

                lines.append(f"")
                lines.append(f"[Full log]({log.path})")
                lines.append("")

        return "\n".join(lines)

    def format_log(self, entry: LogEntry) -> str:
        """Format a single log for display."""
        rt = reading_time_minutes(entry.body)
        score_str = f"{entry.score:.1f}" if entry.score else "?"
        rubric_str = ""
        if entry.rubric:
            parts = [f"  {k}: {v}" for k, v in entry.rubric.items() if isinstance(v, (int, float))]
            rubric_str = "\n".join(parts)

        lines = [
            f"# {entry.title}",
            f"",
            f"Vessel: {entry.vessel_id} ({entry.vessel_type})",
            f"Date: {entry.date.isoformat()} · Sequence: #{entry.sequence}",
            f"Score: {score_str}/10 · ~{rt:.1f} min read",
            f"",
        ]
        if rubric_str:
            lines.append(f"**Rubric:**\n{rubric_str}")
            lines.append("")

        lines.append(entry.body)
        return "\n".join(lines)
