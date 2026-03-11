"""
kg/kg_engine.py
─────────────────────────────────────────────────────────────────────────────
Knowledge Graph Engine for LLM-ITS
─────────────────────────────────────────────────────────────────────────────
Builds a lightweight in-memory directed Knowledge Graph from extracted topics
using the Groq LLM to infer prerequisite relationships.

NO Neo4j needed — uses networkx (pure Python, pip install networkx).

Architecture:
  - Nodes  : curriculum topics (from your existing DB topics)
  - Edges  : prerequisite relationships (A → B means "learn A before B")
  - Weights: edge confidence (0-1) + node difficulty (1-5)

Integrates with:
  - database/db.py   → get_topics() to load topic nodes
  - llm/llm_engine.py → infer prerequisite edges via Groq
  - rag/rag_pipeline.py → hallucination guard (validate generated topics exist)
"""

import json
import re
import os
import pickle
from pathlib import Path
from typing import Optional

# networkx for graph structure
try:
    import networkx as nx
except ImportError:
    raise ImportError("Run: pip install networkx")

# ─── Constants ────────────────────────────────────────────────────────────────

KG_CACHE_DIR = Path("kg_cache")
KG_CACHE_DIR.mkdir(exist_ok=True)

BLOOM_LEVELS = {
    1: "Remember",
    2: "Understand",
    3: "Apply",
    4: "Analyze",
    5: "Create"
}

DIFFICULTY_KEYWORDS = {
    1: ["introduction", "basic", "overview", "what is", "definition", "fundamentals", "intro"],
    2: ["concept", "principle", "understanding", "explain", "describe", "types of"],
    3: ["application", "implementation", "using", "solving", "applying", "method"],
    4: ["analysis", "comparison", "evaluation", "advanced", "optimization", "complex"],
    5: ["design", "creation", "synthesis", "architecture", "custom", "novel", "research"],
}


# ─── KnowledgeGraph class ─────────────────────────────────────────────────────

class KnowledgeGraph:
    """
    Directed weighted graph of curriculum concepts.
    Edge A→B means: "A is a prerequisite of B"
    """

    def __init__(self, subject: str):
        self.subject = subject
        self.graph   = nx.DiGraph()
        self._topic_index = {}  # lowercase → original topic name

    # ── Node operations ───────────────────────────────────────────────────────

    def add_topic(self, topic: str, difficulty: int = 2, bloom_level: int = 2,
                  description: str = ""):
        node_id = self._normalize(topic)
        self.graph.add_node(
            node_id,
            label       = topic,
            difficulty  = max(1, min(5, difficulty)),
            bloom_level = max(1, min(5, bloom_level)),
            description = description,
            mastered    = False,
        )
        self._topic_index[node_id] = topic

    def _normalize(self, topic: str) -> str:
        return topic.lower().strip()

    def get_node(self, topic: str) -> Optional[dict]:
        nid = self._normalize(topic)
        if self.graph.has_node(nid):
            return self.graph.nodes[nid]
        return None

    def all_topics(self) -> list:
        return [self.graph.nodes[n].get("label", n) for n in self.graph.nodes]

    # ── Edge operations ───────────────────────────────────────────────────────

    def add_prerequisite(self, prereq: str, topic: str, confidence: float = 0.8):
        """Add edge: prereq → topic (learn prereq before topic)."""
        pid = self._normalize(prereq)
        tid = self._normalize(topic)
        if self.graph.has_node(pid) and self.graph.has_node(tid):
            self.graph.add_edge(pid, tid, confidence=confidence)

    def get_prerequisites(self, topic: str) -> list:
        """Return direct prerequisites of a topic (sorted by difficulty)."""
        tid = self._normalize(topic)
        if not self.graph.has_node(tid):
            return []
        preds = list(self.graph.predecessors(tid))
        return [self.graph.nodes[p].get("label", p) for p in preds]

    def get_learning_chain(self, topic: str) -> list:
        """
        Return the full prerequisite chain to reach a topic,
        sorted from foundational → advanced (topological order).
        """
        tid = self._normalize(topic)
        if not self.graph.has_node(tid):
            return [topic]

        try:
            ancestors = nx.ancestors(self.graph, tid)
            subgraph  = self.graph.subgraph(list(ancestors) + [tid])
            order     = list(nx.topological_sort(subgraph))
            return [self.graph.nodes[n].get("label", n) for n in order]
        except nx.NetworkXError:
            return [topic]

    def get_next_topics(self, mastered_topics: list) -> list:
        """
        Given a set of mastered topics, return the next recommended topics —
        topics whose ALL prerequisites are already mastered.
        """
        mastered_ids = {self._normalize(t) for t in mastered_topics}
        recommendations = []

        for node in self.graph.nodes:
            if node in mastered_ids:
                continue
            prereqs = set(self.graph.predecessors(node))
            if prereqs.issubset(mastered_ids):
                label      = self.graph.nodes[node].get("label", node)
                difficulty = self.graph.nodes[node].get("difficulty", 2)
                recommendations.append((label, difficulty))

        # Sort by difficulty (easiest first)
        recommendations.sort(key=lambda x: x[1])
        return [r[0] for r in recommendations]

    def get_remediation_topic(self, topic: str) -> Optional[str]:
        """
        Return the best remediation topic when a student struggles —
        the most foundational unmastered prerequisite.
        """
        chain = self.get_learning_chain(topic)
        if len(chain) > 1:
            return chain[0]  # most foundational
        return None

    def path_to_topic(self, from_topic: str, to_topic: str) -> list:
        """Return shortest prerequisite path between two topics."""
        fid = self._normalize(from_topic)
        tid = self._normalize(to_topic)
        try:
            path = nx.shortest_path(self.graph, fid, tid)
            return [self.graph.nodes[n].get("label", n) for n in path]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return [from_topic, to_topic]

    def mark_mastered(self, topic: str):
        nid = self._normalize(topic)
        if self.graph.has_node(nid):
            self.graph.nodes[nid]["mastered"] = True

    def get_difficulty(self, topic: str) -> int:
        node = self.get_node(topic)
        return node.get("difficulty", 2) if node else 2

    def stats(self) -> dict:
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "subject": self.subject,
        }

    # ── Serialization ─────────────────────────────────────────────────────────

    def save(self):
        path = KG_CACHE_DIR / f"{self._normalize(self.subject)}_kg.pkl"
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(subject: str) -> Optional["KnowledgeGraph"]:
        path = KG_CACHE_DIR / f"{subject.lower().strip()}_kg.pkl"
        if path.exists():
            with open(path, "rb") as f:
                return pickle.load(f)
        return None

    @staticmethod
    def exists(subject: str) -> bool:
        path = KG_CACHE_DIR / f"{subject.lower().strip()}_kg.pkl"
        return path.exists()

    def to_json(self) -> dict:
        """Export graph to JSON (for display)."""
        nodes = []
        for n in self.graph.nodes:
            d = dict(self.graph.nodes[n])
            d["id"] = n
            nodes.append(d)
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "from": self.graph.nodes[u].get("label", u),
                "to":   self.graph.nodes[v].get("label", v),
                "confidence": data.get("confidence", 0.8)
            })
        return {"subject": self.subject, "nodes": nodes, "edges": edges}


# ─── Auto-difficulty from topic name ─────────────────────────────────────────

def infer_difficulty(topic: str) -> int:
    t = topic.lower()
    for level, keywords in sorted(DIFFICULTY_KEYWORDS.items(), reverse=True):
        if any(kw in t for kw in keywords):
            return level
    return 2  # default: Understand level


# ─── LLM-based prerequisite inference ────────────────────────────────────────

def infer_prerequisites_llm(subject: str, topics: list, groq_client) -> list:
    """
    Ask the LLM to infer prerequisite relationships between topics.
    Returns list of (prereq, topic, confidence) tuples.
    
    Uses batching — sends topics in groups of 15 to stay within token limits.
    """
    all_edges = []
    batch_size = 15

    for i in range(0, len(topics), batch_size):
        batch = topics[i:i + batch_size]
        topic_list = "\n".join(f"- {t}" for t in batch)

        prompt = f"""You are an expert educator in {subject}.

Given these curriculum topics:
{topic_list}

Identify prerequisite relationships: which topics must be learned BEFORE others.
Return ONLY a valid JSON array. No explanation, no markdown.

Format:
[
  {{"prereq": "Topic A", "topic": "Topic B", "confidence": 0.9}},
  ...
]

Rules:
- Only include relationships where the prerequisite is clearly necessary
- confidence must be 0.5 to 1.0
- Only use exact topic names from the list above
- Return empty array [] if no clear prerequisites exist"""

        try:
            from llm.llm_engine import MODEL_NAME
            response = groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=600,
            )
            raw = response.choices[0].message.content.strip()
            # Extract JSON array
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                edges = json.loads(match.group())
                # Validate: only accept topics that exist in our list
                topic_set = {t.lower() for t in batch}
                for edge in edges:
                    p = edge.get("prereq", "")
                    t = edge.get("topic", "")
                    c = float(edge.get("confidence", 0.8))
                    if p.lower() in topic_set and t.lower() in topic_set and p != t:
                        all_edges.append((p, t, c))
        except Exception as e:
            print(f"[KG] LLM edge inference error: {e}")
            continue

    return all_edges


# ─── Cross-batch prerequisite inference ──────────────────────────────────────

def infer_cross_batch_prerequisites(subject: str, topics: list, groq_client) -> list:
    """
    For larger topic sets, also infer relationships ACROSS batches
    by checking foundational vs advanced topic pairs.
    """
    if len(topics) <= 15:
        return []

    # Sample: take first 8 (likely foundational) and last 8 (likely advanced)
    sample_topics = topics[:8] + topics[-8:]
    return infer_prerequisites_llm(subject, sample_topics, groq_client)


# ─── Main builder function ────────────────────────────────────────────────────

def build_knowledge_graph(subject: str, topics: list, groq_client,
                          force_rebuild: bool = False) -> KnowledgeGraph:
    """
    Build (or load cached) Knowledge Graph for a subject.

    Args:
        subject      : subject name (e.g. "Data Structures")
        topics       : list of topic strings from get_topics()
        groq_client  : initialized Groq client
        force_rebuild: ignore cache and rebuild from scratch

    Returns:
        KnowledgeGraph instance
    """
    if not force_rebuild and KnowledgeGraph.exists(subject):
        kg = KnowledgeGraph.load(subject)
        if kg and kg.graph.number_of_nodes() > 0:
            return kg

    kg = KnowledgeGraph(subject)

    # Step 1: Add all topics as nodes with auto-inferred difficulty
    for topic in topics:
        difficulty = infer_difficulty(topic)
        kg.add_topic(topic, difficulty=difficulty)

    # Step 2: Infer prerequisite edges via LLM
    edges = infer_prerequisites_llm(subject, topics, groq_client)
    cross_edges = infer_cross_batch_prerequisites(subject, topics, groq_client)

    for prereq, topic, confidence in edges + cross_edges:
        kg.add_prerequisite(prereq, topic, confidence)

    # Step 3: Remove cycles (keep graph a DAG)
    while True:
        try:
            cycle = nx.find_cycle(kg.graph)
            # Remove the lowest-confidence edge in the cycle
            min_edge = min(cycle, key=lambda e: kg.graph[e[0]][e[1]].get("confidence", 0.8))
            kg.graph.remove_edge(min_edge[0], min_edge[1])
        except nx.NetworkXNoCycle:
            break

    # Step 4: Cache to disk
    kg.save()
    return kg


# ─── KG-aware prompt context builder ─────────────────────────────────────────

def build_kg_context(kg: KnowledgeGraph, topic: str, mastered_topics: list) -> str:
    """
    Build a structured KG context string to inject into LLM prompts.
    This replaces/supplements RAG context with structured prerequisite info.
    """
    if not kg:
        return ""

    prereqs     = kg.get_prerequisites(topic)
    chain       = kg.get_learning_chain(topic)
    next_topics = kg.get_next_topics(mastered_topics + [topic])[:3]
    difficulty  = kg.get_difficulty(topic)
    remediation = kg.get_remediation_topic(topic)

    lines = [f"KNOWLEDGE GRAPH CONTEXT FOR: {topic}"]
    lines.append(f"• Difficulty Level: {difficulty}/5")

    if prereqs:
        lines.append(f"• Direct Prerequisites: {', '.join(prereqs)}")
    else:
        lines.append("• Direct Prerequisites: None (foundational topic)")

    if len(chain) > 1:
        chain_str = " → ".join(chain)
        lines.append(f"• Learning Chain: {chain_str}")

    if next_topics:
        lines.append(f"• Topics Unlocked After This: {', '.join(next_topics)}")

    if remediation and remediation != topic:
        lines.append(f"• If Student Struggles: Re-route to '{remediation}' first")

    unmastered_prereqs = [p for p in prereqs if p not in mastered_topics]
    if unmastered_prereqs:
        lines.append(f"⚠️  Unmastered Prerequisites: {', '.join(unmastered_prereqs)}")
        lines.append("   → Consider reviewing prerequisites before this topic.")

    return "\n".join(lines)


# ─── Hallucination guard ──────────────────────────────────────────────────────

def validate_topics_against_kg(kg: KnowledgeGraph, generated_text: str) -> dict:
    """
    Check if topics mentioned in LLM-generated text exist in the KG.
    Returns dict with valid/invalid topic counts for transparency.
    """
    all_topics = {t.lower() for t in kg.all_topics()}
    words      = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', generated_text))
    mentioned  = {w.lower() for w in words if len(w) > 4}

    matched   = mentioned & all_topics
    unmatched = mentioned - all_topics

    return {
        "total_mentioned": len(mentioned),
        "verified":        len(matched),
        "unverified":      len(unmatched),
        "hallucination_risk": len(unmatched) / max(1, len(mentioned))
    }