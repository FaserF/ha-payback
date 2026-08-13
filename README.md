# Home Assistant Integration for PAYBACK Deutschland

[![CI](https://github.com/FaserF/ha-payback/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-payback/actions/workflows/ci-orchestrator.yml)
[![HACS Validation](https://github.com/FaserF/ha-payback/actions/workflows/ci-orchestrator.yml/badge.svg?branch=main)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/FaserF/ha-payback)](https://github.com/FaserF/ha-payback/releases)

Home Assistant Integration to view your **PAYBACK Deutschland** points balance, active coupons, and recent account activity.

> ⚠️ **WAF / Cloud Protection Notice**: Payback uses Imperva/Incapsula bot protection on web & mobile servers. To guarantee live data updates, provide a session cookie string from your desktop browser as described in the step-by-step guide below.

## Features

- 🪙 **Points Balance**: View total Payback points & available points balance.
- 🎟️ **Active Coupons**: Track active and available coupons in Home Assistant.
- ⚡ **Auto Coupon Activation**: Option to automatically activate new coupons.
- 🛡️ **Anti-Ban Architecture**:
  - `curl_cffi` TLS client impersonation to bypass bot detection.
  - `asyncio.Lock` serialization to prevent concurrent requests.
  - Randomized jitter between API queries.
  - Persistent caching to withstand Home Assistant restarts during rate limiting.

## Installation

### Via HACS (Recommended)

1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right corner and choose **Custom repositories**.
3. Add `https://github.com/FaserF/ha-payback` as an **Integration**.
4. Search for **PAYBACK Deutschland** and click **Download**.
5. Restart Home Assistant.

### Manual Installation

1. Download the latest release `.zip` file from the [Releases](https://github.com/FaserF/ha-payback/releases) page.
2. Copy the `custom_components/payback` directory into your Home Assistant `<config>/custom_components/` folder.
3. Restart Home Assistant.

## Configuration & Bypassing Bot Protection

1. Go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **PAYBACK Deutschland**.
3. Enter your Payback **Customer Number / Email** and **Password**.

### 💡 Step-by-Step Guide: Obtaining your Session Cookie (Idiotensichere Anleitung)

If Payback blocks server queries, paste your browser session cookie into the **Session Cookie** field during setup or via **Configure**:

1. Open Chrome/Firefox on desktop and navigate to [PAYBACK.de Coupons](https://www.payback.de/coupons).
2. Log in with your Payback email and password.
3. Open **Developer Tools** by pressing `F12` (or Right-Click -> Inspect).
4. Go to the **Network** tab (`Netzwerk`).
5. Refresh the page (`F5`).
6. Click on any request starting with `coupons` or `account`.
7. In the request headers section (`Anfrage-Kopfzeilen`), find the `Cookie:` entry.
8. Copy the entire cookie string (or specifically the `incap_ses...` / `visid_incap...` tokens).
9. Paste it into the **Session Cookie** input box in Home Assistant.

## Options

Click **Configure** on the integration page to customize:

- **Update Interval**: Default is 12 hours (recommended min: 4 hours to avoid rate limits).
- **Auto Activate Coupons**: Automatically activate all available coupons in your account.
- **Session Cookie**: Update or paste a fresh browser session cookie string at any time.

## Support / Sponsor

If you find this integration useful, consider supporting the development:

[![Sponsor](https://img.shields.io/badge/Sponsor-PayPal-blue.svg)](https://paypal.me/FaserF)
