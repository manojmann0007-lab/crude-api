from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from textblob import TextBlob

app = FastAPI()

# मोबाइल ऐप / ब्राउज़र से रिक्वेस्ट की अनुमति देने के लिए (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Crude Oil API is running successfully!"}

@app.get("/api/crude-signals")
def get_crude_signals():
    try:
        # 1. लाइव डेटा फ़ेच करना (WTI Crude Oil)
        wti = yf.download("CL=F", period="5d", interval="1h", progress=False)
        
        close = wti["Close"].squeeze()
        high = wti["High"].squeeze()
        low = wti["Low"].squeeze()
        
        cmp_price = round(float(close.iloc[-1]), 2)
        
        # 2. टेक्निकल इंडिकेटर्स (20 EMA & RSI)
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        
        # 3. पिवट प्वाइंट्स (Support & Resistance)
        prev_high = float(high.iloc[-2])
        prev_low = float(low.iloc[-2])
        prev_close = float(close.iloc[-2])
        pivot = (prev_high + prev_low + prev_close) / 3
        r1 = round((2 * pivot) - prev_low, 2)
        s1 = round((2 * pivot) - prev_high, 2)
        
        # 4. बुलिश / बेरिश / साइडवेज़ निर्णय लॉजिक
        if 45 <= rsi <= 55:
            trend = "SIDEWAYS"
            action = "रेंज-बाउंड मार्केट - ब्रेकआउट का इंतज़ार करें (No Trade Zone)"
            entry = "ब्रेकआउट पर"
            sl = "-"
            target = "-"
        elif cmp_price > ema20 and rsi > 55:
            trend = "BULLISH"
            action = "Buy on Dips (सपोर्ट के पास खरीदारी करें)"
            entry = f"${cmp_price}"
            sl = f"${s1}"
            target = f"${r1}"
        else:
            trend = "BEARISH"
            action = "Sell on Rallies (रेजिस्टेंस पर बिकवाली करें)"
            entry = f"${cmp_price}"
            sl = f"${r1}"
            target = f"${s1}"

        # 5. ग्लोबल न्यूज़ सेंटीमेंट
        headline = "EIA reports unexpected draw in US crude stockpiles; OPEC+ holds output policy."
        sentiment_score = TextBlob(headline).sentiment.polarity
        sentiment_label = "बुलिश (सकारात्मक)" if sentiment_score > 0.05 else ("बेरिश (नकारात्मक)" if sentiment_score < -0.05 else "न्यूट्रल")

        return {
            "status": "success",
            "cmp": cmp_price,
            "trend": trend,
            "action": action,
            "entry": entry,
            "sl": sl,
            "target": target,
            "rsi": round(rsi, 1),
            "ema20": round(ema20, 2),
            "news_headline": headline,
            "news_sentiment": sentiment_label
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
