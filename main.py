from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib

app = FastAPI(title="IPL Analytics Dashboard API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Models
try:
    win_model = joblib.load('win_predictor_model.pkl')
    win_encoders = joblib.load('win_predictor_encoders.pkl')
    auction_model = joblib.load('auction_estimator_model.pkl')
    batsman_stats = pd.read_csv('batsman_stats.csv')
    bowler_stats = pd.read_csv('bowler_stats.csv')
    
    # Pre-compute estimated values for all batsmen
    # Only keep players with > 100 runs to filter out tailenders, etc.
    top_batsmen = batsman_stats[batsman_stats['runs'] > 100].copy()
    X_bat = top_batsmen[['runs', 'strike_rate', 'sixes']].fillna(0)
    top_batsmen['estimated_value'] = auction_model.predict(X_bat)
    top_batsmen = top_batsmen.sort_values(by='estimated_value', ascending=False)

    top_bowlers = bowler_stats[bowler_stats['wickets'] > 5].copy()
    top_bowlers = top_bowlers.sort_values(by='wickets', ascending=False)
except Exception as e:
    print("Failed to load models. Ensure train_models.py has been run.")
    print(e)

class MatchState(BaseModel):
    batting_team: str
    bowling_team: str
    venue: str
    runs_left: float
    balls_left: float
    wickets_left: float
    target_score: float
    crr: float
    rrr: float

@app.get("/api/meta")
def get_meta():
    """Returns available teams and venues for the frontend dropdowns."""
    try:
        teams = list(win_encoders['batting_team'].classes_)
        venues = list(win_encoders['venue'].classes_)
        return {"teams": teams, "venues": venues}
    except:
        return {"teams": [], "venues": []}

@app.post("/api/predict")
def predict_win(state: MatchState):
    try:
        # Encode inputs
        bat_enc = win_encoders['batting_team'].transform([state.batting_team])[0]
        bowl_enc = win_encoders['bowling_team'].transform([state.bowling_team])[0]
        ven_enc = win_encoders['venue'].transform([state.venue])[0]
        
        # Prepare feature array: ['batting_team', 'bowling_team', 'venue', 'runs_left', 'balls_left', 'wickets_left', 'target_score', 'crr', 'rrr']
        features = np.array([[bat_enc, bowl_enc, ven_enc, state.runs_left, state.balls_left, state.wickets_left, state.target_score, state.crr, state.rrr]])
        
        # Predict probability
        probs = win_model.predict_proba(features)[0]
        
        # Output is typically [Prob Loss, Prob Win] based on classes
        # Let's find index of class '1' (Win)
        win_idx = list(win_model.classes_).index(1)
        win_prob = probs[win_idx] * 100
        loss_prob = 100 - win_prob
        
        return {
            "batting_team": state.batting_team,
            "bowling_team": state.bowling_team,
            "win_probability": round(win_prob, 2),
            "loss_probability": round(loss_prob, 2)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.get("/api/players/batsmen")
def get_top_batsmen(limit: int = 20):
    try:
        res = top_batsmen.head(limit).to_dict(orient='records')
        return res
    except:
        return []

@app.get("/api/players/bowlers")
def get_top_bowlers(limit: int = 20):
    try:
        res = top_bowlers.head(limit).to_dict(orient='records')
        return res
    except:
        return []

@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")

app.mount("/", StaticFiles(directory="frontend"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
