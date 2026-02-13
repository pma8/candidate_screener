"""Parse Workable CSV exports into Candidate objects."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from .models import Candidate

# Maps our internal field names to common Workable CSV column headers.
# Each key can match multiple possible column names (lowercase for matching).
DEFAULT_COLUMN_MAP: dict[str, list[str]] = {
    "name": ["name", "candidate name", "full name", "candidate"],
    "email": ["email", "email address", "e-mail"],
    "job_title": ["job title", "job", "position", "applied for"],
    "headline": ["headline", "title", "professional headline"],
    "creation_time": ["creation time", "created", "applied date", "date applied", "applied on"],
    "stage": ["stage", "pipeline stage", "status"],
    "tags": ["tags", "labels"],
    "job_department": ["job department", "department"],
    "job_location": ["job location", "location"],
    "source": ["source", "sourced from", "channel"],
    "candidate_type": ["type", "candidate type"],
    "phone": ["phone", "phone number", "mobile"],
    "address": ["address", "location", "city"],
    "summary": ["summary", "bio", "about"],
    "keywords": ["keywords"],
    "educations": ["educations", "education"],
    "experiences": ["experiences", "experience", "work experience"],
    "skills": ["skills", "skill set"],
    "social_profiles": ["social profiles", "linkedin", "linkedin url", "social links", "social"],
}


def _build_column_index(
    headers: list[str], overrides: dict[str, str] | None = None
) -> dict[str, int]:
    """Map internal field names to CSV column indices."""
    column_map = dict(DEFAULT_COLUMN_MAP)

    # Apply user overrides: override key -> actual column header
    if overrides:
        for field_name, col_header in overrides.items():
            column_map[field_name] = [col_header.lower()]

    header_lower = [h.strip().lower() for h in headers]
    index: dict[str, int] = {}

    for field_name, possible_names in column_map.items():
        for name in possible_names:
            if name in header_lower:
                index[field_name] = header_lower.index(name)
                break

    return index


def _get(row: list[str], index: dict[str, int], field: str) -> str:
    """Safely get a field value from a row."""
    idx = index.get(field)
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def parse_csv(csv_path: str | Path, column_overrides: dict[str, str] | None = None) -> list[Candidate]:
    """Parse a Workable CSV export and return a list of Candidate objects."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    # Detect encoding: try utf-8 first, fall back to latin-1
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Could not decode CSV file: {path}")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if len(rows) < 2:
        return []

    headers = rows[0]
    index = _build_column_index(headers, column_overrides)

    candidates = []
    for row in rows[1:]:
        # Skip empty rows
        if not any(cell.strip() for cell in row):
            continue

        name = _get(row, index, "name")
        email = _get(row, index, "email")
        if not name and not email:
            continue

        candidates.append(
            Candidate(
                name=name,
                email=email,
                job_title=_get(row, index, "job_title"),
                headline=_get(row, index, "headline"),
                creation_time=_get(row, index, "creation_time"),
                stage=_get(row, index, "stage"),
                tags=_get(row, index, "tags"),
                job_department=_get(row, index, "job_department"),
                job_location=_get(row, index, "job_location"),
                source=_get(row, index, "source"),
                candidate_type=_get(row, index, "candidate_type"),
                phone=_get(row, index, "phone"),
                address=_get(row, index, "address"),
                summary=_get(row, index, "summary"),
                keywords=_get(row, index, "keywords"),
                educations=_get(row, index, "educations"),
                experiences=_get(row, index, "experiences"),
                skills=_get(row, index, "skills"),
                social_profiles=_get(row, index, "social_profiles"),
            )
        )

    return candidates
