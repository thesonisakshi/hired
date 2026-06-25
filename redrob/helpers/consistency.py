"""
Cross-field consistency scorer.

Fabricators create local coherence but fail at global coherence.
Build a consistency graph — claims are nodes, cross-field relationships are edges.

This module detects contradictions across work history, skills, certifications, and claims.
"""

import re
from datetime import datetime


def _extract_year(date_str):
    """Extract year from ISO date string or return None."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(str(date_str)).year
    except (ValueError, TypeError):
        return None


def compute_consistency_score(candidate: dict) -> tuple[float, list[str]]:
    """
    Returns (score 0-1, list of flag strings).
    
    Six cross-field checks:
    1. Expert skill count vs experience length
    2. Leadership claims vs career stage
    3. Scale claims vs company type
    4. OSS claims vs GitHub activity
    5. Senior titles vs total years
    6. Cert farming vs project evidence
    
    Each flag deducts 0.15. Floor at 0.0.
    
    Args:
        candidate: dict with career_history, skills, projects, certifications, etc.
        
    Returns:
        (score float 0-1, list of flag strings)
    """
    flags = []
    current_year = datetime.now().year
    roles = candidate.get('career_history', [])

    # Calculate total experience years from date strings
    total_exp = 0
    for role in roles:
        start_str = role.get('start_date')
        end_str = role.get('end_date')
        start_year = _extract_year(start_str)
        end_year = _extract_year(end_str) if end_str else current_year
        if start_year and end_year:
            total_exp += (end_year - start_year)
    total_exp = max(total_exp, 0)

    # Aggregate all descriptive text
    profile = candidate.get('profile', {})
    all_text = ' '.join([
        profile.get('summary', ''),
        ' '.join(r.get('description', '') for r in roles),
        ' '.join(p.get('description', '')
                 for p in candidate.get('projects', []))
    ])

    # Check 1: Expert skill count vs experience length
    expert_skills = [s for s in candidate.get('skills', [])
                     if s.get('proficiency') in ('expert', 'advanced')]
    if len(expert_skills) > 12 and total_exp < 5:
        flags.append('too_many_expert_claims_for_experience_length')

    # Check 2: Leadership claims vs career stage
    lead_count = len(re.findall(
        r'led (?:a )?team|managed \d+|head of|director of',
        all_text, re.IGNORECASE
    ))
    if lead_count > 3 and total_exp < 3:
        flags.append('leadership_claims_inconsistent_with_career_stage')

    # Check 3: Scale claims vs company type
    from helpers.narrative import classify_company
    scale_nums = re.findall(
        r'\b(\d+)M\s+(?:users|requests|records|transactions)',
        all_text, re.IGNORECASE
    )
    large_scale = [int(m) for m in scale_nums if int(m) > 10]
    ctypes = [classify_company(r.get('company', '')) for r in roles]
    if large_scale and ctypes and all(t == 'services' for t in ctypes):
        flags.append('large_scale_claims_at_services_firm')

    # Check 4: OSS claims vs GitHub activity
    github_score = candidate.get('redrob_signals', {}).get(
        'github_activity_score', -1
    )
    oss_count = len(re.findall(
        r'open.source|github\.com|contributed to', all_text, re.IGNORECASE
    ))
    if oss_count > 3 and github_score != -1 and github_score < 10:
        flags.append('oss_contribution_claims_no_github_activity')

    # Check 5: Senior titles inconsistent with years
    titles_text = ' '.join(r.get('title', '').lower() for r in roles)
    if (any(t in titles_text for t in ['principal', 'staff', 'distinguished'])
            and total_exp < 4):
        flags.append('senior_title_inconsistent_with_years')

    # Check 6: Cert farming pattern
    certs = candidate.get('certifications', [])
    projects = candidate.get('projects', [])
    if len(certs) > 6 and len(projects) == 0 and total_exp < 4:
        flags.append('cert_farming_pattern_no_project_evidence')

    score = max(0.0, 1.0 - len(flags) * 0.15)
    return score, flags
