# Connect Craigslist (free)

The app now has a **Craigslist intake** section. It shows results imported from Craigslist's **official saved-search alert emails**. It does **not** scrape Craigslist pages.

## One-time setup

1. Sign in to Craigslist and save searches under **Cars & Trucks → by owner**, with max price **$20,000**. Start with separate keywords: `911`, `Porsche`, `964`, `993`, `930`, `Carrera`, `Targa`, and misspelling `Porshe`. Create searches for relevant Craigslist cities/regions; saving one search does **not** guarantee all 50 states. Check **alert** in Craigslist account's Searches page.
2. Use a *dedicated Gmail inbox* for Craigslist alerts (don't use your main personal mailbox). In Google account settings, turn on 2-Step Verification and create an **App Password** for this inbox, if your account permits it.
3. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Add:
   - `CL_IMAP_USER` = the dedicated Gmail address
   - `CL_IMAP_APP_PASSWORD` = that inbox's Gmail App Password (not regular password)
4. Under **Settings → Actions → General**, allow workflows and give the repository workflow **Read and write permissions** (needed to update `deals.json`).
5. Under **Actions → Craigslist deal intake**, choose **Run workflow** for your first import. Afterwards GitHub schedules a check approximately every 10 minutes at offset times, but GitHub scheduled runs may be delayed or skipped.
6. Visit your Home Screen app and press **Refresh** in its Craigslist section.

## Limitations

- No guaranteed national coverage until Craigslist searches are configured for the relevant areas.
- Email alerts come when Craigslist sends them; the schedule is not instant.
- Email titles often omit price/year/condition and descriptions; the intake shows **unverified** candidates and labels uncertainty instead of inventing details.
- The detector excludes explicit dealer wording, but hidden dealerships can still slip through. Open the listing and verify seller identity.
- No genuine market valuation yet. The collector's number is a **triage score**, not a profit forecast.
- **No automatic iPhone push yet.** The app refreshes candidate data when opened/when Refresh is tapped.
- Data in `deals.json` is **public** because GitHub Pages is public. This app publishes listing URLs and text only; do not upload private seller contact information or your inbox contents.
- Keep Gmail credentials **only in GitHub Actions secrets**, never committed into files.

If GitHub Actions cannot access Gmail, check that Gmail IMAP is enabled for the account and that App Password authentication is available. No paid API is needed.
