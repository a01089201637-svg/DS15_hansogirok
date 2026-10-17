import streamlit as st
import base64
from streamlit_cropper import st_cropper
from PIL import Image
import io
import datetime
import json
import os
import hashlib

# 페이지 전체 폭 설정
st.set_page_config(layout="wide", page_title="나만의 비밀 채팅 앱")

# --- 1. 사용자 계정 데이터베이스 관리 ---
USER_DB_FILE = "users_db.json"

def load_user_db():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_db(db):
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- 2. 로그인/회원가입 섹션 (중앙 집중 레이아웃) ---
if "user_session" not in st.session_state:
    st.session_state.user_session = None

if not st.session_state.user_session:
    # 화면을 3분할하여 중앙에만 로그인창 배치 (좌우 여백을 넓게 줌)
    _, login_col, _ = st.columns([1.2, 1.0, 1.2]) 
    
    with login_col:
        st.markdown("<br><br>", unsafe_allow_html=True) # 상단 여백
        st.title("💬페어한소기록")
        
        tab1, tab2 = st.tabs(["로그인", "계정 생성"])
        user_db = load_user_db()

        with tab1:
            st.subheader("로그인")
            l_id = st.text_input("아이디", key="login_id")
            l_pw = st.text_input("비밀번호", type="password", key="login_pw")
            if st.button("로그인 하기", use_container_width=True):
                if l_id in user_db and user_db[l_id] == make_hash(l_pw):
                    st.session_state.user_session = make_hash(l_id + l_pw)
                    st.session_state.display_id = l_id
                    st.success(f"{l_id}님, 환영합니다!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")

        with tab2:
            st.subheader("새 계정 만들기")
            new_id = st.text_input("새 아이디", key="new_id")
            new_pw = st.text_input("새 비밀번호", type="password", key="new_pw")
            confirm_pw = st.text_input("비밀번호 확인", type="password", key="confirm_pw")
            
            if st.button("가입하기", use_container_width=True):
                if not new_id or not new_pw:
                    st.warning("아이디와 비밀번호를 모두 입력해주세요.")
                elif new_id in user_db:
                    st.error("이미 존재하는 아이디입니다.")
                elif new_pw != confirm_pw:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    user_db[new_id] = make_hash(new_pw)
                    save_user_db(user_db)
                    st.success("계정이 생성되었습니다! 로그인해주세요.")
    
    st.stop() # 로그인 전까지 아래의 넓은 레이아웃 코드를 읽지 않음

# --- 3~5. 데이터 관리 및 유틸리티 (기존과 동일) ---
SESSION_KEY = st.session_state.user_session
DATA_FILE = f"chat_data_{SESSION_KEY}.json"

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
        except: return None
    return None

# 현재 세션 키에 맞는 파일 로드
loaded_data = load_from_file()

# 1. 필수 제어 변수들이 세션에 없으면 기본값으로 생성 (에러 방지 핵심)
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "editing_idx" not in st.session_state:
    st.session_state.editing_idx = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. 계정 전환 감지 및 유저 데이터 로드
if "current_user_key" not in st.session_state or st.session_state.current_user_key != SESSION_KEY:
    # 파일에서 데이터 가져오기
    st.session_state.saved_chats = loaded_data["saved_chats"] if loaded_data else []
    
    TRANSPARENT_PIXEL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    st.session_state.me_pic = loaded_data["me_pic"] if loaded_data else TRANSPARENT_PIXEL
    st.session_state.other_pic = loaded_data["other_pic"] if loaded_data else TRANSPARENT_PIXEL
    st.session_state.me_name = loaded_data["me_name"] if loaded_data else "나"
    st.session_state.other_name = loaded_data["other_name"] if loaded_data else "상대방"
    
    # 계정 전환 시 현재 작업 중이던 채팅창 초기화
    st.session_state.messages = []
    st.session_state.chat_title = "새로운 채팅"
    st.session_state.show_settings = False
    
    # 로드 완료 표시
    st.session_state.current_user_key = SESSION_KEY

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
    st.markdown(f"<span style='color: #808080; font-size: 0.85rem;'>*삭제할 경우, '{title}' 의 모든 기록이 지워집니다.*</span>", unsafe_allow_html=True)
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

# --- 6. 스타일 설정 ---
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

# --- 7. 사이드바 ---
with st.sidebar:
    st.header(f"👤 {st.session_state.display_id}님")
    if st.button("로그아웃", use_container_width=True):
        # 특정 유저 세션 정보만 삭제하여 계정 전환 유도
        st.session_state.user_session = None
        st.session_state.display_id = None
        # 데이터가 섞이지 않도록 로드 상태 초기화
        if "current_user_key" in st.session_state:
            del st.session_state.current_user_key
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

# --- 8. 메인 레이아웃 (채팅 전용 넓은 폭 유지) ---
if st.session_state.show_settings:
    col_main, col_settings = st.columns([0.45, 0.35]) # 설정창 열렸을 때
else:
    # 로그인 전과 달리 여백 비율을 [0.2, 0.6, 0.2]로 설정하여 넓게 사용
    _, col_main, _ = st.columns([0.2, 0.6, 0.2])

with col_main:
    h_left, h_right = st.columns([0.92, 0.08])
    h_left.markdown(f"### 💬 {st.session_state.chat_title}")
    if h_right.button("⚙️", use_container_width=True):
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

# --- 9. 설정 섹션 (동일) ---
if st.session_state.show_settings:
    with col_settings:
        with st.expander("👤 프로필 및 이름", expanded=True):
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

        with st.expander("📝 메시지 관리", expanded=True):
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
