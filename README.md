<div align="center">

```
███████╗██████╗ ██████╗ ██╗███████╗███████╗███╗   ██╗
██╔════╝██╔══██╗██╔══██╗██║╚══███╔╝██╔════╝████╗  ██║
███████╗██████╔╝██████╔╝██║  ███╔╝ █████╗  ██╔██╗ ██║
╚════██║██╔═══╝ ██╔══██╗██║ ███╔╝  ██╔══╝  ██║╚██╗██║
███████║██║     ██║  ██║██║███████╗███████╗██║ ╚████║
╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝
```

### 🤖 Autonomous AI Workflow Engine — Bug Hunter Module

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Android%20%7C%20Linux-green?style=for-the-badge&logo=android)](.)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Dependencies](https://img.shields.io/badge/Dependencies-requests%20only-orange?style=for-the-badge)](requirements.txt)
[![AI](https://img.shields.io/badge/AI-Groq%20%7C%20Kimi%20%7C%20Ollama-purple?style=for-the-badge)](.)

**World's first Mobile-First AI Development Agent**  
*Runs on your Android phone. No cloud. No bloat. Just pure intelligence.*

</div>

---

## ⚡ What is Sprizen?

Sprizen is an **autonomous AI workflow agent** that hunts bugs in your code using multiple AI providers — with automatic fallback, circuit breaking, and parallel scanning. Built to run on **edge devices** like Android (Termux) with zero heavy dependencies.

```
Your Code → Sprizen → AI Analysis → Professional Bug Report
              ↓
    Groq (Fast) → Kimi (Smart) → Ollama (Private)
    [Auto-fallback if one fails]
```

---

## 🏗️ Architecture

```
sprizen/
├── provider_router.py      ← Dual-Engine Router (Heart of Sprizen)
│   ├── CircuitBreaker      ← 5 failures = 60s auto-block
│   ├── ExponentialBackoff  ← 2s → 4s → 8s + jitter
│   ├── FallbackChain       ← Groq → Kimi → Ollama
│   └── RoutingRules        ← privacy_sensitive → local only
│
├── sprizen_bug_hunter.py   ← Bug Hunter Module
│   ├── ParallelScanning    ← 4 files scanned simultaneously
│   ├── SHA256 Cache        ← Unchanged files skipped
│   ├── MarkdownReporter    ← Professional CI/CD-ready reports
│   └── GitHubConnector     ← (v2.1 — auto PR creation)
│
└── config.json             ← Provider config + routing rules
```

---

## 🔥 Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Dual-Engine Router** | Switch between Cloud API & Local AI | ✅ Live |
| **Circuit Breaker** | Auto-block failing providers (5 fails → 60s) | ✅ Live |
| **Exponential Backoff** | Smart retry: 2s→4s→8s + random jitter | ✅ Live |
| **Fallback Chain** | Groq → Kimi → Ollama automatic | ✅ Live |
| **Parallel Scanning** | 4 files scanned simultaneously | ✅ Live |
| **SHA256 Cache** | Skip unchanged files, 10x faster rescan | ✅ Live |
| **Privacy Routing** | Sensitive files → local model only | ✅ Live |
| **Markdown Reports** | CRITICAL/HIGH/MEDIUM/LOW severity index | ✅ Live |
| **GitHub Connector** | Auto PR with AI fixes | 🚧 v2.1 |
| **Web Dashboard** | Usage analytics & team management | 🚧 v3.0 |

---

## 🚀 Quick Start

### Prerequisites
```bash
# Termux (Android)
pkg install python git
pip install requests

# Linux/Mac
pip install requests
```

### Installation
```bash
git clone https://github.com/YOUR_USERNAME/sprizen.git
cd sprizen
```

### Run
```bash
# Scan a single file
python3 -c "
from provider_router import ProviderRouter
from sprizen_bug_hunter import create_bug_hunter
router = ProviderRouter('./config.json')
hunter = create_bug_hunter(router=router)
hunter.scan('./your_file.py')
"

# Scan entire project
hunter.scan('./your_project/')
```

---

## ⚙️ Configuration

Edit `config.json` to set your providers:

```json
{
  "fallback_chain": ["groq", "kimi", "ollama"],
  "routing_rules": {
    "privacy_sensitive": "ollama",
    "high_reasoning": "groq"
  },
  "providers": {
    "groq": {
      "enabled": true,
      "api_key": "your_groq_key",
      "model": "llama3-8b-8192"
    },
    "ollama": {
      "enabled": true,
      "model": "tinyllama"
    }
  }
}
```

### Provider Options

| Provider | Type | Cost | Best For |
|----------|------|------|----------|
| **Groq** | Cloud API | Free tier | Fast analysis |
| **Kimi** | Cloud API | Free tier | Complex reasoning |
| **Ollama** | Local | Free forever | Privacy, offline |
| **llama.cpp** | Local | Free forever | Low RAM devices |

---

## 📊 Sample Report Output

```markdown
# Sprizen Bug Hunter v2.0 — Security Audit Report

| Severity | Line | Issue                        | Fix                          |
|----------|------|------------------------------|------------------------------|
| CRITICAL | 45   | SQL Injection via f-string   | Use parameterized queries    |
| HIGH     | 12   | Hardcoded credentials        | Use environment variables    |
| HIGH     | 3    | Mutable default argument     | Use None, init inside func   |
| MEDIUM   | 78   | Bare except clause           | Catch specific exceptions    |
| LOW      | 91   | Unused import (sqlite3)      | Remove unused imports        |
```

---

## 🧠 How the Router Works

```
Request arrives
      ↓
Routing Rules check
      ↓
privacy_sensitive? → Ollama (local, no data leaves device)
high_reasoning?   → Groq (fastest cloud)
      ↓
Fallback Chain:
  1. Groq → fail? Circuit Breaker records failure
  2. Kimi → fail? Exponential backoff (2s→4s→8s)
  3. Ollama → last resort, always available
      ↓
All fail? → Clear error with fix suggestions
```

---

## 📱 Why Mobile-First?

Most AI dev tools require powerful machines. Sprizen was built differently:

- ✅ **Runs on Android** via Termux — no PC needed
- ✅ **Zero heavy deps** — only `requests` library
- ✅ **Low RAM** — parallel workers configurable
- ✅ **Offline mode** — Ollama/llama.cpp work without internet
- ✅ **Smart caching** — don't re-scan unchanged files

---

## 🗺️ Roadmap

```
v2.0 (Now)    → Bug Hunter, Dual-Engine Router, Parallel Scan
v2.1          → GitHub Connector (auto PR with fixes)
v2.2          → Multi-language support (.js, .ts, .java, .go)
v3.0          → SaaS Dashboard + Team accounts
v3.1          → CI/CD GitHub Actions integration
v4.0          → Enterprise self-hosted + Slack/Jira integration
```

---

## 📁 File Structure

```
sprizen/
├── provider_router.py      # AI provider routing engine
├── sprizen_bug_hunter.py   # Core bug hunting logic
├── config.json             # Provider configuration
├── requirements.txt        # Only: requests>=2.28.0
├── sprizen_reports/        # Generated bug reports (auto-created)
└── README.md
```

---

## 🤝 Contributing

Pull requests welcome! For major changes, open an issue first.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">

**Built with ❤️ on Android | Powered by Groq + Kimi + Ollama**

*"Why wait for a PC when your phone is powerful enough?"*

⭐ **Star this repo if Sprizen helped you!** ⭐

</div>
