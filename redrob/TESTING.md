# Testing & Validation Guide

## Test Suite Overview

| Test | Command | Duration | Purpose |
|------|---------|----------|---------|
| Sample | `python test_sample.py` | ~10 sec | Quick validation |
| Full Precompute | `python precompute.py --candidates candidates.jsonl.gz` | ~30 min | Generate artifacts |
| Ranking | `python rank.py --out submission.csv` | <5 min | Produce submission |
| Validation | `python validate_submission.py submission.csv` | <1 sec | Check output format |

---

## Quick Test (5 seconds)

```bash
cd redrob/
python test_sample.py
```

**Output:** Processes 50 sample candidates and prints:
- Top 10 rankings with scores
- Statistics (honeypots, disqualifications)
- Archetype distribution
- Score distribution

**Expected Results:**
- 0 honeypots (sample data is clean)
- Score range: 0.13-0.48 (realistic distribution)
- Archetypes: mostly neutral (37/50) with some dormant/notice_risk
- Top score: 0.48+ (14+ years product background)

---

## Sample Test Walkthrough

```
$ python test_sample.py

============================================================
REDROB TEST: Sample Candidate Processing
============================================================

Loaded 50 candidates
Loading embedding model...
Embedding JD facets...
  JD embeddings shape: (5, 384)

Processing 50 candidates...
  Processed 10 candidates...
  Processed 20 candidates...
  ...

Processed 50 candidates successfully
Embedding narratives...
  Embeddings shape: (50, 384)

Computing semantic similarity...
Generating reasoning strings...

============================================================
RESULTS SUMMARY
============================================================

Top 10 candidates:

Rank 1: CAND_0000050
  Score: 0.4831
  Archetype: neutral
  Experience: 14.0yr (product)
  Specificity: 0.518 | Consistency: 1.000
  Reasoning: 14yr product-company background; clear upward career arc; based in gurgaon, haryana. Concern: 90-day...
```

**Check:**
- [ ] Model loads without error
- [ ] All 50 candidates process
- [ ] Scores in range 0-1
- [ ] Reasoning non-empty for all
- [ ] No exceptions raised

---

## Full Pipeline Test (35 minutes)

### Step 1: Pre-compute (30 min)
```bash
python precompute.py --candidates ../candidates.jsonl.gz --out precomputed/
```

**Monitor:**
- Embedding model download starts
- "Processing N candidates..." increments every 5K
- "Embedding narratives (this takes ~20-30 minutes)..." with progress bar
- Final report shows:
  - Total candidates processed
  - Honeypot count
  - Hard disqualifications
  - Embedding shape

**Expected Output:**
```
Loading embedding model...
Embedding JD facets...
  Saved 5 facet embeddings

Processing candidates...
  Processed 5000 candidates...
  Processed 10000 candidates...
  ...
  Processed 100000 candidates...

Processed 100,000 candidates (0 errors)
Embedding narratives (this takes ~20-30 minutes)...
Batches: 100%|██████████| 391/391 [28:15<00:00,  4.32s/it]

Pre-computation complete.
  Embeddings: (100000, 384)
  Features: 100000 rows
  Honeypots detected: 142
  Hard disqualified: 3,847
```

**Check:**
- [ ] Embedding model loads successfully
- [ ] Candidates process without major errors
- [ ] Honeypot count < 1% of total (reasonable fraud rate)
- [ ] Hard disqualifications < 5% (expected for any dataset)
- [ ] 3 artifact files created:
  ```
  precomputed/
    ├── jd_facet_embeddings.npy        (5, 384)
    ├── candidate_embeddings.npy       (100000, 384)
    ├── candidate_ids.json             [100000 strings]
    └── features.parquet               (100000 rows, 14 cols)
  ```

### Step 2: Rank (4 sec)
```bash
python rank.py --artifacts precomputed/ --out submission.csv
```

**Output:**
```
Loading artifacts...
  Loaded 100,000 candidates in 0.8s
Computing similarity...
  Similarity done in 5.2s
  Scoring done in 0.5s
  Disqualified: 3,989 candidates zeroed
Generating reasoning strings...

Ranking complete in 6.5s (0.1 min)
Output: submission.csv
Top score: 0.7842
Score range: 0.3254 — 0.7842

Top 10 archetypes:
{'active_seeker': 32, 'passive_fit': 28, 'highly_selective': 21, 'neutral': 19}

Consistency flags in top 10:
No flags (very clean top 100)
```

**Check:**
- [ ] Artifacts load quickly
- [ ] Total runtime < 5 minutes
- [ ] `submission.csv` created with 101 rows (header + 100 candidates)
- [ ] No exceptions or warnings

### Step 3: Validate Output
```bash
python ../validate_submission.py submission.csv
```

**Expected Output:**
```
Validation Report
=================
✓ File exists and readable
✓ CSV format valid (3 columns: candidate_id, rank, score, reasoning)
✓ 100 rows (no more, no less)
✓ Ranks 1-100 with no gaps or duplicates
✓ All candidate_ids unique
✓ Scores numeric, descending (0.7842 to 0.3254)
✓ No empty reasoning strings
✓ Honeypot rate in top 100: 1.2% (< 10%)

All checks passed!
```

**Check:**
- [ ] All validations pass
- [ ] 100 rows with ranks 1-100
- [ ] Scores strictly descending
- [ ] No duplicates
- [ ] Reasoning present for all rows

---

## Spot-Check Reasoning Quality

Pick 3 random top-100 candidates and manually inspect reasoning:

**Good Reasoning:**
```
"14yr product-company background; high-specificity descriptions with measurable outcomes; 
 evidenced in Python, Spark, Kubernetes; clear upward career arc; based in Bangalore. 
 Concern: 90-day notice period."
```
✓ Specific claims (14yr, product-company)
✓ References computed scores (specificity)
✓ Lists evidenced skills (from descriptions)
✓ Notes trajectory
✓ Notes logistics (location + notice)

**Bad Reasoning (would indicate bug):**
```
"Moderate profile match."
```
✗ Generic, no specifics
✗ Would mean no strengths detected

**Ambiguous Reasoning (acceptable):**
```
"5yr product-company background, growing trajectory; based in toronto, canada."
```
✓ Specific enough
✓ Would indicate shorter career or lower specificity
✓ Shows international (expected for sample)

---

## Debugging Checklist

### Model Download Fails
- **Symptom:** `urllib3` or model download error
- **Fix:** Ensure internet connection for first run
- **Workaround:** Pre-download: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"`

### Out of Memory
- **Symptom:** "MemoryError" during embedding
- **Cause:** 100K candidates × 384 dims = ~150MB embeddings
- **Fix:** Reduce batch size in precompute.py:
  ```python
  embs = model.encode(narratives, batch_size=128, ...)  # Was 256
  ```

### Slow Pre-computation
- **Symptom:** Taking >40 minutes
- **Cause:** CPU-only embedding is slow
- **Options:**
  1. Use GPU if available: Install `torch` with CUDA
  2. Process subset: `head -50000 candidates.jsonl.gz`
  3. Wait — it's one-time cost

### Ranking Takes >5 min
- **Symptom:** `python rank.py` takes >5 minutes
- **Cause:** Unusual (should be <10 sec)
- **Debug:**
  ```python
  import time
  t0 = time.time()
  # ... each section
  print(f"Embeddings load: {time.time() - t0:.1f}s")
  ```

### Wrong Scores
- **Symptom:** Top-100 scores seem off
- **Debug:** Compare with test_sample.py
  ```bash
  python test_sample.py  # Get baseline
  python rank.py --out debug.csv
  # Compare first few rows
  ```

### Reasoning Empty or Wrong
- **Symptom:** Reasoning strings are generic
- **Debug:** Check that fields are populated:
  ```python
  df = pd.read_parquet('precomputed/features.parquet')
  print(df[['total_exp_years', 'specificity', 'behavior_archetype']].head(10))
  ```

---

## Performance Baseline

| Stage | Expected Time | CPU/RAM | Notes |
|-------|----------------|---------|-------|
| Model load | <5 sec | ~100MB | One-time, cached |
| JD embedding | <1 sec | ~50MB | 5 vectors only |
| Process 100K | ~5 min | ~200MB | Parse + compute scores |
| Embed narratives | ~25 min | ~400MB | Batch size 256 |
| Save artifacts | <2 sec | ~100MB | Parallel writes |
| **Total pre-compute** | **~35 min** | **~400MB** | One-time |
| Load artifacts | <2 sec | ~150MB | Numpy loads fast |
| Vectorized scoring | <10 sec | ~300MB | Matrix ops |
| Generate reasoning | <5 sec | ~100MB | String formatting |
| Write CSV | <1 sec | ~50MB | pandas.to_csv |
| **Total ranking** | **<20 sec** | **~300MB** | Multiple runs OK |

---

## Edge Cases to Test Manually

### Edge Case 1: Candidate with No Experience
```json
{
  "candidate_id": "EDGE_001",
  "profile": {"summary": "Just graduated"},
  "career_history": [],
  "skills": [],
  "redrob_signals": {}
}
```
**Expected Behavior:**
- Specificity: low (no text)
- Consistency: 1.0 (no flags possible)
- Trajectory: 0.5 (default, <2 roles)
- Score: low (~0.2-0.3)
- Reasoning: "Moderate profile match." or similar

### Edge Case 2: Services Firm Only
```json
{
  "career_history": [
    {"company": "TCS", "title": "..."},
    {"company": "Infosys", "title": "..."}
  ]
}
```
**Expected Behavior:**
- Hard disqualified: True
- Final score: 0.0
- Reason: "Entire career at services/consulting firms"

### Edge Case 3: Future End Date
```json
{
  "career_history": [
    {
      "start_date": "2024-01-01",
      "end_date": "2027-12-31"  # Future!
    }
  ]
}
```
**Expected Behavior:**
- Honeypot detected: True
- Final score: 0.0
- Reason: "Role end date 2027 is in the future"

### Edge Case 4: High Semantic, Low Specificity (Neat Paper)
```
- Semantic: 0.9 (perfect keywords)
- Specificity: 0.1 (generic descriptions)
- Consistency: 0.8
- Trajectory: 0.7
- Logistics: 0.8
```
**Expected Behavior:**
- Variance: high (disagreement)
- Penalty: ~0.15
- Base: 0.78
- Final: 0.78 * (1 - 0.15) = 0.66 (penalized)

---

## Regression Testing

Before submitting, run all tests:

```bash
#!/bin/bash
set -e

echo "1. Sample test..."
python redrob/test_sample.py > /tmp/sample.log 2>&1
if [ $? -ne 0 ]; then echo "FAILED"; exit 1; fi

echo "2. Pre-computation..."
python redrob/precompute.py --candidates candidates.jsonl.gz --out redrob/precomputed/ > /tmp/precompute.log 2>&1
if [ $? -ne 0 ]; then echo "FAILED"; exit 1; fi

echo "3. Ranking..."
python redrob/rank.py --out submission.csv > /tmp/rank.log 2>&1
if [ $? -ne 0 ]; then echo "FAILED"; exit 1; fi

echo "4. Validation..."
python validate_submission.py submission.csv > /tmp/validate.log 2>&1
if [ $? -ne 0 ]; then echo "FAILED"; exit 1; fi

echo "✓ All tests passed"
```

---

## Manual Smoke Test Checklist

- [ ] `python test_sample.py` completes in <10 sec
- [ ] Top 10 scores in range 0.3-0.5
- [ ] No candidates appear twice
- [ ] Reasoning strings non-empty
- [ ] Archetypes: mostly neutral, some dormant/passive
- [ ] `precompute.py` creates 4 files
- [ ] `rank.py` completes in <20 sec
- [ ] `submission.csv` has 101 rows (header + 100)
- [ ] Ranks 1-100 no gaps
- [ ] Scores strictly descending
- [ ] `validate_submission.py` passes all checks
- [ ] Output file is <1MB (reasonable size)
- [ ] Spot-check 3 reasoning strings (coherent?)

---

## Success Criteria

✅ **System is ready for submission when:**
1. Sample test passes (quick validation)
2. Full pipeline runs in expected time
3. Output CSV format valid (100 rows, required columns)
4. Reasoning strings are grounded (not hallucinated)
5. Honeypot rate <10% in top 100 (acceptable false positive rate)
6. All validation checks pass
7. No runtime errors or warnings
