"""
Evidence narrative construction.

Build a structured narrative from what the candidate demonstrably DID.
Extract only action-verb sentences to filter for real evidence vs fabrication.
"""

ACTION_VERBS = [
    'built', 'shipped', 'deployed', 'reduced', 'scaled', 'designed',
    'led', 'launched', 'improved', 'optimized', 'migrated', 'architected',
    'implemented', 'created', 'developed', 'established', 'automated',
    'trained', 'fine-tuned', 'evaluated', 'benchmarked', 'monitored',
    'refactored', 'integrated', 'productionized', 'maintained', 'debugged',
    'owned', 'drove', 'delivered', 'introduced', 'rewrote', 'replaced'
]

SERVICES_FIRMS = {
    'tcs', 'infosys', 'wipro', 'accenture', 'cognizant', 'capgemini',
    'hcl', 'tech mahindra', 'mphasis', 'ltimindtree', 'hexaware',
    'niit', 'mastech', 'kpit', 'persistent', 'zensar',
    'dxc', 'atos', 'unisys', 'fujitsu', 'ntt data'
}


def classify_company(name: str) -> str:
    """Classify company as 'services' or 'product' based on name matching."""
    if not name:
        return 'unknown'
    n = name.lower().strip()
    if any(s in n for s in SERVICES_FIRMS):
        return 'services'
    return 'product'


def build_evidence_narrative(candidate: dict) -> str:
    """
    Extract what the candidate demonstrably did.
    
    Select only action-verb sentences. Ignore claims, skills lists, summaries.
    Include: verified project descriptions, action sentences from roles,
    issuer-backed certifications.
    Exclude: summary statements, skills lists, bare responsibilities.
    
    Args:
        candidate: dict with career_history, projects, certifications, profile
        
    Returns:
        Concatenated evidence narrative string
    """
    parts = []

    # Extract action-verb sentences from career history
    for role in candidate.get('career_history', []):
        company_type = classify_company(role.get('company', ''))
        title = role.get('title', '')
        desc = role.get('description', '')
        
        if desc:
            # Split into sentences
            sentences = [s.strip() for s in desc.replace('\n', '. ').split('.')
                        if len(s.strip()) > 15]
            # Filter for action-verb sentences
            action_sents = [s for s in sentences
                           if any(v in s.lower() for v in ACTION_VERBS)]
            if action_sents:
                parts.append(
                    f"{title} at {company_type}-co: {'. '.join(action_sents[:5])}"
                )

    # Extract project descriptions
    for proj in candidate.get('projects', []):
        name = proj.get('name', '')
        desc = proj.get('description', '')
        tech = ', '.join(proj.get('technologies', []))
        if desc:
            parts.append(f"Project {name}: {desc}. Tech: {tech}")

    # Extract verified certifications
    for cert in candidate.get('certifications', []):
        if cert.get('issuer') and cert.get('name'):
            parts.append(f"Certified: {cert['name']} by {cert['issuer']}")

    # Fallback to profile summary if no evidence found
    profile = candidate.get('profile', {})
    fallback = profile.get('summary', '')
    
    return ' | '.join(parts) if parts else fallback
