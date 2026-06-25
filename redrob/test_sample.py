#!/usr/bin/env python3
"""
Test script for sample data.
Works with sample_candidates.json (non-gzipped JSON).

Usage:
    python test_sample.py
"""

import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# Add parent directory to path so we can import redrob helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers.narrative import build_evidence_narrative, classify_company
from helpers.specificity import compute_specificity_score
from helpers.consistency import compute_consistency_score
from helpers.honeypot import is_honeypot, check_jd_disqualifiers
from helpers.behavioral import classify_behavioral_archetype
from helpers.trajectory import compute_trajectory_score
from helpers.logistics import compute_logistics_score
from helpers.jd import JD_FACETS
from helpers.reasoning import generate_reasoning


def compute_total_experience_years(candidate: dict) -> float:
    """Calculate total years of work experience from career_history dates."""
    current_year = datetime.now().year
    roles = candidate.get('career_history', [])
    
    def _extract_year(date_str):
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(str(date_str)).year
        except (ValueError, TypeError):
            return None
    
    total = 0
    for r in roles:
        start_year = _extract_year(r.get('start_date'))
        end_str = r.get('end_date')
        end_year = _extract_year(end_str) if end_str else current_year
        if start_year and end_year:
            total += (end_year - start_year)
    
    return max(float(total), 0.0)


def get_evidenced_skills(candidate: dict, n: int = 3) -> str:
    """Return top-N skills that appear in description text — verified, not claimed."""
    all_desc = ' '.join([
        ' '.join(r.get('description', '') for r in candidate.get('career_history', [])),
        ' '.join(p.get('description', '') for p in candidate.get('projects', []))
    ]).lower()
    skills = candidate.get('skills', [])
    evidenced = [
        s['name'] for s in skills
        if s.get('name') and s['name'].lower() in all_desc
    ]
    return ', '.join(evidenced[:n])


def test_on_sample(sample_path: str = './sample_candidates.json'):
    """Test system on sample data."""
    print("=" * 60)
    print("REDROB TEST: Sample Candidate Processing")
    print("=" * 60)
    
    # Resolve sample path from repo root if needed
    sample_path = os.path.abspath(sample_path)
    if not os.path.exists(sample_path):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alt_path = os.path.join(repo_root, 'sample_candidates.json')
        if os.path.exists(alt_path):
            sample_path = alt_path

    # Load sample data
    print(f"\nLoading {sample_path}...")
    with open(sample_path, 'r', encoding='utf-8') as f:
        candidates = json.load(f)
    
    if isinstance(candidates, dict):
        candidates = [candidates]
    
    print(f"Loaded {len(candidates)} candidates")

    # Load model
    print("\nLoading embedding model...")
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')

    # Embed JD facets
    print("Embedding JD facets...")
    facet_texts = list(JD_FACETS.values())
    jd_embs = model.encode(facet_texts, normalize_embeddings=True)
    print(f"  JD embeddings shape: {jd_embs.shape}")

    # Process candidates
    records, narratives, ids = [], [], []
    
    print(f"\nProcessing {len(candidates)} candidates...")
    for i, c in enumerate(candidates):
        try:
            cid = c.get('candidate_id', f'unknown_{i}')
            ids.append(cid)
            
            narrative = build_evidence_narrative(c)
            narratives.append(narrative)
            
            is_hp, hp_reason = is_honeypot(c)
            disq = check_jd_disqualifiers(c)
            spec = compute_specificity_score(c)
            cons, flags = compute_consistency_score(c)
            traj = compute_trajectory_score(c)
            logi = compute_logistics_score(c)
            arch, bmult = classify_behavioral_archetype(c.get('redrob_signals', {}))
            evidenced = get_evidenced_skills(c, 3)
            exp_yrs = compute_total_experience_years(c)
            ctypes = [classify_company(r.get('company', ''))
                      for r in c.get('career_history', [])]
            ctype_summary = 'product' if any(t == 'product' for t in ctypes) else 'services'
            sig = c.get('redrob_signals', {})
            notice = sig.get('notice_period_days', 60)
            loc = c.get('profile', {}).get('location', '')
            
            records.append({
                'candidate_id': cid,
                'is_honeypot': is_hp,
                'hard_disqualified': disq['hard_disqualify'],
                'specificity': round(spec, 4),
                'consistency': round(cons, 4),
                'trajectory': round(traj, 4),
                'logistics': round(logi, 4),
                'behavior_mult': round(bmult, 3),
                'behavior_archetype': arch,
                'consistency_flags': '|'.join(flags),
                'evidenced_skills': evidenced,
                'total_exp_years': exp_yrs,
                'company_type_summary': ctype_summary,
                'notice_period_days': notice,
                'location_city': loc,
            })
            
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1} candidates...")
        
        except Exception as e:
            print(f"  ERROR processing candidate {i}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nProcessed {len(records)} candidates successfully")
    
    # Embed narratives
    print("Embedding narratives...")
    embs = model.encode(narratives, batch_size=32, show_progress_bar=True, 
                       normalize_embeddings=True)
    print(f"  Embeddings shape: {embs.shape}")
    
    # Create DataFrame
    df = pd.DataFrame(records)
    df['candidate_id'] = ids
    
    # Compute semantic similarity
    print("Computing semantic similarity...")
    sim = embs @ jd_embs.T
    facet_weights = np.array([0.35, 0.20, 0.25, 0.10, -0.10])
    df['semantic'] = np.clip((sim * facet_weights).sum(axis=1), 0, 1)
    
    # Composite score
    dim_cols = ['semantic', 'specificity', 'consistency', 'trajectory', 'logistics']
    weights   = [0.30,       0.20,          0.20,          0.15,         0.15]
    
    df['base'] = sum(df[col] * w for col, w in zip(dim_cols, weights))
    df['variance_penalty'] = (df[dim_cols].var(axis=1).clip(0, 0.08) * 2.5)
    df['final_score'] = (
        (df['base'] - df['variance_penalty']) * df['behavior_mult']
    ).clip(lower=0)
    
    # Hard zeros
    mask = df['is_honeypot'] | df['hard_disqualified']
    df.loc[mask, 'final_score'] = 0.0
    
    # Generate reasoning
    print("Generating reasoning strings...")
    df['reasoning'] = df.apply(
        lambda row: generate_reasoning(row.to_dict()), axis=1
    )
    
    # Sort and select top N
    top = df.nlargest(min(10, len(df)), 'final_score').reset_index(drop=True)
    top['rank'] = top.index + 1
    top['score'] = top['final_score'].round(4)
    
    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"\nTop {len(top)} candidates:")
    print()
    
    for idx, row in top.iterrows():
        print(f"Rank {row['rank']}: {row['candidate_id']}")
        print(f"  Score: {row['score']}")
        print(f"  Archetype: {row['behavior_archetype']}")
        print(f"  Experience: {row['total_exp_years']:.1f}yr ({row['company_type_summary']})")
        print(f"  Specificity: {row['specificity']:.3f} | Consistency: {row['consistency']:.3f}")
        print(f"  Reasoning: {row['reasoning'][:100]}...")
        print()
    
    # Statistics
    print("=" * 60)
    print("STATISTICS")
    print("=" * 60)
    print(f"\nTotal candidates: {len(df)}")
    print(f"Honeypots: {df['is_honeypot'].sum()}")
    print(f"Hard disqualified: {df['hard_disqualified'].sum()}")
    print(f"\nScore distribution:")
    print(df['final_score'].describe())
    print(f"\nArchetype distribution:")
    print(df['behavior_archetype'].value_counts())


if __name__ == '__main__':
    test_on_sample()
