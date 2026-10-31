# USA.USD — operational foundation

This is a deployable foundation, not a claim that live payments are already enabled.
It includes Telegram WebApp authentication, a FastAPI backend, PostgreSQL models,
support tickets, referrals, VIP plan catalogue, deposit transaction verification
for USDT BEP20, and an admin-reviewed withdrawal queue.

## Important payment design
A single shared BEP20 address cannot identify which Telegram user sent a transfer.
Users therefore submit the transaction hash. The backend verifies the USDT contract,
recipient, amount, successful receipt and confirmations on BSC before crediting once.
Never credit from a screenshot or user-entered amount alone.

Withdrawals are queued for administrator review. Do not enable automatic hot-wallet
payouts until a separate audited signer/custody design, limits, monitoring and key
management are in place. Never put a private key in this repository.

## Configure
Copy `.env.example` to `.env`, fill every required secret and verify the receiving
address directly from your wallet. The previously mentioned address is intentionally
not hard-coded because the full address/QR could not be independently verified here.

## Run locally
`docker compose up --build`

Then open `http://localhost:8000/health`.
Set the Telegram bot domain to the deployed HTTPS domain and configure `BOT_TOKEN`.
