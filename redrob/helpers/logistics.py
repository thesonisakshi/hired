"""
Logistics scorer.

Location + notice period fit.
Target locations: Pune, Noida, Delhi NCR, Mumbai, Hyderabad, Bangalore.
"""


def compute_logistics_score(candidate: dict) -> float:
    """
    Location + notice period fit.
    
    Target locations: Pune, Noida, Delhi NCR, Mumbai, Hyderabad, Bangalore.
    
    Args:
        candidate: dict with profile and redrob_signals
        
    Returns:
        float 0-1 logistics score
    """
    TARGET_CITIES = {
        'pune', 'noida', 'delhi', 'gurugram', 'gurgaon', 'mumbai',
        'hyderabad', 'bangalore', 'bengaluru', 'new delhi'
    }

    signals = candidate.get('redrob_signals', {})
    profile = candidate.get('profile', {})
    city = (profile.get('location') or '').lower()
    relocation = signals.get('willing_to_relocate', False)
    notice = signals.get('notice_period_days', 60)

    # Location score
    if any(t in city for t in TARGET_CITIES):
        loc_score = 1.0
    elif relocation:
        loc_score = 0.8
    else:
        loc_score = 0.4

    # Notice period score
    if notice <= 30:
        notice_score = 1.0
    elif notice <= 60:
        notice_score = 0.75
    elif notice <= 90:
        notice_score = 0.50
    else:
        notice_score = 0.25

    final_score = loc_score * 0.6 + notice_score * 0.4
    return round(final_score, 3)
