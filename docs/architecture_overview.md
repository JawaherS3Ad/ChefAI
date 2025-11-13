# ChefAI - Complete Architecture Overview

## 🏗️ System Architecture

ChefAI is an AI-powered recipe generation system that analyzes fridge images and suggests recipes based on available ingredients. The system is built using **LangGraph** for workflow orchestration and **Qwen models** via OpenRouter for AI capabilities.

---

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend/Client                         │
│                    (sends image + preferences)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP POST
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server (main.py)                      │
│                  Endpoint: /api/chef/start                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LangGraph Core (langgraph_core.py)              │
│                    State Machine Workflow                        │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │  Vision  │──▶│NameFixer │──▶│ Prepare  │──▶│ Generate │    │
│  │          │   │          │   │          │   │  Recipe  │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│       │                                              │           │
│       └──────────────────┬───────────────────────────┘           │
│                          ▼                                       │
│                    ┌──────────┐   ┌──────────┐                 │
│                    │   Post   │──▶│ Assemble │                 │
│                    │Processing│   │  Result  │                 │
│                    └──────────┘   └──────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ JSON Response │
                   └───────────────┘
```

---

## 🔧 Core Components

### 1. **FastAPI Server** (`main.py`)

**Purpose**: HTTP API layer handling client requests

**Key Features**:
- **Endpoint**: `POST /api/chef/start`
- **CORS**: Enabled for all origins
- **Input Model**: `StartInput` (Pydantic)
  - `image_base64`: Base64 encoded image
  - `meal_type`: Optional (e.g., "Dinner")
  - `time_limit`: Optional (e.g., "30m")
  - `servings`: Optional integer
  - `cuisines`: Optional list of cuisine types

**Output Model**: `ChefOutput` (Pydantic)
- `session_id`: Unique session identifier
- `recipe`: Generated recipe dictionary
- `missing_items`: List of missing ingredients
- `shopping_suggestions`: Shopping recommendations
- `error`: Error message if any

**Flow**:
1. Receives client request
2. Creates unique session ID
3. Initializes `ChefState` with input data
4. Invokes `chef_graph.invoke(init)`
5. Returns final payload or error

---

### 2. **LangGraph Core** (`langgraph_core.py`)

**Purpose**: Orchestrates the entire recipe generation pipeline using a state machine

**State Definition** (`ChefState` TypedDict):
```python
{
    "session_id": str,
    "image_base64": str,
    "vision_raw": Any,                    # Raw vision output
    "ingredients_raw": List[Dict],        # After name fixing
    "items_clean": List[Dict],            # After sanitization
    "used_items": List[Dict],             # High confidence items
    "uncertain_items": List[Dict],        # Low confidence items
    "preferences": Dict,                   # User preferences
    "policy": Dict,                        # Recipe generation policy
    "recipe": Dict,                        # Generated recipe
    "missing_items": List[str],            # Missing ingredients
    "shopping_suggestions": List[Dict],    # Shopping recommendations
    "final_payload": Dict,                 # Final output
    "error": Optional[str]                 # Error message if any
}
```

**Pipeline Nodes**:

1. **node_vision**: Analyzes fridge image
   - Calls `analyze_image_api()` from `vision_agent`
   - Returns `vision_raw` with detected ingredients
   - Handles errors gracefully with empty ingredients list

2. **node_namefixer**: Fixes ingredient names
   - Calls `fix_ingredients_names()` from `namefixer_agent`
   - Translates names to Arabic using dictionaries and LLM
   - Returns `ingredients_raw` with Arabic names

3. **node_prepare**: Prepares and filters ingredients
   - Sanitizes items (removes buckets, merges duplicates)
   - Splits by confidence threshold (0.5)
   - Ensures minimum 3 used items
   - Applies recipe policy rules
   - Returns `items_clean`, `used_items`, `uncertain_items`, `policy`

4. **node_generate_recipe**: Generates recipe
   - Calls `generate_recipe()` from `recipe_generator`
   - Uses Qwen models with structured output
   - Respects policies and preferences
   - Returns `recipe` dictionary

5. **node_missing_and_shop**: Calculates missing items
   - Compares recipe ingredients with available items
   - Calls `get_shopping_suggestions()` for missing items
   - Returns `missing_items` and `shopping_suggestions`

6. **node_assemble**: Assembles final result
   - Combines all data into `final_payload`
   - Includes metadata and confidence threshold
   - Handles errors by returning error messages

**Configuration**:
- **Confidence Threshold**: 0.5 (items below go to uncertain list)
- **Minimum Used Items**: 3 (promotes uncertain items if needed)

---

### 3. **Vision Agent** (`vision_agent.py`)

**Purpose**: Analyzes fridge images using computer vision AI

**Model**: `qwen/qwen2.5-vl-32b-instruct:free` via OpenRouter

**Key Features**:
- **Multi-format Support**: 
  - Base64 with/without data URI prefix
  - HTTP/HTTPS URLs
  - Local file paths
- **Chinese Prompt**: Uses Chinese for better results with Qwen
- **Structured Output**: JSON object with ingredients array
- **Error Handling**: Graceful fallback on length errors

**Output Schema**:
```json
{
  "ingredients": [
    {
      "name_en": "tomato",
      "name_ar": "",
      "quantity_estimate": 3,
      "unit": "piece",
      "state": "fresh",
      "category": "vegetable",
      "confidence": 0.92,
      "inferred": false
    }
  ],
  "notes": "optional notes"
}
```

**Prompt Strategy**:
- Strict JSON output requirement
- Maximum 10 items (prioritize proteins, starches, vegetables)
- English names required (Arabic filled by downstream agent)
- Confidence scoring for uncertain items
- Excludes packaging and containers

---

### 4. **Name Fixer Agent** (`namefixer_agent.py`)

**Purpose**: Translates and normalizes ingredient names to Arabic

**Strategy (Priority Order)**:
1. **Direct Mapping**: Checks if Arabic name already exists
2. **Dictionary Lookup**: Uses `EN2AR` and `ZH2AR` dictionaries
3. **LLM Translation**: Falls back to `qwen/qwen-2.5-72b-instruct:free`

**Key Features**:
- Bucket Detection: Skips generic terms like "mixed vegetables"
- Normalization: Standardizes Arabic spellings
- Attribution: Marks source as "dict" or "llm"

**Translation Rules** (LLM Prompt):
- Classical Arabic (فصحى)
- No transliteration
- No explanations or brackets
- 1-2 words maximum
- Falls back to original if unknown

---

### 5. **Recipe Generator** (`recipe_generator.py`)

**Purpose**: Generates recipes using AI with structured output

**Models** (Priority Fallback):
1. `qwen/qwen3-30b-a3b:free`
2. `qwen/qwen3-14b:free`
3. `qwen/qwen3-4b:free`

**Output Schema** (`SuggestedRecipe` Pydantic model):
```python
{
    "recipe_name": str,
    "ingredients_needed": List[str],
    "preparation_steps": List[str],
    "cooking_time_minutes": int,
    "cuisine_type": str
}
```

**Critical Rules**:
1. **Ingredient Usage**: Use only available ingredients
2. **Dough Policy**: 
   - Forbid generic "dough" unless flour + water + yeast available
3. **Lettuce & Cucumber**: Never cook on heat (raw/cold only)
4. **No Generic Terms**: Avoid "mixed vegetables", "frozen meats", etc.
5. **Specific Sauces Only**: No generic "sauce" unless specific type available

**Configuration**:
- Temperature: 0.3 (controlled creativity)
- Max Tokens: 700
- Response Format: JSON object

---

### 6. **Ontology** (`ontology.py`)

**Purpose**: Knowledge base for ingredient translation and normalization

**Dictionaries**:

**EN2AR** (English → Arabic):
- 40+ common ingredients
- Examples: "tomato" → "طماطم", "chicken breast" → "صدر دجاج"

**ZH2AR** (Chinese → Arabic):
- 30+ ingredients in Chinese characters
- Examples: "番茄" → "طماطم", "鸡蛋" → "بيض"

**AR_NORMALIZE** (Arabic Synonyms):
- "بندورة" → "طماطم"
- "فليفلة" → "فلفل رومي"
- "كوسا" → "كوسة"

**Banned Terms**:
- English: "mixed vegetables", "frozen vegetables", "sauces"
- Arabic: "خضروات متنوعة", "خضروات مجمدة", "صلصات"

**Functions**:
- `lookup_to_ar()`: Converts EN/ZH to Arabic
- `is_bucket()`: Detects generic terms
- `normalize_ar()`: Standardizes Arabic spellings

---

### 7. **Utilities** (`utils.py`)

**Purpose**: Helper functions for parsing and normalization

**Functions**:

1. **parse_vision_json()**: Robust JSON parser
   - Handles code fences (```json ... ```)
   - Extracts JSON from mixed text
   - Graceful fallback to empty ingredients

2. **normalize_ar_basic()**: Arabic text normalization
   - Removes diacritics and symbols
   - Unifies letter variants (أ → ا, ة → ه)
   - Lowercases for comparison

---

### 8. **Shopping Integration** (`shopping_integration.py`)

**Purpose**: Generates shopping suggestions for missing ingredients

**Current Implementation**: Placeholder for HungryStation

**Output Format**:
```json
{
  "item": "طماطم",
  "quantity": 1,
  "unit": "علبة",
  "vendor": "HungryStation",
  "estimated_price": "12.45 SAR",
  "product_url": "https://hungerstation.com/search?q=..."
}
```

**Future Enhancements**: Real API integration with delivery services

---

### 9. **Legacy Orchestrator** (`agents.py`)

**Status**: Deprecated (replaced by LangGraph)

**Purpose**: Original pipeline implementation before LangGraph migration

**Retained Functions**:
- `analyze_image_api()`: Wrapper for LangGraph compatibility
- `suggest_recipes_agent()`: Wrapper for LangGraph compatibility
- `process_recipe_request()`: Full legacy pipeline (unused)

**Note**: Kept for reference and backward compatibility

---

## 🔄 Complete Data Flow

### Request Flow:
```
1. Client sends POST /api/chef/start
   ├─ image_base64
   ├─ meal_type (optional)
   ├─ time_limit (optional)
   ├─ servings (optional)
   └─ cuisines (optional)

2. FastAPI creates ChefState
   └─ session_id: UUID
   └─ preferences: {meal_type, time_limit, servings, cuisines}

3. LangGraph Node: Vision
   ├─ analyze_fridge_image(image_base64)
   ├─ Uses Qwen2.5-VL model
   └─ Returns: {"ingredients": [...], "notes": "..."}

4. LangGraph Node: NameFixer
   ├─ fix_ingredients_names(ingredients)
   ├─ Lookup: EN2AR, ZH2AR dictionaries
   ├─ Fallback: LLM translation
   └─ Returns: ingredients with Arabic names

5. LangGraph Node: Prepare
   ├─ sanitize_items() - remove buckets, merge duplicates
   ├─ split by confidence (0.5 threshold)
   ├─ ensure minimum 3 used items
   ├─ apply_policy() - dough rules, time limits
   └─ Returns: used_items, uncertain_items, policy

6. LangGraph Node: Generate
   ├─ generate_recipe({ingredients, preferences, policy})
   ├─ Uses Qwen3 models with structured output
   ├─ Respects policies and constraints
   └─ Returns: SuggestedRecipe model

7. LangGraph Node: Post-Processing
   ├─ estimate_missing(used_items, recipe.ingredients_needed)
   ├─ get_shopping_suggestions(missing_items)
   └─ Returns: missing_items, shopping_suggestions

8. LangGraph Node: Assemble
   ├─ Combines all data into final_payload
   └─ Returns: complete response structure

9. FastAPI returns ChefOutput
   └─ Client receives JSON response
```

### State Transitions:
```
START
  ↓
vision → namefixer → prepare → generate → post → assemble
                                                      ↓
                                                     END
```

---

## 🚀 Deployment Configuration

### **Dependencies** (`requirements.txt`):
```
# Core LangChain ecosystem
langchain
langchain-openai
langchain-core
langchain-community

# Utilities
python-dotenv
pydantic
requests

# Backend framework
fastapi
uvicorn
```

### **Environment Variables**:
```
OPENAI_API_KEY=sk-...           # OpenRouter API key
NAMEFIXER_MODEL=qwen/qwen-2.5-72b-instruct:free
```

### **Deployment Platforms**:

**1. Render** (`render.yaml`):
```yaml
- type: web
  name: chefai
  env: python
  region: singapore
  buildCommand: pip install -r requirements.txt
  startCommand: uvicorn chef_backend.main:app --host 0.0.0.0 --port 10000
  plan: free
```

**2. Railway** (`railway.toml`):
```toml
[build]
builder = "railway/python"

[start]
cmd = "uvicorn chef_backend.main:app --host 0.0.0.0 --port $PORT"
```

**3. Heroku** (`Procfile`):
```
web: uvicorn chef_backend.main:app --host 0.0.0.0 --port $PORT
```

**Runtime**: Python 3.10+

---

## 📁 Project Structure

```
ChefAI/
├── chef_backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI server entry point
│   ├── langgraph_core.py          # LangGraph workflow orchestration
│   ├── agents.py                  # Legacy orchestrator (deprecated)
│   ├── vision_agent.py            # Image analysis with Qwen2.5-VL
│   ├── namefixer_agent.py         # Name translation to Arabic
│   ├── recipe_generator.py        # Recipe generation with Qwen3
│   ├── ontology.py                # Translation dictionaries
│   ├── utils.py                   # Helper functions
│   ├── shopping_integration.py    # Shopping suggestions (placeholder)
│   └── cache/                     # Cached results (JSON files)
│
├── chef_frontend/                 # (Currently empty)
│
├── docs/
│   └── architecture_overview.md   # This document
│
├── .env.example                   # Environment variables template
├── .gitignore
├── requirements.txt               # Python dependencies
├── runtime.txt                    # Python version
├── Procfile                       # Heroku deployment
├── railway.toml                   # Railway deployment
├── render.yaml                    # Render deployment
└── README.md                      # Setup guide
```

---

## 🎯 Key Design Decisions

### 1. **LangGraph State Machine**
- **Why**: Provides clear, debuggable workflow
- **Benefits**: Easy to extend, modify, and test individual nodes
- **Alternative**: Traditional function chaining (more coupled)

### 2. **Qwen Models via OpenRouter**
- **Why**: Free tier, good multilingual support (EN/ZH/AR)
- **Vision**: Qwen2.5-VL-32B for image analysis
- **Text**: Qwen3 series (30B/14B/4B) for recipe generation
- **Fallback**: Multiple models for rate limit resilience

### 3. **Dual Translation Strategy**
- **Dictionaries First**: Fast, reliable for common items
- **LLM Fallback**: Handles rare/specialized ingredients
- **Hybrid**: Balances performance and coverage

### 4. **Confidence-Based Filtering**
- **Threshold**: 0.5 for used vs uncertain
- **Minimum Items**: 3 items to ensure viable recipes
- **Promotion**: Uncertain items promoted if too few used items

### 5. **Policy-Driven Recipe Generation**
- **Dough Policy**: Prevents suggesting "make dough" without basics
- **Cooking Rules**: Never cook lettuce/cucumber on heat
- **Generic Term Ban**: Forces specific ingredient names

### 6. **Caching System**
- **Purpose**: Debugging and analysis
- **Format**: JSON files with timestamps
- **Location**: `chef_backend/cache/`

---

## 🔒 Error Handling

### **Vision Agent**:
- Empty ingredients list if model fails
- Length error handling with partial response parsing
- Graceful fallback to empty state

### **Recipe Generator**:
- Fallback chain through 3 models
- Rate limit resilience
- Structured error messages

### **LangGraph Nodes**:
- Each node handles errors independently
- Error propagation through state
- Error field in final payload

### **FastAPI**:
- HTTP 500 for system errors
- Detailed error messages for debugging
- CORS-enabled error responses

---

## 🔮 Future Enhancements

### **Planned Features**:
1. **Real Shopping Integration**: HungryStation/Jahez API
2. **Nutrition Calculation**: Calorie and macro tracking
3. **User Preferences**: Dietary restrictions, allergies
4. **Recipe Rating**: User feedback loop
5. **Multi-Image Support**: Multiple fridge sections
6. **Recipe History**: Save and retrieve past recipes
7. **Frontend Development**: Web/mobile interface

### **Technical Improvements**:
1. **Caching Layer**: Redis for faster responses
2. **Async Processing**: Background tasks for image analysis
3. **Model Fine-tuning**: Custom Qwen model for Saudi ingredients
4. **Database Integration**: PostgreSQL for recipe storage
5. **Authentication**: User accounts and sessions
6. **Monitoring**: Logging, metrics, error tracking

---

## 📝 Notes

### **Arabic Language Support**:
- All output text in Arabic (except English names from vision)
- Normalization handles dialectical variations
- Classical Arabic (فصحى) preferred for recipes

### **Chinese Integration**:
- Vision model uses Chinese prompts (better results)
- Chinese ingredient names supported (ZH2AR dictionary)
- Seamless translation to Arabic

### **Confidence Scoring**:
- Vision model provides confidence per ingredient
- Used to filter uncertain detections
- Helps prioritize ingredient usage

### **Session Management**:
- UUID-based sessions for tracking
- Stateless API (no server-side session storage)
- Cache files preserve session data

---

## 🧪 Testing

### **Local Testing**:
```bash
# Run vision agent test
python chef_backend/vision_agent.py

# Run recipe generator test  
python chef_backend/recipe_generator.py

# Run full orchestrator test
python chef_backend/agents.py

# Run FastAPI server
uvicorn chef_backend.main:app --reload
```

### **API Testing**:
```bash
# Test endpoint with curl
curl -X POST http://localhost:8000/api/chef/start \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "...",
    "meal_type": "Dinner",
    "time_limit": "30m",
    "servings": 2
  }'
```

---

## 📚 References

- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **OpenRouter**: https://openrouter.ai/
- **Qwen Models**: https://huggingface.co/Qwen
- **FastAPI**: https://fastapi.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/

---

**Last Updated**: November 13, 2025  
**Version**: 1.0 - LangGraph Integrated with Shopping  
**Maintainers**: ChefAI Team
