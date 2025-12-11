# Finance Dashboard Web Application

This is a React/JavaScript frontend with a Python/Flask backend for visualizing finance data, specifically P/E ratio valuations and charts.

## Features

1. **Value P/E Average Gauge**: Displays valuation scores as a half-dial gauge (0 on the left, 100 on the right)
   - Green fill shows the score value
   - Red fill shows the remaining portion
   
2. **P/E Ratio Charts**: Line graphs showing P/E ratios over time with price on a secondary axis
   - TTM P/E ratio
   - Forward P/E ratio (optional)
   - Stock price

## Project Structure

```
.
├── app.py                 # Flask backend API
├── requirements.txt       # Python dependencies
├── frontend/              # React frontend
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── App.css
│       └── components/
│           ├── ValueGauge.jsx
│           ├── ValueGauge.css
│           ├── PERatioChart.jsx
│           └── PERatioChart.css
├── valuation.py          # Existing valuation functions (maintained)
├── finance_plots.py      # Existing plotting functions (maintained)
├── EPS_manual.txt        # EPS data file
└── [other existing files] # All original files are preserved
```

## Setup Instructions

### Backend Setup (Flask)

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have `EPS_manual.txt` in the project root directory.

3. Start the Flask server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend Setup (React)

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## Usage

1. Start both the Flask backend and React frontend (in separate terminals)

2. Open your browser to `http://localhost:3000`

3. Enter comma-separated ticker symbols (e.g., "NFLX,AMD,GOOG,NVDA,INTC,AMZN")

4. Set the number of years for:
   - Valuation gauges (default: 2)
   - P/E ratio charts (default: 5)

5. Click "Load All" to fetch and display both gauges and charts

## API Endpoints

### GET `/api/value_pe_avg/<ticker>`
Get valuation score for a single ticker.
- Query params: `years` (default: 2), `filename` (default: "EPS_manual.txt")

### POST `/api/batch/value_pe_avg`
Get valuation scores for multiple tickers.
- Body: `{"tickers": ["AAPL", "NVDA"], "years": 2, "filename": "EPS_manual.txt"}`

### GET `/api/pe_ratios/<ticker>`
Get P/E ratio time series for a single ticker.
- Query params: `years`, `source`, `include_forward`, `smoothing`, `filename`

### POST `/api/batch/pe_ratios`
Get P/E ratio data for multiple tickers.
- Body: `{"tickers": [...], "years": 5, "source": "manual", "include_forward": true, ...}`

### GET `/api/health`
Health check endpoint.

## Original Files

All original Python files are preserved and can still be used independently:
- `distribute2.py` - Original analysis scripts
- `valuation.py` - Valuation functions
- `finance_plots.py` - Plotting functions
- `pe_comparison_visualizer.py` - P/E comparison visualizer

## Notes

- The backend uses the same calculation functions from `valuation.py` and `finance_plots.py`
- The frontend displays data fetched from the Flask API
- Both systems can be used independently - the web app doesn't modify any existing functionality

