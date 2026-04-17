import streamlit as st
from openai import OpenAI
import uuid
import json
import os
import base64

# ====== 0. 页面配置与精准 UI 校准 ======
st.set_page_config(page_title="AI 多模型网页版", page_icon="🎨", layout="centered")

st.markdown("""
    <style>
    /* 1. 彻底隐藏上传组件的原生装饰 */
    .stFileUploader section {
        padding: 0 !important;
        min-height: unset !important;
        border: none !important;
        background: transparent !important;
    }
    .stFileUploader [data-testid="stMarkdownContainer"] { display: none; }
    .stFileUploader section > div { display: none; }
    
    /* 2. 定位：精准放置在输入框的正左侧外部 */
    .stFileUploader {
        position: fixed;
        bottom: 27px;
        left: calc(50% - 415px); 
        width: 42px !important;
        height: 42px !important;
        z-index: 9999;
    }
    
    /* 3. 上传按钮样式 */
    .stFileUploader button {
        border-radius: 8px !important;
        width: 100% !important;
        height: 100% !important;
        padding: 0 !important;
        border: 1px solid #3d414b !important;
        background-color: #1e1e1e !important;
        color: #aaa !important;
        transition: 0.2s;
    }
    .stFileUploader button:hover {
        border-color: #ff4b4b !important;
        color: white !important;
    }

    /* 4. 输入框样式还原 */
    [data-testid="stChatInput"] textarea {
        padding-left: 15px !important; 
        border-radius: 8px !important;
    }
    
    /* 5. 预览提示框 */
    .upload-preview-tag {
        position: fixed;
        bottom: 80px;
        left: calc(50% - 415px);
        background: #262730;
        border: 1px solid #ff4b4b;
        padding: 4px 8px;
        border-radius: 5px;
        font-size: 11px;
        z-index: 10000;
        white-space: nowrap;
    }
    
    @media (max-width: 850px) {
        .stFileUploader { left: 10px !important; }
        [data-testid="stChatInput"] { padding-left: 55px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# ====== 1. 模型库配置 ======
MODELS_CONFIG = {
    "Gemini": {"base_url": "https://lumos.diandian.info/winky/gemini/v1", "fast": "google/gemini-2.0-flash", "think": "google/gemini-3.1-pro-preview", "vision": True},
    "OpenAI": {"base_url": "https://lumos.diandian.info/winky/openai/v1", "fast": "gpt-4o-mini", "think": "gpt-4o", "vision": True},
    "DeepSeek": {"base_url": "https://lumos.diandian.info/winky/deepseek/v1", "fast": "deepseek-chat", "think": "deepseek-reasoner", "vision": False},
    "Claude": {"base_url": "https://lumos.diandian.info/winky/claude/v1", "fast": "claude-3-5-haiku", "think": "claude-sonnet-4-5", "vision": True},
    "Qwen": {"base_url": "https://lumos.diandian.info/winky/qwen/v1", "fast": "qwen-plus", "think": "qwen-max", "vision": True},
    "Kimi": {"base_url": "https://lumos.diandian.info/winky/kimi/v1", "fast": "moonshot-v1-8k", "think": "moonshot-v1-32k", "vision": False}
}
DEFAULT_VENDOR = "Gemini"
DB_FILE = "chat_history_v2.json"

# ====== 2. 持久化逻辑 ======
def save_data():
    if "current_session_id" not in st.session_state: return
    data = {"sessions": st.session_state.sessions, "current_session_id": st.session_state.current_session_id, "api_key": st.session_state.api_key}
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return None
    return None

def img_to_base64(file):
    return base64.b64encode(file.getvalue()).decode()

def create_new_session():
    session_id = str(uuid.uuid4())[:8]
    st.session_state.sessions[session_id] = {"title": f"新对话 {len(st.session_state.sessions) + 1}", "messages": [], "vendor": DEFAULT_VENDOR, "mode": "快速"}
    st.session_state.current_session_id = session_id
    save_data()

# ====== 3. 数据初始化 ======
if "sessions" not in st.session_state:
    saved = load_data()
    if saved:
        st.session_state.sessions, st.session_state.current_session_id, st.session_state.api_key = saved["sessions"], saved["current_session_id"], saved.get("api_key", "")
    else:
        st.session_state.sessions, st.session_state.api_key = {}, ""
        create_new_session()

# ====== 4. 侧边栏 UI ======
with st.sidebar:
    st.title("⚙️ AI 设置 (已开启记忆)")
    if st.button("✨ 新建对话", use_container_width=True): create_new_session(); st.rerun()
    st.divider()
    
    session_ids = list(st.session_state.sessions.keys())
    selected_sid = st.radio("历史记录", options=session_ids, index=session_ids.index(st.session_state.current_session_id), format_func=lambda x: st.session_state.sessions[x]["title"])
    if selected_sid != st.session_state.current_session_id: st.session_state.current_session_id = selected_sid; st.rerun()
    
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("🗑️ 删除会话", use_container_width=True):
            if len(st.session_state.sessions) > 1:
                del st.session_state.sessions[st.session_state.current_session_id]
                st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
                save_data(); st.rerun()
    with c2: 
        if st.button("✏️ 重命名", use_container_width=True): st.session_state.rename_mode = True
    
    if st.session_state.get("rename_mode", False):
        new_title = st.text_input("对话名称", value=st.session_state.sessions[st.session_state.current_session_id]["title"])
        if st.button("确定"):
            st.session_state.sessions[st.session_state.current_session_id]["title"] = new_title
            st.session_state.rename_mode = False; save_data(); st.rerun()

    st.divider()
    curr_sess = st.session_state.sessions[st.session_state.current_session_id]
    curr_sess["vendor"] = st.selectbox("核心驱动", options=list(MODELS_CONFIG.keys()), index=list(MODELS_CONFIG.keys()).index(curr_sess.get("vendor", DEFAULT_VENDOR)), on_change=save_data)
    curr_sess["mode"] = st.radio("性能模式", ["快速", "思考"], index=0 if curr_sess.get("mode") == "快速" else 1, horizontal=True, on_change=save_data)
    
    active_id = MODELS_CONFIG[curr_sess["vendor"]]["fast"] if curr_sess["mode"] == "快速" else MODELS_CONFIG[curr_sess["vendor"]]["think"]
    st.caption(f"当前模型: `{active_id}`")
    
    st.session_state.api_key = st.text_input("API Key", type="password", value=st.session_state.api_key)

# ====== 5. 聊天记录展示 ======
curr_sess = st.session_state.sessions[st.session_state.current_session_id]
st.subheader(f"⚡ {curr_sess['vendor']} ({curr_sess['mode']})")

for message in curr_sess["messages"]:
    with st.chat_message(message["role"]):
        if message.get("origin_model"): st.caption(f"来自 {message['origin_model']}")
        content = message["content"]
        if isinstance(content, list):
            for item in content:
                if item["type"] == "text": st.markdown(item["text"])
                if item["type"] == "image_url": st.image(item["image_url"]["url"])
        else: st.markdown(content)

# ====== 6. 交互区与多文件处理修复 ======

if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0

# 新增 accept_multiple_files=True，并将变量名改为复数 uploaded_files
uploaded_files = st.file_uploader(
    "📎", 
    type=["png", "jpg", "jpeg", "pdf", "txt", "py", "docx"], 
    accept_multiple_files=True, 
    label_visibility="collapsed",
    key=f"up_v87_{st.session_state.uploader_key}"
)

if uploaded_files:
    if len(uploaded_files) == 1:
        preview_text = f"📎 待发送: {uploaded_files[0].name[:12]}..."
    else:
        preview_text = f"📎 待发送: {uploaded_files[0].name[:10]}... 等 {len(uploaded_files)} 个文件"
    st.markdown(f'<div class="upload-preview-tag">{preview_text}</div>', unsafe_allow_html=True)

if prompt := st.chat_input("在此输入指令..."):
    if not st.session_state.api_key:
        st.warning("请填写 API Key")
    else:
        vendor_cfg = MODELS_CONFIG[curr_sess['vendor']]
        active_model = vendor_cfg["fast"] if curr_sess["mode"] == "快速" else vendor_cfg["think"]
        
        # --- 多文件核心处理逻辑 ---
        content_to_send = [{"type": "text", "text": prompt}]
        appended_text = ""
        display_images = []
        display_files = []
        
        if uploaded_files:
            for file in uploaded_files:
                if file.type.startswith("image/") and vendor_cfg['vision']:
                    # 处理图片：转 base64 存入内容列表
                    content_to_send.append({"type": "image_url", "image_url": {"url": f"data:{file.type};base64,{img_to_base64(file)}"}})
                    display_images.append(file)
                else:
                    # 处理纯文本文件：读取并拼接到 prompt 中
                    try:
                        text_data = file.read().decode("utf-8")
                        appended_text += f"\n\n--- [附件: {file.name}] ---\n{text_data}"
                        display_files.append(file.name)
                    except Exception as e:
                        st.error(f"读取文件 {file.name} 失败: {str(e)}")

        # 如果有文本文件被读取，更新第一项的 text
        if appended_text:
            content_to_send[0]["text"] = prompt + appended_text

        # 用户气泡展示
        with st.chat_message("user"):
            st.markdown(prompt)
            # 一次性展示多张图片
            if display_images:
                st.image(display_images, width=200)
            # 展示附加了哪些文本文件
            if display_files:
                for fname in display_files:
                    st.caption(f"📄 附带文件: {fname}")

        # 如果只有文本/文本文件，直接存为字符串；如果有图片，按列表格式存
        save_content = content_to_send if display_images else content_to_send[0]["text"]
        
        curr_sess["messages"].append({"role": "user", "content": save_content})
        save_data()

        # AI 响应逻辑
        with st.chat_message("assistant"):
            origin_label = f"{curr_sess['vendor']}-{curr_sess['mode']}"
            st.caption(f"响应模型: {origin_label}")
            with st.spinner("思考中..."):
                try:
                    client = OpenAI(api_key=st.session_state.api_key, base_url=vendor_cfg["base_url"])
                    formatted_msgs = []
                    for m in curr_sess["messages"]:
                        m_content = m["content"]
                        if isinstance(m_content, str): m_content = [{"type": "text", "text": m_content}]
                        formatted_msgs.append({"role": m["role"], "content": m_content})

                    resp = client.chat.completions.create(model=active_model, messages=formatted_msgs)
                    answer = resp.choices[0].message.content
                    st.markdown(answer)
                    curr_sess["messages"].append({"role": "assistant", "content": answer, "origin_model": origin_label})
                    save_data()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        st.session_state.uploader_key += 1
        st.rerun()