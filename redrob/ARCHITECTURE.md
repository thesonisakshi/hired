# System Architecture & Design Philosophy

## Core Mission

**Read people, not documents.**

The resume is a marketing document optimized for screener algorithms. We instead look for:
1. **What candidates revealed without intending to** — specificity they couldn't fake, vocabulary from real work
2. **What they demonstrably did** — action-verb language that only appears when recounting real events

## Three Core Insights

### Insight 1: Specificity is Signal
Fabricators write in generalities. Real practitioners write specifics because specifics are what they remember.
- "Implemented machine learning" = generic, suspicious
- "Fine-tuned sentence-transformers embeddings for 300K document corpus, boosted NDCG@10 from 0.62 to 0.71" = specific, credible

### Insight 2: Global Consistency > Local Coherence
Fabricators nail local coherence (each claim sounds reasonable in isolation) but fail at global coherence.
- Bad: "15 years experience" + "worked at startup pre-seed" + "senior director role" all sound plausible independently
- Contradiction: 15 years is impossible if career started 4 years ago

### Insight 3: Behaviors Matter as Much as Skills
A brilliant candidate who never responds is functionally unavailable.
- Behavioral archetypes (active_seeker, ghost, dormant_star) gate hirability multiplicatively
- Not: "0.9 score × 0.2 responsiveness = 0.18" (additive)
- But: "0.9 score × 0.2 responsiveness = 0.18" (multiplicative, gates hard)

---

## Architecture: 8-Layer Scoring System

```
┌─ Layer 1: JD Decomposition ────────────┐
│ 5 semantic facets (separate vectors)   │
├────────────────────────────────────────┤
│ ↓                                      │
├─ Layer 2: Evidence Narrative ──────────┤
│ Action-verb extraction (ground truth)   │
├────────────────────────────────────────┤
│ ↓                                      │
├─ Layers 3-8: Scoring Dimensions ──────┤
│ • Specificity (regex, 5D)              │
│ • Consistency (cross-field checks)     │
│ • Honeypot Detection (disqualify)      │
│ • Behavioral Archetype (multiplier)    │
│ • Trajectory (growth arc)              │
│ • Logistics (location + notice)        │
├────────────────────────────────────────┤
│ Composite Score Formula                │
│ (base - variance_penalty) × behavior   │
├────────────────────────────────────────┤
│ ↓                                      │
├─ Grounded Reasoning ──────────────────┤
│ 1-2 sentence explanation from data     │
└────────────────────────────────────────┘
```

---

## Layer Details

### Layer 1: JD Facet Decomposition

**Why?** Semantic similarity is crude. A "retrieval" candidate might match on CV/robotics (wrong), NLP (better), or ranking (best). Single embeddings can't distinguish.

**How?** 5 independent facets:
```
core_technical       → embedding, vector DB, retrieval, ranking, ANN, reranking
evaluation_rigor     → NDCG, MRR, A/B testing, benchmarking, metrics
product_engineer     → shipped, deployed, real users, scale, ownership, iteration
mindset              → async, scrappy, founding team, ambiguity, ownership, move fast
anti_patterns        → research, consulting, CV/speech, no NLP, no deployment
```

Weights: [0.35, 0.20, 0.25, 0.10, -0.10]
- Anti-patterns weight is **negative** (high similarity penalizes)

**Example:**
- Candidate A: "ML researcher, computer vision focus, published 3 papers"
  - Semantic: core_tech=0.2, eval_rigor=0.1, product=0.05, mindset=0.2, anti=**0.9** → PENALIZED
- Candidate B: "Led search ranking team, shipped NDCG improvements, 50M queries/day"
  - Semantic: core_tech=0.85, eval_rigor=0.8, product=0.95, mindset=0.6, anti=0.1 → REWARDED

---

### Layer 2: Evidence Narrative

**Why?** Raw profile text is noisy (disclaimers, claims, skill lists). We want only demonstrable facts.

**How?** Extract action-verb sentences:
```python
ACTION_VERBS = [
    'built', 'shipped', 'deployed', 'scaled', 'designed',
    'led', 'launched', 'improved', 'optimized', 'migrated', 'architected',
    'implemented', 'created', 'developed', 'established', 'automated',
    'trained', 'fine-tuned', 'evaluated', 'benchmarked', 'monitored',
    'owned', 'drove', 'delivered', 'introduced', 'rewrote', 'replaced'
]
```

**Example:**
```
Raw: "Skilled in Python, Java, and C++. Experienced with machine learning.
     Interested in working with great teams on challenging problems. 
     Led team of 5 engineers."

Action sentences: "Led team of 5 engineers."

Result: Narrative focused on concrete actions.
```

---

### Layer 3: Specificity Entropy (0-1)

**Why?** Fabricators generalize; practitioners specify. This is our most powerful fraud detector.

**How?** 5 regex dimensions:

1. **Numeric Density** (counts, scale, performance)
   - "10K requests/sec", "99.9% uptime", "5x improvement"
   - Low score if no numbers

2. **Versioned Tech** (named tools + versions)
   - "PostgreSQL 14", "Kafka with exactly-once", "sentence-transformers 2.3"
   - High score if specific tool + configuration

3. **Failure/Tradeoff Language** (only experienced practitioners mention what broke)
   - "We tried approach X but bottlenecked on Y"
   - "Switched from Redis to Memcached for"
   - High score if admits tradeoffs

4. **Temporal Precision** (exact dates/durations)
   - "18 months", "Q4 2023", "3 weeks to MVP"
   - Low score if vague ("several years")

5. **Scope/Team Language** (real leads mention structure)
   - "Team of 12", "Collaborated with 3 data scientists"
   - High score if mentions people/structure

**Score Computation:**
```python
components = [numeric_density, versioned_tech, failures, temporal, scope]
score = mean(components)  # 0-1
```

**Example:**
- Generic: "Developed machine learning system" → [0.0, 0.1, 0.0, 0.0, 0.0] → 0.02
- Specific: "Fine-tuned BERT-large on 200K domain docs, improved F1 from 0.78→0.85,
  deployed to 2M monthly users, took 3 weeks, worked with product team of 4"
  → [0.8, 0.9, 0.7, 0.9, 0.95] → 0.87

---

### Layer 4: Cross-Field Consistency (0-1)

**Why?** Global contradictions flag fabrication. Local coherence isn't enough.

**How?** Build consistency graph, check 6 edge types:

1. **Expert Skills vs Experience Length**
   - Flag if: 12+ expert skills claimed BUT <5 years total experience
   - Cost: -0.15

2. **Leadership Claims vs Career Stage**
   - Flag if: "led team" appears 3+ times BUT <3 years experience
   - Cost: -0.15

3. **Scale Claims vs Company Type**
   - Flag if: "10M users" claimed BUT only at services firms (TCS, Infosys, etc.)
   - Cost: -0.15

4. **OSS Claims vs GitHub Activity**
   - Flag if: "contributed to open source" appears 3+ times BUT GitHub score <10
   - Cost: -0.15

5. **Senior Title vs Years**
   - Flag if: "Principal", "Staff", "Distinguished" BUT <4 years total
   - Cost: -0.15

6. **Cert Farming**
   - Flag if: 6+ certifications BUT 0 projects AND <4 years experience
   - Cost: -0.15

**Score:** `max(0.0, 1.0 - num_flags * 0.15)`

**Example:**
```
Candidate claims: "Principal Engineer, 15 years XP, led ML team, 
                   10M user platform, AWS certified, GCP certified, 
                   Azure certified"

But actually: Started career in 2023 (2 years)

Flags:
- Principal + 2 years: -0.15
- Led team + 2 years: -0.15
- 10M users + services only: -0.15
- 3 certs + 2 years: -0.15

Score: max(0.0, 1.0 - 4*0.15) = 0.40
```

---

### Layer 5: Honeypot Detection (Hard Disqualify = 0.0)

**Why?** Some profiles are logically impossible, not just low-quality.

**How?** 4 checks:

1. **Timeline Impossibility**
   - Worked at OpenAI in 2013 (founded 2015)
   - Disqualify: Yes

2. **Experience Exceeds Career Span**
   - Claimed 25 years in 12-year career
   - Disqualify: Yes

3. **Expert Skills with Zero Evidence**
   - "Expert in deep learning" appears in skills BUT never mentioned in descriptions
   - Only if: 10+ expert claims AND 0 evidenced
   - Disqualify: Yes

4. **Future Dates**
   - End date 2027 (current year 2026)
   - Disqualify: Yes

**Score:** `0.0` (not gradual penalty; hard cutoff)

---

### Layer 6: Behavioral Archetype Classifier (0.20-1.30 Multiplier)

**Why?** Skills matter, but availability matters more. A sleeping genius is unavailable.

**How?** Map platform signals to 7 archetypes:

| Archetype | Signals | Multiplier | Meaning |
|-----------|---------|-----------|---------|
| **active_seeker** | open=true, active<14d, response>0.6 | 1.30 | Hungry, responsive |
| **highly_selective** | accept_rate>0.7, completion>0.85, apps<5 | 1.15 | High bar, quality seeker |
| **passive_fit** | open=false, active<60d, response>0.4 | 1.00 | Recruiters can reach |
| **neutral** | Mixed/unclear signals | 0.85 | Default |
| **notice_risk** | notice>90d, response>0.5 | 0.75 | Good fit but slow hire |
| **serial_applier** | apps_30d>20 | 0.65 | Spam pattern |
| **dormant_star** | active>120d, response<0.3 | 0.45 | Went dark |
| **ghost** | response<0.1, completion<0.25 | 0.20 | Never engages |

**Application:** Final score = (base - penalty) **×** archetype_multiplier

**Example:**
- Base score 0.8, archetype "active_seeker" (1.30): Final = 0.8 × 1.30 = 1.04 (capped at 1.0)
- Base score 0.8, archetype "ghost" (0.20): Final = 0.8 × 0.20 = 0.16

---

### Layer 7: Trajectory Scorer (0-1)

**Why?** 4-year candidate growing 50% YoY beats 10-year candidate who peaked at year 3.

**How?** Measure career arc:

1. **Verb Tier Progression**
   - Operator (implemented, deployed)
   - Builder (architected, designed, built)
   - Director (led, set direction, owned strategy)
   - Do scores increase chronologically?

2. **Scope Growth**
   - Extract max numbers from each role
   - Do numbers increase over time?

3. **Title Progression**
   - Does title seniority increase?

**Formula:**
```
verb_trend = % of roles where tier ≥ previous tier
scope_trend = % of roles where scope ≥ previous scope
score = 0.6 * verb_trend + 0.4 * scope_trend
```

**Example:**
```
Role 1 (2020): "Implemented data pipeline" → verb=1 (operator), scope=0
Role 2 (2021): "Built real-time system for 1M events" → verb=2 (builder), scope=1M
Role 3 (2022): "Architected platform serving 100M queries" → verb=2 (builder), scope=100M

Verb trend: 50% of increases (1→2 is increase, 2→2 is flat) = 0.50
Scope trend: 100% of increases (0→1M is increase, 1M→100M is increase) = 1.00
Score: 0.6 * 0.50 + 0.4 * 1.00 = 0.70
```

---

### Layer 8: Logistics Scorer (0-1)

**Why?** Hiring is logistics. Location and notice period matter.

**How?** Two dimensions:

**Location** (0.4-1.0):
- In target city (Pune, Mumbai, Delhi, Bangalore, Hyderabad, Noida): 1.0
- Willing to relocate: 0.8
- Other: 0.4

**Notice Period** (0.25-1.0):
- ≤30 days: 1.0
- ≤60 days: 0.75
- ≤90 days: 0.50
- >90 days: 0.25

**Formula:** `0.6 * location_score + 0.4 * notice_score`

---

## Composite Scoring

### Formula
```
base = 0.30*semantic + 0.20*specificity + 0.20*consistency + 0.15*trajectory + 0.15*logistics

variance_penalty = min(var(dimensions) * 2.5, 0.20)

final = max(0.0, (base - variance_penalty) * behavior_multiplier)

if is_honeypot or hard_disqualified:
    final = 0.0
```

### Why Variance Penalty?
High disagreement between dimensions is suspicious:
- 0.9 semantic + 0.1 specificity = 0.5 base, but high variance (disagreement flagged)
- 0.7 semantic + 0.7 specificity = 0.7 base, low variance (consistent profile)

Candidates with narrow paper (good keywords, vague details) get penalized. Those with broad consistency get rewarded.

### Dimension Weights
- **Semantic** (0.30): Largest — direct JD match matters most
- **Specificity** (0.20): High — fraud detection critical
- **Consistency** (0.20): High — catches global contradictions
- **Trajectory** (0.15): Medium — growth matters but not primary signal
- **Logistics** (0.15): Medium — hiring practical constraint

---

## Reasoning Generator

Every output row includes a grounded 1-2 sentence reasoning. **No hallucination.**

Template: `"{strengths}. [Concern: {concerns}.]"`

**Strengths picked from:**
- Total exp years + company type ("5yr product background")
- Specificity bucket ("high-specificity descriptions")
- Evidenced skills ("evidenced in Python, Kubernetes, FastAPI")
- Trajectory ("clear upward career arc")
- Behavioral archetype ("actively available", "passive fit", "dormant")
- Location ("based in Bangalore")

**Concerns picked from:**
- Consistency flags ("expert skill count vs experience mismatch")
- Notice period ("90-day notice period")
- Behavioral patterns ("platform inactive 4+ months", "ghost")

---

## Two-Mode Runtime

### Pre-computation (No Time Limit)
```
precompute.py
├─ Load 100K candidates
├─ For each candidate:
│  ├─ Build evidence narrative
│  ├─ Compute specificity, consistency, trajectory, logistics
│  ├─ Check honeypot/disqualifiers
│  └─ Store pre-computed scores
├─ Batch embed all narratives (~20-30 min)
├─ Embed JD facets
└─ Save artifacts (npy, json, parquet)
```

### Ranking (Must finish <5 min, CPU only, no network)
```
rank.py
├─ Load pre-computed embeddings + features (~1 sec)
├─ Vectorized semantic similarity (5 sec)
├─ Vectorized composite scoring (<1 sec)
├─ Select top 100
├─ Generate reasoning strings
└─ Write CSV
```

Total: ~6-7 seconds

---

## Key Innovations

1. **Evidence Narratives**: Not raw profiles → action-verb extraction
2. **Specificity Entropy**: Regex-based fabrication detection (5 dimensions)
3. **Consistency Graph**: Cross-field contradiction detection (6 checks)
4. **Honeypot Disqualification**: Hard gates for impossible profiles
5. **Behavioral Archetype**: 7 named patterns with multipliers, not flat signals
6. **Variance Penalty**: Punishes dimensional disagreement (neat paper suspect)
7. **Grounded Reasoning**: Zero hallucination — every claim traces to data
8. **JD Decomposition**: 5 independent semantic facets, not one embedding

---

## Limitations & Future Work

### Known Constraints
- Founding year dict incomplete (manual curation needed)
- Geographic targeting limited to India (easily extensible)
- No photo/video/portfolio URL signals
- No recommendation graph analysis
- Behavioral signals assume platform data quality

### Potential Improvements
1. **Dynamic Weights**: Learn optimal dimension weights from labeled holdout
2. **Graph Signals**: Network analysis (who referred, who endorsed, collaboration patterns)
3. **Semantic Drift**: Track consistency of language over time (fabricators shift tone)
4. **Portfolio**: Embed GitHub repos, deployed projects, papers
5. **Cross-Validation**: Check claims against external sources (LinkedIn, GitHub, research databases)
6. **Temporal Signals**: Career velocity trends, role duration patterns
7. **Fine-grained NLP**: Dependency parsing for nuanced claim extraction

---

## Validation Metrics

**Proxy Metrics** (on test set if labeled data available):
- Specificity ROC-AUC (precision of fraud detection)
- Consistency flags precision (% caught actually fabricate)
- Archetype prediction accuracy (platform signals reliable?)
- Final score correlation with hiring outcomes (if labeled)

**Operational Metrics**:
- Honeypot rate in top 100 (target <10%)
- Average notice period in top 100 (target <60 days)
- Archetype distribution (target 60% active_seeker + highly_selective)
- Reasoning string coherence (manual sampling)

---

## Design Philosophy Summary

> **Read people, not documents.**
>
> The resume is a sales pitch. We look for:
> 1. Specificity they couldn't fake
> 2. Contradictions they didn't notice
> 3. Vocabulary only from doing the work
> 4. Availability signals that reflect reality
>
> Every score is explainable from data. No hallucination. No inference beyond grounding.
> 
> Match the job description precisely across 5 dimensions. Catch fabricators with consistency checks.
> Gate on behavior because brilliant but unavailable is worthless.
>
> Output: top 100 genuine fits, ranked by real hirability, explained by specific facts.
