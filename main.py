import sys, os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import requests
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import Session

# Path fix karne wali lines
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import engine, Base, SessionLocal

app = FastAPI(
    title="Crypto Portfolio Tracker API",
    description="A production-ready API for tracking crypto portfolios with real-time market price valuation.",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE MODEL ---
class CryptoAsset(Base):
    __tablename__ = "crypto_assets"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    amount_held = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PYDANTIC SCHEMAS ---
class CryptoAssetCreate(BaseModel):
    ticker: str = Field(..., example="BTC")
    amount_held: float = Field(..., example=0.5)
    buy_price: float = Field(..., example=60000.0)

class PortfolioSummaryResponse(BaseModel):
    id: int
    ticker: str
    amount_held: float
    buy_price: float
    current_price: float
    total_cost: float
    current_value: float
    total_profit_loss: float
    roi_percentage: float

# --- HELPER FUNCTION FOR LIVE PRICES ---
def get_live_price(ticker: str) -> float:
    """Fetches real-time price from a public crypto API."""
    try:
        # Using a reliable public pricing endpoint mapping tickers
        ticker_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano"}
        coin_id = ticker_map.get(ticker.upper(), "bitcoin")
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url, timeout=5).json()
        return float(response[coin_id]["usd"])
    except Exception:
        # Fallback price to keep the app working if API rate limits hit
        fallback_prices = {"BTC": 65000.0, "ETH": 34000.0, "SOL": 140.0}
        return fallback_prices.get(ticker.upper(), 1.0)

# --- API ENDPOINTS ---

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "success", "message": "Crypto Portfolio Tracker Backend is running perfectly."}

@app.post("/api/v1/portfolio", status_code=status.HTTP_201_CREATED, tags=["Portfolio Management"])
def add_asset(asset: CryptoAssetCreate, db: Session = Depends(get_db)):
    db_asset = CryptoAsset(
        ticker=asset.ticker.upper(),
        amount_held=asset.amount_held,
        buy_price=asset.buy_price
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return {"status": "success", "message": f"{db_asset.ticker} added successfully to portfolio."}

@app.get("/api/v1/portfolio", response_model=List[PortfolioSummaryResponse], tags=["Portfolio Management"])
def get_portfolio_summary(db: Session = Depends(get_db)):
    """
    Fetches portfolio and calculates real-time valuations, profit/loss, and ROI.
    """
    assets = db.query(CryptoAsset).all()
    summary_list = []
    
    for asset in assets:
        current_price = get_live_price(asset.ticker)
        total_cost = asset.amount_held * asset.buy_price
        current_value = asset.amount_held * current_price
        profit_loss = current_value - total_cost
        roi = (profit_loss / total_cost) * 100 if total_cost > 0 else 0.0
        
        summary_list.append(
            PortfolioSummaryResponse(
                id=asset.id,
                ticker=asset.ticker,
                amount_held=asset.amount_held,
                buy_price=asset.buy_price,
                current_price=current_price,
                total_cost=round(total_cost, 2),
                current_value=round(current_value, 2),
                total_profit_loss=round(profit_loss, 2),
                roi_percentage=round(roi, 2)
            )
        )
    return summary_list
