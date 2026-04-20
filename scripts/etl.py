"""
English Learning Analytics - ETL Pipeline
==========================================
Transform raw quiz data into analysis-ready format

Pipeline:
1. EXTRACT: Load raw data
2. CLEAN: Remove errors, fix formats
3. TRANSFORM: Add derived features
4. LOAD: Save to processed/
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# ============================================
# CONFIGURATION
# ============================================

RAW_PATH = 'raw/'
PROCESSED_PATH = 'processed/'

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
LEVEL_SCORE = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}

# ============================================
# 1. EXTRACT
# ============================================

def extract_data():
    """Load raw data from CSV files"""
    print("\n[EXTRACT] Loading raw data...")
    
    # Load with correct delimiter for Excel format
    words = pd.read_csv(f'{RAW_PATH}words.csv', sep=';', encoding='utf-8-sig')
    users = pd.read_csv(f'{RAW_PATH}users.csv', sep=';', encoding='utf-8-sig')
    quiz = pd.read_csv(f'{RAW_PATH}quiz_results.csv', sep=';', encoding='utf-8-sig')
    
    print(f"  ✓ Loaded {len(words)} words")
    print(f"  ✓ Loaded {len(users)} users")
    print(f"  ✓ Loaded {len(quiz)} quiz results")
    
    return words, users, quiz

# ============================================
# 2. CLEAN
# ============================================

def clean_data(quiz_df):
    """
    Clean raw data:
    - Remove duplicates
    - Fix invalid values
    - Handle missing data
    """
    print("\n[CLEAN] Cleaning data...")
    
    initial_count = len(quiz_df)
    
    # Remove exact duplicates
    quiz_df = quiz_df.drop_duplicates()
    duplicates_removed = initial_count - len(quiz_df)
    
    # Remove invalid time_spent (negative or > 5 minutes)
    invalid_time = quiz_df[
        (quiz_df['time_spent'] < 0) | 
        (quiz_df['time_spent'] > 300)
    ]
    quiz_df = quiz_df[
        (quiz_df['time_spent'] >= 0) & 
        (quiz_df['time_spent'] <= 300)
    ]
    
    # Convert timestamp to datetime if not already
    if quiz_df['timestamp'].dtype == 'object':
        quiz_df['timestamp'] = pd.to_datetime(quiz_df['timestamp'])
    
    # Remove rows with missing critical fields
    quiz_df = quiz_df.dropna(subset=['user_id', 'word_id', 'is_correct'])
    
    print(f"  ✓ Removed {duplicates_removed} duplicates")
    print(f"  ✓ Removed {len(invalid_time)} invalid time records")
    print(f"  ✓ Final count: {len(quiz_df)} records")
    
    return quiz_df

# ============================================
# 3. TRANSFORM - ADD FEATURES
# ============================================

def add_derived_features(quiz_df, words_df, users_df):
    """
    Add derived features for analysis:
    - is_hard_word: word difficulty relative to user
    - is_slow_response: response time above threshold
    - user_performance_score: rolling accuracy
    - level_gap: difference between word and user level
    """
    print("\n[TRANSFORM] Adding derived features...")
    
    # Merge with words and users to get levels
    quiz_enriched = quiz_df.merge(
        words_df[['word_id', 'level', 'frequency']], 
        on='word_id', 
        how='left',
        suffixes=('', '_word')
    )
    
    quiz_enriched = quiz_enriched.merge(
        users_df[['user_id', 'level']], 
        on='user_id', 
        how='left',
        suffixes=('', '_user')
    )
    
    # Rename columns for clarity
    quiz_enriched = quiz_enriched.rename(columns={
        'level': 'word_level',
        'level_user': 'user_level'
    })
    
    # Feature 1: Level gap (word difficulty relative to user)
    quiz_enriched['user_level_score'] = quiz_enriched['user_level'].map(LEVEL_SCORE)
    quiz_enriched['word_level_score'] = quiz_enriched['word_level'].map(LEVEL_SCORE)
    quiz_enriched['level_gap'] = (
        quiz_enriched['word_level_score'] - quiz_enriched['user_level_score']
    )
    
    # Feature 2: Is hard word (level gap > 0)
    quiz_enriched['is_hard_word'] = (quiz_enriched['level_gap'] > 0).astype(int)
    
    # Feature 3: Is slow response (time > median + 1 std)
    median_time = quiz_enriched['time_spent'].median()
    std_time = quiz_enriched['time_spent'].std()
    threshold_time = median_time + std_time
    quiz_enriched['is_slow_response'] = (
        quiz_enriched['time_spent'] > threshold_time
    ).astype(int)
    
    # Feature 4: User performance score (rolling accuracy per user)
    # Sort by user and timestamp
    quiz_enriched = quiz_enriched.sort_values(['user_id', 'timestamp'])
    
    # Calculate rolling accuracy (last 10 attempts per user)
    quiz_enriched['user_performance_score'] = (
        quiz_enriched.groupby('user_id')['is_correct']
        .transform(lambda x: x.rolling(window=10, min_periods=1).mean())
    )
    
    # Feature 5: Forgetting risk (high if days_since > 7)
    quiz_enriched['forgetting_risk'] = (
        quiz_enriched['days_since_last_seen'] > 7
    ).astype(int)
    
    # Feature 6: Is rare word
    quiz_enriched['is_rare_word'] = (
        quiz_enriched['frequency'] == 'low'
    ).astype(int)
    
    print(f"  ✓ Added level_gap (range: {quiz_enriched['level_gap'].min()} to {quiz_enriched['level_gap'].max()})")
    print(f"  ✓ Added is_hard_word ({quiz_enriched['is_hard_word'].sum()} hard words)")
    print(f"  ✓ Added is_slow_response (threshold: {threshold_time:.1f}s)")
    print(f"  ✓ Added user_performance_score (rolling accuracy)")
    print(f"  ✓ Added forgetting_risk ({quiz_enriched['forgetting_risk'].sum()} at risk)")
    print(f"  ✓ Added is_rare_word ({quiz_enriched['is_rare_word'].sum()} rare words)")
    
    return quiz_enriched

# ============================================
# 4. LOAD
# ============================================

def load_processed_data(df):
    """Save processed data to CSV"""
    print("\n[LOAD] Saving processed data...")
    
    # Create processed folder if not exists
    os.makedirs(PROCESSED_PATH, exist_ok=True)
    
    # Select final columns in logical order
    final_columns = [
        'result_id',
        'user_id',
        'user_level',
        'word_id',
        'word_level',
        'frequency',
        'timestamp',
        'is_correct',
        'time_spent',
        'attempt_number',
        'days_since_last_seen',
        'level_gap',
        'is_hard_word',
        'is_slow_response',
        'is_rare_word',
        'forgetting_risk',
        'user_performance_score'
    ]
    
    df_final = df[final_columns]
    
    # Save to CSV (Excel-compatible)
    output_path = f'{PROCESSED_PATH}quiz_results_clean.csv'
    df_final.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"  ✓ Saved to {output_path}")
    print(f"  ✓ Columns: {len(final_columns)}")
    print(f"  ✓ Rows: {len(df_final)}")
    
    return df_final

# ============================================
# 5. DATA QUALITY REPORT
# ============================================

def generate_quality_report(df_raw, df_processed):
    """Generate data quality summary"""
    print("\n" + "=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)
    
    print(f"\nRecords:")
    print(f"  Raw:       {len(df_raw):,}")
    print(f"  Processed: {len(df_processed):,}")
    print(f"  Removed:   {len(df_raw) - len(df_processed):,} ({(1 - len(df_processed)/len(df_raw))*100:.1f}%)")
    
    print(f"\nMissing values in processed data:")
    missing = df_processed.isnull().sum()
    if missing.sum() == 0:
        print("  ✓ No missing values")
    else:
        print(missing[missing > 0].to_string())
    
    print(f"\nFeature distributions:")
    print(f"  Hard words:      {df_processed['is_hard_word'].mean():.1%}")
    print(f"  Slow responses:  {df_processed['is_slow_response'].mean():.1%}")
    print(f"  Rare words:      {df_processed['is_rare_word'].mean():.1%}")
    print(f"  Forgetting risk: {df_processed['forgetting_risk'].mean():.1%}")
    
    print(f"\nAccuracy by level gap:")
    accuracy_by_gap = df_processed.groupby('level_gap')['is_correct'].mean()
    for gap in sorted(accuracy_by_gap.index):
        print(f"  Gap {gap:+2d}: {accuracy_by_gap[gap]:.1%}")
    
    print("=" * 60)

# ============================================
# MAIN ETL PIPELINE
# ============================================

def main():
    print("=" * 60)
    print("ETL PIPELINE - English Learning Analytics")
    print("=" * 60)
    
    # 1. EXTRACT
    words_df, users_df, quiz_df_raw = extract_data()
    
    # 2. CLEAN
    quiz_df_clean = clean_data(quiz_df_raw.copy())
    
    # 3. TRANSFORM
    quiz_df_transformed = add_derived_features(quiz_df_clean, words_df, users_df)
    
    # 4. LOAD
    quiz_df_final = load_processed_data(quiz_df_transformed)
    
    # 5. QUALITY REPORT
    generate_quality_report(quiz_df_raw, quiz_df_final)
    
    print("\n✅ ETL pipeline completed successfully!")
    print(f"\nNext step: Analyze data in processed/quiz_results_clean.csv")

if __name__ == "__main__":
    main()
