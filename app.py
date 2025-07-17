from flask import Flask, request, jsonify
import yfinance as yf
import os
import pandas as pd
import ta

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


@app.route('/tasa', methods=['GET'])
def obtener_tasa():
    try:
        df = yf.download("USDCOP=X", period="7d", interval="5m")

        if df.empty:
            return jsonify({"error": "Sin datos"}), 400

        # Soporte para MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            valor = float(df[("Close", "USDCOP=X")].dropna().iloc[-1])
        else:
            valor = float(df["Close"].dropna().iloc[-1])

        return jsonify({
            "tasa": round(valor, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/rsi', methods=['GET'])
def calcular_rsi():
    ticker = request.args.get('ticker')
    if not ticker:
        return jsonify({'error': 'Ticker no proporcionado'}), 400

    try:
        data = yf.download(ticker, period="3mo", interval="1d")

        if data.empty:
            return jsonify({'error': 'No se encontraron datos para el ticker'}), 404

        # Manejo de MultiIndex si se descargaron múltiples tickers por error
        if isinstance(data.columns, pd.MultiIndex):
            close_prices = data[("Close", ticker)].dropna()
        else:
            close_prices = data["Close"].dropna()

        # Calcular RSI
        rsi = ta.momentum.RSIIndicator(close=close_prices, window=14).rsi()
        data["RSI"] = rsi

        ultimo_rsi = round(data["RSI"].iloc[-1], 2)
        estado = "neutral"
        if ultimo_rsi > 70:
            estado = "sobrecompra"
        elif ultimo_rsi < 30:
            estado = "sobreventa"

        return jsonify({
            'ticker': ticker,
            'rsi': ultimo_rsi,
            'estado': estado,
            'fecha': str(data.index[-1].date())
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
