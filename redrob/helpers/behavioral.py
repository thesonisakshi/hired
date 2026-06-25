"""
Behavioral archetype classifier.

Do NOT use behavioral signals as flat multipliers. People are patterns.
Classify each candidate into a named behavioral archetype,
then assign a hirability multiplier.

This reflects real hiring reality: a brilliant candidate who never responds
is functionally unavailable.
"""

from datetime import date


def classify_behavioral_archetype(signals: dict) -> tuple[str, float]:
    """
    Returns (archetype_name, hirability_multiplier).
    Multiplier range: 0.20 (ghost) to 1.30 (ideal active fit).
    
    Seven archetypes:
    - active_seeker    (1.30): open, recent, responsive
    - highly_selective (1.15): few apps, high completion, high acceptance
    - passive_fit      (1.00): not hunting but reachable
    - neutral          (0.85): default when pattern unclear
    - notice_risk      (0.75): good fit, long notice period
    - serial_applier   (0.65): applying everywhere, low selectivity
    - dormant_star     (0.45): strong profile, gone dark
    - ghost            (0.20): never responds or completes
    
    Args:
        signals: dict with recruiter_response_rate, offer_acceptance_rate, etc.
        
    Returns:
        (archetype_name str, multiplier float)
    """
    
    def days_since(date_str):
        """Calculate days since a date string. Returns 999 if parse fails."""
        if not date_str:
            return 999
        try:
            from dateutil.parser import parse
            d = parse(str(date_str)).date()
            return (date.today() - d).days
        except Exception:
            return 999

    active_days    = days_since(signals.get('last_active_date'))
    response_rate  = signals.get('recruiter_response_rate', 0.5)
    completion     = signals.get('interview_completion_rate', 0.5)
    open_flag      = signals.get('open_to_work_flag', False)
    apps_30d       = signals.get('applications_submitted_30d', 0)
    offer_acc      = signals.get('offer_acceptance_rate', -1)
    notice         = signals.get('notice_period_days', 60)

    # Active seeker: open, recent, responsive
    if open_flag and active_days < 14 and response_rate > 0.6:
        return 'active_seeker', 1.30

    # Highly selective: high bar, few apps, high completion & acceptance
    if offer_acc != -1 and offer_acc > 0.7 and completion > 0.85 and apps_30d < 5:
        return 'highly_selective', 1.15

    # Passive fit: not hunting but reachable
    if not open_flag and active_days < 60 and response_rate > 0.4:
        return 'passive_fit', 1.00

    # Notice risk: good fit but long notice period
    if notice and notice > 90 and response_rate > 0.5:
        return 'notice_risk', 0.75

    # Serial applier: low selectivity
    if apps_30d > 20:
        return 'serial_applier', 0.65

    # Dormant star: went dark but strong profile
    if active_days > 120 and response_rate < 0.3:
        return 'dormant_star', 0.45

    # Ghost: never responds or completes
    if response_rate < 0.1 and completion < 0.25:
        return 'ghost', 0.20

    # Neutral: default pattern
    return 'neutral', 0.85
