"""Score candidates against a job description using Claude."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from anthropic import Anthropic

from .models import Candidate, LinkedInProfile, QualificationScore

if TYPE_CHECKING:
    from .config import Config

logger = logging.getLogger(__name__)


def load_job_description(jd_path: str | Path) -> str:
    """Load a job description from a markdown or text file."""
    path = Path(jd_path)
    if not path.exists():
        raise FileNotFoundError(f"Job description not found: {path}")
    return path.read_text()


def score_candidate(
    candidate: Candidate,
    linkedin: LinkedInProfile,
    job_description: str,
    config: Config,
) -> QualificationScore:
    """Score a candidate's qualifications against the job description."""
    client = Anthropic(api_key=config.anthropic_api_key)

    # Combine application and LinkedIn data for the richest picture
    experience_data = candidate.experiences
    if linkedin.found and linkedin.past_roles:
        experience_data += "\n\nLinkedIn verified roles:\n" + "\n".join(
            f"- {role}" for role in linkedin.past_roles
        )
        if linkedin.current_title:
            experience_data += f"\nCurrent (LinkedIn): {linkedin.current_title} at {linkedin.current_company}"

    education_data = candidate.educations
    if linkedin.found and linkedin.education:
        education_data += "\n\nLinkedIn education:\n" + "\n".join(
            f"- {edu}" for edu in linkedin.education
        )

    w = config.scoring_weights
    prompt = f"""You are a senior technical recruiter evaluating a candidate for a specific role.

JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
- Name: {candidate.name}
- Headline: {candidate.headline}
- Summary: {candidate.summary}
- Skills: {candidate.skills}
- Keywords: {candidate.keywords}
- Experience:
{experience_data}
- Education:
{education_data}
- Location: {candidate.address or candidate.job_location}

Score this candidate on each dimension (0-100, where 50 = meets basic requirements, 70 = strong match, 90+ = exceptional):

1. **skills_match** ({w.skills_match:.0%} weight): How well do their skills align with the JD requirements?
2. **experience_relevance** ({w.experience_relevance:.0%} weight): How relevant is their work experience to this role?
3. **experience_level** ({w.experience_level:.0%} weight): Do they have the right seniority / years of experience?
4. **education** ({w.education:.0%} weight): Does their education background fit?
5. **overall_impression** ({w.overall_impression:.0%} weight): Overall gut feeling — culture fit, trajectory, unique value?

Return a JSON object:
{{
  "skills_match": 0-100,
  "experience_relevance": 0-100,
  "experience_level": 0-100,
  "education": 0-100,
  "overall_impression": 0-100,
  "justification": "2-3 sentence summary of why you gave these scores",
  "strengths": ["list of key strengths for this role"],
  "concerns": ["list of concerns or gaps"]
}}

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model=config.model,
            max_tokens=768,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[: text.rfind("```")]
            text = text.strip()

        data = json.loads(text)

        score = QualificationScore(
            skills_match=data.get("skills_match", 0),
            experience_relevance=data.get("experience_relevance", 0),
            experience_level=data.get("experience_level", 0),
            education=data.get("education", 0),
            overall_impression=data.get("overall_impression", 0),
            justification=data.get("justification", ""),
            strengths=data.get("strengths", []),
            concerns=data.get("concerns", []),
        )

        # Compute weighted composite
        score.composite_score = (
            score.skills_match * w.skills_match
            + score.experience_relevance * w.experience_relevance
            + score.experience_level * w.experience_level
            + score.education * w.education
            + score.overall_impression * w.overall_impression
        )

        return score
    except Exception as e:
        logger.error("Scoring failed for %s: %s", candidate.name, e)
        return QualificationScore()
