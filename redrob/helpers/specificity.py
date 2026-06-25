"""
Specificity entropy scorer.

Fabricators write in generalities. Real practitioners write in specifics.
This is the single most powerful fraud and inflation detector.

Score five independent dimensions of specificity using regex — no ML needed.
"""

import re


def compute_specificity_score(candidate: dict) -> float:
    """
    Returns 0-1. High score = high specificity = more credible.
    
    Five dimensions:
    1. Numeric density: exact numbers, percentages, scale mentions
    2. Versioned technology: named tools with configuration detail
    3. Failure/tradeoff language: only real practitioners mention what broke
    4. Temporal precision: exact durations, dates
    5. Team/scope language: real leads mention colleagues and structure
    
    Args:
        candidate: dict with profile, career_history, projects
        
    Returns:
        float 0-1 specificity score
    """
    profile = candidate.get('profile', {})
    full_text = ' '.join([
        profile.get('summary', ''),
        ' '.join(r.get('description', '')
                 for r in candidate.get('career_history', [])),
        ' '.join(p.get('description', '')
                 for p in candidate.get('projects', []))
    ])
    
    words = max(len(full_text.split()), 1)
    components = []

    # 1. Numeric density: exact numbers, percentages, scales
    nums = re.findall(
        r'\b\d+(?:\.\d+)?(?:%|ms|µs|GB|TB|MB|M|K|B|x|rps|qps)?\b',
        full_text
    )
    components.append(min(len(nums) / words * 25, 1.0))

    # 2. Named/versioned technologies
    tech_pattern = re.compile(
        r'\b(Python|PyTorch|TensorFlow|JAX|Elasticsearch|Pinecone|Weaviate|'
        r'Qdrant|Milvus|Kafka|Redis|PostgreSQL|MySQL|Kubernetes|Docker|'
        r'FastAPI|Flask|FAISS|BGE|E5|MiniLM|XGBoost|LightGBM|Spark|'
        r'Airflow|dbt|Ray|Triton|ONNX|HuggingFace|LangChain|LlamaIndex|'
        r'Transformers|BERT|GPT|T5|sentence-transformers)'
        r'(?:\s*\d[\d.]*)?',
        re.IGNORECASE
    )
    versioned = tech_pattern.findall(full_text)
    components.append(min(len(versioned) / words * 30, 1.0))

    # 3. Failure / tradeoff language
    failure_re = re.compile(
        r'instead of|we tried|switched from|replaced|bottleneck|'
        r'latency issue|wasn\'t scaling|had to rethink|tradeoff|'
        r'downside|limitation|challenge was|struggled with|'
        r'realized that|turned out|had to abandon|didn\'t work',
        re.IGNORECASE
    )
    components.append(min(len(failure_re.findall(full_text)) / 3.0, 1.0))

    # 4. Temporal precision: durations, dates
    temporal = re.findall(
        r'\b(\d+\s+(?:weeks?|months?|days?|hours?|quarters?)|\d{4})\b',
        full_text
    )
    components.append(min(len(temporal) / 5.0, 1.0))

    # 5. Scope / team language
    scope_re = re.compile(
        r'team of \d+|\d+ engineers?|\d+ developers?|cross-functional|'
        r'collaborated with|mentored|reported to me|my team|'
        r'IC to|partnered with|worked alongside',
        re.IGNORECASE
    )
    components.append(min(len(scope_re.findall(full_text)) / 2.0, 1.0))

    return float(sum(components) / len(components))
