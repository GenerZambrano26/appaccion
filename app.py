from flask import Flask, request, jsonify
import yfinance as yf
import os
import pandas as pd
import ta
from ta.momentum import RSIIndicator

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

def calcular_macd(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    df['MACD'] = macd
    df['MACD_Signal'] = signal
    return df

def calcular_medias_moviles(df):
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    return df

def calcular_volumen(df):
    df['Volumen_Prom_20'] = df['Volume'].rolling(window=20).mean()
    return df

def calcular_rsi(df, ticker, window=14):
    if isinstance(df.columns, pd.MultiIndex):
        close_prices = df[("Close", ticker)].dropna()
    else:
        close_prices = df["Close"].dropna()

    rsi = RSIIndicator(close=close_prices, window=window).rsi()
    df["RSI"] = rsi
    return df

def obtener_datos_con_indicadores(ticker, periodo='6mo', intervalo='1d'):
    df = yf.download(ticker, period=periodo, interval=intervalo, progress=False, timeout=30)

    if df.empty:
        return None

    df = calcular_macd(df)
    df = calcular_medias_moviles(df)
    df = calcular_volumen(df)
    df = calcular_rsi(df, ticker)

    return df

@app.route('/analisis', methods=['GET'])
def analisis_indicadores():
    ticker = request.args.get('ticker')

    df = obtener_datos_con_indicadores(ticker)
    if df is None:
        return jsonify({"error": "No se pudieron obtener datos."}), 404

    # Última fila
    ultima = df.iloc[-1]

    # RSI
    rsi_valor = round(ultima["RSI"], 2)
    rsi_estado = "neutral"
    if rsi_valor > 70:
        rsi_estado = "sobrecompra"
    elif rsi_valor < 30:
        rsi_estado = "sobreventa"

    # MACD
    macd_valor = round(ultima["MACD"], 2)
    signal_valor = round(ultima["MACD_Signal"], 2)
    macd_estado = "compra" if macd_valor > signal_valor else "venta"

    # Medias Móviles
    sma50 = ultima["SMA_50"]
    sma200 = ultima["SMA_200"]
    ema20 = ultima["EMA_20"]
    precio = ultima["Close"]
    tendencia_estado = "alcista" if sma50 > sma200 else "bajista"

    # Volumen
    volumen_actual = ultima["Volume"]
    volumen_prom = ultima["Volumen_Prom_20"]
    if volumen_actual > volumen_prom * 1.2:
        volumen_estado = "volumen alto"
    elif volumen_actual < volumen_prom * 0.8:
        volumen_estado = "volumen bajo"
    else:
        volumen_estado = "normal"

    resultado = {
        "ticker": ticker.upper(),
        "fecha": str(df.index[-1].date()),
        "precio": round(precio, 2),
        "rsi": {
            "valor": rsi_valor,
            "estado": rsi_estado
        },
        "macd": {
            "valor": macd_valor,
            "signal": signal_valor,
            "estado": macd_estado
        },
        "tendencia": {
            "sma_50": round(sma50, 2),
            "sma_200": round(sma200, 2),
            "ema_20": round(ema20, 2),
            "estado": tendencia_estado
        },
        "volumen": {
            "actual": int(volumen_actual),
            "prom_20": int(volumen_prom),
            "estado": volumen_estado
        }
    }

    return jsonify(resultado)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
