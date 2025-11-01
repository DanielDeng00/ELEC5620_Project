
import os, json, pathlib, regex as _re, time as _time
from typing import List, Optional, Dict
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

# ===== 地点解析 =====
_GZ = json.load(open("poi_gazetteer.json","r",encoding="utf-8"))
CANON=[s.lower() for s in _GZ["canonical"]]
ALIASES={k.lower():v.lower() for k,v in _GZ["aliases"].items()}
def _norm(s:str)->str: return (s or "").strip().lower()
def canonicalize(name:str)->str:
    key=_norm(name)
    if key in CANON: return key
    if key in ALIASES: return ALIASES[key]
    for k in CANON:
        if key in k: return k
    return ""
_POI_ALT="|".join(_re.escape(n) for n in sorted(set(CANON+list(ALIASES.values())),key=len,reverse=True))
GAZ_RE=_re.compile(rf"\b({_POI_ALT})\b",_re.IGNORECASE)
def extract_locations_from_text(text:str):
    t=(text or "").strip(); hits=[]
    m=_re.search(r"from\s+(.+?)\s+to\s+(.+?)(?:\s+by\s+\w+)?$",t,_re.IGNORECASE)
    if m:
        a,b=m.group(1),m.group(2); ca,cb=canonicalize(a),canonicalize(b)
        if ca: hits.append(ca)
        if cb and cb!=ca: hits.append(cb)
    m2=_re.search(r"从\s*([\u4e00-\u9fa5A-Za-z0-9 .'-]+?)\s*到\s*([\u4e00-\u9fa5A-Za-z0-9 .'-]+)",t)
    if m2:
        a,b=m2.group(1),m2.group(2); ca,cb=canonicalize(a),canonicalize(b)
        if ca and ca not in hits: hits.append(ca)
        if cb and cb not in hits: hits.append(cb)
    for mt in GAZ_RE.finditer(t):
        c=canonicalize(mt.group(1))
        if c and (not hits or hits[-1]!=c): hits.append(c)
    seen,ordered=set(),[]
    for k in hits:
        if k not in seen: seen.add(k); ordered.append(k)
    return ordered
def infer_origin_dest(names):
    if len(names)>=2: return names[0],names[-1]
    if len(names)==1: return "home",names[0]
    return None,None

TIME_PAT = _re.compile(
    r"(?:(?:at|@)\s*)?("
    r"(?:\d{1,2}:\d{2}\s*(?:am|pm))|"
    r"(?:\d{1,2}\s*(?:am|pm))|"
    r"(?:\d{1,2}:\d{2})|"
    r"(?:[上下]午?\s*\d{1,2}(?::\d{1,2})?分?)|"
    r"(?:\d{1,2}点\d{0,2}分?)"
    r")",
    _re.IGNORECASE
)
VEH_MAP = {"drive":"驾车","driving":"驾车","car":"驾车","taxi":"打车","uber":"打车",
           "walk":"步行","walking":"步行","on foot":"步行","bike":"骑行","cycling":"骑行",
           "bus":"公交","subway":"地铁","metro":"地铁","train":"火车"}
def detect_vehicle(text:str)->str:
    t=_norm(text)
    for k,v in VEH_MAP.items():
        if k in t: return v
    if "步行" in text: return "步行"
    if "地铁" in text: return "地铁"
    if "公交" in text: return "公交"
    if "打车" in text or "出租" in text: return "打车"
    if "骑行" in text or "单车" in text: return "骑行"
    if "自驾" in text or "开车" in text: return "驾车"
    return "出行"

def to_24h(s:str)->str:
    ss=s.strip()
    m=_re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", ss, _re.IGNORECASE)
    if not m: return ss
    h=int(m.group(1)); mm=int(m.group(2) or 0); ap=(m.group(3) or "").lower()
    if "下" in ss or "下午" in ss or "晚上" in ss:
        if h<12: h+=12
    if ap=="pm" and h<12: h+=12
    if ap=="am" and h==12: h=0
    return f"{h:02d}:{mm:02d}"

# ===== 模板回复（无 LLM） =====
def template_plan(user_msg:str)->str:
    def to24(x:str):
        m=_re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", x, _re.IGNORECASE)
        if not m: return x
        h=int(m.group(1)); mm=int(m.group(2) or 0); ap=(m.group(3) or "").lower()
        if "下" in x or "下午" in x or "晚上" in x:
            if h<12: h+=12
        if ap=="pm" and h<12: h+=12
        if ap=="am" and h==12: h=0
        return f"{h:02d}:{mm:02d}"
    places = extract_locations_from_text(user_msg)
    origin, dest = infer_origin_dest(places)
    times = [to24(m.group(1)) for m in TIME_PAT.finditer(user_msg)]
    leave = times[0] if times else None
    veh = detect_vehicle(user_msg)
    zh = any('\u4e00' <= c <= '\u9fff' for c in user_msg)
    if zh:
        lines = []
        lines.append("行程建议（自动模板）：")
        if origin and dest: lines.append(f"- 出发地：{origin} → 目的地：{dest}")
        elif dest:          lines.append(f"- 出发地：home（默认） → 目的地：{dest}")
        else:               lines.append("- 目的地未识别，请补充地点信息。")
        if leave: lines.append(f"- 计划出发：{leave}")
        lines.append(f"- 交通方式：{veh}")
        if dest: lines.append(f"- 建议路线：从“{origin or 'home'}”前往“{dest}”，按导航行驶/步行。")
        lines.append("- 温馨提示：请预留 10–15 分钟机动时间，注意交通与天气。")
        return "\n".join(lines)
    else:
        lines = []
        lines.append("Trip suggestion (auto template):")
        if origin and dest: lines.append(f"- From: {origin} → To: {dest}")
        elif dest:          lines.append(f"- From: home (default) → To: {dest}")
        else:               lines.append("- Destination not recognized. Please provide a place.")
        if leave: lines.append(f"- Planned departure: {leave}")
        lines.append(f"- Mode: {veh if veh!='出行' else 'trip'}")
        if dest: lines.append(f"- Route: head from '{origin or 'home'}' to '{dest}' and follow navigation.")
        lines.append("- Tip: keep 10–15 min buffer; check traffic and weather.")
        return "\n".join(lines)

# ====== 小地图 HTTP 直发（后端侧）======
MINIMAP_URL = os.environ.get("MINIMAP_URL", "").strip()  # e.g. "http://127.0.0.1:8765/set_route"
def _post_minimap(origin:str, dest:str)->bool:
    if not (MINIMAP_URL and origin and dest): 
        return False
    try:
        payload = {"origin":{"name": origin.strip().lower()},
                   "destination":{"name": dest.strip().lower()},
                   "ts": _time.time()}
        import requests
        r = requests.post(MINIMAP_URL, json=payload, timeout=3)
        return bool(getattr(r, "ok", False))
    except Exception:
        return False

# ===== 写桥（可选）=====
def _write_bridge_if_enabled(origin: Optional[str], dest: Optional[str]):
    if not os.environ.get("WRITE_BRIDGE_FROM_BACKEND"): 
        return
    if not origin or not dest: 
        return
    bridge = os.environ.get("CARLA_BRIDGE_JSON", "carla_command.json")
    try:
        payload = {
            "ts": _time.time(),
            "origin": {"name": (origin or "").strip().lower()},
            "destination": {"name": (dest or "").strip().lower()}
        }
        with open(bridge, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ===== FastAPI =====
app = FastAPI(title="Template Place Extraction API (No LLM)", version="1.0.0")

class ChatIn(BaseModel):
    message: str
    max_new_tokens: Optional[int] = 220     # 保留字段以兼容前端
    temperature: Optional[float] = 0.7      # 保留字段以兼容前端

class ChatOut(BaseModel):
    reply: str
    mode: str
    model: str
    places: list
    origin: Optional[str]
    destination: Optional[str]
    pushed_to_minimap: bool = False

@app.get("/health")
def health():
    return {
        "ok": True,
        "model": None,         # 无模型
        "device": None,        # 无设备
        "loaded_in_4bit": False,
        "fewshot_examples": 0,
        "minimap_url": MINIMAP_URL,
    }

@app.post("/chat", response_model=ChatOut)
def chat(inb: ChatIn):
    raw = template_plan(inb.message)
    names = extract_locations_from_text(inb.message)
    origin, dest = infer_origin_dest(names)
    pushed = False
    if origin and dest:
        pushed = _post_minimap(origin, dest)    # 后端尝试 HTTP 直发小地图
        _write_bridge_if_enabled(origin, dest)  # 可选：按需写桥
    return ChatOut(
        reply=raw, mode="template", model="none",
        places=names, origin=origin, destination=dest,
        pushed_to_minimap=pushed
    )

@app.post("/shutdown")
async def shutdown(request: Request):
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1","localhost","::1"):
        raise HTTPException(status_code=403, detail="Local only")
    import threading, time, os as _os
    def _bye():
        time.sleep(0.2)
        _os._exit(0)
    threading.Thread(target=_bye, daemon=True).start()
    return {"ok": True, "msg": "Server exiting..."}
