import streamlit as st
import base64
from streamlit_cropper import st_cropper
from PIL import Image
import io
import datetime
import json
import os

# 페이지 전체 폭 설정
st.set_page_config(layout="wide", page_title="페어한소기록")

# --- 1. 로그인 섹션 (비밀번호 입력) ---
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

if not st.session_state.user_id:
    st.title("🔐 개인 채팅 공간 입장")
    st.write("본인만의 **비밀번호**를 입력하여 접속하세요. 입력한 비밀번호에 따라 별도의 저장 공간이 생성됩니다.")
    
    # 비밀번호 입력창
    user_input = st.text_input("비밀번호 입력", type="password", help="비밀번호가 다르면 다른 저장 목록이 나타납니다.")
    
    if st.button("입장하기", use_container_width=True):
        if user_input.strip():
            st.session_state.user_id = user_input.strip()
            st.rerun()
        else:
            st.error("비밀번호를 입력해 주세요.")
    
    st.info("💡 주의: Streamlit Cloud 환경에서는 서버 재시작 시 파일이 초기화될 수 있습니다.")
    st.stop()  # 로그인 전까지 아래 코드를 실행하지 않음

# --- 2. 데이터 관리 함수 (사용자 ID 기반) ---
# 비밀번호별로 고유한 파일명을 생성합니다.
USER_ID = st.session_state.user_id
DATA_FILE = f"chat_data_{USER_ID}.json"

def save_to_file():
    data = {
        "saved_chats": st.session_state.saved_chats,
        "me_pic": st.session_state.me_pic,
        "other_pic": st.session_state.other_pic,
        "me_name": st.session_state.me_name,
        "other_name": st.session_state.other_name
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_from_file():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

# --- 3. 데이터 및 세션 초기화 ---
loaded_data = load_from_file()

if "saved_chats" not in st.session_state:
    st.session_state.saved_chats = loaded_data["saved_chats"] if loaded_data else []
if "me_pic" not in st.session_state:
    # 기본값은 투명 이미지로 설정 (요청 반영)
    TRANSPARENT_PIXEL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    st.session_state.me_pic = loaded_data["me_pic"] if loaded_data else TRANSPARENT_PIXEL
if "other_pic" not in st.session_state:
    st.session_state.other_pic = loaded_data["other_pic"] if loaded_data else TRANSPARENT_PIXEL
if "me_name" not in st.session_state:
    st.session_state.me_name = loaded_data["me_name"] if loaded_data else "나"
if "other_name" not in st.session_state:
    st.session_state.other_name = loaded_data["other_name"] if loaded_data else "상대방"

if "messages" not in st.session_state: st.session_state.messages = []
if "editing_idx" not in st.session_state: st.session_state.editing_idx = None
if "show_settings" not in st.session_state: st.session_state.show_settings = False
if "chat_title" not in st.session_state: st.session_state.chat_title = "새로운 채팅"

# --- 4. 유틸리티 및 다이얼로그 함수 ---
def get_image_base64(img):
    if img is not None:
        try:
            buffered = io.BytesIO()
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(buffered, format="JPEG", quality=90)
            return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"
        except: return None
    return None

@st.dialog("채팅 삭제 확인")
def confirm_delete_modal(idx, title):
    st.warning(f"**정말로 '{title}'를 삭제하시겠습니까?**")
    st.markdown(
        f"<span style='color: #808080; font-size: 0.85rem;'>*삭제할 경우, '{title}' 의 모든 기록이 지워집니다.*</span>", 
        unsafe_allow_html=True
    )
    col1, col2 = st.columns(2)
    if col1.button("삭제", type="primary", use_container_width=True, key=f"real_del_{idx}"):
        st.session_state.saved_chats.pop(idx)
        save_to_file()
        st.rerun()
    if col2.button("취소", use_container_width=True, key=f"cancel_del_{idx}"): st.rerun()

@st.dialog("프로필 사진 설정")
def edit_profile_pic_modal(target_key):
    st.write("새 프로필 사진을 업로드하세요.")
    file = st.file_uploader("이미지 선택", type=['png','jpg','jpeg'], key=f"modal_f_{target_key}")
    if file:
        img = Image.open(file)
        max_size = 500
        if img.width > max_size:
            ratio = max_size / float(img.width)
            img = img.resize((max_size, int(img.height * ratio)), Image.Resampling.LANCZOS)
        cropped = st_cropper(img, realtime_update=True, box_color='#007AFF', aspect_ratio=(1,1), key=f"modal_cp_{target_key}")
        col1, col2 = st.columns(2)
        if col1.button("적용하기", use_container_width=True):
            st.session_state[f"{target_key}_pic"] = get_image_base64(cropped)
            save_to_file()
            st.rerun()
        if col2.button("취소", use_container_width=True): st.rerun()

# --- 5. 스타일 및 레이아웃 ---
st.markdown("""
<style>
    .chat-container { display: flex; flex-direction: column; gap: 15px; padding: 10px; }
    .message-row { display: flex; width: 100%; align-items: flex-start; margin-bottom: 5px; }
    .row-other { justify-content: flex-start; }
    .row-me { justify-content: flex-end; }
    .profile-pic { 
        width: 40px !important; height: 40px !important; 
        border-radius: 50% !important; object-fit: cover !important; 
        border: 2px solid #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex-shrink: 0;
    }
    .message-content { display: flex; flex-direction: column; max-width: 75%; }
    .me-content { align-items: flex-end; margin-right: 8px; }
    .other-content { align-items: flex-start; margin-left: 8px; }
    .sender-name { font-size: 12px; color: #8E8E93; margin-bottom: 2px; font-weight: 500; }
    .bubble { padding: 8px 12px; border-radius: 16px; font-size: 14px; word-wrap: break-word; }
    .other-bubble { background-color: #ffffff; color: #1C1C1E; border-top-left-radius: 2px; border: 1px solid #e5e5ea; }
    .me-bubble { background-color: #007AFF; color: white; border-top-right-radius: 2px; }
    [data-testid="stDialog"] div:has(canvas) { display: flex !important; justify-content: center !important; }
</style>
""", unsafe_allow_html=True)

# --- 6. 사이드바 (저장된 목록) ---
with st.sidebar:
    st.header(f"🔑 {USER_ID}님의 공간")
    if st.button("로그아웃 (나가기)", use_container_width=True):
        st.session_state.user_id = ""
        st.rerun()
    st.divider()
    st.subheader("📁 저장된 목록")
    if not st.session_state.saved_chats:
        st.info("저장된 채팅이 없습니다.")
    else:
        for idx, saved in enumerate(st.session_state.saved_chats):
            with st.expander(f"📌 {saved['title']}", expanded=False):
                st.caption(f"📅 {saved['date']}")
                c_load, c_del = st.columns(2)
                if c_load.button("로드", key=f"load_btn_{idx}"):
                    st.session_state.messages = list(saved['messages'])
                    st.session_state.me_pic = saved['me_pic']
                    st.session_state.other_pic = saved['other_pic']
                    st.session_state.me_name = saved.get('me_name', "나")
                    st.session_state.other_name = saved.get('other_name', "상대방")
                    st.session_state.chat_title = saved['title']
                    st.rerun()
                if c_del.button("삭제", key=f"del_btn_{idx}"):
                    confirm_delete_modal(idx, saved['title'])
    
    st.divider()
    if st.button("➕ 새 채팅 시작하기", use_container_width=True):
        st.session_state.messages = []
        st.session_state.editing_idx = None
        st.session_state.chat_title = "새로운 채팅"
        st.rerun()

# --- 7. 메인 화면 ---
if st.session_state.show_settings:
    _, col_main, col_settings = st.columns([0.05, 0.55, 0.4])
else:
    _, col_main, _ = st.columns([0.2, 0.6, 0.2])

with col_main:
    h_left, h_right = st.columns([0.9, 0.1])
    h_left.markdown(f"### 💬 {st.session_state.chat_title}")
    if h_right.button("⚙️"):
        st.session_state.show_settings = not st.session_state.show_settings
        st.rerun()

    chat_box = st.container(height=650)
    with chat_box:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for msg in st.session_state.messages:
            is_me = msg["role"] == "me"
            pic = st.session_state.me_pic if is_me else st.session_state.other_pic
            display_name = st.session_state.me_name if is_me else st.session_state.other_name
            if is_me:
                st.markdown(f'''<div class="message-row row-me"><div class="message-content me-content"><div class="sender-name">{display_name}</div><div class="bubble me-bubble">{msg["content"]}</div></div><img src="{pic}" class="profile-pic"></div>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''<div class="message-row row-other"><img src="{pic}" class="profile-pic"><div class="message-content other-content"><div class="sender-name">{display_name}</div><div class="bubble other-bubble">{msg["content"]}</div></div></div>''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- 8. 설정 섹션 ---
if st.session_state.show_settings:
    with col_settings:
        with st.expander("👤 프로필 및 이름", expanded=False):
            n1, n2 = st.columns(2)
            with n1: 
                new_me_name = st.text_input("나", value=st.session_state.me_name, key="set_me_n")
                if new_me_name != st.session_state.me_name:
                    st.session_state.me_name = new_me_name
                    save_to_file()
            with n2: 
                new_ot_name = st.text_input("상대", value=st.session_state.other_name, key="set_ot_n")
                if new_ot_name != st.session_state.other_name:
                    st.session_state.other_name = new_ot_name
                    save_to_file()
            st.write("**이미지 변경**")
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.image(st.session_state.me_pic, width=50)
                if st.button("나 변경", key="btn_me_pic", use_container_width=True): edit_profile_pic_modal("me")
            with p_col2:
                st.image(st.session_state.other_pic, width=50)
                if st.button("상대 변경", key="btn_ot_pic", use_container_width=True): edit_profile_pic_modal("other")

        with st.expander("📝 메시지 관리", expanded=False):
            e_idx = st.session_state.editing_idx
            with st.form("msg_form_wide", clear_on_submit=True):
                s_opt = st.radio("보내는 사람", [st.session_state.me_name, st.session_state.other_name], 
                                 index=0 if e_idx is None or st.session_state.messages[e_idx]["role"]=="me" else 1, horizontal=True)
                text = st.text_area("내용", value=st.session_state.messages[e_idx]["content"] if e_idx is not None else "", height=80)
                if st.form_submit_button("저장/수정", use_container_width=True):
                    if text.strip():
                        role = "me" if s_opt == st.session_state.me_name else "other"
                        if e_idx is not None:
                            st.session_state.messages[e_idx] = {"role": role, "content": text}
                            st.session_state.editing_idx = None
                        else: st.session_state.messages.append({"role": role, "content": text})
                        st.rerun()

            for i, m in enumerate(st.session_state.messages):
                l_col1, l_col2, l_col3 = st.columns([0.6, 0.2, 0.2])
                l_col1.write(f"{i+1}. {m['content'][:15]}..")
                if l_col2.button("✏️", key=f"e_{i}"):
                    st.session_state.editing_idx = i
                    st.rerun()
                if l_col3.button("🗑️", key=f"d_{i}"):
                    st.session_state.messages.pop(i)
                    st.rerun()

        with st.expander("💾 현재 대화 저장", expanded=False):
            input_title = st.text_input("채팅 제목 정하기", value=st.session_state.chat_title)
            st.session_state.chat_title = input_title
            if st.button("목록에 저장", use_container_width=True):
                if st.session_state.chat_title.strip() and st.session_state.messages:
                    st.session_state.saved_chats.append({
                        "title": st.session_state.chat_title, 
                        "date": datetime.datetime.now().strftime("%y-%m-%d %H:%M"),
                        "messages": list(st.session_state.messages),
                        "me_pic": st.session_state.me_pic, 
                        "other_pic": st.session_state.other_pic,
                        "me_name": st.session_state.me_name, 
                        "other_name": st.session_state.other_name
                    })
                    save_to_file()
                    st.success("저장 완료!")
                    st.rerun()
