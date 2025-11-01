
import streamlit as st, requests, time, os, json

st.set_page_config(
    page_title="Place Extraction (Template Only)",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==== 全局 CSS（与原版一致，略） ====
st.markdown("""
<style>
/* 省略：与原版相同的 UI 样式，保持外观一致 */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=Inter:wght@400;600&display=swap');
:root{ --bg:#0A0F1E; --panel:#0F1628; --text:#E8EEFF; --muted:#9FB1D6; --primary:#54F0FF; --secondary:#9B5CFF; --danger:#FF5470;
 --primary-10a: rgba(84,240,255,.10); --primary-12a: rgba(84,240,255,.12); --primary-18a: rgba(84,240,255,.18);
 --primary-22a: rgba(84,240,255,.22); --primary-25a: rgba(84,240,255,.25); --primary-35a: rgba(84,240,255,.35);
 --primary-55a: rgba(84,240,255,.55); --aurora-cyan-07a: rgba(84,240,255,.07); --aurora-violet-06a: rgba(155,92,255,.06);
 --radius:16px; --border-outer:rgba(255,255,255,.06); --border-inner:rgba(255,255,255,.18); }
html, body, [data-testid="stAppViewContainer"]{
 background: radial-gradient(1200px 800px at 70% -10%, var(--aurora-cyan-07a), transparent 60%),
             radial-gradient(900px 600px at 20% 110%, var(--aurora-violet-06a), transparent 60%), var(--bg) !important;
 background-size: 120% 120%, 120% 120%, auto; animation: auroraShift 26s ease-in-out infinite alternate; color: var(--text); }
@keyframes auroraShift{ 0%{background-position:70% -10%, 20% 110%, 0 0;} 100%{background-position:60% -15%, 25% 115%, 0 0;} }
.block-container{ padding-top: 2.4rem; } .stMarkdown, .stText, h1,h2,h3,h4,p,span,div{ font-family: "Space Grotesk","Inter",system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans","PingFang SC","Microsoft YaHei",sans-serif; color: var(--text); }
a { color: var(--primary) !important; } [data-testid="stSidebar"]{ background: rgba(15,22,40,.65) !important; backdrop-filter: blur(10px); border-right: 1px solid rgba(255,255,255,.08); }
.card{ position:relative; background: rgba(15,22,40,.88); backdrop-filter: blur(12px); border-radius: var(--radius);
       box-shadow: 0 6px 24px rgba(0,0,0,.35); outline: 1px solid var(--border-outer); padding: 16px; }
.card:before{ content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none; box-shadow: inset 0 0 0 1px var(--border-inner); }
.msg.glass{ background: rgba(15,22,40,.55); border: 1px solid var(--border-outer); border-radius: 14px; padding: 10px 14px;
            box-shadow: 0 0 16px var(--primary-22a); margin: 6px 0; }
.stButton>button{ width: 100%; border-radius: 999px; padding: .68rem 1.1rem; background: linear-gradient(180deg, var(--primary-18a), var(--primary-12a));
                  color: var(--text); border:1px solid var(--primary-35a); box-shadow: 0 6px 24px var(--primary-22a);
                  backdrop-filter: blur(6px); letter-spacing:.02em; transition: transform .18s ease, box-shadow .18s ease, background .18s ease, filter .18s ease; }
.stButton>button:hover{ transform: translateY(-1.5px) scale(1.025); box-shadow:0 10px 30px var(--primary-35a); filter: drop-shadow(0 0 6px var(--primary-12a)); }
.stButton>button:active{ transform: translateY(0) scale(0.995); box-shadow:0 0 18px var(--primary-22a); }
textarea, input[type="text"], [data-baseweb="input"] input{ background: rgba(15,22,40,.55) !important; color: var(--text) !important;
  border-radius: 12px !important; border: 1px solid rgba(255,255,255,.12) !important; }
textarea:focus, input[type="text"]:focus, [data-baseweb="input"] input:focus{
  border-color: var(--primary-55a) !important; box-shadow: 0 0 0 3px var(--primary-18a), 0 0 22px var(--primary-12a) !important; animation: focusPulse 2.4s ease-in-out infinite; }
@keyframes focusPulse{ 0%,100%{ box-shadow: 0 0 0 3px var(--primary-18a), 0 0 14px var(--primary-10a); }
  50% { box-shadow: 0 0 0 3px var(--primary-18a), 0 0 26px var(--primary-22a); } }
.badge{ display:inline-flex; align-items:center; gap:.4rem; padding:.28rem .7rem; border-radius:999px; font-size:.75rem; border:1px solid var(--primary-35a);
        background: linear-gradient(180deg, var(--primary-12a), transparent); color:var(--text);
        box-shadow: inset 0 0 12px var(--primary-10a), 0 0 12px var(--primary-12a); }
.badge:before{ content:""; width:.48rem; height:.48rem; border-radius:999px; background: var(--primary); box-shadow: 0 0 10px var(--primary); }
.progress{ height:6px; width:100%; background:rgba(255,255,255,.08); border-radius:999px; overflow:hidden; }
.progress>span{ display:block; height:100%; background: linear-gradient(90deg, var(--primary-10a), var(--primary), var(--primary-10a));
                background-size:200% 100%; animation: shimmer 2.2s linear infinite; border-radius:inherit; }
@keyframes shimmer { 0% { background-position:-200% 0; } 100% { background-position:200% 0; } }
[data-testid="stAlert"]{ background: rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.12); border-radius:12px; }
</style>
""", unsafe_allow_html=True)

# ==== 侧边栏 ====
st.sidebar.header("Backend")
api_host = st.sidebar.text_input("API host", "http://127.0.0.1:8000")

# 桥接文件路径
default_bridge = os.environ.get("CARLA_BRIDGE_JSON", "carla_command.json")
bridge_path = st.sidebar.text_input("Bridge file path", default_bridge)

# Minimap HTTP 端点
minimap_url = st.sidebar.text_input("Minimap HTTP endpoint", os.environ.get("MINIMAP_URL","http://127.0.0.1:8765/set_route"))

c1,c2,c3 = st.sidebar.columns(3)
if c1.button("Health", use_container_width=True):
    try:
        st.sidebar.success(requests.get(f"{api_host}/health", timeout=5).json())
    except Exception as e:
        st.sidebar.error(f"Health failed: {e}")
if c3.button("Shutdown", use_container_width=True):
    try:
        st.sidebar.warning(requests.post(f"{api_host}/shutdown", timeout=5).json())
    except Exception as e:
        st.sidebar.error(f"Shutdown failed: {e}")

# ==== 顶部卡片 ====
st.markdown("""
<div class="card" style="padding:20px 20px 14px 20px; margin-top: 16px; margin-bottom: 24px;">
 <div style="display:flex;align-items:center;gap:12px;">
  <div style="height:40px;width:40px;border-radius:12px; background:linear-gradient(180deg, var(--primary-25a), var(--primary-10a));
              outline:1px solid var(--primary-35a); box-shadow: 0 0 24px var(--primary-22a); display:grid;place-items:center;">🧭</div>
  <div>
   <div style="font-weight:600;font-size:20px;letter-spacing:.02em;">Place Extraction (Template)</div>
   <div style="color:var(--muted);font-size:12px;margin-top:2px;">FastAPI + Streamlit · No LLM</div>
  </div>
  <div style="margin-left:auto;"><span class="badge">Online</span></div>
 </div>
 <div class="progress" style="margin-top:12px;"><span></span></div>
</div>
""", unsafe_allow_html=True)
st.caption("Try: “从 家 到 中央广场” 或 “Drive from Home to Central Square”")

# ==== 历史会话 ====
if "history" not in st.session_state:
    st.session_state.history = []
if "last_route" not in st.session_state:
    st.session_state.last_route = {"origin": None, "destination": None}

# ==== 工具函数 ====
def write_bridge(path: str, origin: str, destination: str):
    try:
        payload = {"ts": time.time(),
                   "origin": {"name": (origin or "").strip().lower()},
                   "destination": {"name": (destination or "").strip().lower()}}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True, None
    except Exception as e:
        return False, str(e)

def send_to_minimap_http(url: str, origin: str, destination: str):
    try:
        payload = {"origin":{"name": origin.strip().lower()},
                   "destination":{"name": destination.strip().lower()},
                   "ts": time.time()}
        r = requests.post(url, json=payload, timeout=5)
        return bool(getattr(r, "ok", False)), (None if getattr(r, "ok", False) else f"HTTP {r.status_code}")
    except Exception as e:
        return False, str(e)

# ==== 聊天表单 ====
with st.form("chat"):
    msg = st.text_area("Your message / 您的消息", height=120,
                       placeholder="e.g., I’m leaving Greenwood District at 7:15 pm to Central Square by driving")
    c1,c2,c3 = st.columns(3)
    with c1:
        max_new = st.number_input("Max new tokens / 最大新令牌数（无模型，仅占位）", 32, 2048, 512, 32)
    with c2:
        temp = st.slider("Temperature / 温度（无模型，仅占位）", 0.0, 1.5, 0.7, 0.05)
    with c3:
        submitted = st.form_submit_button("Send / 发送")

# 额外按钮：把“上一次识别的起终点”发到小地图（先 HTTP，失败回落文件桥）
colx, coly = st.columns([1,1])
with colx:
    if st.button("Send last origin/destination to Minimap", use_container_width=True):
        ori = st.session_state.last_route.get("origin")
        dst = st.session_state.last_route.get("destination")
        if ori and dst:
            ok, err = send_to_minimap_http(minimap_url, ori, dst)
            if ok:
                st.success(f"Sent to minimap via HTTP: {ori} -> {dst}")
            else:
                st.warning(f"HTTP failed: {err}; fallback to file bridge...")
                ok2, err2 = write_bridge(bridge_path, ori, dst)
                if ok2: st.success(f"Bridge updated: {ori} -> {dst} ({bridge_path})")
                else:   st.error(f"Write bridge failed: {err2}")
        else:
            st.warning("No previous origin/destination recognized yet.")

# ==== 处理请求 ====
if submitted and msg.strip():
    with st.spinner("Calling backend / 调用后端中..."):
        try:
            r = requests.post(f"{api_host}/chat",
                              json={"message":msg,"max_new_tokens":int(max_new),"temperature":float(temp)},
                              timeout=60)
            r.raise_for_status()
            data = r.json()

            # 历史
            st.session_state.history.append({"role":"user","content":msg})
            tag = "（模板兜底）"  # 纯模板
            pushed = " ✅ 已直发小地图" if data.get("pushed_to_minimap") else ""
            st.session_state.history.append({"role":"assistant",
                "content": f"{data.get('reply','')}\n\n> 输出模式 / Mode: {tag}{pushed}"})

            # 信息卡片
            colA,colB,colC = st.columns([1,1,2])
            with colA:
                st.markdown(f"""<div class="card"><b>Model</b><br>
                    <span style="color:var(--muted);">none</span></div>""", unsafe_allow_html=True)
            with colB:
                st.markdown(f"""<div class="card"><b>Places</b><br>
                    <span style="color:var(--muted);">{data.get('places',[])}</span></div>""", unsafe_allow_html=True)
            with colC:
                st.markdown(f"""<div class="card"><b>Route</b><br>
                    <span style="color:var(--muted);">From: </span>{data.get('origin')}
                    &nbsp;→&nbsp; <span style="color:var(--muted);">To: </span>{data.get('destination')}
                    </div>""", unsafe_allow_html=True)

            # === 识别到起终点 → 先 HTTP，失败回落写桥 ===
            origin = (data.get("origin") or "").strip().lower()
            dest   = (data.get("destination") or "").strip().lower()
            if origin and dest:
                st.session_state.last_route = {"origin": origin, "destination": dest}
                ok, err = send_to_minimap_http(minimap_url, origin, dest)
                if ok:
                    st.success(f"Minimap updated via HTTP: {origin} -> {dest}")
                else:
                    st.warning(f"HTTP send failed ({err}), fallback to file bridge...")
                    ok2, err2 = write_bridge(bridge_path, origin, dest)
                    if ok2: st.success(f"Bridge updated: {origin} -> {dest} ({bridge_path})")
                    else:   st.error(f"Failed to write bridge: {err2}")
            else:
                st.info("No origin/destination recognized to send to minimap.")

        except Exception as e:
            st.error(f"Request failed / 请求失败：{e}")

# ==== 手动覆盖 ====
st.markdown("### Manual override / 手动覆盖")
colm1, colm2 = st.columns(2)
with colm1:
    man_ori = st.text_input("Origin（地名或 x,y）", "")
with colm2:
    man_dst = st.text_input("Destination（地名或 x,y）", "")

def _parse_name_or_xy(s: str):
    s = (s or "").strip()
    if "," in s:
        try:
            xs, ys = s.split(",", 1)
            return {"x": float(xs), "y": float(ys)}
        except Exception:
            pass
    return {"name": s.lower()}

colb1, colb2 = st.columns(2)
with colb1:
    if st.button("Send via HTTP → Minimap", use_container_width=True):
        if man_ori and man_dst:
            try:
                payload = {"origin": _parse_name_or_xy(man_ori),
                           "destination": _parse_name_or_xy(man_dst),
                           "ts": time.time()}
                r = requests.post(minimap_url, json=payload, timeout=5)
                if getattr(r,"ok",False):
                    st.success("Sent to minimap via HTTP.")
                else:
                    st.error(f"HTTP send failed: {getattr(r,'status_code', 'unknown')}")
            except Exception as e:
                st.error(f"HTTP send error: {e}")
        else:
            st.warning("Please fill both origin and destination.")
with colb2:
    if st.button("Write to bridge file", use_container_width=True):
        if man_ori and man_dst:
            ori_name = man_ori.strip().lower()
            dst_name = man_dst.strip().lower()
            ok, err = write_bridge(bridge_path, ori_name, dst_name)
            if ok: st.success(f"Wrote to {bridge_path}")
            else:  st.error(f"Write bridge failed: {err}")

# ==== 最近 12 条对话 ====
if st.session_state.history:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    for turn in st.session_state.history[-12:]:
        who = "你" if turn["role"] == "user" else "助手"
        st.markdown(f"<div class='msg glass'><b>{who}</b>: {turn['content']}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
