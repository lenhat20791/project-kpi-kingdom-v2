import re
import pandas as pd
import streamlit as st
import json
import time
import random
import unicodedata
import os
from admin_module import hien_thi_giao_dien_admin
from user_module import hien_thi_giao_dien_hoc_si
from admin_module import admin_quan_ly_boss
from user_module import hien_thi_san_dau_boss
import base64
import streamlit.components.v1 as components
import user_module
from admin_module import load_dungeon_config
from admin_module import hien_thi_thong_bao_he_thong
from datetime import datetime, timedelta
import zipfile
from user_module import save_data, load_data
        
# --- 🚑 BỘ CỨU HỘ DỮ LIỆU TỪ Ổ CỨNG (SỬA FILE data.json) ---
def emergency_fix_data_file():
    FILE_PATH = "data.json"
    if os.path.exists(FILE_PATH):
        try:
            # 1. Đọc file lên xem có bị lỗi không
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # 2. Nếu phát hiện file đang lưu dạng List -> Sửa ngay lập tức
            if isinstance(content, list):
                print("🚨 PHÁT HIỆN FILE LỖI (LIST) -> ĐANG KHÔI PHỤC...")
                fixed_dict = {}
                for item in content:
                    if isinstance(item, dict):
                        # Tìm key định danh để chuyển thành Dictionary
                        key = item.get('username') or item.get('u_id') or item.get('id') or item.get('name')
                        
                        # Ưu tiên Admin
                        if item.get('role') == 'admin': 
                            key = 'admin'
                        
                        if key:
                            str_key = str(key).strip().lower().replace(" ", "")
                            fixed_dict[str_key] = item
                
                # 3. Ghi đè lại file chuẩn (Dict) ngay lập tức xuống ổ cứng
                with open(FILE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(fixed_dict, f, ensure_ascii=False, indent=4)
                
                # 4. Cập nhật luôn vào session_state để app chạy mượt
                if 'data' in st.session_state:
                    st.session_state.data = fixed_dict
                    
                st.toast("✅ Đã sửa file data.json trong ổ cứng thành công!", icon="💾")
                
        except Exception as e:
            print(f"⚠️ Lỗi khi chạy bộ cứu hộ: {e}")

# 🔥 KÍCH HOẠT NGAY LẬP TỨC
emergency_fix_data_file()
        
@st.dialog("🏟️ SẢNH VINH QUANG ĐẤU TRƯỜNG", width="large")
def show_arena_info_popup():
    import user_module
    top_4, recent_matches = user_module.get_arena_logs()
    
    # --- PHẦN 1: TỨ ĐẠI CAO THỦ (Sử dụng Card bự, font chữ Bangers) ---
    st.markdown("<h2 style='text-align: center; color: #ff4b4b; font-family: sans-serif;'>🏆 TỨ ĐẠI CAO THỦ 🏆</h2>", unsafe_allow_html=True)
    
    if not top_4:
        st.info("Chưa có cao thủ nào lộ diện trên đấu trường!")
    else:
        cols = st.columns(4)
        colors = ["#f1c40f", "#bdc3c7", "#e67e22", "#3498db"]
        icons = ["🥇", "🥈", "🥉", "🏅"]
        
        for i, fighter in enumerate(top_4):
            with cols[i]:
                st.markdown(f"""
                    <div style="text-align:center; border:3px solid {colors[i]}; border-radius:20px; padding:20px; background: #1e1e1e; color: white;">
                        <p style="font-size:50px; margin:0;">{icons[i]}</p>
                        <p style="font-size:24px; font-weight:bold; margin:5px 0;">{fighter['name'].upper()}</p>
                        <p style="font-size:18px; color:{colors[i]};">🔥 {fighter['wins']} TRẬN THẮNG</p>
                    </div>
                """, unsafe_allow_html=True)

    st.write("---")
    
    # --- PHẦN 2: 10 TRẬN CHIẾN GẦN NHẤT (Bảng to, rõ ràng) ---
    st.markdown("<h3 style='text-align: center; color: #3498db;'>⚔️ NHẬT KÝ CHIẾN TRƯỜNG ⚔️</h3>", unsafe_allow_html=True)
    
    if not recent_matches:
        st.write("<p style='text-align:center;'>Đấu trường đang yên bình...</p>", unsafe_allow_html=True)
    else:
        for match in reversed(recent_matches):
            # Thiết kế mỗi dòng trận đấu như một thanh Banner bự
            st.markdown(f"""
                <div style="background: linear-gradient(90deg, #2c3e50, #000000); 
                            border-radius: 15px; padding: 15px; margin-bottom: 10px; 
                            border-left: 10px solid #ff4b4b; display: flex; 
                            justify-content: space-between; align-items: center; color: white;">
                    <div style="flex: 2; font-size: 20px;">
                        <b>{match['p1']}</b> <span style="color:#ff4b4b;">VS</span> <b>{match['p2']}</b>
                    </div>
                    <div style="flex: 1; text-align: center; font-size: 22px; color: #f1c40f; font-weight: bold;">
                        {match['score']}
                    </div>
                    <div style="flex: 2; text-align: right;">
                        <span style="font-size: 16px; color: #aaa;">Tiền cược:</span> 
                        <b style="font-size: 20px; color: #2ecc71;">💰 {match['bet']}</b><br>
                        <span style="font-size: 14px;">Người thắng: <b style="color:#f1c40f;">{match['winner_name']}</b></span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

@st.dialog("📜 THÔNG TIN THÁM HIỂM")
def show_land_info_popup(land_name, land_id):
    import importlib
    import user_module # Import để gọi hàm lấy log
    logs = user_module.get_dungeon_logs(land_id)
    
    if not logs:
        st.info("🌀 Vùng đất này hiện chưa có dấu chân nhà thám hiểm nào.")
        return

    # --- TOP 3 VINH DANH ---
    st.markdown(f"### 🏆 BẢNG VÀNG: {land_name.upper()}")
    # Sắp xếp theo Phase cao nhất, sau đó đến thời gian thấp nhất
    top_3 = sorted(logs, key=lambda x: (-x['phase'], x['time']))[:3]
    
    cols = st.columns(3)
    ranks = ["🥇 HẠNG 1", "🥈 HẠNG 2", "🥉 HẠNG 3"]
    colors = ["#f1c40f", "#bdc3c7", "#e67e22"]
    icons = ["👑", "⚔️", "🛡️"]
    
    for i, player in enumerate(top_3):
        with cols[i]:
            st.markdown(f"""
                <div style="text-align:center; border:2px solid {colors[i]}; border-radius:15px; padding:10px; background: #fffdf0;">
                    <p style="font-size:30px; margin:0;">{icons[i]}</p>
                    <b style="color:{colors[i]}">{ranks[i]}</b><br>
                    <span style="font-weight:bold;">{player['name']}</span><br>
                    <small>Đã đạt: Phase {player['phase']}</small>
                </div>
            """, unsafe_allow_html=True)

    st.write("---")
    
    # --- 10 HOẠT ĐỘNG GẦN ĐÂY ---
    st.markdown("### 🕒 HOẠT ĐỘNG GẦN ĐÂY")
    # Lấy 10 bản ghi mới nhất
    recent_10 = logs[-10:] 
    
    for entry in reversed(recent_10):
        st.markdown(f"""
            <div style="background:#f8f9fa; border-radius:8px; padding:10px; margin-bottom:8px; border-left:4px solid #3498db; display: flex; justify-content: space-between;">
                <span>✨ <b>{entry['name']}</b> vừa thám hiểm Phase {entry['phase']}</span>
                <span style="color:#2ecc71;">🎁 {entry['reward_recent']}</span>
            </div>
        """, unsafe_allow_html=True)
 
def hien_thi_bang_vang_diem_so():
    """Hiển thị Top 10 học sinh (Phiên bản Emerald High Contrast)"""
    
    # 1. CSS SIÊU CẤP - TƯƠNG PHẢN CAO
    st.markdown("""
    <style>
    /* --- ANIMATION --- */
    @keyframes emerald-flow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* --- CONTAINER CHÍNH --- */
    .knowledge-board {
        /* Giữ nguyên nền Xanh Ngọc Lục Bảo huyền bí */
        background: linear-gradient(135deg, #02111b, #073836, #155e58);
        background-size: 300% 300%;
        animation: emerald-flow 15s ease infinite;
        
        /* Đổi viền sang màu Vàng Nhạt để tách biệt với nền */
        border: 2px solid #f1c40f; 
        border-radius: 15px;
        padding: 20px 15px;
        margin-top: 20px;
        box-shadow: 0 0 20px rgba(7, 56, 54, 0.6);
        position: relative;
        overflow: hidden;
        color: white;
    }

    /* Header: Đổi sang màu VÀNG KIM (Gold) để nổi bật trên nền xanh */
    .kb-header {
        text-align: center;
        font-family: 'Bangers', sans-serif;
        font-size: 1.6em;
        letter-spacing: 2px;
        color: #f1c40f; 
        text-shadow: 2px 2px 0px #000;
        margin-bottom: 15px;
        position: relative;
        z-index: 2;
        border-bottom: 1px dashed rgba(241, 196, 15, 0.5); /* Gạch chân vàng */
        padding-bottom: 10px;
    }

    /* --- DANH SÁCH --- */
    .kb-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        position: relative;
        z-index: 2;
        max-height: 400px;
        overflow-y: auto;
    }

    /* Row chung: Nền đen mờ để chữ Trắng nổi lên */
    .kb-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 12px;
        border-radius: 8px;
        background: rgba(0, 0, 0, 0.3); /* Nền đen mờ giúp tăng tương phản */
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: transform 0.2s, background 0.2s;
    }
    .kb-row:hover {
        transform: translateX(5px);
        background: rgba(255, 255, 255, 0.2);
        border-color: #f1c40f;
    }

    /* Text Styles */
    .user-name { 
        font-size: 0.95em; 
        font-weight: 600; 
        color: #ffffff; /* Chữ trắng tinh khôi dễ đọc */
        flex-grow: 1; 
        padding-left: 10px; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }
    
    .score-badge {
        background: #f39c12; /* Nền cam */
        color: #fff; /* Chữ trắng */
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.85em;
        font-weight: 900;
        min-width: 50px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.4);
    }

    /* --- TOP 1 ĐẶC BIỆT --- */
    .kb-top1 {
        background: linear-gradient(90deg, rgba(241, 196, 15, 0.2), rgba(0, 0, 0, 0.4));
        border: 1px solid #f1c40f; /* Viền vàng */
    }
    .kb-top1 .user-name { color: #f1c40f; font-weight: 900; font-size: 1.1em; } /* Tên Top 1 màu vàng */
    .kb-top1 .score-badge { background: #f1c40f; color: #000; box-shadow: 0 0 10px #f1c40f; }

    /* Top 2 & 3 */
    .kb-top2 { border-left: 4px solid #bdc3c7; } /* Bạc */
    .kb-top3 { border-left: 4px solid #d35400; } /* Đồng */

    /* Scrollbar */
    .kb-list::-webkit-scrollbar { width: 4px; }
    .kb-list::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
    .kb-list::-webkit-scrollbar-thumb { background: #f1c40f; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # 2. XỬ LÝ DỮ LIỆU
    if 'data' not in st.session_state or not st.session_state.data: return
    try:
        # --- 🛡️ BỘ LỌC DỮ LIỆU AN TOÀN (ÁP DỤNG CHO TOP CAO THỦ) 🛡️ ---
        # 1. Lấy dữ liệu thô
        raw_data_top = st.session_state.data
        clean_data_top = {}

        # 2. Lọc bỏ các file cấu hình (chỉ lấy User là Dict)
        if raw_data_top:
            for key, value in raw_data_top.items():
                # Chỉ lấy value là Dictionary (Học sinh/Admin)
                if isinstance(value, dict):
                    clean_data_top[key] = value

        # 3. Tạo DataFrame từ dữ liệu sạch
        try:
            # Thay thế st.session_state.data bằng clean_data_top
            df = pd.DataFrame.from_dict(clean_data_top, orient='index')
        except Exception as e:
            # st.error(f"Lỗi tạo bảng xếp hạng: {e}") 
            df = pd.DataFrame() # Tạo bảng rỗng để không crash
        # -------------------------------------------------------------

        # ... (Các đoạn code xử lý sort, head(5)... bên dưới giữ nguyên) ...
        if 'admin' in df.index: df = df.drop('admin')
        if 'total_score' not in df.columns: df['total_score'] = 0.0
        
        df['total_score'] = pd.to_numeric(df['total_score'], errors='coerce').fillna(0)
        top_scores = df.sort_values(by='total_score', ascending=False).head(10)
        top_scores = top_scores[top_scores['total_score'] > 0] 
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return

    # 3. RENDER HTML
    list_html = ""
    if top_scores.empty:
        # Đổi màu chữ thông báo thành màu Bạc sáng để dễ đọc
        list_html = "<div style='text-align:center; padding: 30px; color:#bdc3c7; font-style:italic;'>⏳ Chưa có dữ liệu điểm số...</div>"
    else:
        rank = 1
        for user_id, row in top_scores.iterrows():
            row_class = "kb-row"
            icon = f"{rank}"
            
            if rank == 1:
                row_class += " kb-top1"
                icon = "👑"
            elif rank == 2:
                row_class += " kb-top2"
                icon = "🥈"
            elif rank == 3:
                row_class += " kb-top3"
                icon = "🥉"
            else:
                # Top 4-10: Số trắng trong vòng tròn mờ
                icon = f"<div style='width:22px; height:22px; background:rgba(255,255,255,0.15); border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:0.8em; color:white; font-weight:bold;'>{rank}</div>"

            display_name = row['name']
            
            list_html += f"""
            <div class="{row_class}">
                <div style="width:30px; text-align:center; font-size:1.2em;">{icon}</div>
                <div class="user-name">{display_name}</div>
                <div class="score-badge">{row['total_score']:.1f}</div>
            </div>
            """
            rank += 1

    # In ra màn hình
    st.markdown(f"""
    <div class="knowledge-board">
        <div class="kb-header">📜 CAO THỦ HỌC TẬP</div>
        <div class="kb-list">
            {list_html}
        </div>
        <div style="text-align: center; font-size: 0.7em; margin-top: 15px; color: #bdc3c7; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 5px;">
            ✨ Điểm số được cập nhật liên tục ✨
        </div>
    </div>
    """, unsafe_allow_html=True)
 
# --- KHỞI TẠO TRẠNG THÁI HỆ THỐNG (Clean) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None

# Khởi tạo trang mặc định nếu chưa có
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Trang chủ"

def get_base64_of_bin_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""
    
def hien_thi_sidebar_chung():
    with st.sidebar:
        st.title("🏰 KPI KINGDOM")
        st.info(f"👤 Người dùng: **{st.session_state.u_id}**")
        
        # Nút điều hướng về Trang chủ (Không làm mất Login)
        if st.button("🏠 TRANG CHỦ HỆ THỐNG", use_container_width=True):
            st.session_state.current_page = "Trang chủ"
            st.rerun()

        # Nút Đăng xuất chủ động
        st.divider()
        if st.button("🚪 ĐĂNG XUẤT", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            if os.path.exists("login_cache.json"):
                os.remove("login_cache.json")
            st.rerun()

def load_boss_data():
    # Đường dẫn file này phải khớp với file Admin ghi dữ liệu Boss
    path = "data/boss_config.json" 
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Trả về dữ liệu mặc định nếu Admin chưa tạo Boss
    return {
        "name": "Boss Học Kỳ",
        "hp_current": 1000,
        "hp_max": 1000,
        "image_url": "assets/teachers/toan.png",
        "description": "Chưa có mục tiêu cụ thể"
    }


@st.dialog("📜 BÍ KÍP SINH TỒN TẠI KPI KINGDOM", width="large")
def show_tutorial():
    # Nội dung hướng dẫn chia làm 4 Tab
    tab1, tab2, tab3, tab4 = st.tabs([
        "📖 Cốt Truyện", 
        "⚡ Chỉ Số", 
        "🏰 Khu Vực", 
        "⚠️ Lưu Ý"
    ])
    
    with tab1:
        # Nội dung HTML được dồn sát lề trái của file code để tránh lỗi thụt lề trong Python
        noidung_cotruyen = """
    <div style="font-size: 26px; line-height: 1.6; font-family: sans-serif; text-align: left; padding: 10px;">
        <h2 style='color: #FF4B4B; font-size: 40px; margin: 0 0 20px 0; text-align: left;'>🏰 CHÀO MỪNG ĐẾN VỚI THÁNH ĐỊA KPI KINGDOM 🏰</h2>
        
        <p style='color: #555; margin: 0;'><i>Một cánh cửa không gian mở ra tại <b>Lớp 6/1</b>, mở ra con đường thông đến KPI-Kingdom...</i></p>
        <br>
        
        🔥 <b>Các Sĩ Tử trẻ!</b> Bạn không chỉ là một học sinh. 
        Tại đây, bạn chính là những <b>Chiến Binh Tri Thức</b>. Vương quốc đang đứng trước thử thách lớn, 
        và chỉ những ai làm chủ được sức mạnh của trí tuệ mới có thể vươn tới đỉnh vinh quang.
        <br><br>
        
        ⚔️ <b>Kiến thức là Vũ khí:</b> Mỗi công thức toán học, mỗi phương trình hóa học, mỗi từ vựng mới chính là 
        thanh gươm, tấm khiên sắc bén nhất để bạn đương đầu với những quái thú mang tên "Lỗ Hổng Kiến Thức".
        <br><br>
        
        💎 <b>Điểm số là Công cụ:</b> Đừng coi điểm số là gánh nặng! Trong đấu trường này, điểm số (KPI) 
        chính là <b>Nền Tảng</b>, là nguồn năng lượng tối thượng giúp bạn trang bị những vật phẩm thần kỳ 
        tại Shop và nâng cấp kỹ năng của bản thân.
        <br><br>
        
        🏟️ <b>Đấu trường rực lửa:</b> Đây là nơi duy nhất mà sự nỗ lực được nhìn thấy bằng những con số nhảy múa, 
        nơi mỗi lần bạn giơ tay phát biểu là một lần tung chiêu chí mạng, mỗi bài tập hoàn thành là một bước tiến 
        gần hơn tới ngai vàng của <b>Học Giả Vinh Diệu</b>.
        <br><br>
        
        🌟 <b>Hành trình của bạn bắt đầu từ giây phút này. Hãy chứng minh rằng: Trí tuệ của bạn chính là quyền năng lớn nhất!</b>
    </div>
    """
        # Ép Streamlit đọc đúng định dạng HTML
        st.components.v1.html(noidung_cotruyen, height=800, scrolling=True)   
    st.warning("⚠️ **Ghi chú từ Trưởng lão:** Hãy bảo mật mật mã tài khoản, vì đó là chìa khóa duy nhất bước vào Vương Quốc!")

    with tab2:
        noidung_chiso = """
<div style="font-size: 28px; line-height: 1.6; font-family: sans-serif; text-align: left; padding: 10px;">
    <h2 style='color: #FFA500; font-size: 40px; margin: 0 0 20px 0;'>⚡ HỆ THỐNG SỨC MẠNH & TIỀN TỆ</h2>
    
    🌟 <b>EXP & LEVEL:</b> 
    <ul>
        <li><b>EXP:</b> Nhận được thông qua việc chinh phục các <b>Phó Bản</b>.</li>
        <li><b>Level:</b> Khi đủ EXP sẽ thăng cấp. Cấp càng cao, vị thế càng lớn.</li>
    </ul>

    ⚔️ <b>CÔNG THỨC SỨC MẠNH:</b>
    <ul>
        <li>❤️ <b>HP Nhân vật = KPI * Level</b> (KPI càng cao, sinh mệnh càng bền bỉ).</li>
        <li>🔥 <b>Chiến lực = Tổng điểm các bài kiểm tra hiện tại</b> (Kiến thức thực tế chính là sức mạnh tấn công).</li>
    </ul>

    💰 <b>HỆ THỐNG TIỀN TỆ ĐA DẠNG:</b>
    <br><br>
    🔵 <b>KPI (Điểm Học Tập):</b> Kiếm từ bài kiểm tra, phong trào, phát biểu (Tổ trưởng ghi nhận), thắng Lôi đài hoặc diệt Boss.
    <br><br>
    📚 <b>TRI THỨC:</b> Nhận ngẫu nhiên khi đánh Boss, mở vật phẩm hoặc được Giáo viên chủ nhiệm ban thưởng.
    <br><br>
    ⚔️ <b>CHIẾN TÍCH:</b> Thắng lợi tại <b>Lôi đài cá nhân</b> hoặc <b>Tổ đội</b>.
    <br><br>
    🏆 <b>VINH DỰ:</b> Dành cho <b>Top 10 Cao Thủ</b> hàng tháng (tính theo tổng điểm tích lũy năm học).
    <br><br>
    ✨ <b>VINH QUANG:</b> Nguồn sức mạnh huyền thoại (Đang được khai phá...).
</div>
"""
        st.components.v1.html(noidung_chiso, height=950, scrolling=True)

    with tab3:
        noidung_khuvuc = """
<div style="font-size: 28px; line-height: 1.6; font-family: sans-serif; text-align: left; padding: 10px;">
    <h2 style='color: #4CAF50; font-size: 40px; margin: 0 0 20px 0;'>🏰 CÁC ĐỊA DANH TẠI VƯƠNG QUỐC</h2>
    
    👑 <b>HỌC GIẢ VINH DIỆU:</b> Nơi vinh danh những Sĩ tử có thành tích đặc biệt xuất sắc. Khi tích lũy đủ lượng KPI cần thiết, bạn có thể tiến vào <b>Sảnh Danh Vọng</b> để kích hoạt những danh hiệu cao quý cho bản thân.
    <br><br>

    🏆 <b>CAO THỦ HỌC TẬP:</b> Bảng vàng danh giá dành riêng cho 10 Sĩ tử có tổng điểm kiểm tra cao nhất toàn lớp. Đây là nơi khẳng định vị thế của những bậc trí giả hàng đầu.
    <br><br>

    ⚔️ <b>ĐẤU TRƯỜNG LÔI ĐÀI:</b> Nơi so kè kiến thức theo thể thức cá nhân (1vs1) hoặc tổ đội (2vs2, 3vs3). 
    Các Sĩ tử sẽ tranh tài bằng cách giải đề trắc nghiệm hoặc so điểm tăng trưởng KPI trong 7 ngày. 
    <b>Phần thưởng:</b> Nhận toàn bộ tiền cược KPI và điểm <b>Chiến Tích</b>.
    <br><br>

    🏔️ <b>PHÓ BẢN:</b> Nơi mài giũa kiến thức thành sức mạnh. Phó bản cung cấp lượng <b>EXP</b> dồi dào và các rương vật phẩm quý báu. 
    Sĩ tử vượt phó bản nhanh nhất sẽ được khắc tên lên Phó bản và nhận thưởng đặc biệt từ Giáo viên.
    <br><br>

    👹 <b>ĐẠI CHIẾN BOSS (GIÁO VIÊN):</b> Hoạt động săn Boss Thế Giới (World Boss). Toàn bộ lớp sẽ cùng tấn công một Boss duy nhất theo thời gian thực.
    <ul style="margin-top: 10px;">
        <li>⚔️ <b>Sát thương:</b> Dựa trên chỉ số Tấn Công (ATK) + <b>Combo</b> (Mỗi câu đúng liên tiếp tăng <b>10%</b> sức mạnh).</li>
        <li>🎁 <b>Phần thưởng:</b> Chia thưởng dựa trên Tổng sát thương đóng góp ngay khi Boss gục ngã (HP về 0).</li>
        <li>🛡️ <b>Sinh tồn (QUAN TRỌNG):</b> Boss có sát thương cực lớn. Bạn <b>nên dùng thêm thuốc phụ trợ/Bùa</b> (mua tại Tiệm Tạp Hóa) để tăng cao năng lực bản thân để có thể chịu đòn.</li>
        <li>💀 <b>Hình phạt:</b> Nếu để HP về 0, bạn sẽ bị "Trọng Thương" và phải nghỉ ngơi trong <b>30 phút</b>.</li>
    </ul>
</div>
"""
        st.components.v1.html(noidung_khuvuc, height=1200, scrolling=True)

    with tab4:
        st.warning("🚨 **QUY TẮC VÀNG:** Luôn đổi mật khẩu sau lần đầu đăng nhập!")
        st.write("- Không chia sẻ mật khẩu cho người khác.")
        st.write("- Mọi hành vi gian lận sẽ bị tước bỏ danh hiệu.")
  
    
def initialize_accounts_from_excel(file_path):
    if not os.path.exists(file_path):
        st.error(f"❌ Không tìm thấy file {file_path}") 
        return None

    try:
        # Đọc file Excel
        df = pd.read_excel(file_path) 
        
        # 1. TÌM CỘT TÊN THÔNG MINH (Chấp nhận: Họ và tên, Họ tên, Tên, Name...)
        name_col = next((c for c in df.columns if 'tên' in str(c).lower() or 'name' in str(c).lower()), None)
        
        if not name_col:
            st.error("❌ File Excel thiếu cột chứa 'Họ và tên'. Vui lòng kiểm tra lại tiêu đề.")
            return None

        new_data = {}
        for i, row in df.iterrows():
            # 1. LẤY TÊN VÀ THÔNG TIN CƠ BẢN TRƯỚC
            full_name = str(row[name_col]).strip() 
            
            # 2. KÍCH HOẠT ID ĐĂNG NHẬP (Tạo ID không dấu từ Họ và tên)
            u_id = user_module.generate_username(full_name)

            # 3. LẤY DỮ LIỆU LINH HOẠT (Tự động tìm cột Anh hoặc Việt)
            team_val = str(row.get('team', row.get('Tổ', 'Chưa phân tổ'))).strip() 
            role_val = str(row.get('role', row.get('Chức vụ', 'u3'))).strip().lower() 
            pwd_val = str(row.get('Password', row.get('Mật khẩu', '123456'))).strip() 
            
            # Xử lý KPI (Tiền tệ/Máu Boss)
            kpi_input = row.get('KPI', row.get('kpi', row.get('Điểm', 100))) 
            try:
                kpi_val = int(kpi_input) 
            except:
                kpi_val = 100 

            # 4. Cấu trúc dữ liệu RPG đầy đủ (Đã cập nhật EXP & LEVEL tách biệt)
            new_data[u_id] = {
                "name": full_name, 
                "password": pwd_val, 
                "role": role_val, 
                "team": team_val, 
                "kpi": kpi_val,      # Điểm dùng để mua sắm/xếp hạng lớp 
                "exp": 0,            # Kinh nghiệm tích lũy từ phó bản (Mới)
                "level": 1,          # Cấp độ sức mạnh phó bản (Mới)
                "hp": 100,           # Sinh mệnh thực tế khi đi phó bản
                "dungeon_progress": { # --- PHẦN MỚI: LƯU TIẾN TRÌNH PHÓ BẢN ---
                    "toan": 1, "van": 1, "anh": 1, "ly": 1, "hoa": 1, "sinh": 1
                },
                "Bonus": 0, "Vi_Pham": 0, 
                "KTTX": 0, "KT Sản phẩm": 0, "KT Giữa kỳ": 0, "KT Cuối kỳ": 0, 
                "Tri_Thuc": 0, "Chien_Tich": 0, "Vinh_Du": 0, "Vinh_Quang": 0, 
                "titles": ["Tân Thủ Học Sĩ"], 
                "inventory": [],     # Kho đồ chuyển sang dạng List để dễ quản lý số lượng 
                "purchase_history": {}, # Lịch sử mua đồ để check giới hạn tháng/1 lần
                "unlocked_ranks": []  # Danh hiệu đã mở khóa
            }
        
        # 5. BẢO VỆ TÀI KHOẢN ADMIN (Giữ lại thông tin Admin cũ nếu có)
        admin_info = st.session_state.get('data', {}).get('admin') 
        if not admin_info:
            admin_info = {"name": "Quản Trị Viên", "password": "admin", "role": "Admin"} 
        new_data["admin"] = admin_info 

        # 6. Ghi file và cập nhật Session
        with open("data.json", "w", encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        
        # Cập nhật ngay vào bộ nhớ app
        st.session_state.data = new_data 
        
        return new_data
    except Exception as e:
        st.error(f"❌ Lỗi xử lý dữ liệu: {e}")
        return None
        
# --- QUẢN LÝ DỮ LIỆU TIỆM TẠP HÓA ---

# --- HÀM LƯU DỮ LIỆU SHOP ---
def save_shop_data(shop_data):
    try:
        # Sửa tên file thành shop_data.json cho khớp với hàm Load
        with open('shop_data.json', 'w', encoding='utf-8') as f:
            json.dump(shop_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Lỗi khi lưu Shop: {e}")

# 2. Hàm tải dữ liệu Shop (Chạy 1 lần đầu chương trình)
def load_shop_data():
    if os.path.exists('shop_data.json'):
        with open('shop_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {} # Trả về dict rỗng nếu chưa có file
        


# --- HÀM LƯU DỮ LIỆU ---
import user_module # Đảm bảo đã import

def save_data(data=None):
    """Hàm này bây giờ chỉ đóng vai trò là 'người đưa tin'"""
    if data is None:
        data = st.session_state.data
    
    # Chuyển việc cho user_module làm
    return user_module.save_data(data)
        
# --- KHỞI TẠO DỮ LIỆU ĐẦU VÀO ---
if 'data' not in st.session_state:
    with st.spinner('📡 Đang kết nối vệ tinh tới Google Sheets...'):
        st.session_state.data = user_module.load_data()
        
    # --- HIỂN THỊ TRẠNG THÁI DỮ LIỆU ---
    # Nếu đang dùng Local (Offline), hiện cảnh báo đỏ lòm
    if st.session_state.get('data_source') == 'local':
        st.error("⚠️ CẢNH BÁO: Mất kết nối Google Sheets! Hệ thống đang dùng dữ liệu CŨ (Offline).")
        st.warning("⛔ Vui lòng KHÔNG chỉnh sửa hoặc lưu dữ liệu lúc này để tránh lỗi ghi đè.")
    
    # Nếu đang dùng Cloud (Online), báo xanh
    elif st.session_state.get('data_source') == 'cloud':
        st.toast("✅ Đã đồng bộ dữ liệu mới nhất từ Cloud!", icon="☁️")

if 'shop_items' not in st.session_state:
    # 1. Nếu có file shop_data.json thì load lên
    if os.path.exists("shop_data.json"):
        try:
            with open("shop_data.json", "r", encoding='utf-8') as f:
                loaded_shop = json.load(f)
                
            # Kiểm tra an toàn: shop_items phải là Dictionary
            if isinstance(loaded_shop, dict):
                st.session_state.shop_items = loaded_shop
            else:
                st.session_state.shop_items = {} # Nếu lỗi format thì tạo rỗng
                
        except Exception as e:
            st.error(f"Lỗi đọc shop_data: {e}")
            st.session_state.shop_items = {}
            
    # 2. Nếu chưa có file thì khởi tạo rỗng
    else:
        st.session_state.shop_items = {}

# --- 👆 HẾT ĐOẠN FIX SHOP 👆 ---
    
# --- THIẾT LẬP TRANG ---
st.set_page_config(
    page_title="KPI-Kingdom v1.0", 
    layout="wide",
    initial_sidebar_state="expanded" # Dòng này giúp Sidebar LUÔN HIỆN khi vào app
)    
# --- CSS CUSTOM: GIAO DIỆN RPG & NÚT MENU TỐI THƯỢNG ---
st.markdown("""
    <style>
    /* Khung chứa ảnh banner cố định tỉ lệ */
    .banner-container {
        width: 100%;
        height: 250px; /* Chiều cao cố định để 2 bên bằng nhau tuyệt đối */
        overflow: hidden;
        border-radius: 12px;
        margin-top: 10px;
        border: 3px solid #00d2ff; /* Viền xanh dương cơ bản */
        /* Hiệu ứng Border Neon Xanh Dương Nhạt */
        box-shadow: 0 0 10px #00d2ff, 0 0 20px #00d2ff inset;
        transition: 0.3s;
    }
    .banner-container:hover {
        box-shadow: 0 0 20px #91eaff, 0 0 40px #91eaff inset; /* Sáng mạnh hơn khi di chuột */
        transform: translateY(-5px);
    }

    /* Ép ảnh lấp đầy khung mà không bị biến dạng */
    .banner-container img {
        width: 100%;
        height: 100%;
        object-fit: cover; /* Tự động cắt phần thừa để ảnh vừa khít khung */
        object-position: center;
    }
    /* 1. THIẾT KẾ NÚT "ẨN MENU" (KHI SIDEBAR ĐANG ĐÓNG) */
    /* Target trực tiếp vào nút ở góc trên bên trái */
    [data-testid="stSidebarCollapseButton"] {
        background-color: #ffaa00 !important; /* Màu cam nổi bật */
        border: 2px solid #d35400 !important;
        border-radius: 10px !important;
        height: 50px !important; /* Tăng chiều cao */
        width: auto !important; /* Để chiều rộng tự giãn theo chữ */
        padding: 0 20px !important;
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        z-index: 999999 !important;
        box-shadow: 0 4px 15px rgba(255, 170, 0, 0.4) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Thêm chữ ẨN MENU in đậm vào nút */
    [data-testid="stSidebarCollapseButton"]::after {
        content: "ẨN MENU 📑";
        color: white !important;
        font-size: 18px !important;
        font-weight: 900 !important; /* Siêu đậm */
        margin-left: 10px !important;
        white-space: nowrap !important;
    }

    /* Phóng to biểu tượng mũi tên trắng */
    [data-testid="stSidebarCollapseButton"] svg {
        fill: white !important;
        width: 28px !important;
        height: 28px !important;
    }

    /* Hiệu ứng khi di chuột vào nút */
    [data-testid="stSidebarCollapseButton"]:hover {
        background-color: #ffc300 !important;
        transform: scale(1.1);
        transition: 0.3s;
    }

    /* 2. HIỆU ỨNG CARD CHO NỘI DUNG CHÍNH */
    .main-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 25px;
        border-left: 10px solid #ffaa00;
    }
    
    /* 3. THANH MÁU BOSS (HP BAR) */
    .boss-bar {
        height: 40px;
        background-color: #1e272e;
        border-radius: 20px;
        overflow: hidden;
        border: 3px solid #34495e;
        margin: 15px 0;
    }
    .boss-progress {
        background: linear-gradient(90deg, #ff4b1f, #ff9068);
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 16px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }

    /* Tối ưu Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f1f2f6;
    }
    
    /* THIẾT KẾ NÚT VỀ TRANG CHÍNH SIÊU TO */
    div.stButton > button[key="btn_back_main"] {
        background-color: #34495e !important; /* Màu xám xanh sang trọng */
        color: #ffffff !important;
        font-weight: 900 !important; /* Chữ siêu đậm */
        font-size: 20px !important;
        height: 60px !important;
        width: 100% !important;
        border-radius: 12px !important;
        border: 2px solid #2c3e50 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
        margin-bottom: 20px !important;
    }
    div.stButton > button[key="btn_back_main"]:hover {
        background-color: #e74c3c !important; /* Đổi sang đỏ khi di chuột (nút thoát) */
        border-color: #c0392b !important;
        transform: scale(1.02);
        transition: 0.3s;
    }
    
    /* Định dạng cho nhãn chỉ số nằm trên thanh Bar */
    .stat-label {
        font-weight: 900 !important; /* Siêu đậm */
        font-size: 16px !important;
        color: #2c3e50;
        margin-bottom: 3px; /* Khoảng cách nhỏ với thanh bar bên dưới */
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER CHÍNH ---
st.markdown("## 👑 KPI-KINGDOM: THCS PHAN VĂN TRỊ - LỚP 6/1")
hien_thi_thong_bao_he_thong()
st.warning("✨ CHÀO MỪNG ĐẾN VỚI KPI KINGDOM! Hiện chưa có trận Lôi Đài nào diễn ra. Các tổ hãy mau chóng khiêu chiến!")

def hien_thi_thong_bao_he_thong():
    if os.path.exists('data/admin_notices.json'):
        with open('data/admin_notices.json', 'r', encoding='utf-8') as f:
            try: notices = json.load(f)
            except: notices = []
            
        for n in notices:
            # 1. XỬ LÝ POPUP (Dùng st.dialog)
            if n['type'] == 'popup':
                # Tạo một key riêng dựa trên ID thông báo để tránh hiện lại khi đã đóng
                popup_key = f"seen_popup_{n['id']}"
                if popup_key not in st.session_state:
                    @st.dialog("📢 THÔNG BÁO TỪ BAN QUẢN TRỊ")
                    def show_notice_popup(content, time):
                        st.warning(f"🕒 *Gửi lúc: {time}*")
                        st.markdown(f"### {content}")
                        if st.button("Đã hiểu và Đóng"):
                            st.session_state[popup_key] = True
                            st.rerun()
                    
                    show_notice_popup(n['content'], n['time'])

            # 2. XỬ LÝ MARQUEE (Chạy ngang màn hình)
            elif n['type'] == 'marquee':
                st.markdown(f"""
                    <div style="background: #9c27b0; color: white; padding: 5px; font-weight: bold; border-radius: 5px; margin-bottom: 10px;">
                        <marquee behavior="scroll" direction="left" scrollamount="7">
                            🚀 TIN TỨC ADMIN [{n['time']}]: {n['content']} 🚀
                        </marquee>
                    </div>
                """, unsafe_allow_html=True)

# --- 1. HIỂN THỊ THÔNG BÁO THẾ GIỚI (ĐẶT Ở ĐẦU) ---
if os.path.exists('data/world_announcements.json'):
    try:
        with open('data/world_announcements.json', 'r', encoding='utf-8') as f:
            msgs = json.load(f)
            if msgs:
                last_msg = msgs[-1]
                # Kiểm tra xem tin nhắn còn hạn không (Ví dụ: 60 phút)
                # Nếu file JSON chưa có expire_at thì bỏ qua check này hoặc thêm mặc định
                current_ts = datetime.now().timestamp()
                expire_at = last_msg.get('expire_at', current_ts + 3600)
                
                if current_ts < expire_at:
                    # Giao diện thông báo nổi bật (Style PULSE của bạn)
                    st.markdown(f"""
                        <div style="background: linear-gradient(90deg, #ff8a00, #e52e71); padding: 15px; 
                                    border-radius: 10px; text-align: center; color: white; font-weight: bold;
                                    border: 2px solid gold; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                                    animation: pulse 2s infinite;">
                            📢 LOA PHÁT THANH - {last_msg['user'].upper()}: {last_msg['content']}
                            <br><small style="font-weight: normal; opacity: 0.8;">Gửi lúc: {last_msg['time']}</small>
                        </div>
                        <style>
                        @keyframes pulse {{
                            0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 138, 0, 0.7); }}
                            70% {{ transform: scale(1.02); box-shadow: 0 0 0 10px rgba(255, 138, 0, 0); }}
                            100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 138, 0, 0); }}
                        }}
                        </style>
                    """, unsafe_allow_html=True)
    except Exception as e:
        pass # Bỏ qua nếu lỗi file


# --- KIỂM TRA QUYỀN ADMIN ---
# ==================================================
# MENU SIDEBAR ĐIỀU HƯỚNG
# ==================================================

if st.session_state.get("user_role") is not None:
    
    # 1. LẤY ROLE VÀ CHUẨN HÓA VỀ CHỮ THƯỜNG (Để so sánh chính xác)
    # Ví dụ: "Admin" -> "admin", "U1" -> "u1"
    current_role_menu = str(st.session_state.user_role).strip().lower()

    with st.sidebar:
        # Hiển thị thông tin người dùng (Tuỳ chọn - cho đẹp)
        st.write(f"👤 Xin chào: **{st.session_state.get('user_id', 'Khách')}**")
        st.caption(f"Vai trò: {current_role_menu.upper()}")
        st.divider()
        # ===== MENU DÀNH CHO ADMIN =====
        # So sánh với "admin" chữ thường
        if current_role_menu == "admin":
            menu = [
                "🏠 Thống kê KPI lớp",
                "👥 Quản lý nhân sự",
                "🛡️ Quản lý Phó bản",
                "🔑 Đổi mật khẩu",
                "🏅 Quản lý danh hiệu", 
                "⚔️ Đại chiến Giáo viên",
                "🏟️ Quản lý lôi đài",
                "📢 Thông báo Server",
                "📥 Sao lưu dữ liệu",
                "⚠️ Xóa dữ liệu",
                "🏪 Quản lý Tiệm tạp hóa"
            ]

        elif current_role_menu == "u1":
            menu = [
                "📜 Chỉ số Học sĩ",
                "👥 Quản lý nhân sự Tổ",
                "⚔️ Đại chiến Giáo viên",
                "🗺️ Thám hiểm Phó bản",
                "🏪 Tiệm tạp hóa & Kho đồ",
                "⚖️ Chợ Đen",
                "🏆 Sảnh Danh Vọng",
                "🏟️ Đấu Lôi Đài",
                "📊 Quản lý KPI tổ"
            ]

        elif current_role_menu in ["u2", "u3", "player", "student"]:
            menu = [
                "📜 Chỉ số Học sĩ",
                "⚔️ Đại chiến Giáo viên",
                "🗺️ Thám hiểm Phó bản",
                "🏪 Tiệm tạp hóa & Kho đồ",
                "⚖️ Chợ Đen",
                "🏆 Sảnh Danh Vọng",
                "🏟️ Đấu Lôi Đài"
                
            ]

        # ===== TRƯỜNG HỢP LẠ (Role chưa định nghĩa) =====
        else:
            st.warning(f"⚠️ Role '{current_role_menu}' chưa được cấp quyền Menu!")
            menu = []

        # Hiển thị Radio Button
        if menu:
            st.session_state.page = st.radio("📌 MENU ĐIỀU HƯỚNG", menu, key="main_menu")
        
        # Nút Đăng xuất (Thêm vào cuối Sidebar cho tiện)
        st.divider()
        if st.button("🚪 Đăng xuất"):
            st.session_state.clear()
            st.rerun()
        # ==============================================================================
        # 🔥 CƠ CHẾ TỰ ĐỘNG THOÁT PHÓ BẢN (AUTO-EXIT)
        # ==============================================================================
        # Nếu trang hiện tại KHÔNG PHẢI là "Phó bản", mà máy vẫn đang nhớ là "đang đánh"
        # (Lưu ý: Thay chữ "Phó bản" nếu menu của bạn đặt tên khác, ví dụ "⚔️ Phó bản")
        if "Phó bản" not in str(st.session_state.page) and st.session_state.get("dang_danh_dungeon") == True:
            
            # 1. Tắt trạng thái chiến đấu ngay lập tức
            st.session_state.dang_danh_dungeon = False
            
            # 2. Dọn dẹp sạch sẽ các biến rác (quan trọng để tránh lỗi khi vào lại)
            keys_to_clean = [
                "dungeon_questions", 
                "current_q_idx", 
                "correct_count", 
                "victory_processed", 
                "selected_phase_id"
                # Không xóa 'selected_land' để giữ trải nghiệm người dùng nhớ vùng đất cũ
            ]
            for k in keys_to_clean:
                if k in st.session_state: 
                    del st.session_state[k]
                    
            # 3. Xóa các đồng hồ đếm giờ (Kẻ thù gây Zombie Loop)
            for k in list(st.session_state.keys()):
                if k.startswith("start_time_"): 
                    del st.session_state[k]
                    
            # 4. F5 lại trang để áp dụng trạng thái sạch sẽ
            st.rerun()
        # nút Đăng xuất/Về trang chủ
        st.divider() 
        if st.button("🏠 VỀ TRANG CHỦ", key="btn_back_main", use_container_width=True):
            # Reset toàn bộ trạng thái đăng nhập
            st.session_state.user_role = None
            st.session_state.user_id = None
            st.session_state.page = None
            st.rerun()
# ==================================================
# 🖥️ HIỂN THỊ NỘI DUNG THEO PAGE
# ==================================================

def hien_thi_banner_vinh_quang():
    if 'data' not in st.session_state or not st.session_state.data:
        return

    # --- 🛠️ ĐOẠN CODE SỬA LỖI (BẮT ĐẦU) 🛠️ ---
    # Lọc dữ liệu: Chỉ lấy những cái là "Học sinh" (Dictionary), bỏ qua "Cấu hình" (List)
    raw_data = st.session_state.data
    clean_users = {}

    for key, value in raw_data.items():
        # Chỉ chấp nhận nếu dữ liệu con là Dictionary (tức là thông tin học sinh/admin)
        # Nếu là List (như rank_settings) -> Code sẽ tự động bỏ qua
        if isinstance(value, dict):
            clean_users[key] = value
            
    # Tạo bảng từ dữ liệu đã lọc sạch
    try:
        df = pd.DataFrame.from_dict(clean_users, orient='index')
    except Exception as e:
        st.error(f"Lỗi tạo bảng: {e}")
        return
    # --- 🛠️ ĐOẠN CODE SỬA LỖI (KẾT THÚC) 🛠️ ---
        
    if 'admin' in df.index: 
        df = df.drop('admin') 
    # Nếu sau khi bỏ admin mà bảng trống (vừa Reset xong) 
    if df.empty:
        st.markdown(f"""
            <div style="text-align: center; padding: 50px; background: #1a1a1a; border-radius: 20px; border: 2px dashed #f1c40f; margin-bottom: 30px;">
                <h2 style="color: #f1c40f; letter-spacing: 5px; font-family: 'Bangers', sans-serif;">🏆 HỌC GIẢ VINH DIỆU 🏆</h2>
                <p style="color: #bdc3c7; font-size: 1.2em; font-style: italic;">✨ Đang đợi vinh danh học giả xuất sắc ✨</p>
            </div>
        """, unsafe_allow_html=True)
        return
    # Lấy thiết lập danh hiệu từ Admin 
    ranks = st.session_state.get('rank_settings', [
        {"Danh hiệu": "Học Sĩ", "KPI Yêu cầu": 1, "Màu sắc": "#bdc3c7"}
    ])
    sorted_ranks = sorted(ranks, key=lambda x: x['KPI Yêu cầu'], reverse=True)
    min_kpi_required = min([r['KPI Yêu cầu'] for r in ranks]) if ranks else 1

    # LỌC AN TOÀN: Kiểm tra sự tồn tại của cột kpi trước khi ép kiểu
    if 'kpi' not in df.columns:
        # Nếu DataFrame trống hoặc không có cột kpi, tạo cột kpi giả với giá trị 0
        df['kpi'] = 0
    else:
        # Nếu đã có cột kpi, tiến hành ép kiểu số để tránh lỗi tính toán
        df['kpi'] = pd.to_numeric(df['kpi'], errors='coerce').fillna(0)

    # Lấy dữ liệu vinh danh (Top 10) 
    df_vinh_danh = df[df['kpi'] >= min_kpi_required].sort_values(by='kpi', ascending=False).head(10)
    if df_vinh_danh.empty:
        st.markdown(f"""
            <div style="text-align: center; padding: 50px; background: #1a1a1a; border-radius: 20px; border: 2px dashed #f1c40f; margin-bottom: 30px;">
                <h2 style="color: #f1c40f; letter-spacing: 5px;">🏆 HỌC GIẢ VINH DIỆU 🏆</h2>
                <p style="color: #bdc3c7; font-size: 1.2em; font-style: italic;">✨ Đang đợi vinh danh học giả xuất sắc ✨</p>
            </div>
        """, unsafe_allow_html=True)
        return

    def get_dynamic_rank(user_kpi):
        for r in sorted_ranks:
            if user_kpi >= r['KPI Yêu cầu']: return r['Danh hiệu']
        return "Học Sĩ"

    # 2. CSS Tinh chỉnh: Vũ trụ Sôi động & Sao sáng
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Roboto:wght@300;700&display=swap');

/* --- 1. ANIMATION (CHUYỂN ĐỘNG) --- */

/* Tăng tốc độ chuyển màu nền (Nhanh hơn: 5s) */
@keyframes gradient-bg {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Hiệu ứng sao trôi (Nhanh hơn một chút: 40s) */
@keyframes star-fall {
    from { background-position: 0 0; }
    to { background-position: -500px 500px; } 
}

/* --- 2. CẤU TRÚC BACKGROUND CHÍNH --- */
.glory-banner {
    /* Nền Gradient Tím Đen */
    background: linear-gradient(-45deg, #240b36, #c31432, #2b1055, #000000);
    background-size: 400% 400%;
    /* SỬA: Giảm thời gian xuống 5s để đổi màu nhanh hơn */
    animation: gradient-bg 6s ease infinite;
    
    border: 4px solid #ffd700;
    border-radius: 25px;
    padding: 30px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
    
    /* Đổ bóng rực rỡ hơn */
    box-shadow: 0 0 25px rgba(195, 20, 50, 0.6), 0 0 50px rgba(0, 0, 0, 0.8) inset;
}

/* 🔥 LỚP SAO RƠI (DÀY HƠN & SÁNG HƠN) */
.glory-banner::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    
    /* SỬA: Thêm nhiều lớp gradient hơn để tạo mật độ dày đặc */
    background-image: 
        radial-gradient(white, rgba(255,255,255,.8) 1px, transparent 2px), /* Sao nhỏ cực sáng */
        radial-gradient(white, rgba(255,255,255,.5) 2px, transparent 4px), /* Sao vừa */
        radial-gradient(white, rgba(255,255,255,.3) 1px, transparent 3px), /* Sao mờ */
        radial-gradient(rgba(255,255,255,0.9), transparent 2px); /* Sao điểm xuyết */
        
    /* SỬA: Thu nhỏ kích thước background-size để sao lặp lại nhiều hơn (Dày hơn) */
    background-size: 200px 200px, 300px 300px, 150px 150px, 100px 100px;
    
    background-position: 0 0, 40px 60px, 130px 270px, 70px 100px;
    
    /* Chuyển động sao rơi */
    animation: star-fall 40s linear infinite; 
    
    /* SỬA: Tăng độ rõ nét từ 0.6 lên 0.9 */
    opacity: 0.95; 
    z-index: 0;
}

/* Đảm bảo nội dung nằm trên lớp sao */
.glory-banner > div, .glory-banner > h2 {
    position: relative;
    z-index: 2;
}

/* ... (GIỮ NGUYÊN PHẦN CODE CARD TOP 1, 2, 3 BÊN DƯỚI) ... */
.aurora-card { 
    background: linear-gradient(135deg, #ff00cc, #333399);
    border: 3px solid #fff !important; 
    box-shadow: 0 0 25px rgba(255, 0, 204, 0.7);
    transform: scale(1.05);
}
.top1-name {
    font-family: 'Bangers', cursive;
    font-size: 1.8em !important;
    letter-spacing: 2px;
    color: #fff;
    text-shadow: 0 0 10px #ff00de, 2px 2px 0px #000;
}
.top2-bg { 
    background: linear-gradient(to bottom right, #3498db, #2c3e50); 
    border: 2px solid #a9dfbf; 
}
.top3-bg { 
    background: linear-gradient(to bottom right, #d35400, #5d4037); 
    border: 2px solid #edbb99; 
}
.static-aurora { 
    background: rgba(255, 255, 255, 0.15); /* Tăng độ sáng nền kính một chút */
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255,255,255,0.4); 
    transition: transform 0.2s;
}
.static-aurora:hover {
    background: rgba(255, 255, 255, 0.25);
    transform: translateY(-2px);
}
.rank-card { 
    border-radius: 15px;
    padding: 12px; 
    color: white; 
    transition: 0.3s; 
}
.medal-num { 
    display: inline-flex; align-items: center; justify-content: center; 
    width: 24px; height: 24px; 
    background: #f1c40f; color: #000; font-weight: bold;
    border-radius: 50%; font-size: 11px; margin-right: 8px; 
}
</style>
""", unsafe_allow_html=True)

    # --- 1. CSS HIỆU ỨNG "HÀNG HIẾM" (LEGENDARY) ---
    st.markdown("""
    <style>
    /* --- ANIMATION DEFINITIONS --- */
    
    /* 1. Hiệu ứng dòng chảy (cho Top 1 Gold) */
    @keyframes liquid-gold {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* 2. Hiệu ứng quét sáng (Sheen) - Vệt sáng chạy qua thẻ */
    @keyframes sheen-pass {
        0% { left: -100%; opacity: 0; }
        20% { left: 100%; opacity: 0.8; } /* Chạy nhanh qua */
        100% { left: 100%; opacity: 0; }   /* Đợi một chút rồi chạy lại */
    }

    /* 3. Hiệu ứng lấp lánh (Sparkle) cho Top 2 */
    @keyframes silver-sparkle {
        0% { filter: brightness(100%); }
        50% { filter: brightness(130%); }
        100% { filter: brightness(100%); }
    }

    /* --- STYLE CÁC KHUNG TOP --- */

    /* Cấu trúc chung cho Top 1,2,3 */
    .horizontal-card {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding: 8px 15px !important;
        border-radius: 50px !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5); /* Bóng đổ đậm hơn để nổi khối */
        transition: transform 0.3s;
        margin: 0 auto;
        position: relative;
        overflow: hidden; /* Để hiệu ứng quét sáng không bị tràn ra ngoài */
        z-index: 1;
        border: 2px solid rgba(255,255,255,0.8) !important;
    }
    .horizontal-card:hover { transform: scale(1.05); z-index: 5; }

    /* 👑 TOP 1: LIQUID GOLD (VÀNG CHẢY + QUÉT SÁNG) */
    .gold-legendary {
        /* Gradient vàng rực rỡ pha cam và trắng */
        background: linear-gradient(90deg, #FDC830, #F37335, #FDC830, #fff8db, #FDC830);
        background-size: 300% 300%;
        animation: liquid-gold 4s ease infinite; /* Màu chảy liên tục */
        border: 3px solid #fff !important;
        box-shadow: 0 0 25px rgba(253, 200, 48, 0.6); /* Phát sáng vàng */
    }
    /* Tạo vệt sáng quét qua (Sheen) */
    .gold-legendary::after {
        content: "";
        position: absolute;
        top: 0; left: -100%;
        width: 50%; height: 100%;
        background: linear-gradient(to right, rgba(255,255,255,0) 0%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0) 100%);
        transform: skewX(-25deg); /* Nghiêng vệt sáng */
        animation: sheen-pass 3s infinite; /* Quét qua mỗi 3 giây */
        z-index: 2;
    }

    /* 🥈 TOP 2: HOLOGRAPHIC SILVER (BẠC ĐA SẮC) */
    .silver-legendary {
        /* Màu bạc pha chút xanh băng giá và tím nhẹ */
        background: linear-gradient(135deg, #bdc3c7, #2c3e50, #bdc3c7, #e0eafc);
        background-size: 200% 200%;
        animation: liquid-gold 6s ease infinite; /* Chảy chậm hơn vàng */
        box-shadow: 0 0 15px rgba(189, 195, 199, 0.5);
    }

    /* 🥉 TOP 3: MOLTEN BRONZE (ĐỒNG NUNG) */
    .bronze-legendary {
        /* Màu đồng đỏ pha nâu đất */
        background: linear-gradient(135deg, #ba8b02, #181818, #ba8b02);
        background-size: 200% 200%;
        animation: silver-sparkle 3s infinite; /* Nhấp nháy độ sáng */
        box-shadow: 0 0 15px rgba(186, 139, 2, 0.4);
    }

    /* Nội dung bên trong (Để nổi lên trên lớp hiệu ứng) */
    .h-content-wrapper { position: relative; z-index: 3; display: flex; width: 100%; align-items: center; justify-content: space-between; }
    
    .h-info { text-align: left; flex-grow: 1; padding-left: 15px; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
    .h-kpi { 
        background: rgba(0,0,0,0.5); padding: 5px 12px; 
        border-radius: 20px; font-weight: bold; 
        border: 1px solid rgba(255,255,255,0.6); 
        min-width: 60px; text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }

    /* Top 4-10: Mini Card (Giữ nguyên cái đẹp sẵn có) */
    .mini-card {
        border-radius: 12px; padding: 8px 4px;
        color: white; text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.3);
        transition: transform 0.2s;
        display: flex; flex-direction: column; 
        align-items: center; justify-content: center;
    }
    .mini-card:hover { transform: translateY(-5px) scale(1.05); z-index: 10; border-color: #fff; }
    .rank-num-circle {
        background: white; color: #333; font-weight: 900;
        width: 18px; height: 18px; border-radius: 50%;
        font-size: 11px; display: flex; align-items: center; justify-content: center; margin-bottom: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- 2. RENDER HTML (UPDATE: FONT HOÀNG GIA & BỎ NGOẶC) ---
    
    # 🎨 1. Import Font mới (Cinzel Decorative) ngay tại đây
    # Font này nhìn rất "quyền lực", phù hợp với Vương Quốc
    font_import = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Roboto:wght@400;700&display=swap');
</style>
"""

    # 👑 TẦNG 1: TOP 1 (VUA)
    p1 = df_vinh_danh.iloc[0]
    h1_html = f"""
<div style="display: flex; justify-content: center; margin-bottom: 15px;">
<div class="horizontal-card gold-legendary" style="width: 350px;">
<div class="h-content-wrapper">
<div style="font-size: 2.5em; line-height: 1; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.5));">👑</div>
<div class="h-info">
<div style="font-family: 'Cinzel Decorative', cursive; font-size: 1.5em; color: #fff8db; letter-spacing: 1px; text-shadow: 2px 2px 0px #d35400; font-weight: 900;">{get_dynamic_rank(p1['kpi'])}</div>
<div style="font-family: 'Roboto', sans-serif; font-size: 0.9em; font-weight: 700; color: #fff; opacity: 0.95; font-style: italic;">{p1['name'].upper()}</div>
</div>
<div class="h-kpi" style="font-size: 1.1em; color: #f1c40f;">{p1['kpi']}</div>
</div>
</div>
</div>"""

    # 🥈🥉 TẦNG 2: TOP 2 & 3 (Á QUÂN)
    h23_html = ""
    if len(df_vinh_danh) > 1:
        h23_html = '<div style="display: flex; justify-content: center; gap: 10px; margin-bottom: 25px;">'
        
        # --- Top 2 ---
        p2 = df_vinh_danh.iloc[1]
        h23_html += f"""
<div class="horizontal-card silver-legendary" style="width: 210px;">
<div class="h-content-wrapper">
<span style="font-size: 2em; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.5));">🥈</span>
<div class="h-info" style="padding-left: 10px;">
<div style="font-family: 'Cinzel Decorative', cursive; font-size: 1.1em; color: #fff; letter-spacing: 0.5px; font-weight: 700;">{get_dynamic_rank(p2['kpi'])}</div>
<div style="font-family: 'Roboto', sans-serif; font-size: 0.75em; font-weight: bold; color: #eee;">{p2['name'].upper()}</div>
</div>
<div class="h-kpi" style="font-size: 0.9em; color: #e0e0e0;">{p2['kpi']}</div>
</div>
</div>"""
        
        # --- Top 3 ---
        if len(df_vinh_danh) > 2:
            p3 = df_vinh_danh.iloc[2]
            h23_html += f"""
<div class="horizontal-card bronze-legendary" style="width: 210px;">
<div class="h-content-wrapper">
<span style="font-size: 2em; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.5));">🥉</span>
<div class="h-info" style="padding-left: 10px;">
<div style="font-family: 'Cinzel Decorative', cursive; font-size: 1.1em; color: #fff; letter-spacing: 0.5px; font-weight: 700;">{get_dynamic_rank(p3['kpi'])}</div>
<div style="font-family: 'Roboto', sans-serif; font-size: 0.75em; font-weight: bold; color: #eee;">{p3['name'].upper()}</div>
</div>
<div class="h-kpi" style="font-size: 0.9em; color: #f4d03f;">{p3['kpi']}</div>
</div>
</div>"""
        h23_html += '</div>'

    # 🎖️ TẦNG 3: TOP 4-10 (KHUYẾN KHÍCH)
    rank_colors = [
        "linear-gradient(135deg, #3498db, #2980b9)", 
        "linear-gradient(135deg, #9b59b6, #8e44ad)",
        "linear-gradient(135deg, #e67e22, #d35400)",
        "linear-gradient(135deg, #1abc9c, #16a085)",
        "linear-gradient(135deg, #e74c3c, #c0392b)",
        "linear-gradient(135deg, #34495e, #2c3e50)",
        "linear-gradient(135deg, #7f8c8d, #95a5a6)"
    ]
    h410_html = ""
    if len(df_vinh_danh) > 3:
        h410_html = '<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;">'
        for i in range(3, len(df_vinh_danh)):
            p = df_vinh_danh.iloc[i]
            bg_color = rank_colors[(i-3) % len(rank_colors)]
            
            h410_html += f"""
<div class="mini-card" style="width: 130px; min-height: 100px; background: {bg_color};">
<div class="rank-num-circle">{i+1}</div>
<div style="font-family: 'Cinzel Decorative', cursive; font-size: 1.0em; color: #ffd700; margin-bottom: 2px; text-shadow: 1px 1px 0 #000; font-weight: 700;">{get_dynamic_rank(p['kpi'])}</div>
<div style="font-family: 'Roboto', sans-serif; font-size: 0.7em; font-weight: normal; line-height: 1.2; margin-bottom: 4px; word-wrap: break-word; color: #fff;">{p['name']}</div>
<div style="font-size: 0.9em; font-weight: 900; color: #fff;">{p['kpi']}</div>
</div>"""
        h410_html += '</div>'

    # --- 3. RENDER TỔNG ---
    # Cộng chuỗi font_import vào đầu để nạp font
    final_html = f"""
{font_import}
<div class="glory-banner">
<h2 style="color: #f1c40f; margin-bottom: 20px; font-size: 24px; letter-spacing: 3px; text-shadow: 2px 2px 4px #000; font-family: 'Cinzel Decorative', cursive;">🏆 HỌC GIẢ VINH DIỆU 🏆</h2>
{h1_html}
{h23_html}
{h410_html}
</div>"""

    st.markdown(final_html, unsafe_allow_html=True)

# 1. Lấy role hiện tại (chuyển về chữ thường để so sánh chuẩn xác)
current_role = str(st.session_state.get("user_role", "")).lower().strip()

# --- DEBUG: HIỆN ROLE RA ĐỂ KIỂM TRA (Xóa sau khi chạy ngon) ---
st.info(f"DEBUG ROUTER: Role hiện tại là [{current_role}]")

# ===== ADMIN =====
if st.session_state.user_role and st.session_state.user_role.lower() == "admin":
    import admin_module
    
    # 1. Trang Quản lý Boss (Đại chiến giáo viên)
    if st.session_state.page == "⚔️ Đại chiến Giáo viên": 
        admin_module.admin_quan_ly_boss()
    
    # 2. Trang Quản lý Phó bản 
    elif st.session_state.page == "🛡️ Quản lý Phó bản":
        # Gọi hàm quản lý phó bản và truyền save_shop_data để dùng tính năng đúc đồ
        admin_module.hien_thi_giao_dien_admin(save_data, save_shop_data)
    
    # 3. TRANG THÔNG BÁO SERVER (CHÈN MỚI TẠI ĐÂY)
    elif st.session_state.page == "📢 Thông báo Server":
        admin_module.giao_dien_thong_bao_admin()
    
    # 4. Trang Quản lý Tiệm tạp hóa
    elif st.session_state.page == "🏪 Quản lý Tiệm tạp hóa":
        admin_module.hien_thi_giao_dien_admin(save_data, save_shop_data)
    
    else:
        hien_thi_giao_dien_admin(save_data, save_shop_data) #

# ===== PHẦN HIỂN THỊ CỦA USER (ĐÃ FIX LỖI GIAO DIỆN TRỐNG) =====
elif st.session_state.user_role in ["u1", "u2", "u3"]:
    # ==============================================================================
    # 🔥 FIX LỖI KẸT BOSS (AUTO-KILL BOSS) - CHÈN VÀO ĐÂY
    # ==============================================================================
    # 1. Định nghĩa các từ khóa nhận diện trang Boss (đề phòng bạn đổi tên menu)
    page_hien_tai = str(st.session_state.get("page", ""))
    tu_khoa_boss = ["Boss", "Giáo viên", "Đại chiến", "boss"]
    
    # 2. Kiểm tra: Có đang ở trang Boss không?
    dang_o_trang_boss = any(tu in page_hien_tai for tu in tu_khoa_boss)
    
    # 3. Nếu KHÔNG ở trang Boss mà máy vẫn báo "đang đánh" -> CẮT CẦU DAO
    if not dang_o_trang_boss and st.session_state.get("dang_danh_boss") == True:
        # Tắt trạng thái đánh
        st.session_state.dang_danh_boss = False
        
        # Dọn dẹp biến rác của trận đấu
        keys_to_clean = ["combo", "cau_hoi_active", "thoi_gian_bat_dau"]
        for k in keys_to_clean:
            if k in st.session_state: 
                del st.session_state[k]
        
        # F5 lại trang để áp dụng
        st.rerun() 
        
    # 1. Trang Thám hiểm Phó bản (Xử lý cả Sảnh chờ và Combat bên trong)
    if st.session_state.page == "🗺️ Thám hiểm Phó bản":
        # Nếu đang trong trận đấu thì hiện Combat
        if st.session_state.get("dang_danh_dungeon"):
            u_id = st.session_state.user_id
            l_id = st.session_state.get('selected_land', 'toan')
            d_config = load_dungeon_config()
            
            user_progress = st.session_state.data[u_id].get('dungeon_progress', {})
            p_current_num = user_progress.get(l_id, 1)
            p_id = f"phase_{p_current_num}"
            
            user_module.trien_khai_combat_pho_ban(u_id, l_id, p_id, d_config, save_data)
        else:
            # Nếu chưa vào trận thì hiện Sảnh chờ chọn Phase
            user_module.hien_thi_sanh_pho_ban_hoc_si(st.session_state.user_id)

    # 2. Trang Đấu Lôi Đài
    elif st.session_state.page == "🏟️ Đấu Lôi Đài":
        user_module.hien_thi_loi_dai(st.session_state.user_id, save_data)
        
    # 3. Trang Boss Giáo viên
    elif st.session_state.page == "⚔️ Đại chiến Giáo viên":
        user_module.hien_thi_san_dau_boss(st.session_state.user_id, save_data)
      
    # 4. Trang Tiệm tạp hóa & Kho đồ
    elif st.session_state.page == "🏪 Tiệm tạp hóa & Kho đồ":
        
        # Lấy ID người dùng
        current_user_id = st.session_state.get('user_id')

        # --- PHẦN 1: HIỂN THỊ LOA PHÁT THANH (CHẠY LIÊN TỤC) ---
        # Kiểm tra file tồn tại trước khi đọc để tránh lỗi
        if os.path.exists('data/world_announcements.json'):
            try:
                with open('data/world_announcements.json', 'r', encoding='utf-8') as f:
                    msgs = json.load(f)
                    if msgs:
                        last_msg = msgs[-1] # Lấy tin mới nhất
                        
                        # Kiểm tra hạn sử dụng (Expire)
                        current_ts = datetime.now().timestamp()
                        expire_at = last_msg.get('expire_at', 0)
                        
                        if current_ts < expire_at:
                            st.markdown(f"""
                                <div style="background: linear-gradient(90deg, #ff8a00, #e52e71); 
                                            padding: 10px 0; overflow: hidden; white-space: nowrap; 
                                            border-top: 2px solid gold; border-bottom: 2px solid gold; 
                                            margin-bottom: 20px; position: relative;">
                                    <div style="display: inline-block; padding-left: 100%; 
                                                animation: marquee 20s linear infinite; 
                                                color: white; font-weight: bold; font-size: 1.2em;">
                                        📢 LOA PHÁT THANH - {last_msg['user'].upper()}: {last_msg['content']} 
                                        &nbsp;&nbsp;&nbsp; [Gửi lúc: {last_msg['time']}]
                                    </div>
                                </div>
                                <style>
                                @keyframes marquee {{
                                    0% {{ transform: translate(0, 0); }}
                                    100% {{ transform: translate(-100%, 0); }}
                                }}
                                </style>
                            """, unsafe_allow_html=True)
            except Exception as e:
                pass 

        # --- PHẦN 2: LOGIC NHẬP LIỆU & GỬI TIN ---
        if current_user_id and current_user_id in st.session_state.data:
            
            # 1. Tính toán số lượt chat TRƯỚC khi dùng
            user_info = st.session_state.data[current_user_id]
            chat_count = user_info.get('special_permissions', {}).get('world_chat_count', 0)
            
            # 2. Chỉ hiện khung nhập nếu còn lượt
            if chat_count > 0:
                with st.expander(f"✨ BẠN ĐANG CÓ {chat_count} LƯỢT PHÁT THANH THẾ GIỚI"):
                    world_msg = st.text_input("Nhập thông điệp muốn truyền tin (tối đa 100 ký tự):", 
                                            max_chars=100, 
                                            key="world_chat_input_main")
                    
                    if st.button("🚀 XÁC NHẬN PHÁT TIN", use_container_width=True):
                        if world_msg.strip():
                            # A. Tạo tin nhắn mới
                            new_msg = {
                                "user": current_user_id,
                                "content": world_msg,
                                "time": datetime.now().strftime("%H:%M"),
                                "expire_at": (datetime.now() + timedelta(minutes=60)).timestamp()
                            }
                            
                            # B. Đọc và Cập nhật file JSON
                            current_msgs = []
                            if os.path.exists('data/world_announcements.json'):
                                try:
                                    with open('data/world_announcements.json', 'r', encoding='utf-8') as f:
                                        current_msgs = json.load(f)
                                except:
                                    current_msgs = []
                            
                            current_msgs.append(new_msg)
                            current_msgs = current_msgs[-10:] # Giữ 10 tin gần nhất
                            
                            with open('data/world_announcements.json', 'w', encoding='utf-8') as f:
                                json.dump(current_msgs, f, indent=4, ensure_ascii=False)
                            
                            # C. Trừ lượt trong data
                            if 'special_permissions' in st.session_state.data[current_user_id]:
                                st.session_state.data[current_user_id]['special_permissions']['world_chat_count'] -= 1
                            
                            # D. Lưu dữ liệu
                            save_data(st.session_state.data) 
                            
                            st.success("Tin nhắn của bạn đã được lan tỏa khắp vương quốc!")
                            st.rerun()
                        else:
                            st.warning("Vui lòng nhập nội dung!")

            # 3. Gọi hàm hiển thị Tiệm & Kho (Nằm trong if user check)
            user_module.hien_thi_tiem_va_kho(current_user_id, save_data)
        
    # chợ đen
    elif st.session_state.page == "⚖️ Chợ Đen":
        user_module.hien_thi_cho_den(st.session_state.user_id, save_data)

    # 5. MẶC ĐỊNH: Trang chủ học sĩ
    else:
        hien_thi_giao_dien_hoc_si(st.session_state.user_id, save_data)


# ===== GUEST (KHÁCH - CHƯA ĐĂNG NHẬP) =====
else:    
    # --- GIAO DIỆN KHÁCH ---
    col_sidebar, col_main = st.columns([1, 2.5])

    # --- CỘT TRÁI: ĐĂNG NHẬP & BẢNG CAO THỦ ---
    with col_sidebar:
        st.subheader("🔑 ĐĂNG NHẬP")
        with st.form("login_form"):
            # Truyền giá trị đã lưu vào tham số 'value' 
            u_id_input = st.text_input("Mã Học Sĩ (ID):").strip().lower()
            
            # ✅ DÒNG MỚI CHO MẬT KHẨU LUÔN:
            pwd_input = st.text_input("Mật khẩu:", type="password")             
            
            btn_login = st.form_submit_button("VÀO HỆ THỐNG 🔥")
            
        # --- NÚT HƯỚNG DẪN TÂN THỦ TÙY CHỈNH ---
        st.write("") # Tạo một khoảng cách nhỏ
        # Sử dụng CSS để tạo giao diện nút bấm tùy chỉnh
        st.markdown("""
            <style>
            div.stButton > button:first-child {
                background-color: #FF4B4B; /* Màu nền đỏ nổi bật */
                color: white;               /* Màu chữ trắng */
                font-size: 20px;            /* Cỡ chữ to hơn */
                font-weight: bold;          /* Chữ in đậm */
                border-radius: 10px;        /* Bo góc nút */
                height: 3em;                /* Độ cao của nút */
                width: 100%;                /* Full chiều ngang cột */
                border: 2px solid #ffcc00;  /* Viền vàng rực rỡ */
                transition: 0.3s;
            }
            div.stButton > button:first-child:hover {
                background-color: #ffcc00;  /* Đổi sang màu vàng khi di chuột vào */
                color: #FF4B4B;             /* Đổi màu chữ khi hover */
                border: 2px solid #FF4B4B;
            }
            </style>
            """, unsafe_allow_html=True)
        if st.button("📖 **HƯỚNG DẪN TÂN THỦ**", use_container_width=True):
            show_tutorial()
            
        # Xử lý sự kiện bấm nút đăng nhập
        if btn_login:
            # 1. Chuẩn hóa ID nhập vào (viết thường, KHỬ DẤU TIẾNG VIỆT)
            raw_input = str(u_id_input).strip().lower()
            
            # --- BẢNG MÃ ĐẦY ĐỦ (KHÔNG ĐƯỢC CÓ DẤU BA CHẤM ...) ---
            vietnamese_map = {
                'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a', 'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
                'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
                'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o', 'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
                'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u', 'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
                'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
                'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
                'đ': 'd', ' ': '' # Dòng này xóa khoảng trắng
            }

            # Chạy vòng lặp để thay thế ký tự
            u_id_clean = raw_input
            for char, replacement in vietnamese_map.items():
                u_id_clean = u_id_clean.replace(char, replacement)
            
            # 2. Chuẩn hóa mật khẩu nhập vào (xóa khoảng trắng đầu cuối)
            input_pass = str(pwd_input).strip()

            # 3. Kiểm tra sự tồn tại của tài khoản trong dữ liệu
            if u_id_clean in st.session_state.data:
                user_info = st.session_state.data[u_id_clean]
                
                # --- XỬ LÝ MẬT KHẨU TỪ HỆ THỐNG/GGSHEETS ---
                # Ép kiểu về chuỗi và xóa khoảng trắng
                raw_stored_pass = str(user_info.get("password", "")).strip()
                
                # Xử lý trường hợp mật khẩu bị biến thành số thực (ví dụ: "123456.0")
                stored_pass = raw_stored_pass
                if "." in stored_pass and stored_pass.split('.')[-1] == '0':
                    stored_pass = stored_pass.split('.')[0]
                
                # --- [DEBUG CHẾ ĐỘ ADMIN] ---
                # Nếu bạn vẫn không vào được, hãy bỏ comment 2 dòng dưới đây để soi lỗi:
                # st.write(f"DEBUG: Nhập vào '{input_pass}' | Trong máy '{stored_pass}'")
                # st.write(f"Khớp hay không: {input_pass == stored_pass}")

                # 4. So sánh mật khẩu
                if input_pass == stored_pass:
                    # Đăng nhập thành công
                    raw_role = user_info.get("role", "player")
                    final_role = str(raw_role).strip().lower()
                    
                    st.session_state.user_role = final_role
                    st.session_state.user_id = u_id_clean
                    st.session_state.page = None
                    
                    # Thông báo và chuyển trang
                    if st.session_state.user_role.lower() == "admin":
                        st.success("🔓 Chào mừng Quản trị viên!")
                    else:
                        st.success(f"🔓 Chào mừng {user_info.get('name', 'Chiến binh')}!")
                    
                    st.rerun()
                else:
                    st.error("❌ Mật khẩu không chính xác!")
            else:
                st.error(f"❌ Tài khoản '{u_id_clean}' không tồn tại trên hệ thống!")
                # Gợi ý: Kiểm tra xem ID trên Google Sheets có dấu cách ở giữa không? 
                # Nếu Sheets là "Nguyen Van A" thì key phải là "nguyenvana"
           
        st.divider()
        with st.expander("🕵️‍♂️ KÍNH CHIẾU YÊU (Debug Data)", expanded=True):
            st.warning("Đây là dữ liệu thực tế hệ thống đang đọc:")
            
            # 1. In ra danh sách tất cả tài khoản đang có trong RAM
            # Kiểm tra xem st.session_state.data có tồn tại không trước khi gọi
            if 'data' in st.session_state:
                all_keys = list(st.session_state.data.keys())
                st.write(f"🔑 Danh sách ID tài khoản ({len(all_keys)}):", all_keys)
                
                # 2. Soi chi tiết tài khoản Admin
                if "admin" in st.session_state.data:
                    real_admin_pass = st.session_state.data["admin"].get("password")
                    st.code(f"Mật khẩu Admin trong RAM là: '{real_admin_pass}'")
                    st.write(f"Kiểu dữ liệu: {type(real_admin_pass)}")
                else:
                    st.error("❌ KHÔNG TÌM THẤY key 'admin' trong dữ liệu!")
            else:
                st.error("⚠️ Biến st.session_state.data chưa được khởi tạo!")

            # 3. Nút ép tải lại dữ liệu mới nhất từ Cloud
            if st.button("🔄 ÉP TẢI LẠI DỮ LIỆU TỪ CLOUD (Hard Reset)", type="primary"):
                st.cache_data.clear() # Xóa cache của Streamlit
                # Đảm bảo bạn đã import load_data ở đầu file
                st.session_state.data = load_data() 
                st.success("Đã tải lại! Hãy thử đăng nhập lại ngay.")
                st.rerun() 
        
        # 👇👇👇 [MỚI] CHÈN BẢNG VÀNG VÀO ĐÂY (Vẫn nằm trong with col_sidebar) 👇👇👇
        st.write("") # Tạo khoảng trống cho thoáng       
        # Gọi hàm hiển thị bảng vàng (Bạn đã tạo ở Bước 3)
        # Lưu ý: Cần đảm bảo hàm này đã được import hoặc định nghĩa ở đầu file
        try:
            hien_thi_bang_vang_diem_so()
        except NameError:
            st.error("Chưa tìm thấy hàm 'hien_thi_bang_vang_diem_so'. Hãy kiểm tra lại Bước 3!")
        # 👆👆👆 ----------------------------------------------------------- 👆👆👆


    # --- CỘT PHẢI: BẢNG VINH DANH LỚN (GIỮ NGUYÊN) ---
    with col_main:
        # --- BƯỚC 1: CHÈN BANNER VÀO ĐÂY (VỊ TRÍ CAO NHẤT) ---
        hien_thi_banner_vinh_quang() 

        st.info("👀 Hãy đăng nhập để tham gia vương quốc!")
        st.divider() # Vạch ngăn cách giữa Banner và Chiến trường


        # 2. KHU VỰC CHIẾN TRƯỜNG (LÔI ĐÀI & LIÊN MINH)
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("<div class='main-card' style='border-left-color: #e74c3c; padding: 10px;'>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-weight: bold;'>🏟️ ĐẤU TRƯỜNG LÔI ĐÀI</p>", unsafe_allow_html=True)
            
            # Gắn lệnh gọi hàm vào nút bấm
            if st.button("⚔️ NHẤN ĐỂ VÀO ĐẤU TRƯỜNG ⚔️", key="btn_guest_arena", use_container_width=True, type="primary"):
                show_arena_info_popup() # Gọi hàm hiển thị Popup bự
                
            # Khung chứa ảnh
            st.markdown("""
                <div class="banner-container">
                    <img src="https://i.ibb.co/XZgnRYb1/Gemini-Generated-Image-w8tdjxw8tdjxw8td.png">
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<p style='text-align: center; font-size: 0.8em; color: #7f8c8d; margin-top: 5px;'>SÂN ĐẤU ĐANG TRỐNG - Hãy khiêu chiến!</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='main-card' style='border-left-color: #2980b9; padding: 10px;'>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-weight: bold;'>🛡️ LIÊN MINH CHIẾN</p>", unsafe_allow_html=True)
            st.button("💠 VÀO LIÊN MINH CHIẾN 💠", use_container_width=True, type="primary")
            # Sử dụng khung chứa ảnh cố định kích thước
            st.markdown("""
                <div class="banner-container">
                    <img src="https://i.ibb.co/s9Hj4gxk/Gemini-Generated-Image-dhw36jdhw36jdhw3.png">
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<p style='text-align: center; font-size: 0.8em; color: #7f8c8d; margin-top: 5px;'>THANH LONG VS BẠCH HỔ - Chốt hạ mục tiêu!</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # 3. KHIÊU CHIẾN BOSS HỌC KỲ - PHIÊN BẢN CAM NEON RỰC RỠ


        def get_base64(bin_file):
            if os.path.exists(bin_file):
                with open(bin_file, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            return ""

        # --- BƯỚC 1: LẤY DỮ LIỆU ---
        path_config = r"data/boss_config.json"
        boss = {}
        if os.path.exists(path_config):
            with open(path_config, "r", encoding="utf-8") as f:
                boss = json.load(f).get("active_boss", {})

        if boss and boss.get("status") == "active":
            img_b64 = get_base64(boss.get("anh", "assets/teachers/toan.png"))
            img_src = f"data:image/png;base64,{img_b64}"
            
            hp_cur = boss.get("hp_current", 0)
            hp_max = boss.get("hp_max", 10000)
            percent = (hp_cur / hp_max) * 100
            
            contributions = boss.get("contributions", {})
            top_10 = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # --- BƯỚC 2: DANH SÁCH TOP 10 (22PX) ---
            top_list_html = ""
            for i, (uid, dmg) in enumerate(top_10):
                name = st.session_state.data.get(uid, {}).get("name", uid)
                color = "#f1c40f" if i < 3 else "#ffffff" 
                top_list_html += f"""
                <div style='display:flex; justify-content:space-between; color:{color}; font-size:22px; margin-bottom:12px; border-bottom: 2px solid rgba(255,255,255,0.1); padding-bottom:5px;'>
                    <span><b>#{i+1}</b> {name}</span> 
                    <span style='color:#00d2ff; font-weight:bold;'>{dmg:,} <small style='font-size:12px;'>DMG</small></span>
                </div>"""

            # --- BƯỚC 3: HTML & CSS (CAM NEON) ---
            boss_ui_html = f"""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Bangers&family=Permanent+Marker&display=swap');
                body {{ margin: 0; padding: 0; background: transparent; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}
                
                .boss-card {{
                    background: linear-gradient(135deg, #6c5ce7 0%, #00d2ff 50%, #ff4d4d 100%);
                    border-left: 18px solid #fff;
                    border-radius: 0 50px 50px 0;
                    padding: 35px;
                    display: flex;
                    height: 600px; 
                    box-shadow: 25px 25px 50px rgba(0,0,0,0.7);
                    color: white;
                    border: 5px solid rgba(255,255,255,0.4);
                    box-sizing: border-box;
                }}

                .boss-avatar-box {{
                    flex: 0 0 50%; 
                    height: 100%;
                    border: 10px solid white;
                    border-radius: 30px;
                    overflow: hidden;
                    box-shadow: 0 0 40px rgba(0,0,0,0.6);
                    background: #000;
                }}
                .boss-avatar-box img {{ width: 100%; height: 100%; object-fit: contain; background-color: #1a1a1a; }}

                .boss-main-content {{
                    flex: 0 0 50%;
                    padding-left: 50px;
                    display: flex;
                    flex-direction: column;
                    justify-content: flex-start;
                    box-sizing: border-box;
                }}

                .boss-prefix {{
                    font-family: 'Permanent Marker', cursive;
                    font-size: 65px;
                    color: #fff;
                    text-shadow: 8px 8px 0px #ff4d4d, 12px 12px 0px #000;
                    margin: 0;
                    line-height: 1;
                }}

                /* Tên Boss Màu Xám Kim Loại Đậm có Viền Trắng */
                .boss-header {{
                    font-family: 'Bangers', cursive;
                    font-size: 55px; 
                    color: #2c3e50; /* Màu xám kim loại đậm (Gunmetal) */
                    
                    /* Viền trắng mảnh lại (1px) */
                    -webkit-text-stroke: 1px #ffffff; 
                    
                    /* Bóng đổ khối 3D */
                    text-shadow: 4px 4px 0px #1a1a1a, 
                                 0px 0px 10px rgba(255, 255, 255, 0.3);
                                 
                    margin-bottom: 25px;
                    letter-spacing: 3px;
                    line-height: 1.2;
                    font-weight: bold;
                    text-transform: uppercase;
                }}
                .hp-mini-container {{
                    background: rgba(0,0,0,0.8);
                    border-radius: 20px;
                    height: 55px; 
                    width: 100%;
                    position: relative;
                    overflow: hidden;
                    border: 4px solid white;
                    margin-bottom: 20px;
                }}
                .hp-mini-bar {{
                    background: linear-gradient(90deg, #ff4d4d, #f1c40f);
                    width: {percent}%;
                    height: 100%;
                    box-shadow: 0 0 30px #ff4d4d;
                }}
                .hp-mini-text {{
                    position: absolute; width:100%; text-align:center; top:0;
                    font-size: 26px; font-weight: bold; line-height: 55px;
                    text-shadow: 2px 2px 4px #000;
                }}

                .damage-leaderboard {{
                    background: rgba(0,0,0,0.5);
                    border-radius: 30px;
                    padding: 25px;
                    flex-grow: 1;
                    border: 2px solid rgba(255,255,255,0.3);
                    display: flex;
                    flex-direction: column;
                }}
                .leaderboard-title {{
                    font-size: 26px; font-weight: bold; text-transform: uppercase;
                    margin-bottom: 20px; color: #f1c40f; border-bottom: 4px solid #f1c40f;
                    padding-bottom: 10px; text-align: center;
                }}
                .list-container {{ overflow-y: auto; flex-grow: 1; }}
            </style>

            <div class="boss-card">
                <div class="boss-avatar-box">
                    <img src="{img_src}">
                </div>
                <div class="boss-main-content">
                    <p class="boss-prefix">BOSS</p>
                    <div class="boss-header">{boss.get('ten', 'HỌC KỲ').upper()}</div>
                    <div class="hp-mini-container">
                        <div class="hp-mini-bar"></div>
                        <div class="hp-mini-text">HP: {hp_cur:,} / {hp_max:,}</div>
                    </div>
                    
                    <div class="damage-leaderboard">
                        <div class="leaderboard-title">🏆 TOP 10 CHIẾN BINH</div>
                        <div class="list-container">
                            {top_list_html if top_list_html else "<i style='font-size:22px;'>Đang chờ anh hùng xuất trận...</i>"}
                        </div>
                    </div>
                </div>
            </div>
            """
            components.html(boss_ui_html, height=630)
        else:
            st.info("Hiện không có Boss nào hoạt động.")
            
        # --- 4. SẢNH CHỌN VÙNG ĐẤT PHÓ BẢN ---
        import streamlit.components.v1 as components

        # Danh sách dữ liệu 6 vùng đất (Bạn có thể thay đổi link ảnh nền tương ứng)
        vung_dat_data = [
            {"name": "Rừng Toán Học", "icon": "📐", "bg_url": "https://i.ibb.co/Nd0b47RD/khuvuontoanhoc.png"},
            {"name": "Hang Động Ngôn Ngữ", "icon": "🇬🇧", "bg_url": "https://i.ibb.co/99ppBGf3/hangdongngonngu.png"},
            {"name": "Thung Lũng Văn Chương", "icon": "📖", "bg_url": "https://i.ibb.co/k6kTjVmv/thunglungvanchuong.png"},
            {"name": "Ngọn Núi Vật Lý", "icon": "⚡", "bg_url": "https://i.ibb.co/CsVxQ9R1/ngonnuivatly.png"},
            {"name": "Hồ Nước Hóa Học", "icon": "🧪", "bg_url": "https://i.ibb.co/rX37KRR/honuochoahoc.png"},
            {"name": "Vườn Sinh Học", "icon": "🌿", "bg_url": "https://i.ibb.co/nZmMd2B/vuonsinhhoc.png"}
        ]

        # --- ĐOẠN CODE HIỂN THỊ PHÓ BẢN HOÀN CHỈNH ---
        st.markdown("## 🗺️ KHÁM PHÁ CÁC VÙNG ĐẤT PHÓ BẢN")
        
        # Định nghĩa dữ liệu hiển thị cố định để ánh xạ chính xác vào land_id trong data.json
        display_data = [
            ("Rừng Toán Học", "toan", vung_dat_data[0]['bg_url'], vung_dat_data[0]['icon']),
            ("Hang Động Ngôn Ngữ", "anh", vung_dat_data[1]['bg_url'], vung_dat_data[1]['icon']),
            ("Thung Lũng Văn Chương", "van", vung_dat_data[2]['bg_url'], vung_dat_data[2]['icon']),
            ("Ngọn Núi Vật Lý", "ly", vung_dat_data[3]['bg_url'], vung_dat_data[3]['icon']),
            ("Hồ Nước Hóa Học", "hoa", vung_dat_data[4]['bg_url'], vung_dat_data[4]['icon']),
            ("Vườn Sinh Học", "sinh", vung_dat_data[5]['bg_url'], vung_dat_data[5]['icon']),
        ]

        for i in range(0, len(display_data), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(display_data):
                    # Lấy thông tin từ display_data theo đúng thứ tự
                    name_display, land_key, bg_img, icon_img = display_data[i + j] 
                    
                    with cols[j]:
                        # Hiển thị Card HTML
                        html_code = f"""
                        <div style="background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url('{bg_img}');
                                    background-size: cover; background-position: center; height: 150px; border-radius: 15px; 
                                    display: flex; flex-direction: column; justify-content: center; 
                                    align-items: center; color: white; border: 1px solid rgba(255,255,255,0.3);
                                    margin-bottom: 5px;">
                            <div style="font-size: 35px;">{icon_img}</div>
                            <b style="font-family: sans-serif; font-size: 18px;">{name_display.upper()}</b>
                        </div>"""
                        st.markdown(html_code, unsafe_allow_html=True)
                        
                        # NÚT BẤM: Truyền land_key (toan, van, anh...) cố định vào hàm
                        # Sử dụng land_key riêng biệt cho từng nút để không bị trùng lặp dữ liệu
                        if st.button(f"🏆 Vinh Danh {name_display}", key=f"btn_vinh_danh_{land_key}", use_container_width=True):
                            show_land_info_popup(name_display, land_key)