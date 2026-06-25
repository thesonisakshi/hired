#!/usr/bin/env python3
"""
Offline pre-computation pipeline.
Run once before the competition. No time limit.
Estimated time: 25-40 minutes for 100K candidates on CPU.

Usage:
    python precompute.py --candidates ./candidates.jsonl.gz
"""

import argparse
import gzip
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from helpers.narrative import build_evidence_narrative, classify_company
from helpers.specificity import compute_specificity_score
from helpers.consistency import compute_consistency_score
from helpers.honeypot import is_honeypot, check_jd_disqualifiers
from helpers.behavioral import classify_behavioral_archetype
from helpers.trajectory import compute_trajectory_score
from helpers.logistics import compute_logistics_score
from helpers.jd import JD_FACETS


def compute_total_experience_years(candidate: dict) -> float:
    """Calculate total years of work experience from career_history dates."""
    from datetime import datetime
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


def precompute_all(candidates_path: str, out_dir: str = 'precomputed'):
    """
    Run full offline pre-computation pipeline.
    
    Args:
        candidates_path: path to candidates.jsonl.gz
        out_dir: output directory for artifacts
    """
    os.makedirs(out_dir, exist_ok=True)

    print("Loading embedding model...")
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')

    # Embed JD facets
    print("Embedding JD facets...")
    facet_texts = list(JD_FACETS.values())
    jd_embs = model.encode(facet_texts, normalize_embeddings=True)
    np.save(f'{out_dir}/jd_facet_embeddings.npy', jd_embs)
    print(f"  Saved {len(facet_texts)} facet embeddings")

    # Process all candidates
    records, narratives, ids = [], [], []
    errors = 0

    def open_candidate_file(path: str):
        if path.lower().endswith('.gz'):
            return gzip.open(path, 'rt', encoding='utf-8')
        return open(path, 'rt', encoding='utf-8')

    def candidate_iterator(path: str):
        with open_candidate_file(path) as f:
            if path.lower().endswith('.json'):
                data = json.load(f)
                if isinstance(data, dict):
                    yield data
                elif isinstance(data, list):
                    for item in data:
                        yield item
                return

            for i, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    print("Processing candidates...")
    for i, c in enumerate(candidate_iterator(candidates_path)):
            if not c:
                continue

            cid = c.get('candidate_id', f'unknown_{i}')
            ids.append(cid)
            narratives.append(build_evidence_narrative(c))

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

            if (i + 1) % 5000 == 0:
                print(f"  Processed {i + 1:,} candidates...")

    print(f"Processed {len(records):,} candidates ({errors} errors)")

    # Batch embed all narratives
    print("Embedding narratives (this takes ~20-30 minutes)...")
    embs = model.encode(
        narratives,
        batch_size=256,
        show_progress_bar=True,
        normalize_embeddings=True
    )
    np.save(f'{out_dir}/candidate_embeddings.npy', embs)
    with open(f'{out_dir}/candidate_ids.json', 'w') as f:
        json.dump(ids, f)
    pd.DataFrame(records).to_parquet(f'{out_dir}/features.parquet', index=False)

    print(f"\nPre-computation complete.")
    print(f"  Embeddings: {embs.shape}")
    print(f"  Features: {len(records)} rows")
    print(f"  Honeypots detected: {sum(r['is_honeypot'] for r in records)}")
    print(f"  Hard disqualified: {sum(r['hard_disqualified'] for r in records)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidates', required=True,
                        help='Path to candidates.jsonl.gz')
    parser.add_argument('--out', default='precomputed',
                        help='Output directory for artifacts')
    args = parser.parse_args()
    precompute_all(args.candidates, args.out)
