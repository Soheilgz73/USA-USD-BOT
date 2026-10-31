import hmac, hashlib, json, time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, String, Integer, Numeric, DateTime, Boolean, Text, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from web3 import Web3

class Settings(BaseSettings):
    bot_token: str
    bot_username: str = ""
    telegram_bot_secret: str
    database_url: str
    bsc_rpc_url: str
    usdt_bep20_contract: str = "0x55d398326f99059fF775485246999027B3197955"
    deposit_address: str
    admin_telegram_ids: str = ""
    min_deposit_usd: Decimal = Decimal("10")
    min_withdraw_usd: Decimal = Decimal("2")
    withdraw_cooldown_hours: int = 24
    bsc_confirmations: int = 15
    class Config:
        env_file = ".env"
settings = Settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)
class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Deposit(Base):
    __tablename__ = "deposits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(66), unique=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    address: Mapped[str] = mapped_column(String(42))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)
app = FastAPI(title="USA.USD API", version="1.0.0")

PLANS = [10, 30, 50, 85, 100, 150, 350, 500, 900, 1500, 3000, 5000]
TRANSFER_ABI = [{"anonymous":False,"inputs":[{"indexed":True,"name":"from","type":"address"},{"indexed":True,"name":"to","type":"address"},{"indexed":False,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]
w3 = Web3(Web3.HTTPProvider(settings.bsc_rpc_url, request_kwargs={"timeout":15}))
token = w3.eth.contract(address=Web3.to_checksum_address(settings.usdt_bep20_contract), abi=TRANSFER_ABI)

def verify_telegram_init_data(init_data: str) -> dict:
    from urllib.parse import parse_qsl
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received = data.pop("hash", None)
    if not received: raise HTTPException(401, "Missing Telegram signature")
    check = "\n".join(f"{k}={v}" for k,v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received): raise HTTPException(401, "Invalid Telegram signature")
    if int(time.time()) - int(data.get("auth_date","0")) > 86400: raise HTTPException(401, "Telegram session expired")
    try: return json.loads(data["user"])
    except Exception: raise HTTPException(401, "Invalid Telegram user data")

def authenticated_user(authorization: Optional[str]):
    if not authorization or not authorization.startswith("tma "): raise HTTPException(401, "Telegram WebApp auth required")
    u = verify_telegram_init_data(authorization[4:])
    with Session() as s:
        user = s.scalar(select(User).where(User.telegram_id == int(u["id"])))
        if not user:
            user = User(telegram_id=int(u["id"]), username=u.get("username"), first_name=u.get("first_name",""))
            s.add(user); s.commit()
        return int(u["id"])

class TxRequest(BaseModel):
    tx_hash: str = Field(pattern=r"^0x[a-fA-F0-9]{64}$")
class WithdrawRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
class TicketRequest(BaseModel):
    message: str = Field(min_length=5, max_length=3000)

@app.get("/health")
def health(): return {"status":"ok","service":"usa-usd-api"}

@app.get("/api/config")
def config():
    return {"brand":"USA.USD","plans":PLANS,"min_deposit":str(settings.min_deposit_usd),
            "min_withdraw":str(settings.min_withdraw_usd),"withdraw_cooldown_hours":settings.withdraw_cooldown_hours,
            "network":"BEP20 / BNB Smart Chain","token":"USDT","deposit_address":settings.deposit_address}

@app.get("/api/me")
def me(authorization: Optional[str] = Header(default=None)):
    uid = authenticated_user(authorization)
    with Session() as s:
        u = s.scalar(select(User).where(User.telegram_id==uid))
        return {"telegram_id":uid,"name":u.first_name,"balance":str(u.balance)}

@app.post("/api/deposits/verify")
def verify_deposit(body: TxRequest, authorization: Optional[str] = Header(default=None)):
    uid = authenticated_user(authorization)
    txh = body.tx_hash.lower()
    with Session() as s:
        if s.scalar(select(Deposit).where(Deposit.tx_hash==txh)):
            raise HTTPException(409,"Transaction already credited or submitted")
        try:
            receipt = w3.eth.get_transaction_receipt(txh)
            tx = w3.eth.get_transaction(txh)
        except Exception: raise HTTPException(400,"Transaction not found on BSC")
        if receipt.status != 1: raise HTTPException(400,"Transaction failed")
        if w3.eth.block_number - receipt.blockNumber + 1 < settings.bsc_confirmations:
            raise HTTPException(409,"Waiting for network confirmations")
        events = token.events.Transfer().process_receipt(receipt)
        dest = settings.deposit_address.lower()
        matches = [e for e in events if e["args"]["to"].lower()==dest]
        if not matches: raise HTTPException(400,"No USDT transfer to the configured deposit address")
        raw = sum(int(e["args"]["value"]) for e in matches)
        # BSC USDT uses 18 decimals on the commonly used BEP20 contract.
        amount = Decimal(raw) / Decimal(10**18)
        if amount < settings.min_deposit_usd: raise HTTPException(400,"Deposit is below the $10 minimum")
        u = s.scalar(select(User).where(User.telegram_id==uid))
        s.add(Deposit(tx_hash=txh,telegram_id=uid,amount=amount))
        u.balance = Decimal(u.balance) + amount
        s.commit()
        return {"status":"credited","amount":str(amount),"balance":str(u.balance)}

@app.post("/api/withdrawals")
def request_withdrawal(body: WithdrawRequest, authorization: Optional[str] = Header(default=None)):
    uid = authenticated_user(authorization)
    if body.amount < settings.min_withdraw_usd: raise HTTPException(400,"Minimum withdrawal is $2")
    if not Web3.is_address(body.address): raise HTTPException(400,"Invalid BEP20 address")
    with Session() as s:
        u = s.scalar(select(User).where(User.telegram_id==uid))
        last = s.scalar(select(Withdrawal).where(Withdrawal.telegram_id==uid).order_by(Withdrawal.created_at.desc()))
        now = datetime.now(timezone.utc)
        if last and last.created_at.replace(tzinfo=timezone.utc) > now-timedelta(hours=settings.withdraw_cooldown_hours):
            raise HTTPException(429,"Withdrawals are limited to once every 24 hours")
        if Decimal(u.balance) < body.amount: raise HTTPException(400,"Insufficient balance")
        u.balance = Decimal(u.balance)-body.amount
        w = Withdrawal(telegram_id=uid,address=Web3.to_checksum_address(body.address),amount=body.amount,status="pending")
        s.add(w); s.commit()
        return {"status":"pending_admin_review","withdrawal_id":w.id,"balance":str(u.balance)}

@app.post("/api/support/tickets")
def create_ticket(body: TicketRequest, authorization: Optional[str] = Header(default=None)):
    uid = authenticated_user(authorization)
    with Session() as s:
        t=Ticket(telegram_id=uid,message=body.message); s.add(t); s.commit()
        return {"ticket_id":t.id,"status":t.status}

@app.get("/api/plans")
def plans(): return {"plans":[{"amount":x,"currency":"USDT"} for x in PLANS]}

@app.get("/")
def mini_app():
    return FileResponse("web/index.html")
