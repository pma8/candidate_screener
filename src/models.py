"""Data models for the candidate screening pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FakeRisk(Enum):
    DEFINITELY_FAKE = "definitely_fake"
    LIKELY_FAKE = "likely_fake"
    UNCERTAIN = "uncertain"
    LIKELY_REAL = "likely_real"
    VERIFIED = "verified"


@dataclass
class Candidate:
    """Raw candidate data parsed from Workable CSV."""

    name: str
    email: str
    job_title: str = ""
    headline: str = ""
    creation_time: str = ""
    stage: str = ""
    tags: str = ""
    job_department: str = ""
    job_location: str = ""
    source: str = ""
    candidate_type: str = ""
    phone: str = ""
    address: str = ""
    summary: str = ""
    keywords: str = ""
    educations: str = ""
    experiences: str = ""
    skills: str = ""
    social_profiles: str = ""

    @property
    def linkedin_url(self) -> str | None:
        """Extract LinkedIn URL from social profiles field."""
        if not self.social_profiles:
            return None
        for part in self.social_profiles.replace(",", " ").split():
            part = part.strip()
            if "linkedin.com" in part.lower():
                return part
        return None


@dataclass
class LinkedInProfile:
    """Data gathered about a candidate from web search."""

    found: bool = False
    url: str = ""
    current_title: str = ""
    current_company: str = ""
    past_roles: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    location: str = ""
    summary: str = ""
    raw_search_results: str = ""


@dataclass
class FakeDetectionResult:
    """Result of comparing application data against LinkedIn data."""

    risk_level: FakeRisk = FakeRisk.UNCERTAIN
    confidence_score: int = 50  # 0-100, higher = more confident it's real
    reasons: list[str] = field(default_factory=list)
    details: str = ""


@dataclass
class QualificationScore:
    """Score for how well a candidate matches the job description."""

    skills_match: int = 0  # 0-100
    experience_relevance: int = 0  # 0-100
    experience_level: int = 0  # 0-100
    education: int = 0  # 0-100
    overall_impression: int = 0  # 0-100
    composite_score: float = 0.0  # weighted average
    justification: str = ""
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)


@dataclass
class ScreenedCandidate:
    """A candidate with all enrichment and scoring data attached."""

    candidate: Candidate
    linkedin: LinkedInProfile
    fake_detection: FakeDetectionResult
    qualification: QualificationScore

    @property
    def is_flagged_fake(self) -> bool:
        return self.fake_detection.risk_level in (
            FakeRisk.DEFINITELY_FAKE,
            FakeRisk.LIKELY_FAKE,
        )

    @property
    def final_score(self) -> float:
        if self.is_flagged_fake:
            return 0.0
        return self.qualification.composite_score
