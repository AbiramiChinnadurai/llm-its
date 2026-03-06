# LLM-Assisted Intelligent Tutoring System
### As described in the research paper

---

## 📁 Project Structure

```
llm_its/
├── app.py                        ← Main entry point (Home + Login/Register)
├── requirements.txt
├── pages/
│   ├── 1_Study.py                ← RAG-grounded explanations with AEL
│   ├── 2_Quiz.py                 ← MCQ generation + AEL update logic
│   ├── 3_LearningPlan.py         ← Personalized study plan generation
│   ├── 4_Dashboard.py            ← Analytics: mastery, accuracy, AEL chart
│   └── 5_UploadSyllabus.py       ← PDF upload + FAISS index builder
├── database/
│   └── db.py                     ← SQLite: all 4 tables + AEL state
├── rag/
│   └── rag_pipeline.py           ← PDF chunking, FAISS indexing, retrieval
├── llm/
│   └── llm_engine.py             ← Ollama LLaMA-3 prompts + generation
└── faiss_indexes/                ← Auto-created when you upload a PDF
```

---

## ⚙️ Setup Instructions

### Step 1 — Install Python packages
```bash
cd llm_its
pip install -r requirements.txt
```

### Step 2 — Pull LLaMA-3 via Ollama
```bash
ollama pull llama3
```
Make sure Ollama is running:
```bash
ollama serve
```

### Step 3 — Run the app
```bash
streamlit run app.py
```

Open your browser at: **http://localhost:8501**

---

## 🚀 How to Use

1. **Register** your profile (name, subjects, deadline, daily hours)
2. **Upload Syllabus** → Upload your subject PDF → Build Index
3. **Study** → Ask questions → AI answers only from your PDF
4. **Quiz** → Take adaptive MCQs → Watch AEL modality update
5. **Learning Plan** → Generate your personalized day-by-day schedule
6. **Dashboard** → View your mastery progress, accuracy trends, AEL usage

---

## 🧠 AEL Modality Levels

| Level | Name | When Triggered |
|-------|------|---------------|
| M=0 | Standard Prose | Default |
| M=1 | Step-by-Step | 2 consecutive attempts < 50% |
| M=2 | Analogical Reasoning | Continued struggle |
| M=3 | Worked Example | Persistent difficulty |
| M=4 | Simplified Language | Maximum struggle |

**Mastery signal** (2 consecutive > 75%) → decrements modality back toward M=0

---

## 📊 Database Tables

| Table | Purpose |
|-------|---------|
| `learner_profile` | Student registration data |
| `quiz_attempts` | Every quiz attempt with accuracy + AEL modality |
| `subject_summary` | Aggregated mastery per subject (auto-updated) |
| `learning_plans` | Generated plans with mastery snapshot |
| `ael_state` | Current AEL modality index per topic |
| `error_topics` | Topics with wrong answers (weakness tracker) |
