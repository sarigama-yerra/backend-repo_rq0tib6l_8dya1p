import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Set
from datetime import date

from database import db, create_document, get_documents
from schemas import Fighter, Fight

app = FastAPI(title="MMA Math API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "MMA Math Backend Running"}

# Utility helpers

def slugify(name: str) -> str:
    return "-".join(name.lower().split())

# Fighters endpoints

class CreateFighter(BaseModel):
    name: str

@app.post("/fighters", response_model=dict)
def create_fighter(payload: CreateFighter):
    slug = slugify(payload.name)
    # Ensure unique
    existing = db["fighter"].find_one({"slug": slug}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Fighter already exists")
    fighter = Fighter(name=payload.name, slug=slug)
    fighter_id = create_document("fighter", fighter)
    return {"id": fighter_id, "name": payload.name, "slug": slug}

@app.get("/fighters", response_model=List[dict])
def list_fighters(q: Optional[str] = None, limit: int = 50):
    filt = {}
    if q:
        filt = {"name": {"$regex": q, "$options": "i"}}
    docs = get_documents("fighter", filt, limit)
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
    return docs

# Fights endpoints

class CreateFight(BaseModel):
    winner: str
    loser: str
    event: Optional[str] = None
    method: Optional[str] = None
    round: Optional[int] = None
    fight_date: Optional[date] = None

@app.post("/fights", response_model=dict)
def create_fight(payload: CreateFight):
    if payload.winner == payload.loser:
        raise HTTPException(status_code=400, detail="Winner and loser must differ")
    # validate fighters exist
    w = db["fighter"].find_one({"slug": payload.winner}) if db else None
    l = db["fighter"].find_one({"slug": payload.loser}) if db else None
    if not w or not l:
        raise HTTPException(status_code=404, detail="Both fighters must exist")
    fight = Fight(**payload.model_dump())
    fight_id = create_document("fight", fight)
    return {"id": fight_id}

@app.get("/fights", response_model=List[dict])
def list_fights(limit: int = 100):
    docs = get_documents("fight", {}, limit)
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
    return docs

# MMA Math logic: Path where A beats B, B beats C => A beats C
# We represent directed graph edges winner -> loser

class MathQuery(BaseModel):
    source: str  # fighter slug A
    target: str  # fighter slug C
    max_depth: int = 4

@app.post("/mma-math")
def mma_math(query: MathQuery):
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")

    # Build adjacency from fights
    edges = db["fight"].find({}, {"winner": 1, "loser": 1, "_id": 0})
    adj: Dict[str, Set[str]] = {}
    for e in edges:
        adj.setdefault(e["winner"], set()).add(e["loser"])

    path = shortest_path(adj, query.source, query.target, max_depth=query.max_depth)
    if not path:
        return {"exists": False, "path": []}

    # Convert slugs to names for response
    names = {}
    slugs = list(set(path))
    fighters = db["fighter"].find({"slug": {"$in": slugs}}, {"name": 1, "slug": 1})
    for f in fighters:
        names[f["slug"]] = f["name"]

    steps = []
    for i in range(len(path) - 1):
        winner = path[i]
        loser = path[i + 1]
        fight = db["fight"].find_one({"winner": winner, "loser": loser})
        steps.append({
            "winner": {"slug": winner, "name": names.get(winner, winner)},
            "loser": {"slug": loser, "name": names.get(loser, loser)},
            "event": fight.get("event") if fight else None,
            "method": fight.get("method") if fight else None,
            "fight_date": fight.get("fight_date") if fight else None,
        })

    return {
        "exists": True,
        "source": {"slug": query.source, "name": names.get(query.source, query.source)},
        "target": {"slug": query.target, "name": names.get(query.target, query.target)},
        "path": path,
        "steps": steps
    }

# Simple BFS shortest path

def shortest_path(adj: Dict[str, Set[str]], src: str, dst: str, max_depth: int = 4):
    if src == dst:
        return [src]
    from collections import deque
    q = deque()
    q.append((src, [src]))
    visited = {src}
    depth = {src: 0}

    while q:
        node, path = q.popleft()
        if depth[node] >= max_depth:
            continue
        for nei in adj.get(node, set()):
            if nei == dst:
                return path + [nei]
            if nei not in visited:
                visited.add(nei)
                depth[nei] = depth[node] + 1
                q.append((nei, path + [nei]))
    return None


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available" if db is None else "✅ Connected",
    }
    try:
        if db is not None:
            response["collections"] = db.list_collection_names()[:10]
    except Exception as e:
        response["database"] = f"⚠️ {str(e)[:80]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
