"""Configuration loading from config.yaml and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class ScoringWeights:
    skills_match: float = 0.35
    experience_relevance: float = 0.25
    experience_level: float = 0.20
    education: float = 0.10
    overall_impression: float = 0.10


@dataclass
class Config:
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    model: str = "claude-sonnet-4-5-20250929"
    batch_size: int = 5
    search_max_results: int = 5
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    fake_flag_threshold: int = 40
    report_top_n: int = 20
    column_mapping: dict[str, str] = field(default_factory=dict)


def load_config(config_path: str | None = None) -> Config:
    """Load configuration from yaml file and environment variables."""
    load_dotenv(PROJECT_ROOT / ".env")

    cfg = Config()
    cfg.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    cfg.tavily_api_key = os.environ.get("TAVILY_API_KEY", "")

    yaml_path = Path(config_path) if config_path else PROJECT_ROOT / "config.yaml"
    if yaml_path.exists():
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}

        cfg.model = data.get("model", cfg.model)
        cfg.batch_size = data.get("batch_size", cfg.batch_size)

        search = data.get("search", {})
        cfg.search_max_results = search.get("max_results", cfg.search_max_results)

        weights = data.get("scoring", {}).get("weights", {})
        if weights:
            cfg.scoring_weights = ScoringWeights(**weights)

        fake = data.get("fake_detection", {})
        cfg.fake_flag_threshold = fake.get("flag_threshold", cfg.fake_flag_threshold)

        report = data.get("report", {})
        cfg.report_top_n = report.get("top_n", cfg.report_top_n)

        cfg.column_mapping = data.get("column_mapping", {})

    return cfg
