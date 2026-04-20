"""
English Learning Analytics - Data Generation (CLEAN VERSION)
============================================================
Generates realistic learning data with SIMPLE, EXPLAINABLE logic:
- Level gap effect (user level vs word level)
- Forgetting curve (step-based, NOT exponential)
- Word frequency effect (high/medium/low)
- Learning effect (improves with attempts)

NO over-engineering:
- NO behavior profiles
- NO exponential math
- NO 7-factor difficulty scores
- NO topic sampling
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# ============================================
# CONFIGURATION
# ============================================

NUM_USERS = 100
NUM_WORDS = 2000
NUM_QUIZ_RESULTS = 10000

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
LEVEL_SCORE = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}

WORD_FREQUENCIES = ['high', 'medium', 'low']
FREQUENCY_WEIGHTS = [0.5, 0.3, 0.2]  # high freq words are more common

# ============================================
# GENERATE WORDS (SIMPLE)
# ============================================

def generate_words():
    """Generate word dataset with level and frequency ONLY"""
    words = []
    
    for i in range(NUM_WORDS):
        word_id = f"W{i+1:04d}"
        word = f"word_{i+1}"
        level = random.choice(LEVELS)
        frequency = random.choices(WORD_FREQUENCIES, weights=FREQUENCY_WEIGHTS)[0]
        
        words.append({
            'word_id': word_id,
            'word': word,
            'level': level,
            'frequency': frequency
        })
    
    return pd.DataFrame(words)

# ============================================
# GENERATE USERS (SIMPLE)
# ============================================

def generate_users():
    """Generate user dataset with levels ONLY (no behavior profiles)"""
    users = []
    
    for i in range(NUM_USERS):
        user_id = f"U{i+1:03d}"
        name = f"User_{i+1}"
        level = random.choice(LEVELS)
        
        users.append({
            'user_id': user_id,
            'name': name,
            'level': level
        })
    
    return pd.DataFrame(users)

# ============================================
# FORGETTING EFFECT (STEP-BASED, SIMPLE)
# ============================================

def apply_forgetting_effect(base_prob, days_since):
    """
    Simple step-based forgetting curve
    EASY TO EXPLAIN: accuracy drops at 3, 7, 14 day thresholds
    
    No exponential math — just if-else logic
    """
    if days_since > 14:
        return base_prob - 0.20  # forgot a lot
    elif days_since > 7:
        return base_prob - 0.15  # forgot moderately
    elif days_since > 3:
        return base_prob - 0.05  # forgot a little
    return base_prob  # just learned

# ============================================
# CALCULATE PROBABILITY (CLEAN LOGIC)
# ============================================

def calculate_base_probability(user_level, word_level, word_frequency,
                                days_since_last_seen, attempt_number):
    """
    Calculate probability of correct answer with 4 SIMPLE factors:
    
    1. Level gap: harder if word level > user level
    2. Word frequency: rare words harder to remember
    3. Forgetting effect: accuracy drops over time (step-based)
    4. Learning effect: accuracy improves with attempts
    
    ALL factors easy to explain in interview
    """
    
    # 1. LEVEL GAP EFFECT (base probability)
    user_score = LEVEL_SCORE[user_level]
    word_score = LEVEL_SCORE[word_level]
    level_gap = word_score - user_score
    
    # Base probability from level gap
    if level_gap <= -2:
        base_prob = 0.85  # much easier
    elif level_gap == -1:
        base_prob = 0.75  # easier
    elif level_gap == 0:
        base_prob = 0.65  # same level
    elif level_gap == 1:
        base_prob = 0.50  # harder
    elif level_gap == 2:
        base_prob = 0.35  # much harder
    else:
        base_prob = 0.20  # very hard
    
    # 2. WORD FREQUENCY EFFECT
    if word_frequency == 'low':
        base_prob -= 0.10  # rare words harder
    elif word_frequency == 'medium':
        base_prob -= 0.05
    
    # 3. FORGETTING EFFECT (step-based)
    base_prob = apply_forgetting_effect(base_prob, days_since_last_seen)
    
    # 4. LEARNING EFFECT (improves with attempts)
    learning_boost = min(0.15, attempt_number * 0.03)
    base_prob += learning_boost
    
    # Clamp between 0.05 and 0.95
    base_prob = max(0.05, min(0.95, base_prob))
    
    return base_prob

# ============================================
# GENERATE QUIZ RESULTS
# ============================================

def generate_quiz_results(users_df, words_df):
    """Generate quiz results with realistic patterns"""
    
    results = []
    start_date = datetime(2024, 1, 1)
    
    # Track user-word interaction history
    user_word_history = {}  # (user_id, word_id) -> [timestamps]
    
    for i in range(NUM_QUIZ_RESULTS):
        # Random user
        user = users_df.sample(1).iloc[0]
        user_id = user['user_id']
        
        # IMPROVED: 40% chance to repeat with CONTROLLED spacing
        # This creates realistic spaced repetition patterns
        user_history_keys = [k for k in user_word_history.keys() if k[0] == user_id]
        
        if random.random() < 0.4 and len(user_history_keys) > 0:
            # Pick a word this user has seen before (REPEATED ATTEMPT)
            key = random.choice(user_history_keys)
            word_id = key[1]
            word = words_df[words_df['word_id'] == word_id].iloc[0]
            
            # CRITICAL FIX: Use realistic spacing intervals
            # Simulate spaced repetition: 1-3d, 5-7d, 10-14d, 20-30d
            last_timestamp = user_word_history[key][-1]
            attempt_count = len(user_word_history[key])
            
            # Spacing based on attempt number (realistic SRS pattern)
            if attempt_count == 1:
                # First review: 1-3 days
                days_since = random.randint(1, 3)
            elif attempt_count == 2:
                # Second review: 5-7 days
                days_since = random.randint(5, 7)
            elif attempt_count == 3:
                # Third review: 10-14 days
                days_since = random.randint(10, 14)
            else:
                # Later reviews: 15-30 days
                days_since = random.randint(15, 30)
            
            current_timestamp = last_timestamp + timedelta(days=days_since)
            attempt_number = attempt_count + 1
            
        else:
            # Pick a new random word (FIRST ATTEMPT)
            word = words_df.sample(1).iloc[0]
            word_id = word['word_id']
            days_since = 0
            current_timestamp = start_date + timedelta(days=random.randint(0, 120))
            attempt_number = 1
            key = (user_id, word_id)
        
        user_level = user['level']
        word_level = word['level']
        word_frequency = word['frequency']
        
        # Calculate probability of correct answer
        correct_prob = calculate_base_probability(
            user_level, word_level, word_frequency,
            days_since, attempt_number
        )
        
        # Determine if correct
        is_correct = random.random() < correct_prob
        
        # Time spent (harder questions take longer)
        level_gap = LEVEL_SCORE[word_level] - LEVEL_SCORE[user_level]
        base_time = 5.0  # seconds
        
        if level_gap > 0:
            base_time += level_gap * 2
        
        if not is_correct:
            base_time += random.uniform(2, 5)  # wrong answers take longer
        
        time_spent = max(1.0, base_time + random.normalvariate(0, 1.5))
        
        # Update history
        if key not in user_word_history:
            user_word_history[key] = []
        user_word_history[key].append(current_timestamp)
        
        # Record result
        results.append({
            'result_id': f"R{i+1:05d}",
            'user_id': user_id,
            'word_id': word_id,
            'timestamp': current_timestamp,
            'is_correct': is_correct,
            'time_spent': round(time_spent, 2),
            'attempt_number': attempt_number,
            'days_since_last_seen': days_since
        })
    
    return pd.DataFrame(results)

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("ENGLISH LEARNING ANALYTICS - DATA GENERATION (CLEAN)")
    print("=" * 60)
    
    # Create raw folder if not exists
    import os
    os.makedirs('raw', exist_ok=True)
    
    # Generate datasets
    print("\n[1/3] Generating words...")
    words_df = generate_words()
    print(f"  ✓ Generated {len(words_df)} words")
    print(f"  ✓ Features: level, frequency")
    
    print("\n[2/3] Generating users...")
    users_df = generate_users()
    print(f"  ✓ Generated {len(users_df)} users")
    print(f"  ✓ Features: level only (no behavior profiles)")
    
    print("\n[3/3] Generating quiz results...")
    quiz_df = generate_quiz_results(users_df, words_df)
    print(f"  ✓ Generated {len(quiz_df)} quiz results")
    print(f"  ✓ Logic: level gap + frequency + forgetting (step) + learning")
    
    # Save to CSV (Excel-compatible format)
    print("\n[SAVING] Writing to CSV...")
    words_df.to_csv('raw/words.csv', index=False, sep=';', encoding='utf-8-sig')
    users_df.to_csv('raw/users.csv', index=False, sep=';', encoding='utf-8-sig')
    quiz_df.to_csv('raw/quiz_results.csv', index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Words:        {len(words_df):,}")
    print(f"Users:        {len(users_df):,}")
    print(f"Quiz results: {len(quiz_df):,}")
    print("\nFiles saved to raw/ folder")
    print("Excel-compatible: delimiter=';', encoding='utf-8-sig'")
    print("=" * 60)
    
    # Show sample
    print("\n[SAMPLE] First 5 quiz results:")
    sample_cols = ['result_id', 'user_id', 'word_id', 'is_correct', 
                   'attempt_number', 'days_since_last_seen']
    print(quiz_df[sample_cols].head(5).to_string(index=False))
    
    # Show basic stats
    print("\n[STATS] Accuracy by user level:")
    merged = quiz_df.merge(users_df, on='user_id')
    accuracy_by_level = merged.groupby('level')['is_correct'].mean()
    for level in LEVELS:
        if level in accuracy_by_level:
            print(f"  {level}: {accuracy_by_level[level]:.2%}")
    
    print("\n[STATS] Forgetting curve effect:")
    merged['time_bucket'] = pd.cut(merged['days_since_last_seen'], 
                                     bins=[-1, 3, 7, 14, 30], 
                                     labels=['0-3d', '4-7d', '8-14d', '15-30d'])
    accuracy_by_time = merged.groupby('time_bucket', observed=True)['is_correct'].mean()
    for bucket in accuracy_by_time.index:
        print(f"  {bucket}: {accuracy_by_time[bucket]:.2%}")
    
    print("\n[STATS] Learning effect (by attempt):")
    accuracy_by_attempt = quiz_df[quiz_df['attempt_number'] <= 5].groupby('attempt_number')['is_correct'].mean()
    for attempt in sorted(accuracy_by_attempt.index):
        print(f"  Attempt {attempt}: {accuracy_by_attempt[attempt]:.2%}")

if __name__ == "__main__":
    main()
