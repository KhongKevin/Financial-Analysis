from flask import Flask, jsonify, request
from flask_cors import CORS
from valuation import value_PE_min_max, value_PE_avg, score_debt_to_equity, score_peg
from finance_plots import load_manual_eps, _get_price_history, _get_manual_eps_series
from scraper import fetch_eps_data, append_to_file, fetch_balance_sheet
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json


app = Flask(__name__)
# Force reload
CORS(app)  # Enable CORS for React frontend

@app.route('/api/fetch_eps/<ticker>', methods=['POST'])
def fetch_eps_route(ticker):
    """
    Endpoint to trigger manual fetch of EPS data.
    """
    try:
        data, warning = fetch_eps_data(ticker)
        if data is None:
            return jsonify({'success': False, 'error': warning}), 400
        
        # Append to file
        success, msg = append_to_file(ticker, data, filename="DATA/EPS_manual.txt")
        if not success:
            return jsonify({'success': False, 'error': msg}), 500
        
        response = {'success': True, 'message': f'Successfully fetched EPS for {ticker}'}
        if warning:
            response['warning'] = warning
            
        return jsonify(response)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fetch_balance/<ticker>', methods=['POST'])
def fetch_balance_route(ticker):
    """
    Endpoint to trigger manual fetch of Balance Sheet data.
    """
    try:
        data, error = fetch_balance_sheet(ticker)
        if data is None:
            return jsonify({'success': False, 'error': error}), 400
        
        # Append to Balance_manual.txt
        success, msg = append_to_file(ticker, data, filename="DATA/Balance_manual.txt")
        if not success:
            return jsonify({'success': False, 'error': msg}), 500
            
        return jsonify({'success': True, 'message': f'Successfully fetched Balance Sheet for {ticker}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batch/debt_to_equity', methods=['POST'])
def batch_debt_to_equity():
    """
    Get debt_to_equity score for multiple tickers.
    """
    data = request.get_json()
    tickers = data.get('tickers', [])
    years = int(data.get('years', 2))
    filename = data.get('filename', 'DATA/Balance_manual.txt')
    
    results = []
    for ticker in tickers:
        try:
            score, details = score_debt_to_equity(ticker, filename=filename)
            results.append({
                'ticker': ticker,
                'success': True,
                'score': score,
                'score_100': score * 100,
                'details': {
                    'current_ratio': float(details['current_ratio']),
                    'total_debt': float(details['total_debt']),
                    'total_equity': float(details['total_equity']),
                    'date': details['date'],
                    'score': float(details['score']),
                    'data_gaps': details.get('data_gaps', [])
                }
            })
        except Exception as e:
            err_msg = str(e)
            code = 'MISSING_DATA' if "not found in" in err_msg else 'UNKNOWN'
            results.append({
                'ticker': ticker,
                'success': False,
                'error': err_msg,
                'error_code': code
            })
    
    return jsonify({
        'success': True,
        'results': results
    })


@app.route('/api/value_pe_avg/<ticker>', methods=['GET'])
def get_value_pe_avg(ticker):
    """
    Get value_PE_avg score for a ticker.
    Query params: years (default 2), filename (default "EPS_manual.txt")
    """
    years = int(request.args.get('years', 2))
    filename = request.args.get('filename', 'DATA/EPS_manual.txt')
    
    try:
        score, details = value_PE_avg(ticker, years=years, filename=filename)
        # Convert score (0-1) to 0-100 for display
        score_100 = score * 100
        
        return jsonify({
            'success': True,
            'ticker': ticker,
            'score': score,
            'score_100': score_100,
            'details': {
                'current_pe': float(details['current_pe']),
                'avg_pe': float(details['avg_pe']),
                'min_pe': float(details['min_pe']),
                'max_pe': float(details['max_pe']),
                'score_avg': float(details['score_avg']),
                'score_range': float(details['score_range']),
                'data_gaps': details.get('data_gaps', [])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/pe_ratios/<ticker>', methods=['GET'])
def get_pe_ratios(ticker):
    """
    Get P/E ratio time series data for a ticker.
    Query params: years (default 5), source (default "manual"), 
                  include_forward (default false), smoothing (default 0),
                  filename (default "DATA/EPS_manual.txt")
    """
    years = int(request.args.get('years', 5))
    source = request.args.get('source', 'manual')
    include_forward = request.args.get('include_forward', 'false').lower() == 'true'
    smoothing = int(request.args.get('smoothing', 0))
    filename = request.args.get('filename', 'DATA/EPS_manual.txt')
    
    try:
        # Auto source not available with Stooq
        if source == 'auto':
            return jsonify({
                'success': False,
                'error': 'Auto EPS source not available with Stooq. Use "manual" source.'
            }), 400
        
        hist = _get_price_history(ticker, years)
        
        if hist.empty:
            return jsonify({
                'success': False,
                'error': f'No price data for {ticker}'
            }), 400
        
        # Get EPS data (manual only)
        if source == 'manual':
            manual_eps_by_ticker = load_manual_eps(filename)
            ttm_eps_series = _get_manual_eps_series(ticker, hist.index, manual_eps_by_ticker, compute_ttm=True)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown source: {source}'
            }), 400
        
        # Calculate P/E ratios
        pe_ttm = hist['Close'] / ttm_eps_series
        pe_ttm.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        pe_forward = None
        if include_forward:
            # Forward P/E not available with Stooq
            pass
        
        # Apply smoothing if requested
        if smoothing and smoothing > 1:
            pe_ttm = pe_ttm.rolling(window=smoothing, min_periods=1).mean()
            price_series = hist['Close'].rolling(window=smoothing, min_periods=1).mean()
            if pe_forward is not None:
                pe_forward = pe_forward.rolling(window=smoothing, min_periods=1).mean()
        else:
            price_series = hist['Close']
        
        # Prepare data for JSON response
        dates = [d.isoformat() for d in hist.index]
        
        pe_ttm_data = []
        for date, value in zip(dates, pe_ttm.values):
            if pd.notna(value):
                pe_ttm_data.append({'date': date, 'value': float(value)})
        
        pe_forward_data = []
        if pe_forward is not None:
            for date, value in zip(dates, pe_forward.values):
                if pd.notna(value):
                    pe_forward_data.append({'date': date, 'value': float(value)})
        
        price_data = [{'date': date, 'value': float(val)} for date, val in zip(dates, price_series.values)]
        
        return jsonify({
            'success': True,
            'ticker': ticker,
            'pe_ttm': pe_ttm_data,
            'pe_forward': pe_forward_data if pe_forward_data else None,
            'price': price_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/batch/value_pe_avg', methods=['POST'])
def batch_value_pe_avg():
    """
    Get value_PE_avg for multiple tickers.
    Body: {"tickers": ["AAPL", "NVDA"], "years": 2, "filename": "EPS_manual.txt"}
    """
    data = request.get_json()
    tickers = data.get('tickers', [])
    years = data.get('years', 2)
    filename = data.get('filename', 'DATA/EPS_manual.txt')
    
    results = []
    for ticker in tickers:
        try:
            score, details = value_PE_avg(ticker, years=years, filename=filename)
            score_100 = score * 100
            results.append({
                'ticker': ticker,
                'success': True,
                'score': score,
                'score_100': score_100,
                'details': {
                    'current_pe': float(details['current_pe']),
                    'avg_pe': float(details['avg_pe']),
                    'min_pe': float(details['min_pe']),
                    'max_pe': float(details['max_pe']),
                    'score_avg': float(details['score_avg']),
                    'score_range': float(details['score_range']),
                    'data_points': int(details['data_points']),
                    'data_gaps': details.get('data_gaps', [])
                }
            })
        except Exception as e:
            err_msg = str(e)
            code = 'MISSING_DATA' if "not found in" in err_msg else 'UNKNOWN'
            results.append({
                'ticker': ticker,
                'success': False,
                'error': err_msg,
                'error_code': code
            })
    
    return jsonify({
        'success': True,
        'results': results
    })


@app.route('/api/batch/pe_ratios', methods=['POST'])
def batch_pe_ratios():
    """
    Get P/E ratio data for multiple tickers.
    Body: {"tickers": ["AAPL", "NVDA"], "years": 5, "source": "manual", ...}
    """
    data = request.get_json()
    tickers = data.get('tickers', [])
    years = data.get('years', 5)
    source = data.get('source', 'manual')
    include_forward = data.get('include_forward', False)
    smoothing = data.get('smoothing', 0)
    filename = data.get('filename', 'DATA/EPS_manual.txt')
    
    results = []
    for ticker in tickers:
        try:
            # Auto source not available with Stooq
            if source == 'auto':
                results.append({
                    'ticker': ticker,
                    'success': False,
                    'error': 'Auto EPS source not available with Stooq. Use "manual" source.'
                })
                continue
            
            hist = _get_price_history(ticker, years)
            
            if hist.empty:
                results.append({
                    'ticker': ticker,
                    'success': False,
                    'error': f'No price data for {ticker}'
                })
                continue
            
            if source == 'manual':
                manual_eps_by_ticker = load_manual_eps(filename)
                ttm_eps_series = _get_manual_eps_series(ticker, hist.index, manual_eps_by_ticker, compute_ttm=True)
            else:
                results.append({
                    'ticker': ticker,
                    'success': False,
                    'error': f'Unknown source: {source}'
                })
                continue
            
            pe_ttm = hist['Close'] / ttm_eps_series
            pe_ttm.replace([np.inf, -np.inf], np.nan, inplace=True)
            
            pe_forward = None
            if include_forward:
                # Forward P/E not available with Stooq
                pass
            
            if smoothing and smoothing > 1:
                pe_ttm = pe_ttm.rolling(window=smoothing, min_periods=1).mean()
                price_series = hist['Close'].rolling(window=smoothing, min_periods=1).mean()
                if pe_forward is not None:
                    pe_forward = pe_forward.rolling(window=smoothing, min_periods=1).mean()
            else:
                price_series = hist['Close']
            
            dates = [d.isoformat() for d in hist.index]
            
            pe_ttm_data = []
            for date, value in zip(dates, pe_ttm.values):
                if pd.notna(value):
                    pe_ttm_data.append({'date': date, 'value': float(value)})
            
            pe_forward_data = []
            if pe_forward is not None:
                for date, value in zip(dates, pe_forward.values):
                    if pd.notna(value):
                        pe_forward_data.append({'date': date, 'value': float(value)})
            
            price_data = [{'date': date, 'value': float(val)} for date, val in zip(dates, price_series.values)]
            
            results.append({
                'ticker': ticker,
                'success': True,
                'pe_ttm': pe_ttm_data,
                'pe_forward': pe_forward_data if pe_forward_data else None,
                'price': price_data,
                'data_points': len(pe_ttm_data)
            })
        except Exception as e:
            err_msg = str(e)
            code = 'MISSING_DATA' if "not found in" in err_msg else 'UNKNOWN'
            results.append({
                'ticker': ticker,
                'success': False,
                'error': err_msg,
                'error_code': code
            })
    
    return jsonify({
        'success': True,
        'results': results
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


@app.route('/api/batch/peg_ratio', methods=['POST'])
def batch_peg_ratio():
    """
    Get PEG score for multiple tickers.
    Body: {"tickers": ["AAPL", "NVDA"], "filename": "EPS_manual.txt"}
    """
    data = request.get_json()
    tickers = data.get('tickers', [])
    filename = data.get('filename', 'DATA/EPS_manual.txt')
    years = int(data.get('years', 3)) # Default to 3 years for growth calc
    
    results = []
    for ticker in tickers:
        try:
            score, details = score_peg(ticker, years=years, filename=filename)
            results.append({
                'ticker': ticker,
                'success': True,
                'score': score,
                'score_100': score * 100,
                'details': {
                    'peg': float(details.get('peg', 999.0)),
                    'pe': float(details.get('pe', 999.0)),
                    'growth_rate': float(details.get('growth_rate', 0.0)),
                    'r_squared': float(details.get('r_squared', 0.0)),
                    'data_points': int(details.get('data_points', 0)),
                    'score': float(details.get('score', 0.0)),
                    'data_gaps': details.get('data_gaps', []),
                    'error': details.get('error')
                }
            })
        except Exception as e:
            err_msg = str(e)
            code = 'MISSING_DATA' if "not found in" in err_msg or "No price data" in err_msg or "No EPS data" in err_msg else 'UNKNOWN'
            results.append({
                'ticker': ticker,
                'success': False,
                'error': err_msg,
                'error_code': code
            })
    
    return jsonify({
        'success': True,
        'results': results
    })


@app.route('/api/batch/live_price', methods=['POST'])
def batch_live_price():
    """
    Fetch current price and daily change for multiple tickers via Yahoo Finance.
    """
    import urllib.request, json
    data = request.get_json()
    tickers = data.get('tickers', [])
    results = []

    for ticker in tickers:
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
            hdr = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=hdr)

            with urllib.request.urlopen(req, timeout=10) as response:
                resp_data = json.loads(response.read().decode('utf-8'))

            chart_res = resp_data.get('chart', {}).get('result', [])
            if not chart_res:
                raise ValueError("No chart result")

            meta = chart_res[0].get('meta', {})
            current_price = meta.get('regularMarketPrice', 0)

            # Get the previous trading day's close from the daily close array
            closes = chart_res[0]['indicators']['quote'][0].get('close', [])
            # Filter out None values
            valid_closes = [c for c in closes if c is not None]
            if len(valid_closes) >= 2:
                previous_close = valid_closes[-2]
            else:
                previous_close = current_price  # fallback: no change

            change = current_price - previous_close
            change_pct = (change / previous_close * 100) if previous_close else 0

            results.append({
                'ticker': ticker,
                'success': True,
                'price': round(current_price, 2),
                'previous_close': round(previous_close, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2)
            })
        except Exception as e:
            results.append({
                'ticker': ticker,
                'success': False,
                'error': str(e)
            })

    return jsonify({'success': True, 'results': results})


SETS_FILE = 'DATA/sets.json'

def load_sets():
    if not os.path.exists(SETS_FILE):
        return {}
    try:
        with open(SETS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_sets(data):
    os.makedirs('DATA', exist_ok=True)
    with open(SETS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/api/sets', methods=['GET'])
def get_sets():
    user_id = request.args.get('userId', 'default_user')
    sets = load_sets()
    user_sets = sets.get(user_id, {})
    return jsonify({'success': True, 'sets': user_sets})

@app.route('/api/sets', methods=['POST'])
def save_set():
    data = request.get_json()
    user_id = data.get('userId', 'default_user')
    set_name = data.get('setName')
    tickers = data.get('tickers', [])
    
    if not set_name:
        return jsonify({'success': False, 'error': 'Set name is required'}), 400
        
    sets = load_sets()
    if user_id not in sets:
        sets[user_id] = {}
        
    sets[user_id][set_name] = tickers
    save_sets(sets)
    
    return jsonify({'success': True, 'sets': sets[user_id]})

@app.route('/api/sets/<set_name>', methods=['DELETE'])
def delete_set(set_name):
    user_id = request.args.get('userId', 'default_user')
    
    sets = load_sets()
    if user_id in sets and set_name in sets[user_id]:
        del sets[user_id][set_name]
        save_sets(sets)
        return jsonify({'success': True, 'sets': sets[user_id]})
    
    return jsonify({'success': False, 'error': 'Set not found'}), 404


# ──────────────────────────────────────────────────────────────────────────────
# Backtest Endpoints
# ──────────────────────────────────────────────────────────────────────────────

SNAPSHOTS_FILE = 'DATA/backtest_snapshots.json'

def load_snapshots():
    if not os.path.exists(SNAPSHOTS_FILE):
        return []
    try:
        with open(SNAPSHOTS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_snapshots(data):
    os.makedirs('DATA', exist_ok=True)
    with open(SNAPSHOTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@app.route('/api/backtest/run', methods=['POST'])
def backtest_run():
    """
    Run a backtest.
    Body: {
        tickers: ["AAPL", ...],
        start_date: "2022-01-01",
        lookback_years: 2,
        forward_months: 12,
        weight_sets: [{name, pe, peg, debt}, ...]
    }
    """
    try:
        from backtest import run_backtest
        data = request.get_json()

        tickers = data.get('tickers', [])
        start_date = data.get('start_date', '')
        lookback_years = int(data.get('lookback_years', 2))
        forward_months = int(data.get('forward_months', 12))
        weight_sets = data.get('weight_sets', [{'name': 'Default', 'pe': 70, 'peg': 20, 'debt': 10}])

        if not tickers:
            return jsonify({'success': False, 'error': 'No tickers provided'}), 400
        if not start_date:
            return jsonify({'success': False, 'error': 'start_date is required'}), 400

        result = run_backtest(
            tickers=tickers,
            start_date=start_date,
            lookback_years=lookback_years,
            forward_months=forward_months,
            weight_sets=weight_sets,
        )

        return jsonify({'success': True, **result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backtest/snapshots', methods=['GET'])
def get_snapshots():
    snapshots = load_snapshots()
    return jsonify({'success': True, 'snapshots': snapshots})


@app.route('/api/backtest/snapshots', methods=['POST'])
def save_snapshot():
    """
    Save a backtest snapshot.
    Body: { name, config, results, summary, weight_sets, as_of_date, lookback_years, forward_months }
    """
    try:
        data = request.get_json()
        name = data.get('name', 'Untitled')

        snapshots = load_snapshots()
        snapshot_id = str(int(datetime.now().timestamp() * 1000))

        snapshot = {
            'id': snapshot_id,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'as_of_date': data.get('as_of_date'),
            'lookback_years': data.get('lookback_years'),
            'forward_months': data.get('forward_months'),
            'tickers': data.get('tickers', []),
            'weight_sets': data.get('weight_sets', []),
            'results': data.get('results', []),
            'summary': data.get('summary', []),
        }

        snapshots.append(snapshot)
        save_snapshots(snapshots)

        return jsonify({'success': True, 'snapshot': snapshot, 'snapshots': snapshots})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backtest/snapshots/<snapshot_id>', methods=['DELETE'])
def delete_snapshot(snapshot_id):
    snapshots = load_snapshots()
    snapshots = [s for s in snapshots if s['id'] != snapshot_id]
    save_snapshots(snapshots)
    return jsonify({'success': True, 'snapshots': snapshots})


if __name__ == '__main__':
    app.run(debug=True, port=5000)


