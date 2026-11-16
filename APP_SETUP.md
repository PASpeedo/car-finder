# Porsche Deal Hunter — iPhone app

Free, local-first Porsche 911 watchlist, model years 1965–1997, asking price up to $20,000.

## Deploy to iPhone (GitHub Pages)

**Important:** This repository is currently **private**. On GitHub Free, Pages normally requires a **public** repository. If you make it public, the app source becomes visible to everyone; **do not commit credentials, private listing exports, or API tokens**.

1. Change repository visibility to public only if you're comfortable sharing this app code.
2. In **Settings → Pages**, choose **Deploy from a branch**, select **main** and **/(root)**, then save.
3. After deployment, visit **https://paspeedo.github.io/car-finder/** in iPhone Safari.
4. Safari **Share → Add to Home Screen**.
5. Open the installed app and add or import listings.

## What works

- Mobile dashboard, adding and filtering listings, favorites
- Local text-based triage scores (not verified market appraisals)
- Import/export JSON; offline PWA caching after first load
- Free with no paid APIs

## What is not connected

- No automatic live Facebook/Craigslist search on the hosted website
- No iOS background web push; testing notifications in browser does not enable live alerts
- No phone-to-computer database sync

For alerts while the app is closed, the optional separate collector must run on a computer with listing sources and Telegram configured. The website itself does not monitor marketplaces.

## Security

Never put passwords, bot tokens, private contact details, or saved listing exports into a public GitHub Pages repository. Browser local storage may be cleared, so export backups periodically.
