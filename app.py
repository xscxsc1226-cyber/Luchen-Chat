import streamlit as st
from openai import OpenAI
import time
import re
import json
import os
from PIL import Image
import base64
from datetime import datetime
from uuid import uuid4

# ===================== 0. 身份验证逻辑 =====================

def check_password():
    """如果密码正确则返回 True，否则显示输入框并返回 False。"""
    def password_entered():
        if st.session_state["password"] == "20060308qi":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown(
            """
            <style>
            .auth-container {
                max-width: 400px;
                margin: 100px auto;
                padding: 30px;
                background-color: rgba(255,255,255,0.9);
                border-radius: 15px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stApp { background-color: #EDEDED; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.title("🌹 不信")
        st.caption("欢迎回到你的专属空间")
        st.text_input(
            "请输入访问密码以继续",
            type="password",
            on_change=password_entered,
            key="password",
        )
        st.markdown('</div>', unsafe_allow_html=True)
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("密码错误，请重新输入。")
        return False
    else:
        return st.session_state["password_correct"]

if not check_password():
    st.stop()


# ===================== 1. 配置 & 文件管理 =====================

USER_PROFILE_FILE = "user_profile.json"
APP_SETTINGS_FILE = "app_settings.json"
CHARACTERS_FILE = "characters.json"
MOMENTS_FILE = "moments.json"

def load_data(file_path, default_val):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.endswith(".json"):
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return default_val
            else:
                return f.read()
    return default_val

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        if file_path.endswith(".json"):
            json.dump(data, f, ensure_ascii=False, indent=4)
        else:
            f.write(str(data))

def process_uploaded_image(uploaded_file, target_size=None):
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            if target_size:
                image = image.resize(target_size)
            from io import BytesIO
            buffered = BytesIO()
            image_format = uploaded_file.type.split("/")[1].upper()
            if image_format == "JPG":
                image_format = "JPEG"
            image.save(buffered, format=image_format)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:{uploaded_file.type};base64,{img_str}"
        except Exception as e:
            st.error(f"图片处理失败: {e}")
            return None
    return None

def get_avatar_display(avatar_data, default_emoji):
    if avatar_data and isinstance(avatar_data, str) and avatar_data.startswith("data:image"):
        return avatar_data
    return default_emoji

def load_characters():
    default_char = {
        "id": "luchen",
        "name": "陆沉",
        "avatar": None,
        "persona": "你现在是陆沉。你温文尔雅、掌控欲强。请用温和且有掌控感的语气回复。回复请拆分成1-5个短句，中间用'|'分隔。",
        "memory": "目前还没有特殊的共同回忆。",
        "messages": [],
        "api_key": "",
        "model": "deepseek-chat",
    }
    data = load_data(CHARACTERS_FILE, None)
    if not data:
        save_data(CHARACTERS_FILE, [default_char])
        return [default_char]
    return data

def save_characters(characters):
    save_data(CHARACTERS_FILE, characters)

def load_moments():
    data = load_data(MOMENTS_FILE, [])
    if not isinstance(data, list):
        return []
    return data

def save_moments(moments):
    save_data(MOMENTS_FILE, moments)

# 初始化基础数据
user_profile = load_data(
    USER_PROFILE_FILE, {"nickname": "玩家", "avatar": None, "global_api_key": "", "global_model": "deepseek-chat"}
)
app_settings = load_data(APP_SETTINGS_FILE, {"background_image": None})
characters = load_characters()
moments = load_moments()

def get_current_char():
    if "current_char_id" not in st.session_state and characters:
        st.session_state.current_char_id = characters[0]["id"]
    for c in characters:
        if c["id"] == st.session_state.get("current_char_id"):
            return c
    return characters[0] if characters else None

current_char = get_current_char()

def get_effective_api_info(char):
    char_api_key = (char or {}).get("api_key") or ""
    char_model = (char or {}).get("model") or ""
    api_key = char_api_key or user_profile.get("global_api_key", "")
    model = char_model or user_profile.get("global_model", "deepseek-chat")
    return api_key, model

# ===================== 2. 页面配置 & 全局样式 =====================

st.set_page_config(
    page_title="不信",
    page_icon="🌹",
    layout="centered", # 使用居中布局更像手机屏幕
    initial_sidebar_state="collapsed",
)

# 隐藏默认元素并注入微信样式
st.markdown(
    """
<style>
    /* 隐藏 Streamlit 的 Header 和 Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 调整主页面背景和边距 */
    .stApp {
        background-color: #EDEDED;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 80px;
        max-width: 600px; /* 模拟手机屏幕宽度 */
    }
    
    /* 聊天气泡样式优化 */
    .chat-bubble-row { display: flex; margin-bottom: 16px; align-items: flex-start; }
    .chat-bubble-row.other { justify-content: flex-start; }
    .chat-bubble-row.me { justify-content: flex-end; }
    
    .chat-bubble-avatar { width: 40px; height: 40px; border-radius: 6px; overflow: hidden; margin: 0 10px; flex-shrink: 0; background-color: #fff;}
    .chat-bubble-avatar img { width: 100%; height: 100%; object-fit: cover; }
    
    .chat-bubble-content {
        max-width: 70%;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 15px;
        line-height: 1.5;
        position: relative;
        word-wrap: break-word;
    }
    .chat-bubble-other { background-color: #FFFFFF; border: 1px solid #EAEAEA; }
    .chat-bubble-me { background-color: #95EC69; }

    /* 朋友圈卡片样式 */
    .moment-card {
        background: #FFFFFF;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* 去除 tertiary 按钮的边框，使其更像原生 Tab 或列表项 */
    button[kind="tertiary"] {
        padding: 10px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 背景图处理
if app_settings.get("background_image"):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{app_settings["background_image"]}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ===================== 3. 状态管理 =====================

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "不信"
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "main" # main(主界面) 或 chat(聊天界面)

def switch_tab(name: str):
    st.session_state.active_tab = name
    st.session_state.view_mode = "main"

def enter_chat(char_id: str):
    st.session_state.current_char_id = char_id
    st.session_state.view_mode = "chat"

def exit_chat():
    st.session_state.view_mode = "main"

# ===================== 4. 页面渲染逻辑 =====================

def render_chat_list_page():
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>不信</h3>", unsafe_allow_html=True)

    for char in characters:
        messages = char.get("messages", [])
        last_msg = messages[-1]["content"] if messages else "还没有开始聊天"
        last_time = datetime.now().strftime("%H:%M") if messages else ""
        avatar_src = get_avatar_display(char.get("avatar"), "🌹")
        
        # 使用 Columns 模拟列表项
        col1, col2 = st.columns([1, 4])
        with col1:
            if avatar_src.startswith('data:image'):
                st.markdown(f'<img src="{avatar_src}" style="width:50px;height:50px;border-radius:6px;object-fit:cover;">', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="width:50px;height:50px;background:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:24px;">{avatar_src}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='font-size: 16px; font-weight: 500; color: #333;'>{char.get('name','未命名')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 14px; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{last_msg}</div>", unsafe_allow_html=True)
        
        if st.button(f"进入与 {char.get('name')} 的会话", key=f"btn_chat_{char['id']}", use_container_width=True, type="tertiary"):
            enter_chat(char['id'])
            st.rerun()
        st.markdown("<hr style='margin: 5px 0 10px 0; border: none; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

def render_chat_session():
    global current_char
    current_char = get_current_char()
    
    # 顶部导航条：返回按钮
    col_back, col_title, col_empty = st.columns([1, 3, 1])
    with col_back:
        if st.button("⬅️ 返回", type="tertiary"):
            exit_chat()
            st.rerun()
    with col_title:
        st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:18px; margin-top:8px;'>{current_char['name']}</div>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top:0;'>", unsafe_allow_html=True)

    user_avatar = get_avatar_display(user_profile.get("avatar"), "👤")
    char_avatar = get_avatar_display(current_char.get("avatar"), "🌹")
    messages = current_char.get("messages", [])

    # 渲染气泡
    for m in messages:
        role = m.get("role", "assistant")
        content = m.get("content", "")
        is_user = role == "user"
        row_class = "me" if is_user else "other"
        avatar_src = user_avatar if is_user else char_avatar
        bubble_class = "chat-bubble-me" if is_user else "chat-bubble-other"
        
        avatar_html = f'<img src="{avatar_src}" />' if avatar_src.startswith('data:image') else f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:20px;">{avatar_src}</div>'
        
        if is_user:
            html = f"""
            <div class="chat-bubble-row {row_class}">
                <div class="chat-bubble-content {bubble_class}">{content}</div>
                <div class="chat-bubble-avatar">{avatar_html}</div>
            </div>
            """
        else:
            html = f"""
            <div class="chat-bubble-row {row_class}">
                <div class="chat-bubble-avatar">{avatar_html}</div>
                <div class="chat-bubble-content {bubble_class}">{content}</div>
            </div>
            """
        st.markdown(html, unsafe_allow_html=True)

    # 输入区：st.chat_input 自动停靠底部
    prompt = st.chat_input("想和 TA 说点什么？")
    if prompt:
        api_key, model_choice = get_effective_api_info(current_char)
        if not api_key:
            st.error("请先在个人设置中填写 API Key。")
            return

        current_char["messages"].append({"role": "user", "content": prompt})
        save_characters(characters)
        st.rerun() # 立即刷新显示用户输入

    # 如果最后一条是 user 消息，则触发大模型回复
    if messages and messages[-1]["role"] == "user":
        with st.spinner("对方正在输入..."):
            try:
                api_key, model_choice = get_effective_api_info(current_char)
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                core_mem = current_char.get("memory", "暂无")
                current_char_setting = current_char.get("persona", "")

                system_prompt = f"""{current_char_setting}\n【目前的长期核心记忆】：{core_mem}"""
                MAX_RECENT_CONTEXT = 10
                formatted_context = [{"role": m["role"], "content": m["content"]} for m in current_char["messages"][-MAX_RECENT_CONTEXT:-1]]
                full_messages = [{"role": "system", "content": system_prompt}] + formatted_context + [{"role": "user", "content": messages[-1]["content"]}]

                response = client.chat.completions.create(model=model_choice, messages=full_messages)
                raw_answer = response.choices[0].message.content
                parts = [p.strip() for p in re.split(r"[｜| \n]+", raw_answer) if p.strip()]

                for part in parts:
                    time.sleep(0.5)
                    current_char["messages"].append({"role": "assistant", "content": part})

                save_characters(characters)
                st.rerun()
            except Exception as e:
                st.error(f"连接失败：{e}")


def render_contacts_page():
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>通讯录</h3>", unsafe_allow_html=True)

    for idx, char in enumerate(characters):
        with st.container():
            st.markdown('<div class="moment-card">', unsafe_allow_html=True)
            cols = st.columns([1, 3, 1])
            with cols[0]:
                avatar_src = get_avatar_display(char.get("avatar"), "🌹")
                if isinstance(avatar_src, str) and avatar_src.startswith("data:image"):
                    st.markdown(f'<img src="{avatar_src}" width="50" height="50" style="border-radius:6px; object-fit:cover;">', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="width:50px;height:50px;border-radius:6px;background:#FFEFF4;display:flex;align-items:center;justify-content:center;font-size:24px;">{avatar_src}</div>', unsafe_allow_html=True)
            with cols[1]:
                st.write(f"**{char.get('name','未命名角色')}**")
                st.caption(char.get("persona", "")[:20] + "...")
            with cols[2]:
                if st.button("发消息", key=f"send_msg_{idx}", type="primary"):
                    enter_chat(char["id"])
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("➕ 添加虚拟角色"):
        with st.form("add_char_form"):
            new_avatar_file = st.file_uploader("角色头像", type=["png", "jpg", "jpeg"])
            new_name = st.text_input("角色昵称")
            new_persona = st.text_area("角色设定（Prompt）")
            provider_model = st.selectbox("模型选择", ["deepseek-chat", "gpt-4o", "kimi"], index=0)
            api_key_input = st.text_input("专属 API Key (留空则用全局)", type="password")
            
            if st.form_submit_button("保存角色", use_container_width=True):
                if not new_name.strip():
                    st.error("请填写角色昵称。")
                else:
                    avatar_b64 = process_uploaded_image(new_avatar_file, (100, 100))
                    new_char = {
                        "id": f"char_{uuid4().hex}",
                        "name": new_name.strip(),
                        "avatar": avatar_b64,
                        "persona": new_persona.strip() or "你是一个温柔的虚拟恋人，会用关心的语气和玩家聊天。",
                        "memory": "目前还没有特殊的共同回忆。",
                        "messages": [],
                        "api_key": api_key_input.strip(),
                        "model": provider_model,
                    }
                    characters.append(new_char)
                    save_characters(characters)
                    st.success("角色已创建。")
                    time.sleep(1)
                    st.rerun()


def render_moments_page():
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>发现 · 朋友圈</h3>", unsafe_allow_html=True)

    with st.expander("📷 发布新动态", expanded=False):
        with st.form("post_moment_form"):
            text = st.text_area("这一刻的想法……")
            image_file = st.file_uploader("配图（可选）", type=["png", "jpg", "jpeg"])
            if st.form_submit_button("发表", use_container_width=True):
                if not text.strip() and not image_file:
                    st.error("请至少输入文字或上传图片。")
                else:
                    img_b64 = process_uploaded_image(image_file) if image_file else None
                    moments.append({
                        "id": uuid4().hex,
                        "author": "user",
                        "text": text.strip(),
                        "image": img_b64,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "comments": [],
                    })
                    save_moments(moments)
                    st.rerun()

    if not moments:
        st.info("还没有任何动态，来发布第一条吧。")
        return

    for m in sorted(moments, key=lambda x: x.get("created_at", ""), reverse=True):
        st.markdown('<div class="moment-card">', unsafe_allow_html=True)
        st.markdown(f"<div style='color:#576B95; font-weight:bold; margin-bottom:8px;'>{user_profile.get('nickname','我')}</div>", unsafe_allow_html=True)
        
        if m.get("text"):
            st.write(m["text"])
        if m.get("image"):
            st.markdown(f'<img src="{m["image"]}" style="max-width:100%;border-radius:4px;margin:8px 0;">', unsafe_allow_html=True)
        
        st.caption(m.get('created_at','').replace('T', ' '))

        # 展示评论
        if m.get("comments"):
            st.markdown("<div style='background:#F3F3F5; padding:8px; border-radius:4px; margin-top:10px;'>", unsafe_allow_html=True)
            for c in m.get("comments", []):
                name = user_profile.get("nickname", "我") if c.get("author_type") == "user" else next((ch["name"] for ch in characters if ch["id"] == c.get("author_id")), "角色")
                st.markdown(f"<span style='color:#576B95;font-weight:bold;'>{name}</span>: <span style='color:#333;'>{c.get('text','')}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        cols = st.columns([2, 1])
        with cols[0]:
            role_for_comment = st.selectbox("互动角色", ["我"] + [c["name"] for c in characters], key=f"sel_{m['id']}", label_visibility="collapsed")
        with cols[1]:
            if st.button("💬 评论", key=f"btn_{m['id']}", use_container_width=True):
                # 这里可以扩展弹出对话框让用户输入，或者触发 AI 自动评论
                # 为保持极简，这里暂留入口，你可以按原逻辑扩展
                st.toast("可在原代码基础上绑定具体输入或AI生成逻辑")
        st.markdown('</div>', unsafe_allow_html=True)

def render_profile_page():
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>我</h3>", unsafe_allow_html=True)
    
    st.markdown('<div class="moment-card">', unsafe_allow_html=True)
    cols = st.columns([1, 3])
    with cols[0]:
        preview = get_avatar_display(user_profile.get("avatar"), "👤")
        if isinstance(preview, str) and preview.startswith("data:image"):
            st.markdown(f'<img src="{preview}" width="60" height="60" style="border-radius:6px; object-fit:cover;">', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="width:60px;height:60px;border-radius:6px;background:#EAEAEA;display:flex;align-items:center;justify-content:center;font-size:30px;">{preview}</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"<div style='font-size:20px; font-weight:bold; margin-top:10px;'>{user_profile.get('nickname','玩家')}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("⚙️ 基础与模型设置"):
        nickname = st.text_input("昵称", value=user_profile.get("nickname", "玩家"))
        global_api_key = st.text_input("全局 API Key", type="password", value=user_profile.get("global_api_key", ""))
        global_model = st.selectbox("默认模型", ["deepseek-chat", "gpt-4o", "kimi"], index=0)
        
        if st.button("保存设置", use_container_width=True, type="primary"):
            user_profile["nickname"] = nickname.strip()
            user_profile["global_api_key"] = global_api_key.strip()
            user_profile["global_model"] = global_model
            save_data(USER_PROFILE_FILE, user_profile)
            st.success("设置已保存！")
            time.sleep(1)
            st.rerun()

# ===================== 5. 视图路由与底部 TabBar =====================

# 路由渲染
if st.session_state.view_mode == "chat":
    render_chat_session()
else:
    if st.session_state.active_tab == "不信":
        render_chat_list_page()
    elif st.session_state.active_tab == "通讯录":
        render_contacts_page()
    elif st.session_state.active_tab == "发现":
        render_moments_page()
    elif st.session_state.active_tab == "我":
        render_profile_page()

# 只有在主界面时，才在页面最底部渲染 TabBar
if st.session_state.view_mode == "main":
    st.markdown("<br><br><br>", unsafe_allow_html=True) # 占位防遮挡
    st.markdown("""
        <style>
        .bottom-tab-container {
            position: fixed;
            bottom: 0; left: 0; right: 0;
            background: #F7F7F7;
            border-top: 1px solid #E0E0E0;
            padding: 10px 0 calc(10px + env(safe-area-inset-bottom)) 0;
            z-index: 999;
        }
        </style>
        <div class="bottom-tab-container"></div>
    """, unsafe_allow_html=True)
    
    # 将 Streamlit 原生 columns 强制下沉
    tab_container = st.container()
    with tab_container:
        cols = st.columns(4)
        tabs = [("💬 不信", "不信"), ("👥 通讯录", "通讯录"), ("🌍 发现", "发现"), ("👤 我", "我")]
        for i, (label, name) in enumerate(tabs):
            with cols[i]:
                # 当前激活态按钮给予主色高亮
                btn_type = "primary" if st.session_state.active_tab == name else "tertiary"
                if st.button(label, use_container_width=True, type=btn_type, key=f"tab_{name}"):
                    switch_tab(name)
                    st.rerun()