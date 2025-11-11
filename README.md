
# 🍳 ChefAI — Backend Setup Guide

Welcome to **ChefAI**, the intelligent recipe generator powered by Qwen via OpenRouter.

This short guide will help you (the frontend or backend team member) set up and run the backend locally in a few minutes.

---

## ⚙️ Requirements

Make sure you have **Python 3.10+** and **pip** installed.

---

## 📦 Installation

1. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate    # on macOS/Linux
   venv\Scripts\activate       # on Windows
````

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Environment Variables

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Open the new `.env` file and add your OpenRouter API key:

   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

---

## 🚀 Run the Backend

To test the AI model locally:

```bash
python chef_backend/agents.py
```

This will print a sample recipe response from the Qwen model via OpenRouter.

If you're integrating with the frontend, make sure your local API endpoints are properly connected to this backend.

---

## 🧩 Project Structure

```
CHEFAI/
├── chef_backend/
│   ├── __init__.py
│   ├── agents.py
│   ├── langgraph_core.py
│   └── main.py
├── chef_frontend/
├── docs/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚠️ Notes

* **Do not commit or share `.env` files**. They are ignored by Git for security reasons.
* If you’re using the shared testing key, treat it as temporary — it may be revoked anytime.
* For personal testing, create your own free API key at [OpenRouter.ai](https://openrouter.ai).

---

Happy coding 💡
*— ChefAI Team*
