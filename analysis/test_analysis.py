"""
Quick test of analysis queries (notebook version available as analysis.ipynb)
"""

import pandas as pd
import numpy as np

# Load processed data
df = pd.read_csv('processed/quiz_results_clean.csv', sep=';', encoding='utf-8-sig')

print("=" * 60)
print("ANALYSIS QUERIES - QUICK TEST")
print("=" * 60)
print(f"\nLoaded {len(df):,} quiz results\n")

# Query 1: Error rate by level
print("\n[QUERY 1] ERROR RATE BY LEVEL")
print("-" * 60)
error_by_level = df.groupby('word_level').agg({
    'is_correct': ['mean', 'count']
})
error_by_level.columns = ['accuracy', 'count']
error_by_level['error_rate'] = 1 - error_by_level['accuracy']
level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
error_by_level = error_by_level.reindex(level_order)
print(error_by_level.to_string())

# Query 2: Hardest words
print("\n\n[QUERY 2] TOP 5 HARDEST WORDS")
print("-" * 60)
word_stats = df.groupby('word_id').agg({
    'is_correct': ['mean', 'count'],
    'word_level': 'first',
    'frequency': 'first'
})
word_stats.columns = ['accuracy', 'attempts', 'level', 'frequency']
word_stats['error_rate'] = 1 - word_stats['accuracy']
word_stats_filtered = word_stats[word_stats['attempts'] >= 10]
hardest_words = word_stats_filtered.nlargest(5, 'error_rate')
print(hardest_words[['error_rate', 'attempts', 'level', 'frequency']].to_string())

# Query 3: Learning curve
print("\n\n[QUERY 3] LEARNING CURVE")
print("-" * 60)
learning_curve = df[df['attempt_number'] <= 10].groupby('attempt_number').agg({
    'is_correct': ['mean', 'count']
})
learning_curve.columns = ['accuracy', 'count']
print(learning_curve.to_string())

# Query 4: Time vs accuracy
print("\n\n[QUERY 4] TIME VS ACCURACY")
print("-" * 60)
df['time_bucket'] = pd.cut(df['time_spent'], 
                            bins=[0, 5, 10, 15, 300],
                            labels=['0-5s', '5-10s', '10-15s', '15s+'])
time_accuracy = df.groupby('time_bucket', observed=True).agg({
    'is_correct': ['mean', 'count']
})
time_accuracy.columns = ['accuracy', 'count']
print(time_accuracy.to_string())
correlation = df['time_spent'].corr(df['is_correct'])
print(f"\nCorrelation (time vs accuracy): {correlation:.3f}")

# Query 5: User performance
print("\n\n[QUERY 5] USER PERFORMANCE DISTRIBUTION")
print("-" * 60)
user_performance = df.groupby('user_id').agg({
    'is_correct': ['mean', 'count']
})
user_performance.columns = ['accuracy', 'total_attempts']
user_performance['category'] = pd.cut(user_performance['accuracy'],
                                       bins=[0, 0.4, 0.6, 0.8, 1.0],
                                       labels=['Struggling', 'Below Average', 'Good', 'Excellent'])
category_dist = user_performance['category'].value_counts().sort_index()
print(f"Total users: {len(user_performance)}\n")
for cat in category_dist.index:
    count = category_dist[cat]
    pct = count / len(user_performance) * 100
    print(f"{cat:15s}: {count:3d} users ({pct:5.1f}%)")

# Query 6: RETENTION ANALYSIS ⭐
print("\n\n[QUERY 6] RETENTION CURVE ⭐")
print("-" * 60)
retention_data = df[df['attempt_number'] > 1].copy()
retention_curve = retention_data.groupby('days_since_last_seen').agg({
    'is_correct': ['mean', 'count']
})
retention_curve.columns = ['accuracy', 'count']
retention_curve = retention_curve[retention_curve['count'] >= 10]
print(retention_curve.head(15).to_string())

# Find sweet spot
baseline_accuracy = retention_curve[retention_curve.index <= 3]['accuracy'].mean()
threshold = baseline_accuracy - 0.10
sweet_spot = retention_curve[retention_curve['accuracy'] < threshold].index.min()

print("\n" + "=" * 60)
print("⭐ SWEET SPOT OF REVIEW")
print("=" * 60)
print(f"Baseline accuracy (0-3 days): {baseline_accuracy:.1%}")
if pd.notna(sweet_spot):
    print(f"Sweet spot: Review before day {sweet_spot}")
    print(f"Accuracy at day {sweet_spot}: {retention_curve.loc[sweet_spot, 'accuracy']:.1%}")
else:
    print("No significant drop detected")

# Save retention curve
retention_curve.to_csv('processed/retention_curve.csv', sep=';', encoding='utf-8-sig')
print("\n✅ Saved retention_curve.csv for visualization")
