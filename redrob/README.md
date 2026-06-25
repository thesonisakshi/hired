# Redrob Hackathon — Intelligent Candidate Ranking

## What this does

Ranks 100,000 candidates for a Senior AI Engineer role using a six-layer
people-reading system that detects fabrication, surfaces plain-language gems,
and weights real hirability over paper quality.

## Core innovations

1. **Evidence narratives** (not raw profiles) — action-verb sentence extraction
2. **Specificity entropy scoring** — regex-based fabrication detection
3. **Cross-field consistency graph** — catches global contradictions
4. **Constraint violation detection** — honeypot elimination
5. **Behavioral archetype classification** — 7 named hirability patterns
6. **Variance penalty** — punishes dimensional disagreement in scoring

## Reproduce

```bash
# Install
pip install -r requirements.txt

# Pre-compute (run once, ~30 min)
python precompute.py --candidates ./candidates.jsonl.gz

# Rank (< 5 min)
python rank.py --out ./submission.csv

# Validate
python validate_submission.py ./submission.csv
```

## Runtime

- Pre-computation: ~30 minutes (one-time)
- Ranking step: ~16 seconds

## Memory

Peak RAM: ~450MB (embeddings + features)

## No network at ranking time

All models downloaded during pre-computation and cached locally.
`rank.py` makes zero network calls.

## System Architecture

```
redrob/
  precompute.py       # offline pipeline — run once
  rank.py             # online ranking — must finish <5min
  helpers/
    narrative.py      # evidence narrative builder (Layer 2)
    specificity.py    # specificity entropy scorer (Layer 3)
    consistency.py    # cross-field consistency checker (Layer 4)
    honeypot.py       # constraint violation detector (Layer 5)
    behavioral.py     # archetype classifier (Layer 6)
    trajectory.py     # career growth arc scorer
    logistics.py      # location + notice period scorer
    reasoning.py      # grounded reasoning string generator
    jd.py             # JD decomposition and facet embedder
  precomputed/        # artifact store (generated at runtime)
  submission.csv      # final output
  requirements.txt
  README.md
```

## Layer Descriptions

### Layer 1: JD Facet Decomposition
Decomposes job description into 5 independent semantic facets:
- Core technical (embeddings, vector DBs, retrieval, ranking)
- Evaluation rigor (NDCG, A/B testing, metrics)
- Product engineer (shipped, deployed, real users)
- Mindset (async, scrappy, fast, founding team)
- Anti-patterns (research, consulting, CV/speech, no deployment)

### Layer 2: Evidence Narrative
Extracts demonstrable facts using action-verb filtering and company classification.

### Layer 3: Specificity Entropy
Detects fabrication through 5 specificity dimensions:
- Numeric density
- Versioned technology mentions
- Failure/tradeoff language
- Temporal precision
- Team/scope language

### Layer 4: Cross-field Consistency
Builds consistency graph with 6 checks:
- Expert skill count vs experience length
- Leadership claims vs career stage
- Scale claims vs company type
- OSS claims vs GitHub activity
- Senior titles vs total years
- Cert farming patterns

### Layer 5: Honeypot Detection
Hard disqualification for logically impossible profiles:
- Worked before company founded
- Experience exceeds career span by >4 years
- 10+ expert skills with zero evidence
- Future dates in work history

### Layer 6: Behavioral Archetype
7 named archetypes with hirability multipliers:
- active_seeker (1.30)
- highly_selective (1.15)
- passive_fit (1.00)
- neutral (0.85)
- notice_risk (0.75)
- serial_applier (0.65)
- dormant_star (0.45)
- ghost (0.20)

### Layer 7: Trajectory Scorer
Measures career growth arc (upward movement > total length).

### Layer 8: Logistics Scorer
Location + notice period fit for target cities.

## Composite Scoring

Formula with variance penalty:
```
base = weighted sum of 5 dimensions
base -= variance_penalty (punishes dimensional disagreement)
final = base * behavior_multiplier (hirability gate)
final = 0.0 if honeypot or hard_disqualified
```

Dimension weights:
- Semantic: 0.30
- Specificity: 0.20
- Consistency: 0.20
- Trajectory: 0.15
- Logistics: 0.15

## Validation

Output CSV has columns: `[candidate_id, rank, score, reasoning]`
- Exactly 100 rows
- Ranks 1-100 with no gaps
- No candidate appears twice
- Score numeric and descending
- Reasoning strings grounded in data

## Testing Checklist

- [ ] `validate_submission.py` passes with zero errors
- [ ] Exactly 100 rows in output CSV
- [ ] Ranks are 1-100 with no gaps or duplicates
- [ ] No candidate appears twice
- [ ] Score column is numeric and descending
- [ ] Reasoning strings are non-empty and mention specific facts
- [ ] Honeypot rate in top 100 < 10%
- [ ] Total runtime of rank.py < 5 minutes
- [ ] rank.py makes zero network calls
- [ ] All pre-computation artifacts exist
- [ ] Sample test passes successfully
