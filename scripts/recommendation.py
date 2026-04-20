"""
English Learning Analytics - Recommendation System
==================================================
Provides personalized word recommendations based on:
1. User's learning history
2. Forgetting risk (days since last seen)
3. Error patterns
4. Sweet spot timing (day 9 threshold)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============================================
# CONFIGURATION
# ============================================

# Sweet spot threshold from analysis
SWEET_SPOT_DAYS = 9  # Review before day 10

# Recommendation rules
REVIEW_RULES = {
    'wrong_count_threshold': 2,      # Wrong >= 2 times → review
    'days_since_threshold': SWEET_SPOT_DAYS,  # Not seen > 9 days → review
    'low_accuracy_threshold': 0.5    # User accuracy < 50% on this word → review
}

NEW_WORD_RULES = {
    'level_match': True,             # Recommend words at user's level
    'prefer_high_frequency': True    # Prioritize common words
}

# ============================================
# LOAD DATA
# ============================================

def load_data():
    """Load processed data and prepare for recommendations"""
    
    # Load files
    df = pd.read_csv('processed/quiz_results_clean.csv', sep=';', encoding='utf-8-sig')
    words = pd.read_csv('raw/words.csv', sep=';', encoding='utf-8-sig')
    users = pd.read_csv('raw/users.csv', sep=';', encoding='utf-8-sig')
    
    return df, words, users

# ============================================
# RECOMMENDATION LOGIC
# ============================================

def get_recommendation(user_id, top_n=10):
    """
    Get personalized word recommendations for a user
    
    Args:
        user_id (str): User ID (e.g., 'U001')
        top_n (int): Number of recommendations to return
    
    Returns:
        dict: {
            'review_words': DataFrame of words to review,
            'new_words': DataFrame of new words to learn,
            'stats': Summary statistics
        }
    """
    
    # Load data
    df, words_df, users_df = load_data()
    
    # Get user info
    user = users_df[users_df['user_id'] == user_id]
    if len(user) == 0:
        return {'error': f'User {user_id} not found'}
    
    user_level = user.iloc[0]['level']
    
    # Get user's quiz history
    user_history = df[df['user_id'] == user_id].copy()
    
    if len(user_history) == 0:
        return {'error': f'No history found for user {user_id}'}
    
    # ============================================
    # PART 1: REVIEW WORDS
    # ============================================
    
    # Calculate per-word stats for this user
    word_stats = user_history.groupby('word_id').agg({
        'is_correct': ['sum', 'count', 'mean'],
        'timestamp': 'max'
    })
    
    word_stats.columns = ['correct_count', 'total_attempts', 'accuracy', 'last_seen']
    word_stats['wrong_count'] = word_stats['total_attempts'] - word_stats['correct_count']
    
    # Calculate days since last seen
    now = datetime.now()
    word_stats['last_seen'] = pd.to_datetime(word_stats['last_seen'])
    word_stats['days_since_last_seen'] = (now - word_stats['last_seen']).dt.days
    
    # Add word info
    word_stats = word_stats.merge(
        words_df[['word_id', 'word', 'level', 'frequency']], 
        left_index=True, 
        right_on='word_id'
    )
    
    # REVIEW CRITERIA (3 conditions - ANY triggers review)
    review_mask = (
        # Condition 1: Wrong multiple times (struggling)
        (word_stats['wrong_count'] >= REVIEW_RULES['wrong_count_threshold']) |
        
        # Condition 2: Not seen in a while (forgetting risk)
        (word_stats['days_since_last_seen'] > REVIEW_RULES['days_since_threshold']) |
        
        # Condition 3: Low accuracy on this word (weak spot)
        (word_stats['accuracy'] < REVIEW_RULES['low_accuracy_threshold'])
    )
    
    review_words = word_stats[review_mask].copy()
    
    # Priority scoring for review words
    # Higher score = more urgent to review
    review_words['priority_score'] = (
        review_words['wrong_count'] * 2.0 +                    # Wrong count (weight: 2x)
        (review_words['days_since_last_seen'] / 10) * 1.5 +   # Days since (weight: 1.5x)
        (1 - review_words['accuracy']) * 3.0                   # Inverse accuracy (weight: 3x)
    )
    
    # Sort by priority (highest first)
    review_words = review_words.sort_values('priority_score', ascending=False)
    
    # Select columns for output
    review_output = review_words[[
        'word', 'level', 'frequency', 
        'total_attempts', 'accuracy', 'wrong_count',
        'days_since_last_seen', 'priority_score'
    ]].head(top_n)
    
    # ============================================
    # PART 2: NEW WORDS
    # ============================================
    
    # Get words user has NOT seen yet
    seen_word_ids = set(user_history['word_id'].unique())
    unseen_words = words_df[~words_df['word_id'].isin(seen_word_ids)].copy()
    
    # Filter by level (recommend at user's level or one level below)
    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    user_level_idx = level_order.index(user_level)
    
    # Include current level + one below (if exists)
    recommended_levels = [user_level]
    if user_level_idx > 0:
        recommended_levels.append(level_order[user_level_idx - 1])
    
    new_words = unseen_words[unseen_words['level'].isin(recommended_levels)].copy()
    
    # Priority scoring for new words
    # Prefer high-frequency words (easier to learn)
    freq_score = {'high': 3, 'medium': 2, 'low': 1}
    new_words['priority_score'] = new_words['frequency'].map(freq_score)
    
    # Add small random component for diversity
    new_words['priority_score'] += np.random.uniform(0, 0.5, len(new_words))
    
    # Sort by priority
    new_words = new_words.sort_values('priority_score', ascending=False)
    
    # Select columns for output
    new_output = new_words[['word', 'level', 'frequency', 'priority_score']].head(top_n)
    
    # ============================================
    # SUMMARY STATISTICS
    # ============================================
    
    stats = {
        'user_id': user_id,
        'user_level': user_level,
        'total_words_seen': len(seen_word_ids),
        'total_attempts': len(user_history),
        'overall_accuracy': user_history['is_correct'].mean(),
        'words_needing_review': len(review_words),
        'new_words_available': len(new_words),
        'review_reasons': {
            'wrong_multiple_times': (word_stats['wrong_count'] >= REVIEW_RULES['wrong_count_threshold']).sum(),
            'forgetting_risk': (word_stats['days_since_last_seen'] > REVIEW_RULES['days_since_threshold']).sum(),
            'low_accuracy': (word_stats['accuracy'] < REVIEW_RULES['low_accuracy_threshold']).sum()
        }
    }
    
    return {
        'review_words': review_output,
        'new_words': new_output,
        'stats': stats
    }

# ============================================
# DISPLAY FUNCTION
# ============================================

def display_recommendation(user_id, top_n=10):
    """
    Display recommendations in a readable format
    """
    
    result = get_recommendation(user_id, top_n)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    stats = result['stats']
    
    print("=" * 70)
    print(f"PERSONALIZED RECOMMENDATIONS FOR {user_id}")
    print("=" * 70)
    
    # User stats
    print(f"\n📊 USER PROFILE")
    print(f"  Level: {stats['user_level']}")
    print(f"  Words learned: {stats['total_words_seen']}")
    print(f"  Total attempts: {stats['total_attempts']}")
    print(f"  Overall accuracy: {stats['overall_accuracy']:.1%}")
    
    # Review recommendations
    print(f"\n🔄 WORDS TO REVIEW ({len(result['review_words'])} recommended)")
    print("-" * 70)
    
    if len(result['review_words']) > 0:
        print("\nWhy review?")
        print(f"  • Wrong multiple times (≥2): {stats['review_reasons']['wrong_multiple_times']} words")
        print(f"  • Forgetting risk (>{SWEET_SPOT_DAYS}d): {stats['review_reasons']['forgetting_risk']} words")
        print(f"  • Low accuracy (<50%): {stats['review_reasons']['low_accuracy']} words")
        
        print(f"\nTop {min(top_n, len(result['review_words']))} priority words:")
        print(result['review_words'].to_string(index=False))
    else:
        print("  ✅ No words need review right now!")
    
    # New word recommendations
    print(f"\n\n✨ NEW WORDS TO LEARN ({len(result['new_words'])} recommended)")
    print("-" * 70)
    
    if len(result['new_words']) > 0:
        print(f"\nRecommended for {stats['user_level']} level learners:")
        print(result['new_words'].to_string(index=False))
    else:
        print("  You've learned all available words at your level!")
    
    print("\n" + "=" * 70)

# ============================================
# MAIN - DEMO
# ============================================

if __name__ == "__main__":
    print("=" * 70)
    print("ENGLISH LEARNING RECOMMENDATION SYSTEM")
    print("=" * 70)
    
    # Create output folder
    import os
    os.makedirs('processed', exist_ok=True)
    
    # Demo with 3 different users
    demo_users = ['U001', 'U025', 'U050']
    
    all_results = []
    
    for user_id in demo_users:
        display_recommendation(user_id, top_n=5)
        
        # Get and save results
        result = get_recommendation(user_id, top_n=10)
        if 'error' not in result:
            # Save individual user recommendations
            result['review_words'].to_csv(
                f'processed/rec_{user_id}_review.csv', 
                index=False, 
                sep=';', 
                encoding='utf-8-sig'
            )
            result['new_words'].to_csv(
                f'processed/rec_{user_id}_new.csv', 
                index=False, 
                sep=';', 
                encoding='utf-8-sig'
            )
            all_results.append(result)
        
        print("\n\n")
    
    print("=" * 70)
    print("✅ RECOMMENDATION SYSTEM COMPLETE")
    print("=" * 70)
    print("\nGenerated files:")
    for user_id in demo_users:
        print(f"  - processed/rec_{user_id}_review.csv (words to review)")
        print(f"  - processed/rec_{user_id}_new.csv (new words)")
    
    print("\nUsage:")
    print("  from recommendation import get_recommendation")
    print("  result = get_recommendation('U001', top_n=10)")
    print("\nReturns:")
    print("  - review_words: DataFrame with priority scores")
    print("  - new_words: DataFrame with recommendations")
    print("  - stats: Summary statistics")
    print("=" * 70)
