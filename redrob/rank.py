#!/usr/bin/env python3
"""
Online ranking pipeline.
Must complete in under 5 minutes. CPU only. No network.

Usage:
    python rank.py --out ./submission.csv
"""

import argparse
import json
import time

import numpy as np
import pandas as pd

from helpers.reasoning import generate_reasoning


def rank_candidates(
    out_dir: str = 'precomputed',
    output: str = 'submission.csv',
    top_n: int = 100
):
    """
    Rank candidates and produce final submission CSV.
    
    Must complete in under 5 minutes.
    
    Args:
        out_dir: directory with pre-computed artifacts
        output: path to output CSV file
        top_n: number of top candidates to return (default 100)
    """
    t0 = time.time()

    # Load pre-computed artifacts
    print("Loading artifacts...")
    embs = np.load(f'{out_dir}/candidate_embeddings.npy')          # (100K, dim)
    jd_embs = np.load(f'{out_dir}/jd_facet_embeddings.npy')        # (5, dim)
    with open(f'{out_dir}/candidate_ids.json') as f:
        ids = json.load(f)
    df = pd.read_parquet(f'{out_dir}/features.parquet')
    df['candidate_id'] = ids
    print(f"  Loaded {len(df):,} candidates in {time.time()-t0:.1f}s")

    # Vectorized semantic similarity: (100K, 5) — ~5 seconds
    print("Computing similarity...")
    sim = embs @ jd_embs.T  # dot product, embeddings pre-normalized
    # Facet weights: core_tech, eval_rigor, product_eng, mindset, anti_patterns
    # anti_patterns is negative (high similarity = penalty)
    facet_weights = np.array([0.35, 0.20, 0.25, 0.10, -0.10])
    df['semantic'] = np.clip((sim * facet_weights).sum(axis=1), 0, 1)
    print(f"  Similarity done in {time.time()-t0:.1f}s")

    # Composite score (vectorized, <1 second)
    dim_cols = ['semantic', 'specificity', 'consistency', 'trajectory', 'logistics']
    weights   = [0.30,       0.20,          0.20,          0.15,         0.15]

    df['base'] = sum(df[col] * w for col, w in zip(dim_cols, weights))

    # Variance penalty: punish profiles where dimensions strongly disagree
    df['variance_penalty'] = (
        df[dim_cols].var(axis=1).clip(0, 0.08) * 2.5
    )

    # Behavioral multiplier — applied last, multiplicative
    df['final_score'] = (
        (df['base'] - df['variance_penalty']) * df['behavior_mult']
    ).clip(lower=0)

    # Hard zeros for disqualified and honeypots
    mask = df['is_honeypot'] | df['hard_disqualified']
    df.loc[mask, 'final_score'] = 0.0

    print(f"  Scoring done in {time.time()-t0:.1f}s")
    print(f"  Disqualified: {mask.sum():,} candidates zeroed")

    # Select top N
    top = df.nlargest(top_n, 'final_score').copy().reset_index(drop=True)
    top['rank'] = top.index + 1
    top['score'] = top['final_score'].round(4)

    # Generate grounded reasoning strings
    print("Generating reasoning strings...")
    top['reasoning'] = top.apply(
        lambda row: generate_reasoning(row.to_dict()), axis=1
    )

    # Write CSV
    result = top[['candidate_id', 'rank', 'score', 'reasoning']]
    result.to_csv(output, index=False)

    elapsed = time.time() - t0
    print(f"\nRanking complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Output: {output}")
    print(f"Top score: {top['final_score'].iloc[0]:.4f}")
    print(f"Score range: {top['final_score'].iloc[-1]:.4f} — {top['final_score'].iloc[0]:.4f}")
    print(f"\nTop 10 archetypes:")
    print(top['behavior_archetype'].head(10).value_counts().to_dict())
    print(f"\nConsistency flags in top 10:")
    top10_flags = top['consistency_flags'].head(10).str.split('|').explode()
    top10_flags = top10_flags[top10_flags != '']
    if len(top10_flags) > 0:
        print(top10_flags.value_counts().to_dict())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='submission.csv',
                        help='Output CSV file path')
    parser.add_argument('--artifacts', default='precomputed',
                        help='Directory with pre-computed artifacts')
    args = parser.parse_args()
    rank_candidates(out_dir=args.artifacts, output=args.out)
