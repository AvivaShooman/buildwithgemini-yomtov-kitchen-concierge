# YomTov Kitchen Concierge 🍽️🕯️

[![Agent Engine](https://img.shields.io/badge/Google%20Cloud-Agent%20Engine-4285F4?logo=googlecloud&logoColor=white)](https://cloud.google.com/vertex-ai)
[![ADK](https://img.shields.io/badge/Framework-Google%20ADK-34A853)](https://github.com/google/adk)
[![A2A Protocol](https://img.shields.io/badge/Protocol-A2A-EA4335)](https://a2a-protocol.org/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)

> **A conversational agent that helps Jewish families and holiday hosts plan festive meal menus, kitchen prep timelines, blech/warming drawer management, and grocery lists tailored to guest dietary needs, multi-day leftover strategies, Chol HaMoed transitions, and halachic cooking priorities (where Shabbat rules take precedence over Yom Tov) with a catalog of warming-safe seasonal Jewish recipes and holiday schedules.**

---

## 🌟 Key Features

1. **Household & Guest Dietary Memory (Zero-Tolerance Allergens)**
   - Persists family and guest profiles across conversations, including severe/mild allergies (celiac/gluten, tree nuts, sesame, dairy), dietary restrictions, and kashrut customs (Ashkenazi vs. Sephardic / Kitniyot).
   - Guarantees strict filtering so allergens are never recommended for meals attended by affected guests.

2. **Multi-Day Dish Rotation & 3-Criteria Feedback System**
   - Archives previous Yom Tov and Shabbat meal plans to ensure menu variety without repetitive heavy centerpieces across consecutive meals.
   - Evaluates and remembers dish performance across three distinct criteria on a 1–5 scale:
     - **Crowd Rating (1–5)**: Overall taste and popularity with guests.
     - **Ease of Prep (1–5)**: Preparation simplicity and stress level before Chag.
     - **Yom Tov Suitability (1–5)**: Durability on the blech or warming drawer without drying out or turning soggy.

3. **Jewish Calendar & Halachic Rule Engine (Hebcal Integration)**
   - Live integration with the Hebcal API to fetch upcoming holiday schedules, candle lighting times, and Havdalah times for any 5-digit US ZIP code.
   - Automatic detection of **Shabbat–Yom Tov overlaps**, enforcing strict Shabbat cooking rules (no flame transfer or fresh cooking) over Yom Tov allowances, plus distinct planning for Chol HaMoed.

4. **Blech & Warming Drawer Thermal Physics Scheduling**
   - Computes warming hours for each dish based on the meal sequence (from Friday evening dinner to Day 2 Yom Tov lunch, up to 24–36 hours).
   - Assigns physical blech heat zones: **Center (Direct Heat Zone)** for boiling soups, **Mid-Blech** for braises, and **Perimeter (Gentle Keep-Warm Zone)** to prevent scorching on delicate kugels.
   - Calculates liquid evaporation compensation (+1/2 cup to +1 cup broth, double crimped foil).
   - Enforces halachic readiness checkpoints (fully cooked before candle lighting, covered control knobs).

5. **Dynamic Scaled Grocery Lists**
   - Aggregates ingredients across selected recipes and scales portion quantities dynamically to match guest headcount.
   - Organizes ingredients by supermarket aisle (*Produce, Meat & Poultry, Fish, Refrigerated & Eggs, Pantry & Seasonings*) and saves lists directly to Firestore.

6. **Authentic Kosher Food Blog Recipe Search**
   - Grounded in authentic, tested holiday recipes directly retrieved from premier kosher culinary creators: **Melinda Strauss**, **Naomi Nachman (The Aussie Gourmet)**, and **Ruhama Shitrit (Ruhama's Food)**.

---

## ☁️ Google Cloud & AI Platform Architecture

| Google Cloud Tool / Service | How It Is Used in YomTov Kitchen Concierge |
|---|---|
| **Vertex AI Memory Bank** | Long-term cross-session memory service (`PreloadMemoryTool` & after-agent callbacks) storing persistent household profiles, guest allergies, past holiday menus, and 3-criteria dish feedback. |
| **Google Cloud Firestore (Native)** | High-performance NoSQL database storing structured holiday recipes, warming guidelines, evaporation compensation parameters, user ratings, and categorized grocery lists. |
| **Google Cloud Storage (GCS)** | Object storage bucket repository storing extracted holiday recipe datasets and knowledge artifacts for corpus ingestion. |
| **Vertex AI RAG Engine** | Vector Search RAG corpus indexed with 38 authentic kosher recipes from top culinary blogs, queried via semantic retrieval tool `search_recipe_rag_corpus`. |
| **A2UI (Agent-to-User Interface)** | Interactive UI card specifications designed to render multi-day meal timelines, blech layout maps, and recipe step cards in the web frontend. |
| **Image Generation (Vertex AI Imagen)** | Architecture for generating visual plating presentations and spatial 2D top-down blech heat-zone layout diagrams. |
| **Agent Engine / Reasoning Engine** | Managed deployment runtime hosting the ADK agent with full A2A Protocol compliance and enterprise telemetry. |

---

## 📁 Repository Structure

```
yomtov-kitchen-concierge/
├── app/
│   ├── agent.py                        # Root ADK agent definition & instructions
│   ├── fast_api_app.py                 # FastAPI backend server with A2A endpoints
│   └── app_utils/
│       ├── memory_tools.py             # Memory Bank tools (profiles, rotation, ratings)
│       ├── firestore_tools.py          # Firestore database tools (search, save, ratings)
│       ├── planning_tools.py           # Hebcal API, blech scheduler, grocery scaler
│       ├── rag_tools.py                # Vertex AI RAG retrieval tool
│       ├── services.py                 # Client initialization (Memory Bank, Firestore)
│       └── reasoning_engine_adapter.py # Agent Engine runtime adapter
├── data/
│   ├── rag_recipes.txt                 # Consolidated 38-recipe corpus document
│   └── recipes/                        # Individual scraped recipe markdown files
├── scripts/
│   ├── download_recipes.py             # Blog scraper (Melinda Strauss, Naomi Nachman, Ruhama)
│   ├── seed_firestore.py               # Seeds canonical warming-safe holiday recipes
│   └── create_rag_corpus.py            # Vertex AI RAG corpus provisioning script
├── tests/
│   ├── unit/                           # Unit tests for planning, memory, and firestore tools
│   └── integration/                    # E2E integration tests (RAG, agent flows, A2A)
├── project_brief.md                    # Project brief & requirements specification
├── pyproject.toml                      # Project dependencies & tool configurations
└── README.md                           # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- [agents-cli](https://github.com/google/agents-cli): `uv tool install google-agents-cli`

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/<your-username>/buildwithgemini-yomtov-kitchen-concierge.git
cd buildwithgemini-yomtov-kitchen-concierge

# Install dependencies using uv
uv sync
```

### 3. Running Automated Tests
```bash
GOOGLE_GENAI_USE_VERTEXAI=true uv run pytest tests/
```

### 4. Local Development & Playground
```bash
agents-cli playground
```

### 5. Deploying to Vertex AI Agent Runtime
```bash
agents-cli deploy --project <your-gcp-project-id> --no-confirm-project
```

---

## 📜 Halachic Cooking Notice

*YomTov Kitchen Concierge provides culinary assistance and algorithmic warming timelines based on standard halachic principles regarding Shabbat, Yom Tov, Havdalah, and blech management. For definitive rulings, consult your local Orthodox rabbi or halachic authority.*
