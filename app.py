from flask import Flask, request, jsonify
import yfinance as yf
import os

app = Flask(__name__)

@app.route('/precio', methods=['GET'])
def obtener_precio():
    ticker = request.args.get('ticker')  # Captura el parámetro ?ticker=GOOGL

    if not ticker:
        return jsonify({'error': 'Debe proporcionar un ticker'}), 400

    try:
        data = yf.Ticker(ticker)
        precio = data.history(period='1d')['Close'].iloc[-1]
        return jsonify({
            'accion': ticker,
            'precio': round(precio, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
