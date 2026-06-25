"""
JD decomposition and facet embedding.

Decompose the job description into 5 independent semantic facets.
Each facet is a separate query vector for precise semantic matching.
"""

JD_FACETS = {
    "core_technical": (
        "production embeddings vector database retrieval ranking hybrid search "
        "sentence-transformers FAISS Pinecone Weaviate Qdrant Elasticsearch "
        "ANN index embedding drift retrieval quality reranking"
    ),
    "evaluation_rigor": (
        "NDCG MRR MAP offline benchmark A/B testing evaluation framework "
        "ranking quality metrics recruiter feedback signal measurement"
    ),
    "product_engineer": (
        "shipped deployed real users product company startup scale "
        "user-facing production system fast iteration ownership v2"
    ),
    "mindset": (
        "async writing scrappy fast move quickly founding team ambiguity "
        "ownership disagree decide growth stage mentor open opinions"
    ),
    "anti_patterns": (
        "pure research academic no deployment LangChain tutorial wrapper "
        "consulting TCS Infosys Wipro entire career services firm "
        "computer vision speech robotics no NLP no IR no search"
    )
}

FACET_NAMES = list(JD_FACETS.keys())
FACET_TEXTS = list(JD_FACETS.values())

# Facet weights in composite scoring
# anti_patterns weight is negative (high similarity penalizes)
FACET_WEIGHTS = [0.35, 0.20, 0.25, 0.10, -0.10]  # core, eval, product, mindset, anti
