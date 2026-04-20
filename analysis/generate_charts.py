"""
Generate all 6 visualizations for the dashboard
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# Create output folder
os.makedirs('processed', exist_ok=True)

# Load data
df = pd.read_csv('processed/quiz_results_clean.csv', sep=';', encoding='utf-8-sig')
retention = pd.read_csv('processed/retention_curve.csv', sep=';', encoding='utf-8-sig', index_col=0)

print("=" * 60)
print("GENERATING VISUALIZATIONS")
print("=" * 60)

# Chart 1: Difficulty by word level
print("\n[1/6] Word difficulty by level...")
error_by_level = df.groupby('word_level')['is_correct'].agg(['mean', 'count'])
error_by_level['error_rate'] = 1 - error_by_level['mean']
error_by_level = error_by_level.reindex(['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

fig = go.Figure()
fig.add_trace(go.Bar(
    x=error_by_level.index,
    y=error_by_level['error_rate'] * 100,
    text=[f"{val:.1f}%" for val in error_by_level['error_rate'] * 100],
    textposition='outside',
    marker_color=['#2ecc71', '#27ae60', '#f39c12', '#e67e22', '#e74c3c', '#c0392b']
))
fig.update_layout(
    title='Word Difficulty: Error Rate by CEFR Level (All Users)',
    xaxis_title='Word Level',
    yaxis_title='Error Rate (%)',
    height=500,
    showlegend=False
)
fig.write_html('processed/chart1_difficulty_by_level.html')
print("  ✓ Saved chart1_difficulty_by_level.html")
print("  📊 Insight: Higher-level words are harder for average learners (not learners getting worse)")

# Chart 2: Learning curve
print("\n[2/6] Learning curve...")
learning_curve = df[df['attempt_number'] <= 10].groupby('attempt_number').agg({
    'is_correct': ['mean', 'count']
})
learning_curve.columns = ['accuracy', 'count']

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=learning_curve.index,
    y=learning_curve['accuracy'] * 100,
    mode='lines+markers',
    line=dict(width=3, color='#3498db'),
    marker=dict(size=10)
))
fig.update_layout(
    title='Learning Curve: Accuracy by Attempt Number',
    xaxis_title='Attempt Number',
    yaxis_title='Accuracy (%)',
    height=500
)
fig.write_html('processed/chart2_learning_curve.html')
print("  ✓ Saved chart2_learning_curve.html")

# Chart 3: Error heatmap
print("\n[3/6] Error pattern heatmap...")
pivot = df.pivot_table(
    values='is_correct',
    index='user_level',
    columns='word_level',
    aggfunc='mean'
)
level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
pivot = pivot.reindex(level_order)[level_order]
pivot_error = (1 - pivot) * 100

fig = go.Figure(data=go.Heatmap(
    z=pivot_error.values,
    x=pivot_error.columns,
    y=pivot_error.index,
    colorscale='Reds',
    text=pivot_error.values.round(1),
    texttemplate='%{text}%',
    colorbar=dict(title="Error Rate (%)")
))
fig.update_layout(
    title='Error Pattern: User Level × Word Level',
    xaxis_title='Word Level',
    yaxis_title='User Level',
    height=500
)
fig.write_html('processed/chart3_error_heatmap.html')
print("  ✓ Saved chart3_error_heatmap.html")

# Chart 4: Time vs accuracy
print("\n[4/6] Time vs accuracy scatter...")
sample = df.sample(min(2000, len(df)), random_state=42)

fig = go.Figure()
correct = sample[sample['is_correct'] == True]
fig.add_trace(go.Scatter(
    x=correct['time_spent'],
    y=correct['is_correct'] + np.random.normal(0, 0.02, len(correct)),
    mode='markers',
    name='Correct',
    marker=dict(color='#2ecc71', size=5, opacity=0.5)
))

incorrect = sample[sample['is_correct'] == False]
fig.add_trace(go.Scatter(
    x=incorrect['time_spent'],
    y=incorrect['is_correct'] + np.random.normal(0, 0.02, len(incorrect)),
    mode='markers',
    name='Incorrect',
    marker=dict(color='#e74c3c', size=5, opacity=0.5)
))

correlation = df['time_spent'].corr(df['is_correct'])
fig.update_layout(
    title=f'Time Spent vs Accuracy (Correlation: {correlation:.3f})',
    xaxis_title='Time Spent (seconds)',
    yaxis_title='Outcome',
    yaxis=dict(tickvals=[0, 1], ticktext=['Incorrect', 'Correct']),
    height=500
)
fig.write_html('processed/chart4_time_vs_accuracy.html')
print("  ✓ Saved chart4_time_vs_accuracy.html")

# Chart 5: User distribution
print("\n[5/6] User performance distribution...")
user_accuracy = df.groupby('user_id')['is_correct'].mean() * 100

fig = go.Figure()
fig.add_trace(go.Histogram(
    x=user_accuracy,
    nbinsx=20,
    marker_color='#9b59b6',
    marker_line_color='white',
    marker_line_width=1.5
))

mean_accuracy = user_accuracy.mean()
fig.add_vline(
    x=mean_accuracy,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Mean: {mean_accuracy:.1f}%",
    annotation_position="top right"
)

fig.update_layout(
    title='User Performance Distribution',
    xaxis_title='Overall Accuracy (%)',
    yaxis_title='Number of Users',
    height=500,
    showlegend=False
)
fig.write_html('processed/chart5_user_distribution.html')
print("  ✓ Saved chart5_user_distribution.html")

# Chart 6: SWEET SPOT (signature chart)
print("\n[6/6] ⭐ Sweet Spot of Review (SIGNATURE CHART)...")

# CRITICAL: Define sweet spot threshold with clear rationale
# We use 10% drop as threshold because:
# - 5% = noise/measurement error
# - 10% = significant enough to warrant action
# - 15%+ = already forgotten too much
SWEET_SPOT_DROP_THRESHOLD = 0.10

baseline_accuracy = retention[retention.index <= 3]['accuracy'].mean()
threshold = baseline_accuracy - SWEET_SPOT_DROP_THRESHOLD
sweet_spot = retention[retention['accuracy'] < threshold].index.min()

fig = go.Figure()

# Main curve
fig.add_trace(go.Scatter(
    x=retention.index,
    y=retention['accuracy'] * 100,
    mode='lines+markers',
    name='Accuracy',
    line=dict(width=3, color='#3498db'),
    marker=dict(size=8)
))

# Baseline
fig.add_hline(
    y=baseline_accuracy * 100,
    line_dash="dash",
    line_color="green",
    annotation_text=f"Baseline (0-3d): {baseline_accuracy*100:.1f}%",
    annotation_position="right"
)

# Threshold
fig.add_hline(
    y=threshold * 100,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Threshold (-10%): {threshold*100:.1f}%",
    annotation_position="right"
)

# Sweet spot
if pd.notna(sweet_spot):
    fig.add_vline(
        x=sweet_spot,
        line_dash="dash",
        line_color="orange",
        annotation_text=f"⭐ Sweet Spot: Day {sweet_spot}",
        annotation_position="top"
    )
    
    fig.add_trace(go.Scatter(
        x=[sweet_spot],
        y=[retention.loc[sweet_spot, 'accuracy'] * 100],
        mode='markers',
        marker=dict(size=15, color='orange', symbol='star'),
        showlegend=False
    ))

fig.update_layout(
    title='⭐ Sweet Spot of Review: Optimal Review Timing',
    xaxis_title='Days Since Last Seen',
    yaxis_title='Accuracy (%)',
    height=600
)
fig.write_html('processed/chart6_sweet_spot.html')
print("  ✓ Saved chart6_sweet_spot.html")

# Chart 7: Retention by time bucket (SUPPORTING CHART for sweet spot)
print("\n[7/7] Retention by time bucket (supports sweet spot finding)...")

# Create retention buckets
repeated = df[df['attempt_number'] > 1].copy()
repeated['time_bucket'] = pd.cut(
    repeated['days_since_last_seen'],
    bins=[-1, 3, 7, 14, 30],
    labels=['0-3 days', '4-7 days', '8-14 days', '15-30 days']
)

bucket_stats = repeated.groupby('time_bucket', observed=True).agg({
    'is_correct': ['mean', 'count']
})
bucket_stats.columns = ['accuracy', 'count']

fig = go.Figure()

# Bar chart
fig.add_trace(go.Bar(
    x=bucket_stats.index.astype(str),
    y=bucket_stats['accuracy'] * 100,
    text=[f"{acc*100:.1f}%<br>n={cnt:,}" for acc, cnt in zip(bucket_stats['accuracy'], bucket_stats['count'])],
    textposition='outside',
    marker_color=['#2ecc71', '#f39c12', '#e67e22', '#e74c3c']
))

# Add threshold line
fig.add_hline(
    y=threshold * 100,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Threshold: {threshold*100:.1f}%",
    annotation_position="right"
)

fig.update_layout(
    title='Retention Analysis: Accuracy by Time Since Last Review',
    xaxis_title='Days Since Last Seen',
    yaxis_title='Accuracy (%)',
    height=500,
    showlegend=False
)

fig.write_html('processed/chart7_retention_buckets.html')
print("  ✓ Saved chart7_retention_buckets.html")
print("  📊 Insight: Supports sweet spot — shows when accuracy crosses threshold")

print("\n" + "=" * 60)
print("⭐ SWEET SPOT INSIGHT")
print("=" * 60)
print(f"Baseline accuracy (0-3 days): {baseline_accuracy*100:.1f}%")
print(f"Threshold definition: {SWEET_SPOT_DROP_THRESHOLD*100:.0f}% drop (significant but not catastrophic)")
if pd.notna(sweet_spot):
    print(f"\n⭐ Sweet spot: Review BEFORE day {sweet_spot}")
    print(f"   Accuracy at day {sweet_spot}: {retention.loc[sweet_spot, 'accuracy']*100:.1f}%")
    print(f"   Drop from baseline: {(baseline_accuracy - retention.loc[sweet_spot, 'accuracy'])*100:.1f}%")
    print(f"\n💡 Recommendation: Review words every {sweet_spot-1} days")
    print(f"   Rationale: Prevents accuracy from dropping below {threshold*100:.1f}%")
print("=" * 60)

print("\n" + "=" * 60)
print("✅ ALL VISUALIZATIONS COMPLETE")
print("=" * 60)
print("\nGenerated 7 interactive HTML charts:")
print("  1. chart1_difficulty_by_level.html")
print("  2. chart2_learning_curve.html")
print("  3. chart3_error_heatmap.html")
print("  4. chart4_time_vs_accuracy.html")
print("  5. chart5_user_distribution.html")
print("  6. chart6_sweet_spot.html ⭐ SIGNATURE")
print("  7. chart7_retention_buckets.html (supports #6)")
print("\n📍 Location: processed/ folder")
print("=" * 60)
