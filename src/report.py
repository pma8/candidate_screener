"""Generate a Markdown screening report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .models import FakeRisk, ScreenedCandidate

if TYPE_CHECKING:
    from .config import Config


def _risk_badge(risk: FakeRisk) -> str:
    badges = {
        FakeRisk.DEFINITELY_FAKE: "FAKE",
        FakeRisk.LIKELY_FAKE: "SUSPECT",
        FakeRisk.UNCERTAIN: "UNVERIFIED",
        FakeRisk.LIKELY_REAL: "OK",
        FakeRisk.VERIFIED: "VERIFIED",
    }
    return badges.get(risk, "?")


def generate_report(
    screened: list[ScreenedCandidate],
    job_description_path: str,
    config: Config,
) -> str:
    """Generate a Markdown screening report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(screened)
    fakes = [s for s in screened if s.is_flagged_fake]
    valid = [s for s in screened if not s.is_flagged_fake]
    valid_sorted = sorted(valid, key=lambda s: s.final_score, reverse=True)
    top = valid_sorted[: config.report_top_n]

    lines: list[str] = []

    # Header
    lines.append(f"# Candidate Screening Report")
    lines.append(f"")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Job Description:** `{job_description_path}`")
    lines.append(f"**Total Candidates:** {total}")
    lines.append(f"**Flagged as Fake/Suspect:** {len(fakes)}")
    lines.append(f"**Valid Candidates Scored:** {len(valid)}")
    lines.append("")

    # Summary
    lines.append("---")
    lines.append("")
    lines.append("## Top Candidates")
    lines.append("")
    if top:
        lines.append("| Rank | Name | Score | Skills | Exp. Relevance | Exp. Level | Verification | Key Strengths |")
        lines.append("|------|------|-------|--------|----------------|------------|--------------|---------------|")
        for i, s in enumerate(top, 1):
            strengths = "; ".join(s.qualification.strengths[:2]) if s.qualification.strengths else "-"
            badge = _risk_badge(s.fake_detection.risk_level)
            lines.append(
                f"| {i} | {s.candidate.name} | **{s.final_score:.0f}** "
                f"| {s.qualification.skills_match} "
                f"| {s.qualification.experience_relevance} "
                f"| {s.qualification.experience_level} "
                f"| {badge} "
                f"| {strengths} |"
            )
        lines.append("")
    else:
        lines.append("*No valid candidates to rank.*")
        lines.append("")

    # Detailed breakdowns for top candidates
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Candidate Profiles")
    lines.append("")

    for i, s in enumerate(top, 1):
        c = s.candidate
        q = s.qualification
        f = s.fake_detection
        li = s.linkedin

        lines.append(f"### {i}. {c.name}")
        lines.append(f"")
        lines.append(f"- **Score:** {s.final_score:.0f}/100")
        lines.append(f"- **Email:** {c.email}")
        if c.headline:
            lines.append(f"- **Headline:** {c.headline}")
        if c.source:
            lines.append(f"- **Source:** {c.source}")
        if c.job_location:
            lines.append(f"- **Location:** {c.address or c.job_location}")
        if li.url:
            lines.append(f"- **LinkedIn:** {li.url}")
        lines.append(f"- **Verification:** {_risk_badge(f.risk_level)} (confidence: {f.confidence_score}/100)")
        lines.append(f"")

        # Scores
        lines.append(f"**Scores:** Skills: {q.skills_match} | Experience Relevance: {q.experience_relevance} | Experience Level: {q.experience_level} | Education: {q.education} | Overall: {q.overall_impression}")
        lines.append(f"")

        if q.justification:
            lines.append(f"**Assessment:** {q.justification}")
            lines.append(f"")

        if q.strengths:
            lines.append(f"**Strengths:** {', '.join(q.strengths)}")
        if q.concerns:
            lines.append(f"**Concerns:** {', '.join(q.concerns)}")
        lines.append(f"")

        if f.reasons:
            lines.append(f"**Verification Notes:** {'; '.join(f.reasons)}")
            lines.append(f"")

        lines.append("---")
        lines.append("")

    # Flagged candidates section
    if fakes:
        lines.append("## Flagged Candidates (Likely Fake / Suspect)")
        lines.append("")
        lines.append("| Name | Email | Risk | Confidence | Reasons |")
        lines.append("|------|-------|------|------------|---------|")
        for s in fakes:
            reasons = "; ".join(s.fake_detection.reasons[:2]) if s.fake_detection.reasons else "-"
            lines.append(
                f"| {s.candidate.name} | {s.candidate.email} "
                f"| {_risk_badge(s.fake_detection.risk_level)} "
                f"| {s.fake_detection.confidence_score}/100 "
                f"| {reasons} |"
            )
        lines.append("")

    # Remaining candidates (scored but not in top N)
    rest = valid_sorted[config.report_top_n :]
    if rest:
        lines.append("---")
        lines.append("")
        lines.append("## Other Candidates (Ranked)")
        lines.append("")
        lines.append("| Rank | Name | Score | Verification |")
        lines.append("|------|------|-------|--------------|")
        for i, s in enumerate(rest, config.report_top_n + 1):
            badge = _risk_badge(s.fake_detection.risk_level)
            lines.append(f"| {i} | {s.candidate.name} | {s.final_score:.0f} | {badge} |")
        lines.append("")

    return "\n".join(lines)


def save_report(report_content: str, output_path: str | Path) -> Path:
    """Save the report to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_content)
    return path
