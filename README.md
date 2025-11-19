# 🍳 **ChefAI – Image-to-Recipe Agent System**

*A structured, production-ready recipe generation pipeline for AgentX Hackathon*

ChefAI is an agent-driven system designed to reduce food waste by transforming any fridge photo into a clean ingredient list and a personalized, cookable recipe.
It combines **vision analysis**, **data cleaning**, and a **two-step orchestration pipeline** to ensure accuracy, speed, and reliable outcomes.

This repository documents the **current working version**, and outlines the **planned upgrades for the final stage**.

---

# 🚀 **Mission**

Help users cook with what they already have by:

1. Understanding real ingredients from a fridge photo
2. Cleaning & normalizing them
3. Generating accurate, personalized recipes
4. Suggesting missing ingredients *when needed*

All while keeping the system lightweight, fast, and practical for real-world use.

---

# 🧠 **Core Features (Current Version)**

### ✔️ **1. Vision Model (Qwen-VL)**

* Detects items from the fridge photo
* Outputs strict structured JSON
* Extracts up to ~10 edible ingredients
* Works through OpenRouter API

### ✔️ **2. Cleaning Layer**

* Arabic/English normalization
* Name fixing
* Duplicate merging
* Confidence filtering
* Splits results into:

  * *confirmed ingredients*
  * *uncertain items*

### ✔️ **3. Two-Step Pipeline (Analyze → Generate)**

Separated for UX clarity and frontend integration:

**Step 1:** `/api/chef/analyze`

* Image → Vision Model → Cleaning Layer
* Returns ingredient list only

**Step 2:** `/api/chef/generate`

* Uses Step1 ingredients + user preferences
* Calls Recipe LLM
* Returns full structured recipe

### ✔️ **4. LangGraph Orchestrator**

* Manages both steps
* Ensures deterministic flow
* Connects between agents cleanly

### ✔️ **5. Recipe LLM**

* Generates recipe name, steps, nutrition estimate
* Uses available ingredients only
* Respects preferences (time, cuisine, servings)
* Produces clean JSON for frontend

### ✔️ **6. Optional Shopping Agent**

* Detects missing items
* Suggests replacements

### ✔️ **7. FastAPI Backend (Railway-Ready)**

* Simple, stateless design
* No Redis / No workers
* Easy to deploy
* session_id store for step linking

---

# 🏗️ **Architecture Diagram (ASCII)**

```
User (PWA)
    ↓ POST /api/chef/analyze
FastAPI Gateway
    ↓ Image
Vision Model (Qwen-VL)
    ↓ Raw JSON
Cleaning Layer
    ↓ Clean Ingredients (stored in SESSION_STORE)
-----------------------------------------------
User Preferences
    ↓ POST /api/chef/generate
LangGraph Orchestrator
    ↓ Recipe Request
Recipe LLM
    ↓ Final JSON
Final User Output (PWA)
```

Optional:

```
          Clean Ingredients
                 ↓
     Shopping Agent (Optional)
                 ↓
         Missing Item Suggestions
```

---

# 📡 **API Endpoints**

## **POST /api/chef/analyze**

Input → Base64 Image
Output → Clean ingredient list + uncertain list

## **POST /api/chef/generate**

Input → ingredients + preferences
Output → Recipe JSON (steps, time, missing items…)

---

# 📂 **Project Structure**

```
/chef-backend
│
├── main.py                  # FastAPI endpoints
├── vision_agent.py          # Vision model logic
├── namefixer_agent.py       # Normalization + fixing
├── langgraph_core.py        # Step1 + Step2 graphs
├── recipe_generator.py      # Calls Recipe LLM
├── shopping_integration.py  # Optional agent
├── utils.py                 # helpers
├── constants.py             # shared configs
└── requirements.txt
```

---

# ⚙️ **Running Locally**

```
pip install -r requirements.txt
uvicorn main:app --reload
```

Swagger UI:
`http://localhost:8000/docs`

---

# ☁️ **Deployment (Railway)**

* Connect GitHub repo
* Add environment vars (OPENROUTER_API_KEY, etc.)
* Start command:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

# 🧭 **What’s Done (Finalized for Round 1)**

* Vision → Cleaning → LangGraph → Recipe LLM pipeline
* Two-Step API ready for frontend
* Deterministic JSON outputs
* Basic shopping suggestions
* Fully deployed FastAPI backend
* Working PWA prototype (Lovable + team UI/UX)

---

# 🔮 **Next Phase (Round 2 – Planned Upgrades)**

These items will significantly boost accuracy, speed, and scoring:

### **1) Switch Vision to Gemini Flash / Pro-Vision**

* Faster inference
* Higher accuracy
* Full Arabic support
* Reduces errors in ingredient naming → removes need for heavy cleaning

### **2) Add Specialized Agents**

* CO₂ Impact Agent (estimate environmental impact per recipe)
* Waste-Reduction Agent (calculate unused items)
* Auto-Basket Agent (auto-generate market cart suggestions)

### **3) Improve Performance**

* Faster response by parallelizing steps
* Lighter LLM prompts
* More aggressive input validation

### **4) UI Enhancements**

* Cleaner PWA
* Progress loader states
* Better result presentation (photos, icons)

### **5) Additional Data (Optional)**

* Nutrition API
* Price estimation for missing items
* Diet filters

---

# 🎯 **Goal for Final Round**

A fast, accurate, production-ready system that:

* Understands real fridge photos
* Produces reliable recipes
* Reduces waste
* Adds measurable value (CO₂, missing items, basket suggestions)

And delivers a polished experience end-to-end.

---

# ✔️ **Status**

This repository is the official reference for the team.

---
