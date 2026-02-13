# Candidate Screener

An automated pipeline that screens job candidates exported from Workable by:
1. Parsing the CSV export
2. Enriching each candidate via LinkedIn web search (Tavily)
3. Detecting fake/fraudulent candidates by comparing application vs LinkedIn data
4. Scoring qualified candidates against the job description
5. Generating a prioritized Markdown report

## Project Structure

```
src/
  main.py          - CLI entry point and pipeline orchestrator
  models.py        - Data models (Candidate, LinkedInProfile, scores, etc.)
  csv_parser.py    - Workable CSV parser with flexible column mapping
  enrichment.py    - LinkedIn profile lookup via Tavily web search + Claude
  fake_detector.py - Fake candidate detection via Claude
  scorer.py        - Candidate scoring against JD via Claude
  report.py        - Markdown report generator
  config.py        - Configuration loader (config.yaml + .env)
input/             - Drop Workable CSV exports here
output/            - Generated reports appear here
job_descriptions/  - Store job description files here
config.yaml        - Scoring weights, thresholds, model settings
```

## How to Run

```bash
# Full pipeline
python -m src.main --csv input/candidates.csv --jd job_descriptions/staff_dbre.md -v

# With custom output path
python -m src.main --csv input/candidates.csv --jd job_descriptions/staff_dbre.md --output output/my_report.md
```

## Running as a Claude Code Agent

When the user asks you to screen candidates, follow this workflow:

1. Check `input/` for CSV files. If the user specifies a file, use that.
2. Check `job_descriptions/` for JD files. The current active JD is `staff_dbre.md`.
3. Run the pipeline:
   ```bash
   python -m src.main --csv input/<file>.csv --jd job_descriptions/staff_dbre.md -v
   ```
4. Read the generated report from `output/` and present the key findings to the user.
5. Answer any follow-up questions about specific candidates.

## Environment Requirements

- **ANTHROPIC_API_KEY**: Required. Set in `.env` file.
- **TAVILY_API_KEY**: Required for LinkedIn enrichment. Set in `.env` file. If not set, enrichment is skipped but scoring still works.

## Configuration

Edit `config.yaml` to adjust:
- `model`: Claude model to use (default: claude-sonnet-4-5-20250929)
- `batch_size`: Parallel processing concurrency (default: 5)
- `scoring.weights`: How much each dimension contributes to the composite score
- `fake_detection.flag_threshold`: Score below which candidates are flagged
- `report.top_n`: Number of detailed profiles in the report
- `column_mapping`: Override CSV column name detection

## Workable CSV Columns

Expected columns (auto-detected, case-insensitive):
Name, Job title, Headline, Email, Creation time, Stage, Tags, Job department,
Job location, Source, Type, Phone, Address, Summary, Keywords, Educations,
Experiences, Skills, Social profiles
