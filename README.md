# 🎯 RedRob Hired — Candidate Ranking System

> **Advanced AI-powered candidate ranking system for the RedRob Hackathon**  
> Fast, explainable, offline-precomputed scoring pipeline with semantic understanding.

---

## 📋 Table of Contents

- [🎯 Quick Start](#-quick-start)
- [🏗️ Architecture](#️-architecture)
- [📊 Scoring Dimensions](#-scoring-dimensions)
- [🚀 Pipeline](#-pipeline)
- [📁 Project Structure](#-project-structure)
- [🛠️ Installation & Setup](#️-installation--setup)
- [💻 Running Commands](#-running-commands)
- [📈 Key Features](#-key-features)
- [🧠 Behavioral Archetypes](#-behavioral-archetypes)
- [📝 Output Format](#-output-format)
- [⏱️ Performance](#️-performance)

---

## 🎯 Quick Start

### Prerequisites
```bash
Python 3.8+
pip install sentence-transformers numpy pandas pyarrow python-dateutil
```

### One-Liner (Full Pipeline)
```bash
cd redrob
python precompute.py --candidates ../candidates.jsonl --out ../precomputed
python rank.py --artifacts ../precomputed --out ../submission.csv
```

### Test on Sample Data
```bash
cd redrob
python test_sample.py
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OFFLINE PRECOMPUTE                       │
│  (Run once, ~30 min for 100K candidates on CPU)             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: candidates.jsonl (line-delimited JSON)             │
│                   ↓                                          │
│  1. Load SentenceTransformer (BAAI/bge-small-en-v1.5)      │
│  2. Embed 5 JD facets → jd_facet_embeddings.npy            │
│  3. Build evidence narratives from career history          │
│  4. Compute 6 dimensions for each candidate:               │
│     • Semantic similarity (JD facets)                       │
│     • Specificity (technical depth)                        │
│     • Consistency (data quality)                           │
│     • Trajectory (career growth)                           │
│     • Logistics (location fit)                             │
│  5. Classify behavioral archetype                          │
│  6. Batch embed all narratives → candidate_embeddings.npy  │
│                   ↓                                          │
│  Output: precomputed/                                       │
│    ├── candidate_embeddings.npy        (100K×384 matrix)   │
│    ├── jd_facet_embeddings.npy         (5×384 matrix)      │
│    ├── candidate_ids.json              (ID list)           │
│    └── features.parquet                (all dimensions)    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    ONLINE RANKING                           │
│  (Must complete in <5 min, CPU only, no network)            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Load precomputed artifacts (fast, <1 sec)              │
│  2. Vectorized similarity scoring:                          │
│     sim = embeddings @ jd_facets.T  (100K×384 × 384×5)    │
│  3. Composite scoring:                                      │
│     base = 30% semantic + 20% specificity + 20% cons...    │
│                + 15% trajectory + 15% logistics            │
│  4. Apply variance penalty (punish dimension disagreement) │
│  5. Multiply by behavioral multiplier (archetype bonus)    │
│  6. Hard-zero honeypots & disqualified                     │
│  7. Select top 100, generate reasoning                     │
│                   ↓                                          │
│  Output: submission.csv                                     │
│    ├── candidate_id (RedRob ID)                            │
│    ├── rank (1-100)                                        │
│    ├── score (0.0-1.0)                                     │
│    └── reasoning (human-readable explanation)              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Scoring Dimensions

| Dimension | Weight | Explanation |
|-----------|--------|-------------|
| 🎯 **Semantic** | 30% | Similarity of candidate narrative to JD facets (core_tech, eval_rigor, product_eng, mindset, anti_patterns) |
| 📐 **Specificity** | 20% | Technical depth: numeric metrics, tech stack, failures, dates, scope (0.0–1.0) |
| ✅ **Consistency** | 20% | Data quality: date logic, location validity, coherence flags (0.0–1.0) |
| 📈 **Trajectory** | 15% | Career growth: promotion speed, salary growth signals, seniority progression (0.0–1.0) |
| 🌍 **Logistics** | 15% | Location proximity & timezone fit (0.0–1.0) |
| 🎭 **Behavior Mult** | ×1.0–1.3× | Archetype-based multiplier (neutral, dormant_star, notice_risk, passive_fit) |

### Variance Penalty
- Punishes candidates where dimensions strongly disagree (e.g., high semantic but low specificity)
- Formula: `variance(dimensions).clip(0, 0.08) × 2.5`
- Ensures balanced profiles rank higher

---

## 🚀 Pipeline

### Phase 1: Precomputation (Offline)
Prepare once, reuse infinitely.

```bash
cd redrob
python precompute.py --candidates <path_to_candidates> [--out <output_dir>]
```

**Arguments:**
- `--candidates` (required): Path to `candidates.jsonl`, `candidates.jsonl.gz`, or `candidates.json`
- `--out` (optional, default: `precomputed`): Output directory for artifacts

**Output:** 4 files in `precomputed/`
- `candidate_embeddings.npy` — 384-dim embeddings for all candidates
- `jd_facet_embeddings.npy` — 5 JD facet embeddings (core_tech, rigor, product_eng, mindset, anti_patterns)
- `candidate_ids.json` — Candidate ID list
- `features.parquet` — All scoring dimensions, metadata, flags

**Time:** ~25–40 min for 100K candidates on CPU

---

### Phase 2: Ranking (Online)
Fast, stateless ranking that must complete in <5 minutes.

```bash
cd redrob
python rank.py [--artifacts <precomputed_dir>] [--out <output_csv>]
```

**Arguments:**
- `--artifacts` (optional, default: `precomputed`): Directory with precomputed artifacts
- `--out` (optional, default: `submission.csv`): Output CSV file path

**Output:** `submission.csv`
```
candidate_id,rank,score,reasoning
CAND_0000050,1,0.4831,"14yr product-company background; clear upward career arc..."
CAND_0000041,2,0.4478,"13yr product-company background; based in delhi, delhi..."
```

**Time:** <5 seconds for 100K candidates

---

### Phase 3: Testing (Validation)
Verify end-to-end scoring on sample data.

```bash
cd redrob
python test_sample.py
```

Loads `sample_candidates.json` from repo root, runs full scoring pipeline, prints top 10 + statistics.

---

## 📁 Project Structure

```
RedRob-Hired/
├── README.md                           ← You are here
├── candidate_schema.json               ← Candidate data structure
├── candidates.jsonl                    ← Full production data (100K+)
├── sample_candidates.json              ← 50 samples for testing
├── submission_metadata_template.yaml   ← Submission metadata spec
├── validate_submission.py              ← Output validation script
│
├── redrob/                             ← Main package
│   ├── __init__.py
│   ├── precompute.py                   ← Offline pipeline (Phase 1)
│   ├── rank.py                         ← Online ranking (Phase 2)
│   ├── test_sample.py                  ← Validation harness (Phase 3)
│   │
│   └── helpers/                        ← Scoring modules
│       ├── __init__.py
│       ├── jd.py                       ← JD facet definitions & weights
│       ├── narrative.py                ← Evidence narrative builder
│       ├── specificity.py              ← Technical depth scorer
│       ├── consistency.py              ← Data quality checker
│       ├── honeypot.py                 ← Fake profile detection
│       ├── behavioral.py               ← Archetype classifier
│       ├── trajectory.py               ← Career growth scorer
│       ├── logistics.py                ← Location fit scorer
│       └── reasoning.py                ← Human-readable explanations
│
├── precomputed/                        ← Offline artifacts (auto-generated)
│   ├── candidate_embeddings.npy
│   ├── jd_facet_embeddings.npy
│   ├── candidate_ids.json
│   └── features.parquet
│
└── verify_build.py                     ← System health check
```

---

## 🛠️ Installation & Setup

### 1. Clone or Extract
```bash
cd E:\Projects\RedRob-Hired
```

### 2. Install Dependencies
```bash
pip install sentence-transformers numpy pandas pyarrow python-dateutil
```

### 3. Verify Installation
```bash
python verify_build.py
```

Expected output:
```
✓ redrob/ package structure OK
✓ All helpers importable
✓ SentenceTransformer loadable (BAAI/bge-small-en-v1.5)
✓ All precompute dependencies available
✓ All ranking dependencies available
```

---

## 💻 Running Commands

### Test on Sample (Quick Validation)
```bash
cd redrob
python test_sample.py
```
✓ **Runtime:** ~10 sec  
✓ **Output:** Console table with top 10 candidates + statistics

---

### Full Precomputation (One-Time Setup)
```bash
cd redrob
python precompute.py --candidates ../candidates.jsonl --out ../precomputed
```
✓ **Runtime:** 25–40 minutes (100K candidates, CPU)  
✓ **Disk:** ~2 GB for embeddings + metadata  
✓ **Output:** 4 files in `../precomputed/`

---

### Final Ranking (Submit)
```bash
cd redrob
python rank.py --artifacts ../precomputed --out ../submission.csv
```
✓ **Runtime:** <5 seconds  
✓ **Output:** `submission.csv` (100 top candidates)

---

### Full End-to-End (Complete Pipeline)
```bash
cd redrob
python precompute.py --candidates ../candidates.jsonl --out ../precomputed && \
python rank.py --artifacts ../precomputed --out ../submission.csv
```

---

## 📈 Key Features

### 🎯 Semantic Understanding
- Uses BAAI/bge-small-en-v1.5 embeddings (384-dim, state-of-the-art)
- JD facets extracted: core_tech, eval_rigor, product_eng, mindset, anti_patterns
- Candidate narrative built from career history + project descriptions
- Vectorized dot-product scoring (fast, scalable)

### 🔍 Multi-Dimensional Scoring
- **Not just keyword matching** — semantic + behavioral + career trajectory
- Variance penalty prevents one-dimensional profiles
- Behavioral multiplier adds context (dormant stars valued differently than notice risks)

### 🛡️ Quality Assurance
- Honeypot detection (fake profiles)
- Hard disqualifiers (visa issues, location mismatch, red flags)
- Consistency scoring (date logic, data quality)
- Grounded reasoning (every score has an explanation)

### ⚡ Performance
- Precomputation once (~30 min) → rank millions in seconds
- CPU-only, no GPU required
- <1 second online ranking for 100K candidates
- No network I/O during ranking

### 🧬 Interpretable Archetypes
Candidates classified into 4 behavioral types:
- **Neutral** — Steady, stable profiles (1.0× multiplier)
- **Dormant Star** — High potential but inactive (1.15× multiplier)
- **Notice Risk** — May be flight risk (0.85× multiplier)
- **Passive Fit** — Not actively looking but interested (1.05× multiplier)

---

## 🧠 Behavioral Archetypes

| Archetype | Characteristics | Multiplier | Signal |
|-----------|-----------------|------------|--------|
| 🟢 **Neutral** | Stable, normal career progression | 1.00× | Standard candidate |
| ⭐ **Dormant Star** | High experience, gap in employment | 1.15× | Rare talent, needs activation |
| ⚠️ **Notice Risk** | Recent job changes, short tenure | 0.85× | May leave quickly |
| 💤 **Passive Fit** | Not job searching but strong match | 1.05× | High confidence, lower urgency |

---

## 📝 Output Format

### Sample `submission.csv`
```csv
candidate_id,rank,score,reasoning
CAND_0000050,1,0.4831,"14yr product-company background; clear upward career arc; based in gurgaon, haryana. Concern: 90-day notice."
CAND_0000041,2,0.4478,"13yr product-company background; clear upward career arc; based in delhi, delhi. Concern: 90-day notice not disclosed."
CAND_0000007,3,0.4171,"5yr product-company background; passive candidate — reachable but not actively searching; based in gurgaon."
```

Each reasoning line includes:
- ✅ **Strengths:** Experience, archetype, location
- ⚠️ **Concerns:** Notice period, consistency flags, gaps
- 🎯 **Fit:** JD alignment and trajectory fit

---

## ⏱️ Performance

| Stage | Time | Scale | Notes |
|-------|------|-------|-------|
| **Precompute** | 25–40 min | 100K candidates | One-time, CPU |
| **JD Embedding** | <1 sec | 5 facets | Done once |
| **Candidate Embedding** | 20–30 min | 100K narratives | Batch size 256 |
| **Ranking** | <5 sec | 100K candidates | Vectorized dot-product |
| **Total E2E** | ~30 min | Full pipeline | Ready for submission |

---

## 🎓 Technical Stack

- **Language:** Python 3.8+
- **Embeddings:** `sentence-transformers` (BAAI/bge-small-en-v1.5)
- **Compute:** NumPy (vectorized scoring)
- **Storage:** Parquet (features), NumPy binary (embeddings), JSON (IDs)
- **Data Processing:** Pandas, PyArrow

---

## 📞 Support & Debugging

### ✓ Verify Build
```bash
python verify_build.py
```

### 🔧 Check Sample Test
```bash
cd redrob
python test_sample.py
```

### 📊 Inspect Features
```bash
python -c "import pandas as pd; df = pd.read_parquet('precomputed/features.parquet'); print(df.head())"
```

### 🔍 Validate Output
```bash
python validate_submission.py submission.csv
```

---

## 📋 Checklist

- [ ] Install dependencies: `pip install sentence-transformers numpy pandas pyarrow python-dateutil`
- [ ] Verify build: `python verify_build.py`
- [ ] Test on samples: `cd redrob && python test_sample.py`
- [ ] Run precompute: `python precompute.py --candidates ../candidates.jsonl`
- [ ] Run ranking: `python rank.py --artifacts ../precomputed --out ../submission.csv`
- [ ] Validate output: `python validate_submission.py submission.csv`
- [ ] Submit `submission.csv` to RedRob Hackathon

---

## 🏆 Results at a Glance

After running the full pipeline, you'll have:

✅ **submission.csv** — Top 100 ranked candidates with scores & reasoning  
✅ **Explainability** — Every score grounded in 6 dimensions + archetype  
✅ **Speed** — Ranking 100K candidates in <5 seconds  
✅ **Quality** — Multi-dimensional scoring + honeypot detection + consistency checks  

---

**Built for the RedRob Hackathon · 2026**  
*Advanced hiring intelligence through semantic understanding and behavioral analysis*

