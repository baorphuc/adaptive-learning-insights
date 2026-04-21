"""
English Learning Analytics - Recommendation System (FINAL)
===========================================================
Fix log vs v2:
1. Normalize COMBINED (không riêng từng nhóm)
2. WEIGHTS được apply đúng vào formula
3. frequency dùng trong review score
4. np.random.seed(42) → reproducible
5. Adaptive review ratio theo accuracy
6. 20% harder = proper probability
7. Review criteria tighter (OR + AND combo)
8. normalize() edge case = 0.0
9. Log final distribution
10. Empty new_words guard
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

np.random.seed(42)  # FIX 4: reproducible

# ============================================
# CONFIGURATION
# ============================================

SWEET_SPOT_DAYS = 9
TOP_N = 20

# FIX 2: Weights actually used in formula
WEIGHTS = {
    'days_since':  0.6,
    'wrong_count': 0.3,
    'frequency':   0.1
}

FREQ_SCORE  = {'high': 1.0, 'medium': 0.5, 'low': 0.0}   # review: low freq = harder
FREQ_SCORE_NEW = {'high': 3.0, 'medium': 2.0, 'low': 1.0} # new: high freq = easier first

# ============================================
# HELPERS
# ============================================

def normalize(series):
    """Normalize to 0-10. Edge case: all same → 0.0"""  # FIX 8
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - lo) / (hi - lo) * 10


def load_data():
    df    = pd.read_csv('processed/quiz_results_clean.csv', sep=';', encoding='utf-8-sig')
    words = pd.read_csv('raw/words.csv',                   sep=';', encoding='utf-8-sig')
    users = pd.read_csv('raw/users.csv',                   sep=';', encoding='utf-8-sig')
    return df, words, users

# ============================================
# CORE FUNCTION
# ============================================

def get_recommendation(user_id, top_n=TOP_N, debug=False):
    """
    Personalized word recommendations.

    Priority formula (WEIGHTS applied correctly):
        review_score = 0.6 * norm(days_since)
                     + 0.3 * norm(wrong_count)
                     + 0.1 * norm(freq_penalty)

    new_score = frequency_map (high=3, medium=2, low=1)

    Final: normalize COMBINED scores → compare apples to apples
    """
    df, words_df, users_df = load_data()

    # Validate
    user_row = users_df[users_df['user_id'] == user_id]
    if len(user_row) == 0:
        return {'error': f'User {user_id} not found'}

    user_level   = user_row.iloc[0]['level']
    user_history = df[df['user_id'] == user_id].copy()

    if len(user_history) == 0:
        return {'error': f'No history for {user_id}'}

    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    user_idx    = level_order.index(user_level)

    # ============================================
    # PART 1: REVIEW WORDS
    # ============================================

    word_stats = user_history.groupby('word_id').agg(
        correct_count  = ('is_correct', 'sum'),
        total_attempts = ('is_correct', 'count'),
        accuracy       = ('is_correct', 'mean'),
        last_seen      = ('timestamp',  'max')
    )
    word_stats['wrong_count']        = word_stats['total_attempts'] - word_stats['correct_count']
    word_stats['last_seen']          = pd.to_datetime(word_stats['last_seen'])
    word_stats['days_since_last_seen'] = (datetime.now() - word_stats['last_seen']).dt.days

    word_stats = word_stats.merge(
        words_df[['word_id', 'word', 'level', 'frequency']],
        left_index=True, right_on='word_id'
    )

    # FIX 7: Tighter review criteria
    review_mask = (
        (word_stats['wrong_count'] >= 2) |
        (
            (word_stats['days_since_last_seen'] > SWEET_SPOT_DAYS) &
            (word_stats['accuracy'] < 0.7)
        )
    )

    review_words = word_stats[review_mask].copy()

    if len(review_words) > 0:
        # FIX 2 + 3: Apply WEIGHTS correctly, include frequency
        freq_penalty = review_words['frequency'].map(FREQ_SCORE).fillna(0.5)

        review_words['priority_score'] = (
            WEIGHTS['days_since']  * normalize(review_words['days_since_last_seen']) +
            WEIGHTS['wrong_count'] * normalize(review_words['wrong_count'])          +
            WEIGHTS['frequency']   * normalize(freq_penalty)
        ).round(2)  # ROUND → clean Excel display
    else:
        review_words['priority_score'] = 0.0

    review_words = review_words.sort_values('priority_score', ascending=False)

    # ============================================
    # PART 2: NEW WORDS
    # ============================================

    seen_ids = set(user_history['word_id'].unique())
    unseen   = words_df[~words_df['word_id'].isin(seen_ids)].copy()

    # Base: current level + one below
    rec_levels = [user_level]
    if user_idx > 0:
        rec_levels.append(level_order[user_idx - 1])

    new_words = unseen[unseen['level'].isin(rec_levels)].copy()

    # FIX 6: 20% probability for harder words (not guaranteed)
    if user_idx < len(level_order) - 1 and np.random.rand() < 0.2:
        harder = unseen[unseen['level'] == level_order[user_idx + 1]]
        if len(harder) > 0:
            new_words = pd.concat([new_words, harder.sample(min(2, len(harder)))])

    # FIX 10: Guard empty new_words
    if len(new_words) == 0:
        new_words_output = pd.DataFrame(columns=['word', 'level', 'frequency', 'priority_score', 'type'])
    else:
        new_words['priority_score'] = new_words['frequency'].map(FREQ_SCORE_NEW).astype(float)
        new_words = new_words.sort_values('priority_score', ascending=False)
        new_words_output = new_words[['word', 'level', 'frequency', 'priority_score']]

    # ============================================
    # PART 3: FINAL RECOMMENDATION
    # ============================================

    # FIX 5: Adaptive ratio based on accuracy
    overall_acc = user_history['is_correct'].mean()
    if overall_acc < 0.5:
        n_review, n_new = 16, 4   # weak user → more review
    elif overall_acc < 0.7:
        n_review, n_new = 15, 5   # average
    else:
        n_review, n_new = 12, 8   # strong user → more new words

    review_tagged        = review_words.head(n_review)[['word', 'level', 'frequency', 'priority_score']].copy()
    review_tagged['type'] = 'review'

    new_tagged            = new_words_output.head(n_new).copy()
    new_tagged['type']    = 'new'

    # FIX 1: Normalize COMBINED (not separate)
    combined = pd.concat([review_tagged, new_tagged])
    combined['priority_score'] = normalize(combined['priority_score']).round(2)  # ROUND → clean Excel display
    final = combined.sort_values('priority_score', ascending=False).head(top_n)

    # ============================================
    # STATS
    # ============================================

    stats = {
        'user_id':          user_id,
        'user_level':       user_level,
        'total_words_seen': len(seen_ids),
        'total_attempts':   len(user_history),
        'overall_accuracy': round(overall_acc, 3),
        'words_to_review':  len(review_words),
        'n_review_recommended': n_review,
        'n_new_recommended':    n_new,
        'review_reasons': {
            'wrong_multiple': int((word_stats['wrong_count'] >= 2).sum()),
            'forgetting_and_weak': int(
                ((word_stats['days_since_last_seen'] > SWEET_SPOT_DAYS) &
                 (word_stats['accuracy'] < 0.7)).sum()
            )
        }
    }

    # FIX 9: Log final distribution
    if debug:
        print(f"\n[DEBUG] {user_id} | Level: {user_level} | Accuracy: {overall_acc:.1%}")
        print(f"  Ratio → review: {n_review} | new: {n_new}")
        print(f"  Final type dist: {final['type'].value_counts().to_dict()}")
        print(f"  Score range → review: {review_tagged['priority_score'].min():.2f}-{review_tagged['priority_score'].max():.2f} | "
              f"new: {new_tagged['priority_score'].min():.2f}-{new_tagged['priority_score'].max():.2f}")

    return {
        'review_words':         review_words.head(n_review),
        'new_words':            new_words_output.head(n_new),
        'final_recommendation': final,
        'stats':                stats
    }

# ============================================
# DISPLAY
# ============================================

def display_recommendation(user_id):
    result = get_recommendation(user_id, debug=True)

    if 'error' in result:
        print(f"❌ {result['error']}")
        return

    s = result['stats']

    print(f"\n{'='*70}")
    print(f"  {user_id}  |  Level: {s['user_level']}  |  Accuracy: {s['overall_accuracy']:.1%}")
    print(f"  Ratio: {s['n_review_recommended']} review + {s['n_new_recommended']} new")
    print(f"{'='*70}")

    print(f"\n🔄 REVIEW  (wrong≥2: {s['review_reasons']['wrong_multiple']} | "
          f"forgetting+weak: {s['review_reasons']['forgetting_and_weak']})")
    cols = ['word', 'level', 'accuracy', 'wrong_count', 'days_since_last_seen', 'priority_score']
    print(result['review_words'][cols].to_string(index=False))

    print(f"\n✨ NEW WORDS")
    print(result['new_words'].to_string(index=False))

    print(f"\n🎯 FINAL (normalized 0-10, combined scale)")
    print(result['final_recommendation'][['word', 'level', 'type', 'priority_score']].to_string(index=False))


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    os.makedirs('processed', exist_ok=True)

    print("=" * 70)
    print("RECOMMENDATION SYSTEM — FINAL VERSION")
    print("=" * 70)
    print(f"\nFormula:")
    print(f"  review_score = {WEIGHTS['days_since']}×norm(days_since)")
    print(f"               + {WEIGHTS['wrong_count']}×norm(wrong_count)")
    print(f"               + {WEIGHTS['frequency']}×norm(freq_penalty)")
    print(f"  new_score    = freq_map (high=3, medium=2, low=1)")
    print(f"  final        = normalize(combined) → sort → top N")

    demo_users = ['U001', 'U025', 'U050']

    for user_id in demo_users:
        display_recommendation(user_id)

        result = get_recommendation(user_id)
        if 'error' not in result:
            result['review_words'].to_csv(
                f'processed/rec_{user_id}_review.csv',
                index=False, sep=';', encoding='utf-8-sig'
            )
            result['new_words'].to_csv(
                f'processed/rec_{user_id}_new.csv',
                index=False, sep=';', encoding='utf-8-sig'
            )
            result['final_recommendation'].to_csv(
                f'processed/rec_{user_id}_final.csv',
                index=False, sep=';', encoding='utf-8-sig'
            )
        print()

    print("=" * 70)
    print("✅ DONE — Files exported to processed/")
    for u in demo_users:
        print(f"  rec_{u}_review.csv | rec_{u}_new.csv | rec_{u}_final.csv")
    print("=" * 70)
