"""
evaluation/generate_questions.py

Auto-generates 240 MCQs for evaluation:
  - Data Structures: 120 questions (10 topics x 3 difficulties x 4 questions each)
  - DBMS:            120 questions (10 topics x 3 difficulties x 4 questions each)

Run with: python evaluation/generate_questions.py
"""

import json, os, time, re
import ollama

MODEL       = "llama3"
OUTPUT_FILE = "evaluation/question_bank.json"
os.makedirs("evaluation", exist_ok=True)

SUBJECTS = {
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

DIFFICULTIES        = ["easy", "medium", "hard"]
QUESTIONS_PER_COMBO = 4

DIFFICULTY_DESC = {
    "easy":   "basic recall and comprehension — suitable for a beginner",
    "medium": "application and understanding — requires knowing how concepts work",
    "hard":   "analysis and synthesis — requires comparing, evaluating, or applying to new scenarios"
}


def generate_mcq(subject, topic, difficulty, existing_questions):
    prev = "\n".join([f"- {q}" for q in existing_questions[-5:]]) if existing_questions else "None"
    prompt = f"""Generate exactly 1 multiple choice question about "{topic}" in {subject}.
Difficulty: {difficulty} — {DIFFICULTY_DESC[difficulty]}
Do NOT repeat any of these questions:
{prev}

Return ONLY valid JSON in this exact format, nothing else:
{{
  "subject": "{subject}",
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "question": "The question text here?",
  "options": ["A) first option", "B) second option", "C) third option", "D) fourth option"],
  "correct_index": 0,
  "explanation": "Brief explanation of why the correct answer is right."
}}
correct_index must be 0, 1, 2, or 3."""

    try:
        response = ollama.generate(
            model=MODEL,
            prompt=prompt,
            options={"temperature": 0.4, "num_predict": 350}
        )
        raw   = response["response"].strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if all(k in data for k in ["question","options","correct_index","explanation"]):
                if len(data["options"]) == 4 and data["correct_index"] in [0,1,2,3]:
                    data["subject"]    = subject
                    data["topic"]      = topic
                    data["difficulty"] = difficulty
                    return data
    except Exception as e:
        print(f"    Error: {e}")
    return None


def main():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            all_questions = json.load(f)
        print(f"Resuming — {len(all_questions)} questions already done.")
    else:
        all_questions = []

    generated    = len(all_questions)
    total_target = 240

    for subject, topics in SUBJECTS.items():
        print(f"\n{'='*55}\n  Subject: {subject}\n{'='*55}")
        for topic in topics:
            for difficulty in DIFFICULTIES:
                existing = [q for q in all_questions
                            if q["subject"]==subject and q["topic"]==topic
                            and q["difficulty"]==difficulty]
                need = QUESTIONS_PER_COMBO - len(existing)
                if need <= 0:
                    print(f"  SKIP [{difficulty:6}] {topic}")
                    continue
                print(f"\n  GEN  [{difficulty:6}] {topic}  (need {need})")
                prev_qs = [q["question"] for q in existing]
                for i in range(need):
                    print(f"    Q{len(existing)+i+1}/{QUESTIONS_PER_COMBO}...", end=" ", flush=True)
                    q = None
                    for _ in range(3):
                        q = generate_mcq(subject, topic, difficulty, prev_qs)
                        if q: break
                    if q:
                        all_questions.append(q)
                        prev_qs.append(q["question"])
                        generated += 1
                        print(f"OK  [{generated}/{total_target}]")
                    else:
                        print("FAILED")
                    with open(OUTPUT_FILE, "w") as f:
                        json.dump(all_questions, f, indent=2)
                    time.sleep(0.3)

    print(f"\nDONE — {len(all_questions)} questions saved to {OUTPUT_FILE}")
    print("\nBreakdown:")
    for subject in SUBJECTS:
        sq = [q for q in all_questions if q["subject"]==subject]
        print(f"\n  {subject}: {len(sq)} total")
        for d in DIFFICULTIES:
            c = len([q for q in sq if q["difficulty"]==d])
            print(f"    {d:6}: {c}")

if __name__ == "__main__":
    main()