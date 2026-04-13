import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib

def generate_player_stats(deliveries):
    # Batsman stats
    batsman_grouped = deliveries.groupby('striker')
    runs = batsman_grouped['runs_off_bat'].sum()
    balls = batsman_grouped['ball'].count()
    fours = deliveries[deliveries['runs_off_bat'] == 4].groupby('striker')['runs_off_bat'].count()
    sixes = deliveries[deliveries['runs_off_bat'] == 6].groupby('striker')['runs_off_bat'].count()
    
    batsman_stats = pd.DataFrame({'runs': runs, 'balls': balls, 'fours': fours, 'sixes': sixes}).fillna(0)
    batsman_stats['strike_rate'] = (batsman_stats['runs'] / batsman_stats['balls']) * 100
    
    # Bowler stats
    bowler_grouped = deliveries.groupby('bowler')
    runs_given = bowler_grouped['runs_off_bat'].sum() + bowler_grouped['wides'].sum() + bowler_grouped['noballs'].sum()
    valid_balls = bowler_grouped['ball'].count() - bowler_grouped['wides'].count() - bowler_grouped['noballs'].count()
    wickets = deliveries.dropna(subset=['wicket_type']).groupby('bowler')['wicket_type'].count()
    
    bowler_stats = pd.DataFrame({'runs_given': runs_given, 'balls_bowled': valid_balls, 'wickets': wickets}).fillna(0)
    bowler_stats['economy'] = (bowler_stats['runs_given'] / (bowler_stats['balls_bowled'] / 6))
    bowler_stats['average'] = (bowler_stats['runs_given'] / bowler_stats['wickets'].replace(0, np.nan)).fillna(0)
    
    return batsman_stats, bowler_stats

def prepare_win_predictor_data(matches, deliveries):
    # Only keep completed matches
    matches = matches[matches['outcome'].isna() | (matches['outcome'] == '') | (pd.isna(matches['outcome']))]
    
    # Calculate 1st innings total
    first_innings = deliveries[deliveries['innings'] == 1].groupby(['match_id', 'batting_team']).apply(
        lambda x: x['runs_off_bat'].sum() + x['extras'].sum()
    ).reset_index(name='target_score')
    
    # Merge target back
    df = deliveries[deliveries['innings'] == 2].merge(first_innings[['match_id', 'target_score']], on='match_id', how='inner')
    
    # Merge match winner
    df = df.merge(matches[['match_id', 'winner']], on='match_id', how='inner')
    
    # We will sample to make training faster if needed, but let's calculate rolling metrics
    # Sort by match and ball
    df = df.sort_values(by=['match_id', 'ball'])
    
    df['total_runs_delivery'] = df['runs_off_bat'] + df['extras']
    df['current_score'] = df.groupby('match_id')['total_runs_delivery'].cumsum()
    df['runs_left'] = df['target_score'] - df['current_score']
    # If runs_left < 0, handle it
    df['runs_left'] = df['runs_left'].apply(lambda x: 0 if x < 0 else x)
    
    df['is_wicket'] = df['wicket_type'].notna().astype(int)
    df['wickets_fallen'] = df.groupby('match_id')['is_wicket'].cumsum()
    df['wickets_left'] = 10 - df['wickets_fallen']
    
    # Ball calculation: ball format is over.ball (e.g. 0.1, 0.2 ... 19.6)
    # Let's approximate balls_bowled
    df['over'] = df['ball'].astype(int)
    df['ball_in_over'] = (df['ball'] - df['over']).round(1) * 10
    df['balls_bowled'] = (df['over'] * 6) + df['ball_in_over']
    df['balls_left'] = 120 - df['balls_bowled']
    df['balls_left'] = df['balls_left'].apply(lambda x: 1 if x <= 0 else x) # avoid div zero
    
    df['crr'] = (df['current_score'] * 6) / df['balls_bowled'].replace(0, 1)
    df['rrr'] = (df['runs_left'] * 6) / df['balls_left']
    
    df['result'] = (df['batting_team'] == df['winner']).astype(int)
    
    # Keep useful columns
    final_df = df[['batting_team', 'bowling_team', 'venue', 'runs_left', 'balls_left', 'wickets_left', 'target_score', 'crr', 'rrr', 'result']].dropna()
    return final_df

def train_win_predictor(df):
    print("Training Win Predictor...")
    # Encode categorical variables
    encoders = {}
    for col in ['batting_team', 'bowling_team', 'venue']:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le
        
    X = df.drop('result', axis=1)
    y = df['result']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=50, max_depth=10, n_jobs=-1, random_state=42)
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"Win Predictor Accuracy: {score:.4f}")
    
    # Save the model
    joblib.dump(model, 'win_predictor_model.pkl')
    joblib.dump(encoders, 'win_predictor_encoders.pkl')
    print("Model saved to win_predictor_model.pkl")

def train_auction_estimator(batsman_stats, bowler_stats):
    print("Training Auction Estimator...")
    try:
        auction_df = pd.read_csv('IPL_Sold_players_2013_23.csv')
        # Clean price (e.g. "50,00,000 ") -> 5000000
        auction_df['Price'] = auction_df['Price'].replace('[\", ]', '', regex=True).astype(float)
        # Clean names (strip whitespaces)
        auction_df['Name'] = auction_df['Name'].str.strip()
        
        # Merge player stats with auction data using Name as key.
        # We will use recent stats to estimate price. We simplify by merging generic stats.
        batsman_stats_stripped = batsman_stats.copy()
        batsman_stats_stripped.index = batsman_stats_stripped.index.str.strip()
        
        merged = auction_df.merge(batsman_stats_stripped, left_on='Name', right_index=True, how='inner')
        # Simple Model for batter prices
        if not merged.empty:
            X = merged[['runs', 'strike_rate', 'sixes']].fillna(0)
            y = merged['Price']
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            joblib.dump(model, 'auction_estimator_model.pkl')
            print(f"Auction Estimator trained and saved! (Trained on {len(merged)} players)")
        else:
            print("No matching players found for Auction Estimator.")
    except Exception as e:
        print(f"Error training auction estimator: {e}")

if __name__ == "__main__":
    print("Loading data...")
    matches = pd.read_csv('matches.csv')
    deliveries = pd.read_csv('deliveries.csv')
    
    # 1. Performance Index
    batsman_stats, bowler_stats = generate_player_stats(deliveries)
    batsman_stats.to_csv('batsman_stats.csv')
    bowler_stats.to_csv('bowler_stats.csv')
    print("Player stats generated and saved.")
    
    # 2. Win Predictor
    win_data = prepare_win_predictor_data(matches, deliveries)
    train_win_predictor(win_data)
    
    # 3. Auction Estimator
    train_auction_estimator(batsman_stats, bowler_stats)
    
    print("All tasks completed.")
