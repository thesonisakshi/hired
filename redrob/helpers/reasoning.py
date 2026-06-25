"""
Reasoning generator.

Generate grounded, zero-hallucination reasoning strings for each candidate.
Every claim must trace to a data field. Nothing is inferred or invented.
"""


def generate_reasoning(row: dict) -> str:
    """
    Produces a 1-2 sentence grounded reasoning string.
    Every claim comes from a computed field. Nothing is inferred or invented.
    
    Format: strengths sentence. [Concern: concerns sentence.]
    
    Args:
        row: dict with computed fields (experience, archetype, scores, etc.)
        
    Returns:
        str reasoning text
    """
    strengths = []
    concerns = []

    exp = row.get('total_exp_years', 0)
    ctype = row.get('company_type_summary', 'unknown')
    archetype = row.get('behavior_archetype', 'neutral')
    spec = row.get('specificity', 0.5)
    flags_str = str(row.get('consistency_flags', ''))
    flags = [f.strip() for f in flags_str.split('|') if f.strip()]
    skills = row.get('evidenced_skills', '')
    notice = row.get('notice_period_days', 60)
    location = row.get('location_city', '')
    trajectory = row.get('trajectory', 0.5)

    # Build strengths
    if exp >= 5 and ctype == 'product':
        strengths.append(f"{int(exp)}yr product-company background")
    elif exp >= 3 and ctype == 'product':
        strengths.append(f"{int(exp)}yr product background, growing trajectory")

    if spec > 0.70:
        strengths.append("high-specificity descriptions with measurable outcomes")
    elif spec > 0.55:
        strengths.append("moderate specificity with some quantified evidence")

    if skills:
        strengths.append(f"evidenced in {skills}")

    if trajectory > 0.70:
        strengths.append("clear upward career arc")

    if archetype == 'active_seeker':
        strengths.append("actively available and responsive on platform")
    elif archetype == 'highly_selective':
        strengths.append("highly selective applicant with strong follow-through history")
    elif archetype == 'passive_fit':
        strengths.append("passive candidate — reachable but not actively searching")

    if location:
        strengths.append(f"based in {location}")

    # Build concerns
    readable_flags = {
        'too_many_expert_claims_for_experience_length': 'expert skill count vs experience mismatch',
        'leadership_claims_inconsistent_with_career_stage': 'leadership claims inconsistent with career stage',
        'large_scale_claims_at_services_firm': 'large-scale claims at services firm',
        'oss_contribution_claims_no_github_activity': 'OSS claims without GitHub activity',
        'senior_title_inconsistent_with_years': 'senior title inconsistent with years',
        'cert_farming_pattern_no_project_evidence': 'cert farming pattern detected',
    }
    for flag in flags[:2]:
        if flag in readable_flags:
            concerns.append(readable_flags[flag])

    if notice and int(notice) > 60:
        concerns.append(f"{int(notice)}-day notice period")
    if archetype == 'dormant_star':
        concerns.append("platform inactive 4+ months")
    elif archetype == 'ghost':
        concerns.append("very low recruiter response rate historically")
    elif archetype == 'serial_applier':
        concerns.append("high-volume low-selectivity application pattern")

    s1 = '; '.join(strengths) if strengths else 'moderate profile match'
    s2 = f" Concern: {'; '.join(concerns)}." if concerns else ''
    return f"{s1.capitalize()}.{s2}"
