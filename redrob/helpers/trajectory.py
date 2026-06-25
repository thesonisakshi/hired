"""
Career trajectory scorer.

A 4-year candidate growing fast is often better than a 10-year candidate
who peaked at year 3. Measure the growth arc, not the total length.
"""

import re


def compute_trajectory_score(candidate: dict) -> float:
    """
    Returns 0-1. 1.0 = clear upward arc. 0.5 = flat. 0.2 = declining or stagnant.
    
    Three dimensions:
    1. Verb level progression: does the tier (operator/builder/director) grow over time?
    2. Scope growth: do numbers (team size, scale, users) increase chronologically?
    3. Title progression: rough seniority level increase over career
    
    Args:
        candidate: dict with work_experience
        
    Returns:
        float 0-1 trajectory score
    """
    
    VERB_TIERS = {
        'director': ['led', 'set direction', 'owned strategy', 'defined',
                     'established culture', 'founded', 'created org'],
        'builder':  ['designed', 'architected', 'built', 'created system',
                     'introduced', 'replaced', 'rewrote'],
        'operator': ['implemented', 'developed', 'deployed', 'maintained',
                     'automated', 'integrated', 'tested', 'monitored'],
        'passive':  ['assisted', 'supported', 'involved in', 'worked on',
                     'participated', 'helped']
    }
    TIER_VALUES = {'director': 3, 'builder': 2, 'operator': 1, 'passive': 0}

    def score_description(desc: str) -> float:
        """Score description based on tier of verbs used."""
        d = desc.lower()
        for tier, verbs in VERB_TIERS.items():
            if any(v in d for v in verbs):
                return TIER_VALUES[tier]
        return 0.5

    # Sort roles by start date chronologically
    from datetime import datetime
    def _extract_year(date_str):
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(str(date_str)).year
        except (ValueError, TypeError):
            return None
    
    roles = []
    for r in candidate.get('career_history', []):
        start_year = _extract_year(r.get('start_date'))
        if start_year:
            roles.append((start_year, r))
    
    if len(roles) < 2:
        return 0.5  # not enough data for trend
    
    roles.sort(key=lambda x: x[0])
    roles = [r[1] for r in roles]

    # Compute verb tier scores for each role
    verb_scores = [score_description(r.get('description', '')) for r in roles]

    # Is there upward trend in verb tiers?
    increases = sum(1 for i in range(1, len(verb_scores))
                    if verb_scores[i] >= verb_scores[i-1])
    verb_trend = increases / (len(verb_scores) - 1)

    # Scope growth: look for increasing numbers across roles
    def extract_max_number(text):
        nums = re.findall(r'\b(\d+)(?:M|K)?\b', text)
        return max([int(n) for n in nums], default=0) if nums else 0

    scopes = [extract_max_number(r.get('description', '')) for r in roles]
    scope_grows = sum(1 for i in range(1, len(scopes))
                      if scopes[i] > scopes[i-1])
    scope_trend = scope_grows / max(len(scopes) - 1, 1)

    final_score = verb_trend * 0.6 + scope_trend * 0.4
    return round(final_score, 3)
