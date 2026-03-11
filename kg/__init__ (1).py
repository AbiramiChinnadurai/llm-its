# kg/__init__.py
from kg.kg_engine import (
    KnowledgeGraph,
    build_knowledge_graph,
    build_kg_context,
    validate_topics_against_kg,
    infer_difficulty,
)
from kg.kg_widget import (
    render_kg_status,
    render_prereq_chain,
    render_next_topics,
    render_kg_context_card,
    render_hallucination_score,
    get_or_build_kg,
)
