# FX Real-Time Pricing Project

This repository contains code and documentation for streaming, storing, and analyzing real-time FX prices obtained via WebSocket connections. The project is designed to support lightweight apps that track ~10–12 currency pairs in real time, without requiring enterprise-grade market data infrastructure.

---

## 📌 Goals

- Stream real-time FX prices from a WebSocket API
- Store data locally or in a lightweight database for analysis
- Provide utilities for visualizing spreads, volatility, and cross-pair moves
- Maintain a modular, extensible structure for multiple analytic apps

---

## 📁 Project Structure

```
fx-realtime/
├── .venv/                 # Local virtual environment (not committed)
├── requirements.txt       # Python dependencies
├── src/
│   ├── data/              # Storage helpers (CSV, DuckDB, etc.)
│   ├── stream/            # WebSocket connection and handlers
│   ├── utils/             # Helpers for logging, config, env vars
│   └── analysis/          # Jupyter notebooks & analysis scripts
└── README.md              # Project documentation (this file)
```

---

## 🛠 Setup Instructions

### **1. Clone the repo**

```sh
git clone <YOUR_REPO_LINK>
cd fx-realtime
```

### **2. Create & activate virtual environment**

```sh
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# OR
.venv\Scripts\activate    # Windows
```

### **3. Install dependencies**

```sh
pip install -r requirements.txt
```

---

## 🔌 WebSocket Streaming

This project will include streaming adapters for APIs like:

- **Twelve Data**
- **Polygon.io**
- **OANDA**
- **FXCM**
- **Alpha Vantage** (less real‑time, more polling)

The first prototype will target a low-cost provider that allows lightweight usage.

---

## 🧪 Example Usage (WIP)

```python
from src.stream.client import PriceStream

stream = PriceStream(pairs=["USD/JPY", "EUR/USD"])
stream.connect()
```

---

## 🤝 Openscapes-Inspired Practices

- Use clear folder organization to support reproducibility
- Human-friendly naming and comments
- Document decisions in `docs/` or commit messages
- Prefer open formats (CSV, Parquet, DuckDB)
- Keep code modular for reuse across analyses

---

## 📝 To‑Do

- [ ] Select provided WebSocket API + pricing plan
- [ ] Build price stream handler
- [ ] Add DuckDB storage option
- [ ] Build simple plotting utility
- [ ] Add CLI for starting a stream
- [ ] Create notebooks that replicate:
  - spreads
  - realized vol
  - intraday patterns

---

## 🧻 Notes / Decisions

- `.venv/` is used to auto-integrate with VS Code Python environment detection
- Repository assumes *non‑hi‑freq usage* (not suitable for trading systems)
- API keys will be handled via `.env` (not committed)

---

## 📄 License

TBD — MIT or Apache 2 recommended.

---

*Let me know anytime if you’d like automated setup scripts or sample WebSocket code.*
