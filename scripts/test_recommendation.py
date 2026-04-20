"""
Recommendation System - Quick Demo
===================================
Standalone script to test recommendations for multiple users
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================

SWEET_SPOT_DAYS = 9
REVIEW_RULES = {
    'wrong_count_threshold': 2,
    'days_since_threshold': SWEET_SPOT_DAYS,
    'low_accuracy_threshold': 0.5
}

# ============================================
# RECOMMENDATION FUNCTION
# ============================================

def get_recommendation(user_id, top_n=10):
    """Get personalized recommendations"""
    
    # Load data
    df = pd.read_csv('processed/quiz_results_clean.csv', sep=';', encoding='utf-8-sig')
    words_df = pd.read_csv('raw/words.csv', sep=';', encoding='utf-8-sig')
    users_df = pd.read_csv('raw/users.csv', sep=';', encoding='utf-8-sig')
    
    # Get user
    user = users_df[users_df['user_id'] == user_id]
    if len(user) == 0:
        return {'error': f'User {user_id} not found'}
    
    user_level = user.iloc[0]['level']
    user_history = df[df['user_id'] == user_id].copy()
    
    if len(user_history) == 0:
        return {'error': f'No history for {user_id}'}
    
    # REVIEW WORDS
    word_stats = user_history.groupby('word_id').agg({
        'is_correct': ['sum', 'count', 'mean'],
        'timestamp': 'max'
    })
    
    word_stats.columns = ['correct_count', 'total_attempts', 'accuracy', 'last_seen']
    word_stats['wrong_count'] = word_stats['total_attempts'] - word_stats['correct_count']
    
    now = datetime.now()
    word_stats['last_seen'] = pd.to_datetime(word_stats['last_seen'])
    word_stats['days_since_last_seen'] = (now - word_stats['last_seen']).dt.days
    
    word_stats = word_stats.merge(
        words_df[['word_id', 'word', 'level', 'frequency']], 
        left_index=True, 
        right_on='word_id'
    )
    
    # Review criteria
    review_mask = (
        (word_stats['wrong_count'] >= REVIEW_RULES['wrong_count_threshold']) |
        (word_stats['days_since_last_seen'] > REVIEW_RULES['days_since_threshold']) |
        (word_stats['accuracy'] < REVIEW_RULES['low_accuracy_threshold'])
    )
    
    review_words = word_stats[review_mask].copy()
    
    # Priority scoring
    review_words['priority_score'] = (
        review_words['wrong_count'] * 2.0 +
        (review_words['days_since_last_seen'] / 10) * 1.5 +
        (1 - review_words['accuracy']) * 3.0
    )
    
    review_words = review_words.sort_values('priority_score', ascending=False)
    review_output = review_words[[
        'word', 'level', 'frequency', 
        'total_attempts', 'accuracy', 'wrong_count',
        'days_since_last_seen', 'priority_score'
    ]].head(top_n)
    
    # NEW WORDS
    seen_word_ids = set(user_history['word_id'].unique())
    unseen_words = words_df[~words_df['word_id'].isin(seen_word_ids)].copy()
    
    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    user_level_idx = level_order.index(user_level)
    
    recommended_levels = [user_level]
    if user_level_idx > 0:
        recommended_levels.append(level_order[user_level_idx - 1])
    
    new_words = unseen_words[unseen_words['level'].isin(recommended_levels)].copy()
    
    # Priority scoring (FIXED: ensure float type from start)
    freq_score = {'high': 3.0, 'medium': 2.0, 'low': 1.0}
    new_words['priority_score'] = new_words['frequency'].map(freq_score).astype(float)
    new_words['priority_score'] = new_words['priority_score'] + np.random.uniform(0, 0.5, len(new_words))
    new_words = new_words.sort_values('priority_score', ascending=False)
    
    new_output = new_words[['word', 'level', 'frequency', 'priority_score']].head(top_n)
    new_output['priority_score'] = new_output['priority_score'].round(1)
    
    # Stats
    stats = {
        'user_id': user_id,
        'user_level': user_level,
        'total_words_seen': len(seen_word_ids),
        'total_attempts': len(user_history),
        'overall_accuracy': user_history['is_correct'].mean(),
        'words_needing_review': len(review_words),
        'new_words_available': len(new_words)
    }
    
    return {
        'review_words': review_output,
        'new_words': new_output,
        'stats': stats
    }

# ============================================
# DEMO
# ============================================

if __name__ == "__main__":
    import os
    os.makedirs('processed', exist_ok=True)
    
    print("=" * 70)
    print("RECOMMENDATION SYSTEM - QUICK DEMO")
    print("=" * 70)
    
    # Test with 5 users
    test_users = ['U001', 'U010', 'U025', 'U050', 'U075']
    
    for user_id in test_users:
        print(f"\n{'='*70}")
        print(f"USER: {user_id}")
        print(f"{'='*70}")
        
        result = get_recommendation(user_id, top_n=5)
        
        if 'error' in result:
            print(f"❌ {result['error']}")
            continue
        
        stats = result['stats']
        
        # Display stats
        print(f"\n📊 PROFILE")
        print(f"  Level: {stats['user_level']}")
        print(f"  Accuracy: {stats['overall_accuracy']:.1%}")
        print(f"  Words learned: {stats['total_words_seen']}")
        
        # Review words
        print(f"\n🔄 REVIEW ({stats['words_needing_review']} total)")
        if len(result['review_words']) > 0:
            print(result['review_words'][['word', 'level', 'accuracy', 'days_since_last_seen']].to_string(index=False))
        else:
            print("  ✅ None needed!")
        
        # New words
        print(f"\n✨ NEW WORDS ({stats['new_words_available']} available)")
        if len(result['new_words']) > 0:
            print(result['new_words'][['word', 'level', 'frequency']].to_string(index=False))
        
        # Save to CSV
        result['review_words'].to_csv(
            f'processed/rec_{user_id}_review.csv', 
            index=False, sep=';', encoding='utf-8-sig'
        )
        result['new_words'].to_csv(
            f'processed/rec_{user_id}_new.csv', 
            index=False, sep=';', encoding='utf-8-sig'
        )
    
    print("\n\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print("\nGenerated files in processed/:")
    for user_id in test_users:
        print(f"  - rec_{user_id}_review.csv")
        print(f"  - rec_{user_id}_new.csv")
    print("=" * 70)
