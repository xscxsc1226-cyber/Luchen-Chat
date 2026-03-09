import streamlit as st
from openai import OpenAI
import time
import random
import re
import json
import os
from PIL import Image
import base64

# --- 0. 身份验证逻辑 ---
def check_password():
    """如果密码正确则返回 True，否则显示输入框并返回 False。"""
    def password_entered():
        """检查输入的密码是否正确。"""
        if st.session_state["password"] == "20060308qi":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 不在 session_state 中保留密码
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 还没输入过密码，显示输入界面
        st.markdown("""
            <style>
            .auth-container {
                max-width: 400px;
                margin: 100px auto;
                padding: 20px;
                background-color: rgba(255,255,255,0.8);
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.title("🌹 陆沉聊天室")
        st.text_input(
            "请输入访问密码以继续", type="password", on_change=password_entered, key="password"
        )
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("密码错误，请重新输入。")
        return False
    else:
        return st.session_state["password_correct"]

# 如果密码不正确，停止运行后续代码
if not check_password():
    st.stop()

# --- 1. Configuration & File Management ---
CHAT_LOG = "chat_log.json"
MEMORY_FILE = "core_memory.txt"
SETTING_FILE = "char_setting.txt"
USER_PROFILE_FILE = "user_profile.json"
CHAR_PROFILE_FILE = "char_profile.json"
APP_SETTINGS_FILE = "app_settings.json"

def load_data(file_path, default_val):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.endswith('.json'):
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return default_val
            else:
                return f.read()
    return default_val

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        if file_path.endswith('.json'):
            json.dump(data, f, ensure_ascii=False, indent=4)
        else:
            f.write(str(data))

# --- Initialize data ---
user_profile = load_data(USER_PROFILE_FILE, {"nickname": "玩家", "avatar": None})
char_profile = load_data(CHAR_PROFILE_FILE, {"nickname": "陆沉", "avatar": None})
app_settings = load_data(APP_SETTINGS_FILE, {"background_image": None})
saved_char_info = load_data(SETTING_FILE, "你现在是陆沉。你温文尔雅、掌控欲强。请用温和且有掌控感的语气回复。回复请拆分成1-5个短句，中间用'|'分隔。")
current_memory = load_data(MEMORY_FILE, "目前还没有特殊的共同回忆。")

# --- Function to handle image upload and conversion to base64 ---
def process_uploaded_image(uploaded_file, target_size=None):
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            if target_size:
                image = image.resize(target_size)
            
            from io import BytesIO
            buffered = BytesIO()
            image_format = uploaded_file.type.split('/')[1].upper()
            if image_format == 'JPG': image_format = 'JPEG'
            image.save(buffered, format=image_format)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:{uploaded_file.type};base64,{img_str}"
        except Exception as e:
            st.error(f"图片处理失败: {e}")
            return None
    return None

# --- Function to get avatar (emoji or base64) ---
def get_avatar_display(avatar_data, default_emoji):
    if avatar_data and avatar_data.startswith("data:image"):
        return avatar_data
    return default_emoji

# --- 2. Page Configuration & Layout ---
st.set_page_config(page_title="陆沉聊天室", page_icon="🌹", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for Layout and Background ---
bg_image_style = ""
if app_settings["background_image"]:
    bg_image_style = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url("{app_settings["background_image"]}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
    }}
    </style>
    """
st.markdown(bg_image_style, unsafe_allow_html=True)

# CSS to fix chat input at bottom and add some spacing
st.markdown("""
    <style>
    div[data-testid="stChatInput"] {
        position: fixed;
        bottom: 1rem;
        z-index: 1000;
        padding: 1rem 0;
    }
    .main .block-container {
        padding-bottom: 8rem;
    }
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# Page pillars: Chat area (left), Character Setting & Profile (right)
col_chat, col_right = st.columns([2, 1], gap="large")

# --- 3. Sidebar: System Settings ---
with st.sidebar:
    st.title("⚙️ 设置中心")
    st.markdown("---")
    
    with st.expander("👤 个人资料设置", expanded=False):
        st.subheader("你的资料")
        current_nickname = st.text_input("你的昵称", value=user_profile["nickname"], key="user_nickname")
        if current_nickname != user_profile["nickname"]:
            user_profile["nickname"] = current_nickname
            save_data(USER_PROFILE_FILE, user_profile)
        
        uploaded_user_avatar = st.file_uploader("上传你的头像", type=["png", "jpg", "jpeg"], key="user_avatar_uploader")
        new_user_avatar_base64 = process_uploaded_image(uploaded_user_avatar, target_size=(100, 100))
        if new_user_avatar_base64:
            user_profile["avatar"] = new_user_avatar_base64
            save_data(USER_PROFILE_FILE, user_profile)
            st.rerun()
        
        st.write("当前头像预览:")
        st.markdown(f'<img src="{get_avatar_display(user_profile["avatar"], "👤")}" width="50" style="border-radius: 50%;">', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("人物资料")
        current_char_remark = st.text_input("修改备注 (人物昵称)", value=char_profile["nickname"], key="char_nickname")
        if current_char_remark != char_profile["nickname"]:
            char_profile["nickname"] = current_char_remark
            save_data(CHAR_PROFILE_FILE, char_profile)
        
        uploaded_char_avatar = st.file_uploader("上传人物头像", type=["png", "jpg", "jpeg"], key="char_avatar_uploader")
        new_char_avatar_base64 = process_uploaded_image(uploaded_char_avatar, target_size=(100, 100))
        if new_char_avatar_base64:
            char_profile["avatar"] = new_char_avatar_base64
            save_data(CHAR_PROFILE_FILE, char_profile)
            st.rerun()

        st.write("当前头像预览:")
        st.markdown(f'<img src="{get_avatar_display(char_profile["avatar"], "🌹")}" width="50" style="border-radius: 50%;">', unsafe_allow_html=True)

    with st.expander("🖼️ 外观设置", expanded=False):
        uploaded_bg = st.file_uploader("上传聊天背景图", type=["png", "jpg", "jpeg"], key="bg_uploader")
        new_bg_base64 = process_uploaded_image(uploaded_bg)
        if new_bg_base64:
            app_settings["background_image"] = new_bg_base64
            save_data(APP_SETTINGS_FILE, app_settings)
            st.rerun()
        
        if app_settings["background_image"] and st.button("移除背景图", key="remove_bg"):
            app_settings["background_image"] = None
            save_data(APP_SETTINGS_FILE, app_settings)
            st.rerun()

    with st.expander("🔑 API设置", expanded=True):
        api_key = st.text_input("API Key", type="password", key="api_key_input")
        model_choice = st.selectbox("模型", ["deepseek-chat", "gpt-4o"], key="model_selectbox")
    
    st.markdown("---")
    if st.button("🚨 重置所有数据（记录+记忆）", key="reset_all_button"):
        files_to_reset = [CHAT_LOG, MEMORY_FILE]
        for f in files_to_reset:
            if os.path.exists(f): 
                os.remove(f)
        st.session_state.messages = []
        st.rerun()

# --- 4. Right Column: Character Setting area ---
with col_right:
    st.subheader("🎭 人物设定")
    char_info_input = st.text_area(
        "在此输入陆沉的具体人设等：",
        value=saved_char_info,
        height=400,
        key="char_info_textarea"
    )
    if char_info_input != saved_char_info:
        saved_char_info = char_info_input
        save_data(SETTING_FILE, char_info_input)
        st.success("人设已同步后台")

    st.divider()
    st.subheader("📝 核心记忆提取")
    st.info(current_memory)

# --- 5. Left Column: Chat Display area ---
with col_chat:
    st.header(f"与 {char_profile['nickname']} 的对话")
    
    def resolve_avatar(role):
        if role == "user":
            return get_avatar_display(user_profile["avatar"], "👤")
        elif role == "assistant":
            return get_avatar_display(char_profile["avatar"], "🌹")
        return None

    if "messages" not in st.session_state:
        if os.path.exists(CHAT_LOG):
            with open(CHAT_LOG, "r", encoding="utf-8") as f:
                try:
                    st.session_state.messages = json.load(f)
                except json.JSONDecodeError:
                    st.session_state.messages = []
        else:
            st.session_state.messages = []

    for m in st.session_state.messages:
        current_avatar = resolve_avatar(m["role"])
        with st.chat_message(m["role"], avatar=current_avatar):
            st.markdown(m["content"])

# --- 6. Chat Input ---
if prompt := st.chat_input("想和他说点什么？"):
    if not api_key:
        st.sidebar.error("请先在侧边栏输入 API Key")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_data(CHAT_LOG, st.session_state.messages)
        st.rerun()

# --- 7. Response Logic ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    if api_key:
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            core_mem = load_data(MEMORY_FILE, "暂无")
            current_char_setting = load_data(SETTING_FILE, saved_char_info)
            
            system_prompt = f"""{current_char_setting}\n【目前的长期核心记忆】：{core_mem}"""
            
            MAX_RECENT_CONTEXT = 10
            formatted_context = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-MAX_RECENT_CONTEXT:]]
            full_messages = [{"role": "system", "content": system_prompt}] + formatted_context
            
            response = client.chat.completions.create(model=model_choice, messages=full_messages)
            raw_answer = response.choices[0].message.content
            parts = [p.strip() for p in re.split(r'[｜| \n]+', raw_answer) if p.strip()]

            for part in parts:
                time.sleep(1.0) # 模拟思考
                current_avatar = get_avatar_display(char_profile["avatar"], "🌹")
                with col_chat:
                    with st.chat_message("assistant", avatar=current_avatar):
                        st.markdown(part)
                st.session_state.messages.append({"role": "assistant", "content": part})
            
            save_data(CHAT_LOG, st.session_state.messages)

            # 记忆提取逻辑 (保持不变)
            if len(st.session_state.messages) % 10 == 0:
                 summary_prompt = f"请提取关于玩家（{user_profile['nickname']}）的新特质：{raw_answer}"
                 memo_messages = [{"role": "system", "content": "你是一个记忆整理助手。"}, {"role": "user", "content": summary_prompt}]
                 try:
                     memo_res = client.chat.completions.create(model=model_choice, messages=memo_messages)
                     extracted = memo_res.choices[0].message.content.strip()
                     current_memory = f"{current_memory}，{extracted}" if current_memory != "目前还没有特殊的共同回忆。" else extracted
                     save_data(MEMORY_FILE, current_memory)
                 except: pass

        except Exception as e:
            st.sidebar.error(f"连接失败：{e}")
