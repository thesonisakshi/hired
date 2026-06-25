"""
Honeypot and constraint violation detector.

Run this FIRST. Flagged candidates get score = 0.0.
These are logically impossible profiles, not just low-quality ones.
"""

import re
from datetime import datetime


# Populate this as you inspect the dataset
# Format: 'company name lowercase': year_founded
KNOWN_FOUNDING_YEARS = {
    'openai': 2015,
    'anthropic': 2021,
    'google': 1998,
    'microsoft': 1975,
    'meta': 2004,
    'amazon': 1994,
    'apple': 1976,
    'tesla': 2003,
    'netflix': 1997,
}


def is_honeypot(candidate: dict) -> tuple[bool, str]:
    """
    Hard disqualification. Returns (is_honeypot, reason).
    
    Four checks:
    1. Worked at company before it was founded
    2. Total claimed experience exceeds career span by >4 years
    3. 10+ expert skills with zero textual evidence anywhere
    4. Future dates in experience (end_year > current_year)
    
    Args:
        candidate: dict with career_history, skills, projects, etc.
        
    Returns:
        (is_honeypot bool, reason string)
    """
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

    # Check 1: Timeline impossibility — worked before company founded
    for role in roles:
        company = role.get('company', '').lower().strip()
        start_str = role.get('start_date')
        start_year = _extract_year(start_str)
        founded = KNOWN_FOUNDING_YEARS.get(company)
        if start_year and founded and start_year < founded - 1:
            return True, f"Worked at {role['company']} before it was founded ({founded})"

    # Check 2: Experience exceeds career span by >4 years
    if roles:
        start_years = [_extract_year(r.get('start_date')) for r in roles]
        start_years = [y for y in start_years if y]
        if start_years:
            career_start = min(start_years)
            career_span = current_year - career_start
            total_claimed = 0
            for r in roles:
                start_year = _extract_year(r.get('start_date'))
                end_str = r.get('end_date')
                end_year = _extract_year(end_str) if end_str else current_year
                if start_year and end_year:
                    total_claimed += (end_year - start_year)
            if total_claimed > career_span + 4:
                return (True,
                    f"Claimed {total_claimed}yr experience in {career_span}yr career")

    # Check 3: Expert claims with zero evidence
    all_desc = ' '.join([
        ' '.join(r.get('description', '') for r in roles),
        ' '.join(p.get('description', '')
                 for p in candidate.get('projects', []))
    ]).lower()
    expert_skills = [s['name'] for s in candidate.get('skills', [])
                     if s.get('proficiency') == 'expert']
    evidenced = [s for s in expert_skills if s.lower() in all_desc]
    if len(expert_skills) >= 10 and len(evidenced) == 0:
        return (True,
            f"{len(expert_skills)} expert skill claims, zero appear in any description")

    # Check 4: Future dates
    for role in roles:
        end_str = role.get('end_date')
        end_year = _extract_year(end_str)
        if end_year and end_year > current_year + 1:
            return True, f"Role end date {end_year} is in the future"

    return False, ""


def check_jd_disqualifiers(candidate: dict) -> dict:
    """
    Hard disqualifiers from the JD text.
    Returns dict with hard_disqualify (bool) and reason (str).
    
    Args:
        candidate: dict with work_experience, projects, etc.
        
    Returns:
        {'hard_disqualify': bool, 'reason': str}
    """
    from helpers.narrative import classify_company
    
    roles = candidate.get('work_experience', [])
    ctypes = [classify_company(r.get('company', '')) for r in roles]
    all_text = ' '.join(r.get('description', '') for r in roles)

    # Entire career at services firms with zero product exposure
    if roles and all(t == 'services' for t in ctypes if ctypes):
        return {'hard_disqualify': True,
                'reason': 'Entire career at services/consulting firms'}

    # Zero production deployment evidence anywhere
    deploy_re = re.compile(
        r'deployed|production|shipped|launched|served \d+|real users|'
        r'in prod|went live|released to|rolled out',
        re.IGNORECASE
    )
    if roles and not deploy_re.search(all_text):
        return {'hard_disqualify': True,
                'reason': 'No production deployment evidence in any role'}

    # Primary domain is CV/speech/robotics with no NLP or retrieval
    cv_re = re.compile(
        r'computer vision|image classif|object detect|speech recogni|'
        r'autonomous vehicle|robotics',
        re.IGNORECASE
    )
    nlp_re = re.compile(
        r'NLP|retrieval|ranking|recommendation|search|language model|'
        r'text classif|information retrieval|semantic',
        re.IGNORECASE
    )
    if cv_re.search(all_text) and not nlp_re.search(all_text):
        return {'hard_disqualify': True,
                'reason': 'Primary domain CV/speech/robotics, no NLP/IR evidence'}

    return {'hard_disqualify': False, 'reason': ''}
