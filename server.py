import os
import asyncio
import json
from typing import Any, Dict, List
import re

from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util, ObjectId

from mcp.server.fastmcp import FastMCP, Context

from llama_cpp import Llama

# --- Config ---

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://admin:admin1234@<mongo-endpoint>/")

MONGO_DB = os.getenv("MONGO_DB", "myshop")

PRODUCTS_COLL = os.getenv("PRODUCTS_COLL", "products")

MODEL_PATH = os.getenv("MODEL_PATH", "Phi-3-mini-4k-instruct-q4.gguf")

LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "256"))

# --- Init MCP ---

mcp = FastMCP("llamacpp-mongo-server")

# --- Init Mongo (motor async) ---

mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo[MONGO_DB]
products = db[PRODUCTS_COLL]

# --- Init LLM (sync) ---

llm = Llama(model_path=MODEL_PATH)
# Helper: serialize Mongo docs to JSON-safe form

def doc_to_json(doc: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json_util.dumps(doc))

# Helper: run llama in thread to avoid blocking

def llm_sync_generate(prompt: str, max_tokens: int = LLM_MAX_TOKENS) -> str:
    out = llm(prompt, max_tokens=max_tokens, echo=False)
    return out["choices"][0]["text"]



async def llm_generate(prompt: str, max_tokens: int = LLM_MAX_TOKENS) -> str:

 return await asyncio.to_thread(llm_sync_generate, prompt, max_tokens)



# ----------------------

# Tools exposed to MCP

# ----------------------



@mcp.tool()

async def get_product_by_id(product_id: str) -> str:
    """Returns a single product JSON given its ObjectId or string id."""
    print(f"get_product_by_id called with id={product_id}")
    try:
        _id = ObjectId(product_id)
        doc = await products.find_one({"_id": _id})
    except Exception:
        doc = await products.find_one({"id": product_id})
    if not doc:
        return "{}"
    return json.dumps(doc_to_json(doc))

# ---------------------
# Tools exposed to MCP
# ----------------------


# Add a mapping from possible LLM outputs to normalized category names
# Normalization map
CATEGORY_MAP = {
 "dress": "dress",
 "dresses": "dress",
 "dre": "dress",
 "shirt": "shirt",
 "shirts": "shirt",
 "t-shirt": "t-shirt",
 "tshirts": "t-shirt",
 "jeans": "jeans",
 "kurta": "kurta",
 "saree": "saree",
 "shorts": "shorts",
 "jacket": "jacket",
 "skirt": "skirt"
}

@mcp.tool()
async def nl_to_mongo_filter(nl_query: str, ctx: Context) -> str:
    await ctx.info("nl_to_mongo_filter called")
    prompt = f"""
You are a safe assistant that converts user product search queries into a MongoDB filter JSON.
Respond ONLY as a single JSON object suitable as a Mongo filter. Keys should be product fields (like color, material, category, gender, season, price).
If a numeric comparison is present, use $lte/$gte. If nothing found, return {{}}.

User query:
\"\"\"{nl_query}\"\"\"
"""
    resp = await llm_generate(prompt, max_tokens=200)
    text = resp.strip()

    # extract JSON block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        await ctx.info("nl_to_mongo_filter: could not parse JSON from model output; returning empty filter")
        return "{}"
    json_str = text[start:end+1]
    try:
        parsed = json.loads(json_str)
    except Exception as e:
        await ctx.info(f"nl_to_mongo_filter: JSON parse failed: {e}; returning empty filter")
        return "{}"
    allowed_keys = {"color","material","category","gender","season","price","type","brand","size"}
    safe_filter = {}
    for k,v in parsed.items():
        if k in allowed_keys:
            # Normalize category
            if k == "category" and isinstance(v, str):
                v_lower = v.lower()
                safe_filter[k] = CATEGORY_MAP.get(v_lower, v_lower)
            else:
                safe_filter[k] = v
    return json.dumps(safe_filter)


@mcp.tool()
async def search_products(filter_json: dict, limit: int = 10, ctx: Context = None) -> str:

    """
    Flexible search:
        - Optional fields included if present
        - Category does partial match (regex)
    """
    if ctx:
        await ctx.info(f"search_products called with filter={filter_json}, limit={limit}")
    mongo_filter = {}
    for k, v in filter_json.items():
        if k == "category":
            # regex for partial match (case-insensitive)
            mongo_filter[k] = {"$regex": f"^{re.escape(v)}", "$options": "i"}
        else:
            mongo_filter[k] = v
    cursor = products.find(mongo_filter).limit(limit)
    docs = []
    async for d in cursor:
       docs.append(doc_to_json(d))
    # return in expected format
    return json.dumps({"products": docs})

@mcp.tool()

async def recommend_for_profile(profile_json: Dict[str, Any], limit: int = 6) -> str:
    """Recommend products matching profile."""
    print(f"recommend_for_profile called with profile={profile_json}")
    filt = {}
    if "preferred_material" in profile_json:
        filt["material"] = profile_json["preferred_material"]
    if "season" in profile_json:
        filt["season"] = profile_json["season"]
    if "gender" in profile_json:
        filt["gender"] = profile_json["gender"]
    cursor = products.find(filt).limit(limit)
    docs = []
    async for d in cursor:
        docs.append(doc_to_json(d))
    return json.dumps(docs)

@mcp.tool()
async def summarize_products(product_docs_json: dict, ctx: Context) -> str:
    """
    Summarize products for the user, handling empty results and limiting token usage.
    """
    if ctx:
        await ctx.info("summarize_products called (summarizing returned product docs)")
    products_list = product_docs_json.get("products", [])
    if not products_list:
        return "No matching products found — try adjusting your filters!"
    # Trim details to avoid exceeding context window
    trimmed_products = []
    for p in products_list:
        trimmed = {
            "title": p.get("title"),
            "description": p.get("description"),
            "color": p.get("color"),
            "material": p.get("material"),
            "season": p.get("season"),
            "price": p.get("price"),
        }
        trimmed_products.append(trimmed)
    products_str = json.dumps(trimmed_products, indent=2)
    prompt = f"""
You are a helpful shopping assistant. Given the following products (JSON array), craft a concise, friendly user-facing response summarizing top matches and highlighting key details like material, season, color, and price. Return plain text.

Products JSON:
{products_str}
"""
    # Reduce max_tokens if needed
    resp = await llm_generate(prompt, max_tokens=150)
    return resp.strip()

# ---- Entrypoint ----

def main():
    print("🚀 Starting MCP LlamaCpp-Mongo Server...")
    mcp.run()

if __name__ == "__main__":
    main()