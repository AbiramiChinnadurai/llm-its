"""
evaluation/simulated_profiles.py

Defines 5 simulated learner profiles from the paper:
  P1 — Consistently High Performing
  P2 — Consistently Low Performing
  P3 — Improving Trajectory
  P4 — Declining Trajectory
  P5 — Topic-Uneven Performance

Each profile defines:
  - initial_accuracy_range: (min, max) starting accuracy per topic
  - trajectory: function that adjusts accuracy each session
  - description: human-readable label
"""

import random

SUBJECTS = ["Data Structures", "DBMS"]

TOPICS = {
    "Data Structures": [
        "Arrays and Linked Lists",
        "Stacks and Queues",
        "Trees and Binary Search Trees",
        "Sorting Algorithms",
        "Searching Algorithms",
        "Graphs and Graph Traversal",
        "Hashing and Hash Tables",
        "Recursion",
        "Time and Space Complexity",
        "Dynamic Programming"
    ],
    "DBMS": [
        "Database Concepts and Architecture",
        "Entity Relationship Model",
        "Relational Model and Algebra",
        "SQL Queries and Commands",
        "Normalization and Normal Forms",
        "Transaction Management and ACID",
        "Concurrency Control",
        "Indexing and Hashing",
        "Query Processing and Optimization",
        "Database Security and Authorization"
    ]
}


def clamp(val, lo=0, hi=100):
    return max(lo, min(hi, val))


# ── Profile trajectory functions ──────────────────────────────────────────────
# Each function takes (current_accuracy, session_num, topic_index)
# and returns new accuracy for next session

def p1_trajectory(acc, session, topic_idx):
    """High performer — stable, slight improvement."""
    delta = random.uniform(0, 5)
    return clamp(acc + delta)

def p2_trajectory(acc, session, topic_idx):
    """Low performer — slow improvement."""
    delta = random.uniform(2, 6)
    return clamp(acc + delta)

def p3_trajectory(acc, session, topic_idx):
    """Improving — consistent +8 to +12 pp per session."""
    delta = random.uniform(8, 12)
    return clamp(acc + delta)

def p4_trajectory(acc, session, topic_idx):
    """Declining — drops 5 to 10 pp per session."""
    delta = random.uniform(5, 10)
    return clamp(acc - delta)

def p5_trajectory(acc, session, topic_idx):
    """Topic-uneven — strong topics stay strong, weak topics slowly improve."""
    if topic_idx % 2 == 0:  # strong topics (even index)
        delta = random.uniform(-2, 3)
    else:                    # weak topics (odd index)
        delta = random.uniform(3, 8)
    return clamp(acc + delta)


# ── Profile definitions ───────────────────────────────────────────────────────

PROFILES = {
    "P1": {
        "name":        "P1 — High Performer",
        "description": "Consistently high accuracy (80–90%), stable or slightly improving.",
        "initial_accuracy": lambda topic_idx: random.uniform(80, 90),
        "trajectory":  p1_trajectory,
        "sessions":    3
    },
    "P2": {
        "name":        "P2 — Low Performer",
        "description": "Consistently low accuracy (25–45%), slow improvement.",
        "initial_accuracy": lambda topic_idx: random.uniform(25, 45),
        "trajectory":  p2_trajectory,
        "sessions":    3
    },
    "P3": {
        "name":        "P3 — Improving",
        "description": "Starts moderate (45–55%), improves +8–12pp per session.",
        "initial_accuracy": lambda topic_idx: random.uniform(45, 55),
        "trajectory":  p3_trajectory,
        "sessions":    3
    },
    "P4": {
        "name":        "P4 — Declining",
        "description": "Starts good (65–75%), declines 5–10pp per session.",
        "initial_accuracy": lambda topic_idx: random.uniform(65, 75),
        "trajectory":  p4_trajectory,
        "sessions":    3
    },
    "P5": {
        "name":        "P5 — Topic-Uneven",
        "description": "High on 60% of topics (80%+), low on 40% (30–45%).",
        "initial_accuracy": lambda topic_idx: random.uniform(80, 90) if topic_idx % 2 == 0
                                              else random.uniform(30, 45),
        "trajectory":  p5_trajectory,
        "sessions":    3
    }
}


def generate_accuracy_matrix(profile_key, seed=42):
    """
    Generate a full accuracy matrix for a profile:
    Returns dict: {subject: {topic: [acc_s1, acc_s2, acc_s3]}}
    This simulates what a real student of this profile type would score.
    """
    random.seed(seed)
    profile = PROFILES[profile_key]
    matrix  = {}

    for subject in SUBJECTS:
        matrix[subject] = {}
        topics = TOPICS[subject]
        for t_idx, topic in enumerate(topics):
            accs = []
            acc  = profile["initial_accuracy"](t_idx)
            accs.append(round(acc, 1))
            for session in range(1, profile["sessions"]):
                acc = profile["trajectory"](acc, session, t_idx)
                accs.append(round(acc, 1))
            matrix[subject][topic] = accs

    return matrix


def print_profile_summary(profile_key):
    """Print a readable summary of a profile's accuracy trajectory."""
    profile = PROFILES[profile_key]
    matrix  = generate_accuracy_matrix(profile_key)

    print(f"\n{'='*60}")
    print(f"  {profile['name']}")
    print(f"  {profile['description']}")
    print(f"{'='*60}")

    for subject in SUBJECTS:
        print(f"\n  📚 {subject}")
        print(f"  {'Topic':<45} S1     S2     S3")
        print(f"  {'-'*70}")
        for topic, accs in matrix[subject].items():
            s1, s2, s3 = accs
            trend = "↑" if s3 > s1 else ("↓" if s3 < s1 else "→")
            print(f"  {topic:<45} {s1:5.1f}  {s2:5.1f}  {s3:5.1f}  {trend}")

        # Subject-level summary
        all_s1 = [v[0] for v in matrix[subject].values()]
        all_s3 = [v[2] for v in matrix[subject].values()]
        print(f"\n  Mean accuracy:  S1={sum(all_s1)/len(all_s1):.1f}%  →  S3={sum(all_s3)/len(all_s3):.1f}%")
        qai = sum(all_s3)/len(all_s3) - sum(all_s1)/len(all_s1)
        print(f"  QAI (S3-S1):   {qai:+.1f} pp")


if __name__ == "__main__":
    print("SIMULATED LEARNER PROFILES — ACCURACY MATRICES")
    for pk in PROFILES:
        print_profile_summary(pk)
    print(f"\n\nAll 5 profiles generated successfully.")
    print("These will be used by evaluation/run_evaluation.py in Step 3.")