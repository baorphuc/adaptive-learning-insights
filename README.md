# English Learning Analytics System

> **End-to-end data pipeline**: từ data generation → ETL → analysis → visualization → recommendation

---

## 📌 Project Overview

Hệ thống phân tích dữ liệu học tiếng Anh, mô phỏng hành vi học từ vựng của 100 người dùng với 2000 từ.  
Mục tiêu: tìm ra **Sweet Spot of Review** (thời điểm tối ưu để ôn lại từ) và xây dựng hệ thống recommendation cá nhân hóa.


---

## 🏗️ Architecture

```
raw data → ETL pipeline → analysis → visualization → recommendation
```

```
adaptive-learning-insights/
├── raw/                          # Generated datasets
│   ├── words.csv                 # 2,000 words (level, frequency)
│   ├── users.csv                 # 100 users (CEFR level)
│   └── quiz_results.csv          # 10,000 quiz results
├── processed/                    # ETL output + chart files
│   ├── quiz_results_clean.csv    # Cleaned data with 6 derived features
│   ├── retention_curve.csv       # Retention data for Sweet Spot chart
│   └── chart*.html               # 7 interactive Plotly charts
├── scripts/
│   ├── generate_data.py          # Data simulation (SRS-controlled spacing)
│   ├── etl.py                    # ETL pipeline
│   ├── generate_charts.py        # 7 visualizations
│   └── recommendation.py         # Recommendation system
└── analysis/
    └── analysis.ipynb            # 6 analytical queries
```

---

## 📊 Dataset

| File | Records | Key Fields |
|------|---------|------------|
| `words.csv` | 2,000 | word_id, level (A1–C2), frequency (high/medium/low) |
| `users.csv` | 100 | user_id, level (A1–C2) |
| `quiz_results.csv` | 10,000 | is_correct, time_spent, attempt_number, days_since_last_seen |

### Data Generation Logic

Data được tạo với 4 yếu tố có logic rõ ràng:

```python
probability = base_from_level_gap      # word level vs user level
            - frequency_penalty        # rare words harder
            - forgetting_penalty       # step-based: -5% (>3d), -15% (>7d), -20% (>14d)
            + learning_boost           # +3% per attempt, max +15%
```

**Controlled spaced repetition spacing:**

| Attempt | Interval |
|---------|----------|
| 2nd review | 1–3 days |
| 3rd review | 5–7 days |
| 4th review | 10–14 days |
| 5th+ review | 15–30 days |

---

## ⚙️ ETL Pipeline

**Input:** `raw/quiz_results.csv`  
**Output:** `processed/quiz_results_clean.csv` (17 columns)

### Cleaning steps:
- Remove duplicates
- Filter invalid `time_spent` (< 0 hoặc > 300 giây)
- Drop missing values on critical fields

### Derived features (6 features added):

| Feature | Logic |
|---------|-------|
| `level_gap` | word_level_score − user_level_score |
| `is_hard_word` | level_gap > 0 |
| `is_slow_response` | time_spent > median + 1 std |
| `is_rare_word` | frequency == 'low' |
| `forgetting_risk` | days_since_last_seen > 7 |
| `user_performance_score` | Rolling accuracy (window=10) per user |

---

## 📈 Analysis — 6 Queries

| # | Query | Key Finding |
|---|-------|-------------|
| 1 | Word difficulty by level | C2 words có error rate 64% vs A1 chỉ 20% |
| 2 | Hardest words | Top words có error rate 80–91%, đều là C1/C2 |
| 3 | Learning curve | Accuracy cải thiện rõ rệt qua các lần attempt |
| 4 | Time vs accuracy | Correlation −0.70: spending longer = struggling |
| 5 | User performance | 25% users struggling (accuracy < 40%) |
| 6 | **Retention analysis** | Accuracy drops từ 60.7% → 50.0% sau day 10 |

---

## 📊 Visualizations — 7 Charts

| Chart | Type | Insight |
|-------|------|---------|
| `chart1_difficulty_by_level.html` | Bar | Error rate tăng theo CEFR level |
| `chart2_learning_curve.html` | Line | Accuracy cải thiện qua attempts |
| `chart3_error_heatmap.html` | Heatmap | User level × Word level error pattern |
| `chart4_time_vs_accuracy.html` | Scatter | Time spent là signal của difficulty |
| `chart5_user_distribution.html` | Histogram | Distribution of user accuracy |
| `chart6_sweet_spot.html` ⭐ | Line + markers | **Sweet Spot of Review** |
| `chart7_retention_buckets.html` | Bar | Retention by time bucket (supports chart 6) |

---

## ⭐ Sweet Spot of Review

**Signature insight của project.**

```
Baseline accuracy (0–3 days):  60.7%
Accuracy at day 10:             50.0%
Drop:                          −10.7%

→ Review BEFORE day 10 để tránh accuracy drop dưới threshold
```

**Threshold definition:**  
10% drop được chọn vì:
- < 5% = measurement noise
- **10% = significant, actionable**
- > 15% = đã quên quá nhiều, recovery tốn kém hơn

**Visualization:**

```
Accuracy (%)
  60.7% ┄┄┄┄┄┄┄┄┄┄ Baseline (green dashed)
        │ ╲
  55%   │   ╲
  50.7% ┄┄┄┄┄╲┄┄┄┄ Threshold −10% (red dashed)
        │     ★  ← Sweet Spot: Day 10 (orange marker)
  45%   │       ╲
        └──────────────────────
        0   5   10  15  20  30
             Days Since Last Seen
```

---

## 🎯 Recommendation System

### Function signature

```python
result = get_recommendation(user_id='U001', top_n=20)

# Returns:
# result['review_words']          — words to review (priority scored)
# result['new_words']             — new words to learn
# result['final_recommendation']  — combined list (normalized 0–10)
# result['stats']                 — user summary
```

### Priority formula (explainable)

```python
review_score = 0.6 × norm(days_since_last_seen)
             + 0.3 × norm(wrong_count)
             + 0.1 × norm(frequency_penalty)
```

### Review criteria

```python
review_mask = (
    (wrong_count >= 2) |                           # struggling
    (days_since > 9) & (accuracy < 0.7)            # forgetting risk
)
```

### Explore vs Exploit (adaptive ratio)

| User Accuracy | Review | New Words |
|---------------|--------|-----------|
| < 50% (weak)  | 16 | 4 |
| 50–70% (avg)  | 15 | 5 |
| ≥ 70% (strong)| 12 | 8 |

### Score normalization

```python
# Both review and new words normalized on COMBINED scale → apples-to-apples comparison
combined = pd.concat([review_tagged, new_tagged])
combined['priority_score'] = normalize(combined['priority_score'])
```

### Output example

```
word      level  type    priority_score
word_634  B2     review  10.00   ← top priority (wrong×2 + 797 days)
word_1078 C1     review   9.97
word_1838 C1     review   9.78
...
word_22   B2     new      0.00   ← guaranteed slot (explore)
word_6    B2     new      0.00
```

---

## 🚀 How to Run

```bash
# 1. Setup
git clone https://github.com/your-username/adaptive-learning-insights
cd adaptive-learning-insights
pip install pandas numpy plotly

# 2. Generate data
python scripts/generate_data.py

# 3. Run ETL
python scripts/etl.py

# 4. Generate charts (open HTML files in browser)
python scripts/generate_charts.py

# 5. Run recommendation
python scripts/recommendation.py
```

---

## 🛠️ Tech Stack

| Tool | Usage |
|------|-------|
| Python 3.x | Core language |
| pandas | Data manipulation |
| numpy | Numerical operations |
| Plotly | Interactive visualizations |
| Jupyter | Analysis notebooks |

---

## 💡 Key Insights

1. **Level gap is the strongest predictor** — C2 words are 3× harder than A1 for average users
2. **Time spent = struggling signal** — correlation −0.70 between time and accuracy
3. **Sweet Spot at day 9** — accuracy drops 10.7% after 10 days without review
4. **25% of users need intervention** — accuracy below 40% threshold
5. **Spaced repetition works** — controlled SRS spacing shows clear retention improvement

---

## 📝 Notes

- `np.random.seed(42)` ensures reproducible results
- All CSV files use `;` delimiter + `utf-8-sig` encoding (Excel VN compatible)
- Charts are standalone HTML files — no server needed, open in any browser
- Recommendation system is rule-based (no ML) — fully explainable logic
