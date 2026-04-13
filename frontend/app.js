// Initialize Icons
lucide.createIcons();

const API_BASE = '';

// Global State
let matchMeta = { teams: [], venues: [] };

// Elements
const battingTeamSelect = document.getElementById('batting-team');
const bowlingTeamSelect = document.getElementById('bowling-team');
const venueSelect = document.getElementById('venue');

// Inputs
const targetInput = document.getElementById('target');
const currentScoreInput = document.getElementById('current_score');
const oversBowledInput = document.getElementById('overs_bowled');
const wicketsDownInput = document.getElementById('wickets_down');

// Outputs
const runsNeededEl = document.getElementById('runs_needed');
const ballsLeftEl = document.getElementById('balls_left');
const rrrEl = document.getElementById('rrr');
const crrEl = document.getElementById('crr');
const winFill = document.getElementById('win-fill');
const lossFill = document.getElementById('loss-fill');
const winPercEl = document.getElementById('win-perc');
const lossPercEl = document.getElementById('loss-perc');
const batTeamLabel = document.getElementById('bat-team-label');
const bowlTeamLabel = document.getElementById('bowl-team-label');

const predictBtn = document.getElementById('predict-btn');

async function init() {
    await fetchMeta();
    await fetchPlayers();
    setupTabs();
    
    // Set default calculation once meta is loaded
    if (matchMeta.teams.length > 0) {
        calculateAndPredict();
    }
}

async function fetchMeta() {
    try {
        const res = await fetch(`${API_BASE}/api/meta`);
        const data = await res.json();
        matchMeta = data;
        
        populateDropdown(battingTeamSelect, data.teams, 'Chennai Super Kings');
        populateDropdown(bowlingTeamSelect, data.teams, 'Mumbai Indians');
        populateDropdown(venueSelect, data.venues, data.venues[0]);
    } catch (e) {
        console.error("Failed to fetch meta", e);
    }
}

function populateDropdown(selectElement, items, defaultVal) {
    selectElement.innerHTML = '';
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        if (item === defaultVal) opt.selected = true;
        selectElement.appendChild(opt);
    });
}

// Calculate logic based on user inputs
function computeMatchState() {
    const target = parseFloat(targetInput.value) || 0;
    const currentScore = parseFloat(currentScoreInput.value) || 0;
    
    // Parse overs format (e.g. 10.3 means 10 overs, 3 balls)
    const oversText = oversBowledInput.value.toString();
    let overs = 0, balls = 0;
    if (oversText.includes('.')) {
        const parts = oversText.split('.');
        overs = parseInt(parts[0]);
        balls = parseInt(parts[1]);
        if (balls > 5) balls = 5; // clamp
    } else {
        overs = parseInt(oversText);
    }
    
    const ballsBowled = (overs * 6) + balls;
    const ballsLeft = 120 - ballsBowled;
    const runsLeft = target - currentScore;
    const wicketsLeft = 10 - (parseInt(wicketsDownInput.value) || 0);
    
    const crr = ballsBowled > 0 ? (currentScore * 6) / ballsBowled : 0;
    const rrr = ballsLeft > 0 ? (runsLeft * 6) / ballsLeft : 0;
    
    return { target, runsLeft, ballsLeft, wicketsLeft, crr, rrr, ballsBowled, currentScore };
}

function updateMetricUI(state) {
    runsNeededEl.textContent = state.runsLeft > 0 ? state.runsLeft : 0;
    ballsLeftEl.textContent = state.ballsLeft > 0 ? state.ballsLeft : 0;
    crrEl.textContent = state.crr.toFixed(2);
    rrrEl.textContent = state.rrr.toFixed(2);
    
    batTeamLabel.textContent = battingTeamSelect.value;
    bowlTeamLabel.textContent = bowlingTeamSelect.value;
}

async function calculateAndPredict() {
    const state = computeMatchState();
    updateMetricUI(state);
    
    predictBtn.textContent = 'Calculating...';
    predictBtn.disabled = true;
    
    try {
        const payload = {
            batting_team: battingTeamSelect.value,
            bowling_team: bowlingTeamSelect.value,
            venue: venueSelect.value,
            runs_left: state.runsLeft,
            balls_left: state.ballsLeft,
            wickets_left: state.wicketsLeft,
            target_score: state.target,
            crr: state.crr,
            rrr: state.rrr
        };
        
        const res = await fetch(`${API_BASE}/api/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            const data = await res.json();
            const winP = data.win_probability;
            const lossP = data.loss_probability;
            
            winFill.style.width = `${winP}%`;
            winPercEl.textContent = `${winP}%`;
            lossPercEl.textContent = `${lossP}%`;
        }
    } catch (e) {
        console.error("Prediction Error", e);
    } finally {
        predictBtn.textContent = 'Calculate Probability';
        predictBtn.disabled = false;
    }
}

predictBtn.addEventListener('click', calculateAndPredict);

// Player Tables
async function fetchPlayers() {
    try {
        const batRes = await fetch(`${API_BASE}/api/players/batsmen?limit=10`);
        const batsmen = await batRes.json();
        
        const tbodyBat = document.getElementById('batsmen-tbody');
        tbodyBat.innerHTML = batsmen.map(p => `
            <tr>
                <td><strong>${p.striker}</strong></td>
                <td>${p.runs}</td>
                <td>${p.strike_rate.toFixed(2)}</td>
                <td>${p.sixes}</td>
                <td style="color:var(--win-green)">${p.estimated_value ? '₹'+p.estimated_value.toLocaleString(undefined, {maximumFractionDigits:0}) : 'N/A'}</td>
            </tr>
        `).join('');
        
        const bowlRes = await fetch(`${API_BASE}/api/players/bowlers?limit=10`);
        const bowlers = await bowlRes.json();
        
        const tbodyBowl = document.getElementById('bowlers-tbody');
        tbodyBowl.innerHTML = bowlers.map(p => `
            <tr>
                <td><strong>${p.bowler}</strong></td>
                <td>${p.wickets}</td>
                <td>${p.economy.toFixed(2)}</td>
                <td>${p.average.toFixed(2)}</td>
            </tr>
        `).join('');
        
    } catch (e) {
        console.error("Error fetching players", e);
    }
}

// Tabs
function setupTabs() {
    const btns = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            contents.forEach(c => c.style.display = 'none');
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.target).style.display = 'block';
        });
    });
}

// Start
init();
