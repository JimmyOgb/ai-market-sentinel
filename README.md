# ◈ AI Market Sentinel

> A GenLayer Intelligent Contract that monitors crypto markets using plain-English alert conditions — five validator nodes fetch live data from CoinGecko and CryptoPanic, reach LLM consensus on whether conditions are met, and commit verdicts on-chain. Frontend makes real contract calls to Studionet via genlayer-js.

[![GenLayer Studio](https://img.shields.io/badge/GenLayer_Studio-Open_Contract-00e5ff?style=for-the-badge&logoColor=black)](https://studio.genlayer.com/?import-contract=0xc616067C1d45B68D801566A0439D580E260C9098)
[![Network](https://img.shields.io/badge/Network-GenLayer_Studionet-39ff14?style=for-the-badge&logoColor=black)](https://studio.genlayer.com)
[![License](https://img.shields.io/badge/License-MIT-00e5ff?style=for-the-badge&logoColor=black)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Live Deployment](#-live-deployment)
- [What Changed from v1](#-what-changed-from-v1)
- [How It Works](#-how-it-works)
- [Contract Architecture](#-contract-architecture)
- [Methods](#-methods)
- [Frontend](#-frontend-real-genlayer-js-calls)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)

---

## 🌐 Overview

**AI Market Sentinel** lets you register a market alert in plain English — *"Alert me when BTC dominance drops below 50%"* — and have five independent GenLayer validator nodes evaluate it against live web data. When all five agree the condition is met, the alert flips to `Triggered` on-chain.

No hardcoded thresholds. No price feed oracles. Just natural language + live data + decentralized consensus.

---

## 🚀 Live Deployment

| Resource | Link |
|---|---|
| **Contract on GenLayer Studio** | [0xc616067C1d45B68D801566A0439D580E260C9098](https://studio.genlayer.com/?import-contract=0xc616067C1d45B68D801566A0439D580E260C9098) |
| **Network** | GenLayer Studionet |
| **Contract Address** | `0xc616067C1d45B68D801566A0439D580E260C9098` |

---

## 🔧 What Changed from v1

The original submission was rejected by judges for three reasons. All three are fixed:

### 1. `raise Exception()` → `raise gl.vm.UserError()`
The genvm-lint check requires `gl.vm.UserError` for contract-level validation failures.
```python
# Before (fails lint)
raise Exception("Alert does not exist.")

# After (passes lint)
raise gl.vm.UserError("Alert does not exist.")
```

### 2. Non-Standard Nondet Structure → `gl.eq_principle.strict_eq()`
The original returned a raw string from `exec_prompt` and passed it through `strict_eq`. The correct pattern is an inner function that returns a parsed dict, consistent with the official SDK:
```python
def run_ai_adjudication() -> typing.Any:
    market_data = gl.nondet.web.render(cg_url, mode="text")[:2000]
    news_data   = gl.nondet.web.render(news_url, mode="text")[:1500]
    result = gl.nondet.exec_prompt(prompt).replace("```json","").replace("```","")
    return json.loads(result)   # ← parsed dict, not raw string

consensus = gl.eq_principle.strict_eq(run_ai_adjudication)
```

### 3. Simulated Frontend → Real genlayer-js Calls
The v1 frontend used `setTimeout` and `Math.random()` to fake validator consensus. The v2 frontend uses the real `genlayer-js` SDK loaded from CDN:
```js
client = GenLayerJS.createClient({ endpointUrl: rpc });
const txHash = await client.writeContract({
  address:      CONTRACT_ADDRESS,
  functionName: 'process_sentinel_check',
  args:         [parseInt(id)],
  account,
});
const receipt = await client.waitForTransactionReceipt({ hash: txHash });
```

---

## ⚙️ How It Works

```
create_intelligent_alert(asset, natural_language_intent)
        │
        └── alert stored with status = "Active"
            history = {verdict: "PENDING", reasoning: "Initialized"}

process_sentinel_check(alert_id)
        │
        ├── validates alert exists and is Active
        │   raises gl.vm.UserError on failure
        │
        └── run_ai_adjudication() inner function
                │
                ├── gl.nondet.web.render(CoinGecko trending URL, mode="text")[:2000]
                ├── gl.nondet.web.render(CryptoPanic news URL,   mode="text")[:1500]
                ├── gl.nondet.exec_prompt(prompt with live data)
                │   → 5 nodes each independently fetch + evaluate
                │
                └── gl.eq_principle.strict_eq()
                    All 5 nodes must return identical {verdict, reasoning, confidence}
                            │
                    "TRIGGERED" → status = "Triggered", returns True
                    "PENDING"   → history updated, returns False

cancel_alert(alert_id)
        └── owner-only, raises gl.vm.UserError if not owner
```

---

## 🏗️ Contract Architecture

```python
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

class AIMarketSentinel(gl.Contract):
    state: TreeMap[str, str]
```

### Storage Design

| Key | Value | Description |
|---|---|---|
| `"owner"` | `"0xOwner…"` | Contract owner |
| `"counter"` | `"4"` | Total alerts created |
| `"meta:{id}"` | JSON | `{owner, asset, intent}` |
| `"status:{id}"` | `"Active"` | Alert status |
| `"history:{id}"` | JSON | Last AI evaluation result |

---

## 📌 Methods

### Write Methods

#### `create_intelligent_alert(asset, natural_language_intent) → int`
Registers a new alert. Returns the alert ID.

#### `process_sentinel_check(alert_id) → bool`
Fetches live market data, runs 5-node consensus. Returns `True` if triggered.

#### `cancel_alert(alert_id) → bool`
Owner-only. Cancels an active alert.

### View Methods

| Method | Returns |
|---|---|
| `inspect_alert_state(alert_id)` | `{status, history}` JSON |
| `get_alert_meta(alert_id)` | `{owner, asset, intent}` JSON |
| `get_total_alerts()` | Total count string |
| `get_owner()` | Owner address |

---

## 🖥️ Frontend — Real genlayer-js Calls

The frontend loads `genlayer-js` from CDN and makes real contract calls to Studionet:

```html
<script src="https://cdn.jsdelivr.net/npm/genlayer-js@latest/dist/index.umd.js"></script>
```

**To use:**
1. Enter the contract address and Studionet RPC URL
2. Enter a private key (test key only — never use a mainnet key)
3. Click **Connect to Studionet**
4. Create alerts, run sentinel checks, and cancel alerts — all real on-chain transactions

### Running locally

```bash
open frontend/index.html
npx serve frontend/
```

### Deploying to Cloudflare Pages

Drag the `frontend/` folder to [pages.cloudflare.com](https://pages.cloudflare.com) → Direct Upload.

---

## 🏁 Getting Started

### 1. Open Contract in GenLayer Studio
```
https://studio.genlayer.com/?import-contract=0xc616067C1d45B68D801566A0439D580E260C9098
```

### 2. Create an Alert (Studio or frontend)
```
asset:   BTC
intent:  Alert me when BTC dominance drops below 50% and altcoins show strong momentum.
```

### 3. Run a Sentinel Check
```
process_sentinel_check(0)
```
→ Fetches CoinGecko + CryptoPanic live, 5 validators evaluate, consensus committed.

### 4. View Result
```
inspect_alert_state(0)
→ {"status": "Triggered", "history": {"verdict": "TRIGGERED", "reasoning": "…", "confidence": 87}}
```

---

## 📁 Project Structure

```
ai-market-sentinel/
├── contract/
│   └── ai_market_sentinel.py   # GenLayer Intelligent Contract (v2 — lint-clean)
├── frontend/
│   └── index.html              # Cyber-terminal UI with real genlayer-js calls
├── docs/
│   └── architecture.md         # Fix notes, storage design, consensus pattern
├── .gitignore
├── LICENSE
├── package.json
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Blockchain** | GenLayer (L2, Studionet) |
| **Contract Language** | Python (GenLayer Intelligent Contract) |
| **AI Consensus** | `gl.eq_principle.strict_eq` — 5 validator nodes |
| **Web Data** | `gl.nondet.web.render` → CoinGecko + CryptoPanic |
| **Error Handling** | `gl.vm.UserError` (lint-compliant) |
| **Frontend SDK** | `genlayer-js` from CDN — real Studionet calls |
| **Frontend** | Vanilla HTML / CSS / JS — cyber-terminal aesthetic |

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.
