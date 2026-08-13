<div align="center">
  <h1>PAYBACK Deutschland (for Home Assistant) 💳</h1>
  <p><strong>A secure, robust Home Assistant integration that fetches your PAYBACK points balance, active & available coupons, and account activity directly using TLS-impersonated mobile API clients.</strong></p>

  [![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz)
  [![Downloads (Current release)](https://img.shields.io/github/downloads/FaserF/ha-payback/latest/payback.zip?label=Downloads%20(Current%20release)&style=for-the-badge)](https://github.com/FaserF/ha-payback/releases)
  [![GitHub Release](https://img.shields.io/github/v/release/FaserF/ha-payback?style=for-the-badge)](https://github.com/FaserF/ha-payback/releases)
  [![License](https://img.shields.io/github/license/FaserF/ha-payback?style=for-the-badge)](LICENSE)
</div>

---

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [📦 Installation](#-installation) | [⚙️ Configuration](#-configuration) | [🔐 Session Cookie Guide](#-bypassing-bot-protection-f12-guide) |
| [🛠️ Options](#-options-flow) | [🧑‍💻 Diagnostics](#-diagnostics) | [📄 License](#-license) | |

### Why use this integration?
Instead of brittle web scraping or resource-heavy headless browsers, this integration connects directly using native mobile API endpoints with `curl_cffi` for advanced TLS-fingerprinted client impersonation. It fetches structured points breakdowns and available deal coupons in real time.

It groups all sensors under a single PAYBACK Account device and implements domain-wide lock serialization, random jitter delays, persistent storage caching, and exponential backoffs to keep your setup safe from rate-limiting bans.

---

## ✨ Features

- **🪙 Detailed Points Sensors**:
  - **Total Points**: Total accumulated points balance in your account.
  - **Available Points**: Redeemable points available for rewards & discounts.
  - **Pending Points**: Currently locked/pending points from recent transactions.
- **🎟️ Coupon Management**:
  - **Active Coupons**: Count of currently activated deal coupons.
  - **Auto Coupon Activation**: Optional background feature to auto-activate new partner coupons.
- **📱 PAYBACK Account Device Grouping**:
  - All sensors are grouped under a dedicated **PAYBACK (Account)** device entry.
  - Features a direct **Visit PAYBACK Account** button taking you straight to your web account portal.
- **🛡️ Rate-Limiting & Anti-Ban Protections**:
  - **Lock Queueing**: A domain-wide `asyncio.Lock` ensures concurrent updates run sequentially.
  - **Random Jitter**: Introduces a 5–15 second random sleep between requests to avoid timing signatures.
  - **Restart-Resistance**: Saves parsed data to Home Assistant's JSON storage cache to survive restarts without hitting the API.
  - **Exponential Backoff**: Automatic cool-down state (up to 12h) on rate limits or API connection failures.
- **🔍 Diagnostic Downloads**:
  - Full support for Home Assistant UI Diagnostics. Download complete configurations with credentials and tokens automatically redacted.

---

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job**.
>
> **This project is and will always remain 100% free.**
>
> Donations are completely voluntary — but they help me stay motivated and dedicate more time to maintaining open-source tools!

<div align="center">

[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

---

## 📦 Installation

### HACS (Recommended)

This integration is fully compatible with [HACS](https://hacs.xyz/).

1. Open HACS in Home Assistant.
2. Click on the three dots in the top right corner and select **Custom repositories**.
3. Add `https://github.com/FaserF/ha-payback` with category **Integration**.
4. Search for "PAYBACK Deutschland".
5. Install and restart Home Assistant.

[![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-payback&category=integration)

### Manual Installation

1. Download the latest release zip file.
2. Extract the `custom_components/payback` folder into your Home Assistant's `custom_components` directory.
3. Restart Home Assistant.

---

## ⚙️ Configuration

1. Navigate to **Settings > Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **PAYBACK Deutschland**.

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=payback)

3. Enter your Payback **Customer Number / Email** and **Password**.
4. *(Optional)* Paste your browser session cookie string (`incap_ses...`) to bypass Cloud WAF bot checks.

---

## 🔐 Bypassing Bot Protection (F12 Guide)

Payback utilizes **Imperva/Incapsula** Cloud WAF bot protection. If live API queries are blocked by WAF challenges, provide a desktop browser session cookie string:

### 💡 Step-by-Step Guide: Obtaining your Session Cookie

| Step | Action |
| :--- | :--- |
| **1. Login** | Open Chrome or Firefox on your computer and navigate to [PAYBACK.de Coupons](https://www.payback.de/coupons). Log in with your credentials. |
| **2. Developer Tools** | Press `F12` (or Right-Click anywhere -> Inspect). |
| **3. Network Tab** | Switch to the **Network** (`Netzwerk`) tab at the top. |
| **4. Refresh Page** | Press `F5` to reload the page with network recording enabled. |
| **5. Select Request** | Click on any HTTP request starting with `coupons` or `account`. |
| **6. Copy Cookie** | In the **Request Headers** section on the right, find `Cookie:` and copy the full text string (containing `incap_ses_...` or `visid_incap_...`). |
| **7. Paste in HA** | Paste the copied string into the **Session Cookie** field during setup or in the integration **Configure** menu. |

---

## 🎛️ Options Flow

Click **Configure** on the PAYBACK integration card to adjust settings:

- **Update Interval**: Update frequency in hours (default: 12 hours, min: 2 hours).
- **Auto Activate Coupons**: Automatically activate all available partner coupons in the background.
- **Session Cookie**: Update or refresh your browser session cookie string at any time.

---

## 🔍 Diagnostics

If you encounter issues, you can download a full diagnostics export:
Go to **Settings > Devices & Services > PAYBACK Deutschland > 3 Dots > Download diagnostics**. All credentials and card numbers are automatically redacted.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
