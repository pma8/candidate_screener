# Candidate Screener

Automated candidate screening pipeline that processes Workable CSV exports, verifies candidates against LinkedIn, and scores them against your job description.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   TAVILY_API_KEY=tvly-...
```

**Get your keys:**
- Anthropic: https://console.anthropic.com/settings/keys
- Tavily: https://app.tavily.com/home (free tier: 1000 searches/month)

### 3. Add your job description

Place your job description in `job_descriptions/` as a Markdown file. A template is provided at `job_descriptions/example.md`.

### 4. Run the screener

```bash
# Export your candidates from Workable as CSV and place in input/
python -m src.main --csv input/candidates.csv --jd job_descriptions/staff_dbre.md -v
```

The report will be saved to `output/report_<timestamp>.md`.

## How It Works

```
CSV Export → Parse → LinkedIn Search → Fake Detection → JD Scoring → Report
```

1. **CSV Parsing**: Auto-detects Workable column names (Name, Email, Experiences, Skills, Social profiles, etc.)
2. **LinkedIn Enrichment**: Uses Tavily web search to find each candidate's LinkedIn profile and extract their actual job history
3. **Fake Detection**: Claude compares application claims against LinkedIn data to flag mismatches (inflated titles, non-existent profiles, education discrepancies)
4. **JD Scoring**: Claude scores each legitimate candidate on skills match, experience relevance, experience level, education, and overall fit
5. **Report**: Generates a ranked Markdown report with detailed profiles for top candidates and a flagged-fakes section

## Using with Claude Code

This project includes a `CLAUDE.md` that teaches Claude Code how to operate the pipeline. You can:

```bash
# Start Claude Code in this directory
claude

# Then just tell it what to do:
# "Screen the candidates in input/candidates.csv"
# "Who are the top 5 candidates for the DBRE role?"
# "How many candidates were flagged as fake?"
```

## Weekly Workflow

1. Export candidates from Workable as CSV
2. Drop the CSV in `input/`
3. Run `python -m src.main --csv input/<filename>.csv --jd job_descriptions/staff_dbre.md -v`
4. Review `output/report_*.md` for prioritized candidates

### Automate with cron (optional)

```bash
# Run every Monday at 9am
0 9 * * 1 cd /path/to/candidate_screener && python -m src.main --csv input/latest.csv --jd job_descriptions/staff_dbre.md
```

## Configuration

See `config.yaml` for all options including scoring weights, batch size, and model selection.
