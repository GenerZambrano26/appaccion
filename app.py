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

def calcular_rsi(df, periodo=14):
    delta = df["Close"].diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)

    media_ganancia = ganancia.rolling(window=periodo).mean()
    media_perdida = perdida.rolling(window=periodo).mean()

    rs = media_ganancia / media_perdida
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_macd(df, rapida=12, lenta=26, señal=9):
    ema_rapida = df["Close"].ewm(span=rapida, adjust=False).mean()
    ema_lenta = df["Close"].ewm(span=lenta, adjust=False).mean()
    macd = ema_rapida - ema_lenta
    señal_macd = macd.ewm(span=señal, adjust=False).mean()
    return macd, señal_macd

def calcular_sma(df, periodo=50):
    return df["Close"].rolling(window=periodo).mean()

def calcular_ema(df, periodo=20):
    return df["Close"].ewm(span=periodo, adjust=False).mean()

@app.route('/analisis', methods=['GET'])
def analisis_indicadores():
    ticker = request.args.get('ticker')
    df = yf.download(ticker, period="6mo", interval="1d")
    if df.empty:
        return jsonify({"error": "No se pudo obtener datos del ticker."}), 400

    # Indicadores técnicos
    df["RSI"] = calcular_rsi(df)
    df["MACD"], df["Señal_MACD"] = calcular_macd(df)
    df["SMA_50"] = calcular_sma(df, 50)
    df["SMA_200"] = calcular_sma(df, 200)
    df["EMA_20"] = calcular_ema(df, 20)

    # Volumen promedio
    df["Volumen_promedio_20"] = df["Volume"].rolling(window=20).mean()

    # Bandas de Bollinger
    df['Media_BB'] = df['Close'].rolling(window=20).mean()
    df['Desviacion_BB'] = df['Close'].rolling(window=20).std()
    df['Banda_Superior'] = df['Media_BB'] + (2 * df['Desviacion_BB'])
    df['Banda_Inferior'] = df['Media_BB'] - (2 * df['Desviacion_BB'])

    ult = df.iloc[-1]

    rsi_valor = df["RSI"].iloc[-1]
    rsi_eval = ""
    if pd.isna(rsi_valor):
        rsi_eval = "RSI no disponible"
    elif rsi_valor < 30:
        rsi_eval = f"RSI: {rsi_valor:.2f} - Sobrevendido"
    elif rsi_valor > 70:
        rsi_eval = f"RSI: {rsi_valor:.2f} - Sobrecomprado"
    else:
        rsi_eval = f"RSI: {rsi_valor:.2f} - Neutro"

    # MACD Evaluación
    macd_valor = df["MACD"].iloc[-1]
    señal_macd_valor = df["Señal_MACD"].iloc[-1]
    if pd.isna(macd_valor) or pd.isna(señal_macd_valor):
        macd_eval = "MACD no disponible"
    elif macd_valor > señal_macd_valor:
        macd_eval = "Señal de compra"
    else:
        macd_eval = "Señal de venta"

   
    # Medias móviles
    sma_50 = df["SMA_50"].iloc[-1]
    sma_200 = df["SMA_200"].iloc[-1]
    ema_20 = df["EMA_20"].iloc[-1]
    precio_actual = df["Close"].iloc[-1]

    sma_50_eval = (
        " Precio > SMA 50" if precio_actual > sma_50 else " Bajo Precio < SMA 50"
    )
    sma_200_eval = (
        " Precio > SMA 200" if precio_actual > sma_200 else " Bajo Precio < SMA 200"
    )
    ema_20_eval = (
        " Precio > EMA 20" if precio_actual > ema_20 else " Bajo Precio < EMA 20"
    )

    # Volumen
    volumen_actual = df["Volume"].iloc[-1]
    volumen_prom_20 = df["Volumen_promedio_20"].iloc[-1]
    volumen_eval = "Volumen alto" if volumen_actual > volumen_prom_20 else "Volumen bajo"

    # Bandas de Bollinger
    banda_sup = df['Banda_Superior'].iloc[-1]
    banda_inf = df['Banda_Inferior'].iloc[-1]
    bollinger_eval = "En banda" if banda_inf <= precio_actual <= banda_sup else ("Sobrecomprado (fuera banda sup)" if precio_actual > banda_sup else "Sobrevendido (fuera banda inf)")

    # Recomendación general
    score = 0
    motivos = []

    if precio_actual > ema_20:
        score += 1
        motivos.append("Precio por encima de EMA 20")
    if precio_actual > sma_50:
        score += 1
        motivos.append("Precio por encima de SMA 50")
    if precio_actual > sma_200:
        score += 1
        motivos.append("Precio por encima de SMA 200")
    if macd_valor > señal_macd_valor:
        score += 1
        motivos.append("MACD cruzando hacia arriba")
    if rsi_valor < 30:
        score += 1
        motivos.append("RSI en sobreventa")
    if volumen_actual > volumen_prom_20:
        score += 1
        motivos.append("Volumen por encima del promedio")

    if score >= 4:
        recomendacion = "Comprar"
    elif score <= 2:
        recomendacion = "Vender"
    else:
        recomendacion = "Esperar"

    resumen = {
        "Ticker": ticker.upper(),
        "Fecha": str(ult.name.date()),
        "Precio": round(precio_actual, 2),
        "RSI": round(rsi_valor, 2) if not pd.isna(rsi_valor) else "N/D",
        "Evaluación RSI": rsi_eval,
        "MACD": round(macd_valor, 4) if not pd.isna(macd_valor) else "N/D",
        "Señal MACD": round(señal_macd_valor, 4) if not pd.isna(señal_macd_valor) else "N/D",
        "Evaluación MACD": macd_eval,
        "SMA 50": round(sma_50, 2) if not pd.isna(sma_50) else "N/D",
        "SMA 200": round(sma_200, 2) if not pd.isna(sma_200) else "N/D",
        "EMA 20": round(ema_20, 2) if not pd.isna(ema_20) else "N/D",
        "Volumen actual": int(volumen_actual),
        "Volumen promedio 20": round(volumen_prom_20, 2) if not pd.isna(volumen_prom_20) else "N/D",
        "Evaluación Volumen": volumen_eval,
        "Evaluación SMA 50": sma_50_eval,
        "Evaluación SMA 200": sma_200_eval,
        "Evaluación EMA 20": ema_20_eval,
        "Banda Superior BB": round(banda_sup, 2),
        "Banda Inferior BB": round(banda_inf, 2),
        "Evaluación Bollinger": bollinger_eval,
        "Recomendación general": recomendacion,
        "Motivo": "; ".join(motivos) if motivos else "No se cumplen condiciones claras."
    }

    return jsonify(resumen)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
