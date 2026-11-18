# Free Lock Screen alerts with Telegram

**Already built** in GitHub Actions. No paid APIs, computer or always-on server required.

## One-time setup (iPhone)

1. Install **Telegram** and open [@BotFather](https://t.me/BotFather).
2. Send `/newbot`. Pick a name (for example, Speedy Deal Alerts) and a unique username ending in `bot`. BotFather gives you a **bot token**. **Keep this token private.**
3. In GitHub, open [Car Finder Actions secrets](https://github.com/PASpeedo/car-finder/settings/secrets/actions). Add a new repository secret:
   - **Name:** `TELEGRAM_BOT_TOKEN`
   - **Secret:** paste the token from BotFather
4. In Telegram, open **your new bot** (not BotFather), then tap **Start** or send `/start`.
5. In GitHub **Actions → Craigslist deal intake → Run workflow**, run it once. A green check plus a message from Speedy in Telegram confirms the connection.

**No chat ID is needed** if only one person has ever messaged your bot. If more than one private person messages it, automatic routing intentionally stops. In that situation we can use the optional `TELEGRAM_CHAT_ID` secret.

## What notifications actually do

- Telegram sends a message to your iPhone Lock Screen (enable notifications for Telegram in iPhone Settings).
- New *possible* Porsche 911 candidates from Craigslist official search-alert emails are sent.
- The email must indicate a plausible Porsche 911 and a price at or below $20,000, or indicate seller urgency if the price is missing.
- Known dealers, title-risk wording and out-of-range years are screened out when those details appear in the email.
- The email is often incomplete, so these messages are **unverified candidates, not independently appraised deals**.
- Deduplication prevents repeat alerts, and batches are capped at 4 per scheduled run.
- GitHub Action checks are scheduled about every 10 minutes at offset times. Craigslist may send its emails much later; immediate coverage is **not** guaranteed.

## Privacy / security

- Never commit the bot token in a file or send it into chat. It belongs only in GitHub **Actions secrets**.
- Telegram messages contain public listing URL/title/price, not your email contents or Gmail credentials.
- The public repository tracks sent listing URLs and a cryptographic fingerprint of the Telegram chat (not the Telegram chat ID).
- Keep the bot's identity private; it cannot auto-send to another chat if more than one person messages it.

## Troubleshooting

- Workflow green, no Telegram message: make sure you sent **/start** to your new bot; rerun **Craigslist deal intake**.
- Red workflow: inspect the failed step in GitHub Actions (but don't share secrets).
- Success but no new listings: Craigslist email hasn't produced a candidate or the email title lacks qualifying details.
