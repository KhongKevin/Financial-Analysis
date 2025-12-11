from flask import Flask, jsonify, request
from flask_cors import CORS
from valuation import value_PE_avg, value_PE_min_max
from finance_plots import load_manual_eps, _get_price_history, _get_manual_eps_series
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend


@app.route('/api/value_pe_avg/<ticker>', methods=['GET'])
def get_value_pe_avg(ticker):
    """
    Get value_PE_avg score for a ticker.
    Query params: years (default 2), filename (default "EPS_manual.txt")
    """
    years = int(request.args.get('years', 2))
    filename = request.args.get('filename', 'EPS_manual.txt')
    
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
                'score_range': float(details['score_range'])
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
                  filename (default "EPS_manual.txt")
    """
    years = int(request.args.get('years', 5))
    source = request.args.get('source', 'manual')
    include_forward = request.args.get('include_forward', 'false').lower() == 'true'
    smoothing = int(request.args.get('smoothing', 0))
    filename = request.args.get('filename', 'EPS_manual.txt')
    
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
    filename = data.get('filename', 'EPS_manual.txt')
    
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
                    'score_range': float(details['score_range'])
                }
            })
        except Exception as e:
            results.append({
                'ticker': ticker,
                'success': False,
                'error': str(e)
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
    filename = data.get('filename', 'EPS_manual.txt')
    
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
                'price': price_data
            })
        except Exception as e:
            results.append({
                'ticker': ticker,
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'success': True,
        'results': results
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)

