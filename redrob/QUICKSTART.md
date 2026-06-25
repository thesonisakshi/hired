# Redrob: Quick Start Guide

## Installation

1. **Ensure Python 3.9+** is installed
2. **Install dependencies**:
   ```bash
   cd redrob/
   pip install numpy pandas sentence-transformers python-dateutil pyarrow
   ```

## Workflow

### Option 1: Test on Sample Data
```bash
python test_sample.py
```
This processes `sample_candidates.json` (50 candidates) and prints rankings with explanations.

### Option 2: Full Production Pipeline

#### Step 1: Pre-compute (Run Once, ~30 min)
```bash
python precompute.py --candidates /path/to/candidates.jsonl --out precomputed/
```

This generates:
- `precomputed/jd_facet_embeddings.npy` — 5 JD vectors
- `precomputed/candidate_embeddings.npy` — 100K narrative vectors
- `precomputed/candidate_ids.json` — Candidate IDs
- `precomputed/features.parquet` — Pre-computed scores

#### Step 2: Rank (Run Fast, <5 min)
```bash
python rank.py --artifacts precomputed/ --out submission.csv
```

Produces `submission.csv` with:
- `candidate_id` — Unique ID
- `rank` — 1-100
- `score` — 0.0-1.0 composite score
- `reasoning` — Grounded explanation (1-2 sentences)

### Step 3: Validate
```bash
python ../validate_submission.py submission.csv
```

## Input Format

### Candidates JSON/JSONL
Each candidate object:
```json
{
  "candidate_id": "CAND_0000001",
  "profile": {
    "anonymized_name": "...",
    "headline": "...",
    "summary": "...",
    "location": "City, State",
    "country": "...",
    "years_of_experience": 6.9,
    "current_title": "...",
    "current_company": "...",
    "current_company_size": "...",
    "current_industry": "..."
  },
  "career_history": [
    {
      "company": "...",
      "title": "...",
      "start_date": "2024-03-08",
      "end_date": null,
      "duration_months": 27,
      "is_current": true,
      "industry": "...",
      "company_size": "...",
      "description": "..."
    }
  ],
  "education": [...],
  "skills": [
    {
      "name": "Python",
      "proficiency": "expert",
      "endorsements": 42,
      "duration_months": 60
    }
  ],
  "certifications": [...],
  "redrob_signals": {
    "profile_completeness_score": 0.95,
    "signup_date": "2023-01-15",
    "last_active_date": "2026-06-20",
    "open_to_work_flag": true,
    "applications_submitted_30d": 5,
    "recruiter_response_rate": 0.8,
    "interview_completion_rate": 0.9,
    "offer_acceptance_rate": 0.7,
    "notice_period_days": 30,
    "willing_to_relocate": true,
    "github_activity_score": 42
  }
}
```

## Output Format

`submission.csv`:
```
candidate_id,rank,score,reasoning
CAND_0000050,1,0.4831,"14yr product-company background; clear upward career arc; based in gurgaon, haryana. Concern: 90-day..."
CAND_0000041,2,0.4478,"13yr product-company background; clear upward career arc; based in delhi, delhi. Concern: 90-day..."
...
```

## Scoring Layers

| Layer | Component | Score Range | Key Logic |
|-------|-----------|-------------|-----------|
| 1 | JD Decomposition | 0-1 | 5 facet similarity vectors |
| 2 | Evidence Narrative | Input | Action-verb extraction |
| 3 | Specificity | 0-1 | 5 regex dimensions |
| 4 | Consistency | 0-1 | 6 cross-field checks (-0.15 each) |
| 5 | Honeypot Detection | 0/1 | Hard disqualification |
| 6 | Behavioral Archetype | 0.20-1.30 | 7 named patterns |
| 7 | Trajectory | 0-1 | Growth arc measurement |
| 8 | Logistics | 0-1 | Location + notice fit |

## Key Metrics

- **Specificity**: Measures how much detail candidate provides (0-1)
- **Consistency**: Detects contradictions across fields (0-1)
- **Trajectory**: Upward vs flat career arc (0-1)
- **Behavior Multiplier**: Hirability gate based on platform signals (0.20-1.30)
- **Final Score**: (base - variance_penalty) × behavior_multiplier

## Archetype Meanings

| Archetype | Meaning | Multiplier |
|-----------|---------|-----------|
| active_seeker | Open, recent, responsive | 1.30 |
| highly_selective | Few apps, high quality | 1.15 |
| passive_fit | Not hunting but reachable | 1.00 |
| neutral | Default/mixed signals | 0.85 |
| notice_risk | Good fit, long notice | 0.75 |
| serial_applier | High volume, low quality | 0.65 |
| dormant_star | Gone dark 4+ months | 0.45 |
| ghost | Never responds | 0.20 |

## Troubleshooting

### Model download fails
- The first run downloads `BAAI/bge-small-en-v1.5` (~140MB)
- Ensure you have internet for pre-computation
- Ranking step uses only cached artifacts (no network needed)

### Memory issues
- Peak RAM: ~450MB (100K candidates)
- If limited: Process in batches or reduce candidate set

### Slow embedding
- `sentence-transformers` uses CPU by default
- GPU available if `torch` installed with CUDA support
- Pre-computation is one-time; ranking is fast (<5 min)

## File Dependencies

```
precompute.py → helpers/* → precomputed/
                ↓
                (generates artifacts)
                ↓
rank.py ← precomputed/ → submission.csv
```

## Validation Checklist

- [ ] 100 rows in CSV (no more, no less)
- [ ] Ranks 1-100 with no gaps
- [ ] Each candidate appears once
- [ ] Scores descending (highest at rank 1)
- [ ] Reasoning non-empty for all rows
- [ ] No honeypots in top 100
- [ ] Runtime < 5 minutes
- [ ] No network calls during ranking
