import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
import random
import unicodedata
import re
import uuid
import gspread
from google.oauth2.service_account import Credentials
import ast
from item_system import get_item_info, apply_item_effect
from item_system import get_active_combat_stats

# --- CẤU HÌNH KẾT NỐI GOOGLE SHEETS ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "Data_KPI_Kingdom"

def get_gspread_client():
    # Sử dụng .get() để không bị lỗi "No secrets found" làm sập app
    gcp_info = st.secrets.get("gcp_service_account")
    
    if gcp_info:
        # Nếu tìm thấy Secret (trên Streamlit Cloud hoặc trong file .streamlit/secrets.toml)
        creds_dict = dict(gcp_info)
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        return gspread.authorize(creds)
    
    elif os.path.exists("service_account.json"):
        # Nếu không có Secret nhưng có file json cục bộ
        creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPE)
        return gspread.authorize(creds)
    
    else:
        st.warning("⚠️ Đang chạy mà không có kết nối Database (Secret/JSON missing)")
        return None

try:
    # Ưu tiên 1: Kiểm tra xem có cấu hình trong Streamlit Secrets không (Khi chạy Online)
    if "gcp_service_account" in st.secrets:
        creds_info = st.secrets["gcp_service_account"]
        CREDS = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
        CLIENT = gspread.authorize(CREDS)
        print("✅ Đã kết nối Google Sheets qua Secrets (Online Mode)")
    
    # Ưu tiên 2: Nếu không có Secrets, tìm file local (Khi chạy ở máy nhà để test)
    elif os.path.exists("service_account.json"):
        CREDS = Credentials.from_service_account_file("service_account.json", scopes=SCOPE)
        CLIENT = gspread.authorize(CREDS)
        print("✅ Đã kết nối Google Sheets qua file JSON (Local Test Mode)")
    
    else:
        print("💡 Chế độ Offline: Không tìm thấy phương thức kết nối Google Sheets.")

except Exception as e:
    print(f"⚠️ Chưa kết nối được Google Sheets: {e}")


# --- HÀM POPUP KẾT QUẢ MỞ RƯƠNG (DIALOG) ---
@st.dialog("✨ KẾT QUẢ MỞ RƯƠNG ✨")
def popup_ket_qua_mo_ruong(item_name, rewards):
    """
    Hiển thị Popup kết quả Gacha giữa màn hình.
    """
    # 1. Hiệu ứng pháo hoa chúc mừng
    st.balloons()
    
    # 2. Hiển thị nội dung quà to đẹp
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 60px;">🎁</div>
            <h2 style="color: #d35400; margin: 0;">{item_name}</h2>
            <p style="color: gray;">Bạn đã nhận được các vật phẩm sau:</p>
            <hr>
        </div>
    """, unsafe_allow_html=True)
    
    # 3. Liệt kê từng món quà
    for reward in rewards:
        # Chọn màu sắc dựa trên loại quà (mặc định xanh lá)
        bg_color = "#d4edda" 
        text_color = "#155724"
        icon = "✔️"
        
        # Nếu quay trượt (Miss)
        if "trống rỗng" in reward['msg']:
            bg_color = "#f8d7da"
            text_color = "#721c24"
            icon = "💨"
            
        st.markdown(f"""
            <div style="
                background-color: {bg_color}; 
                color: {text_color}; 
                padding: 15px; 
                border-radius: 10px; 
                margin-bottom: 10px; 
                font-weight: bold; 
                font-size: 1.1em; 
                display: flex; 
                align-items: center;
                justify-content: center;
            ">
                <span style="margin-right: 10px;">{icon}</span> {reward['msg']}
            </div>
        """, unsafe_allow_html=True)

    st.write("") # Khoảng trống
    
    # 4. Nút Đóng Popup (Người chơi tự bấm mới tắt)
    if st.button("🤩 TUYỆT VỜI! NHẬN QUÀ NGAY", type="primary", use_container_width=True):
        # Xóa trạng thái để đóng popup
        del st.session_state.gacha_result
        st.rerun()
        
def load_market():
    if not os.path.exists("market.json"):
        with open("market.json", "w") as f:
            json.dump({"listings": {}}, f)
    with open("market.json", "r") as f:
        return json.load(f)

def save_market(data):
    with open("market.json", "w") as f:
        json.dump(data, f, indent=4)

import streamlit as st
import json
import os
from datetime import datetime
import uuid

# --- CẤU HÌNH ĐƯỜNG DẪN FILE ---
MARKET_FILE = "market.json"
SHOP_DATA_FILE = "shop_data.json" # Đảm bảo file này nằm cùng thư mục

# --- CÁC HÀM LOAD/SAVE DỮ LIỆU ---
def load_json_data(filepath, default_value):
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return default_value

def save_json_data(filepath, data):
    with open(filepath, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def ghi_log_boss(user_id, boss_name, damage, rewards):
    log_file = 'data/boss_logs.json'
    new_log = {
        "boss_name": boss_name,
        "user_id": user_id,
        "damage": int(damage),
        "rewards": ", ".join(rewards) if isinstance(rewards, list) else str(rewards),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    logs = []
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
            except: logs = []
            
    logs.append(new_log)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)
        
def load_market():
    return load_json_data(MARKET_FILE, {"listings": {}})

def save_market(data):
    save_json_data(MARKET_FILE, data)

# --- [QUAN TRỌNG] HÀM MAPPING ẢNH ĐÃ SỬA ---
def get_item_image_map():
    """
    Đọc file shop_data.json cấu trúc phẳng:
    { "tri thuc": { "image": "url..." }, "test": { "image": "url..." } }
    """
    shop_data = load_json_data(SHOP_DATA_FILE, {})
    image_map = {}
    
    # Duyệt trực tiếp qua các key (tên vật phẩm)
    for item_name, details in shop_data.items():
        if isinstance(details, dict):
            # Lấy link ảnh từ trường 'image'
            img_url = details.get('image')
            if img_url:
                image_map[item_name] = img_url
                
    return image_map

# --- ICON DỰ PHÒNG ---
def get_fallback_icon(name):
    name = name.lower()
    if "thẻ" in name or "card" in name: return "🃏"
    if "sách" in name or "tri thức" in name: return "📘"
    if "thuốc" in name or "dược" in name: return "🧪"
    if "kiếm" in name or "vũ khí" in name: return "⚔️"
    if "giáp" in name: return "🛡️"
    return "📦"

# ==============================================================================
# GIAO DIỆN CHỢ ĐEN (DARK RPG STYLE)
# ==============================================================================
def hien_thi_cho_den(current_user_id, save_data_func):
    # 1. Tải dữ liệu
    market_data = load_market()
    user_data = st.session_state.data.get(current_user_id, {})
    item_image_map = get_item_image_map() # Lấy map ảnh mới

    # --- 2. CSS ---
    st.markdown("""
        <style>
        .market-card {
            background: linear-gradient(135deg, #1e1e2e 0%, #252538 100%);
            border: 1px solid #45475a;
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            position: relative;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            overflow: hidden;
        }
        .market-card:hover {
            transform: translateY(-5px);
            border-color: #f9e2af;
            box-shadow: 0 10px 20px rgba(249, 226, 175, 0.15);
        }
        
        /* CSS ẢNH ITEM (Đã tối ưu cho Icon) */
        .item-real-image {
            width: 100px;
            height: 100px;
            object-fit: contain; /* Dùng contain để không bị cắt ảnh icon */
            border-radius: 10px;
            margin: 0 auto 10px auto;
            display: block;
            background-color: rgba(255,255,255,0.05); /* Nền mờ nhẹ cho ảnh png */
            padding: 5px;
            border: 1px dashed #585b70;
        }
        
        .item-fallback-icon {
            font-size: 80px; text-align: center; margin-bottom: 10px;
            filter: drop-shadow(0 0 5px rgba(255,255,255,0.2));
        }
        .item-title {
            color: #cdd6f4; font-size: 18px; font-weight: 800;
            text-align: center; margin-bottom: 5px; text-transform: uppercase;
            letter-spacing: 1px;
        }
        .seller-info {
            color: #bac2de; font-size: 13px; text-align: center; margin-bottom: 15px;
        }
        .price-badge {
            background: rgba(249, 226, 175, 0.1); color: #f9e2af;
            border: 1px solid #f9e2af; padding: 5px 20px; border-radius: 50px;
            font-weight: bold; font-size: 16px;
        }
        .my-item-badge {
            position: absolute; top: 10px; right: 10px;
            background: linear-gradient(45deg, #a6da95, #8bd5ca);
            color: #1e1e2e; font-size: 10px; font-weight: 900;
            padding: 4px 8px; border-radius: 6px; z-index: 5;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #f9e2af; text-shadow: 0 0 15px rgba(249,226,175,0.4);'>⚖️ THỊ TRƯỜNG CHỢ ĐEN</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🛒 SÀN GIAO DỊCH", "🎒 KHO & NIÊM YẾT"])

    # --- TAB 1: MUA HÀNG ---
    with tab1:
        listings = market_data.get('listings', {})
        
        if not listings:
            st.markdown("""<div style="text-align: center; padding: 50px; opacity: 0.5;"><div style="font-size: 60px;">🕸️</div><h3>Chưa có ai bán gì cả...</h3></div>""", unsafe_allow_html=True)
        else:
            cols = st.columns(2) 
            for idx, (item_id, info) in enumerate(listings.items()):
                is_mine = info['seller_id'] == current_user_id
                item_name = info.get('item_name', 'Vật phẩm')
                
                # --- XỬ LÝ ẢNH ---
                # So khớp chính xác tên item trong market với key trong shop_data
                real_image_url = item_image_map.get(item_name)
                
                if real_image_url:
                    image_html = f'<img src="{real_image_url}" class="item-real-image" alt="{item_name}">'
                else:
                    fallback = get_fallback_icon(item_name)
                    image_html = f'<div class="item-fallback-icon">{fallback}</div>'
                # -----------------

                with cols[idx % 2]:
                    seller_name = st.session_state.data.get(info['seller_id'], {}).get('name', 'Ẩn danh')
                    mine_tag = '<div class="my-item-badge">👑 CỦA BẠN</div>' if is_mine else ''
                    
                    st.markdown(f"""
                        <div class="market-card">
                            {mine_tag}
                            {image_html}
                            <div class="item-title">{item_name}</div>
                            <div class="seller-info">Người bán: {seller_name}</div>
                            <div style="display: flex; justify-content: center;">
                                <div class="price-badge">💎 {info['price']} KPI</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Nút bấm
                    if is_mine:
                        c1, c2 = st.columns([4, 1])
                        with c1: st.button("🔒 Đang niêm yết", key=f"st_{item_id}", disabled=True, use_container_width=True)
                        with c2:
                            if st.button("🗑️", key=f"rm_{item_id}", help="Gỡ xuống"):
                                st.session_state.data[current_user_id].setdefault('inventory', []).append(item_name)
                                del market_data['listings'][item_id]
                                save_market(market_data)
                                save_data_func(st.session_state.data)
                                st.rerun()
                    else:
                        if st.button(f"💸 MUA NGAY", key=f"buy_{item_id}", use_container_width=True, type="primary"):
                            price = info['price']
                            if user_data.get('kpi', 0) >= price:
                                # Trừ tiền mua
                                st.session_state.data[current_user_id]['kpi'] -= price
                                # Cộng tiền bán (90%)
                                seller_id = info['seller_id']
                                if seller_id in st.session_state.data:
                                    st.session_state.data[seller_id]['kpi'] += (price * 0.9)
                                # Chuyển đồ
                                st.session_state.data[current_user_id].setdefault('inventory', []).append(item_name)
                                del market_data['listings'][item_id]
                                
                                save_market(market_data)
                                save_data_func(st.session_state.data)
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Không đủ KPI!")

    # --- TAB 2: TREO BÁN (Code cũ, đã ổn định) ---
    with tab2:
        st.markdown("### 🎒 Kho đồ & Niêm yết")
        inventory = user_data.get('inventory', [])
        
        if not inventory:
            st.info("Kho đồ trống.")
        else:
            from collections import Counter
            counts = Counter(inventory)
            
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.write("**Vật phẩm đang có:**")
                for item, count in counts.items():
                    # 1. Lấy link ảnh thật từ map
                    img_url = item_image_map.get(item)
                    
                    # 2. Tạo HTML hiển thị icon/ảnh
                    if img_url:
                        # Nếu có ảnh thật -> Dùng thẻ <img> nhỏ gọn
                        icon_display = f'<img src="{img_url}" style="width:30px; height:30px; object-fit:contain; vertical-align:middle; margin-right:10px; border-radius:4px;">'
                    else:
                        # Nếu không có -> Dùng icon fallback (thu nhỏ kích thước)
                        fallback = get_fallback_icon(item)
                        # Sửa lại font-size cho nhỏ phù hợp với dòng danh sách
                        icon_display = f'<span style="font-size: 24px; vertical-align:middle; margin-right:10px;">{fallback}</span>'
                    
                    # 3. Hiển thị dòng thông tin vật phẩm
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #45475a; display: flex; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center;">
                            {icon_display}
                            <b style="color: #e0e0e0; font-size: 15px;">{item}</b>
                        </div>
                        <span style="background: #313244; color: #a6adc8; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: bold;">x{count}</span>
                    </div>
                    """, unsafe_allow_html=True)
                # -----------------------------------------------------
            
            with c2:
                with st.container(border=True):
                    st.write("**Treo bán mới:**")
                    item_to_sell = st.selectbox("Chọn đồ:", list(counts.keys()), key="mk_sel")
                    price = st.number_input("Giá (KPI):", 1.0, 1000.0, step=0.5, key="mk_pr")
                    
                    st.caption(f"Nhận về: {price*0.9:.1f} KPI (Phí 10%)")
                    
                    if st.button("🚀 Đăng bán", use_container_width=True, type="primary"):
                        new_id = str(uuid.uuid4())[:8]
                        market_data['listings'][new_id] = {
                            "item_name": item_to_sell,
                            "price": price,
                            "seller_id": current_user_id,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state.data[current_user_id]['inventory'].remove(item_to_sell)
                        save_market(market_data)
                        save_data_func(st.session_state.data)
                        st.toast("Đã đăng bán!", icon="✅")
                        st.rerun()

def generate_username(text):
    if not isinstance(text, str):
        return "user"
    
    # 1. Chuyển về chữ thường
    text = text.lower().strip()
    
    # 2. Xử lý THỦ CÔNG chữ 'đ' ngay lập tức để chặn lỗi 'aa'
    text = text.replace('đ', 'd')
    
    # 3. Khử dấu tiếng Việt chuẩn NFKD
    text = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    
    # 4. Loại bỏ mọi ký tự lạ, chỉ giữ chữ a-z và số
    text = re.sub(r'[^a-z0-9]', '', text)
    
    return text
    
def hien_thi_pho_ban(user_id, save_data_func):
    user_info = st.session_state.data[user_id]
    
    # --- PHẦN 1: NẾU ĐANG TRONG TRẬN ĐẤU ---
    if st.session_state.get("dang_danh_dungeon"):
        land_id = st.session_state.get('selected_land')
        p_id = st.session_state.get('selected_phase_id')
        
        # CHỈ HIỂN THỊ DUY NHẤT TRẬN ĐẤU
        trien_khai_combat_pho_ban(user_id, land_id, p_id, dungeon_config, save_data_func)
        
        # Nút thoát khẩn cấp ở sidebar
        if st.sidebar.button("🚩 RÚT LUI"):
            st.session_state.dang_danh_dungeon = False
            st.rerun()
        return # Dừng hàm tại đây để không hiện phần dưới

    # 2. GIAO DIỆN CHỌN VÙNG ĐẤT (Chỉ hiện khi chưa vào trận)
    st.title("🏹 PHIÊU LƯU PHÓ BẢN")
    
    # Hiển thị chỉ số nhanh
    atk = tinh_atk_tong_hop(user_info)
    col1, col2, col3 = st.columns(3)
    col1.metric("Cấp độ", f"Lv.{user_info.get('level', 1)}")
    col2.metric("Sức mạnh (ATK)", atk)
    # Sử dụng hp_max đồng bộ như đã fix trước đó
    col3.metric("Máu (HP)", f"{user_info.get('hp', 100)}/{user_info.get('hp_max', 100)}")

    st.write("---")
    st.subheader("🗺️ Chọn Vùng Đất Thử Thách")
    
    vung_dat = [
        {"id": "toan", "name": "Rừng Toán Học", "icon": "📐", "color": "#2ecc71"},
        {"id": "anh", "name": "Hang Động Ngôn Ngữ", "icon": "🇬🇧", "color": "#3498db"},
        {"id": "van", "name": "Thung Lũng Văn Chương", "icon": "📖", "color": "#e67e22"},
        {"id": "ly", "id_file": "ly", "name": "Ngọn Núi Vật Lý", "icon": "⚡", "color": "#9b59b6"},
        {"id": "hoa", "name": "Hồ Nước Hóa Học", "icon": "🧪", "color": "#1abc9c"},
        {"id": "sinh", "name": "Vườn Sinh Học", "icon": "🌿", "color": "#27ae60"}
    ]

    cols = st.columns(3)
    for i, region in enumerate(vung_dat):
        with cols[i % 3]:
            st.markdown(f"""
                <div style="background:{region['color']}; padding:15px; border-radius:10px; text-align:center; color:white;">
                    <h1 style='margin:0;'>{region['icon']}</h1>
                    <b>{region['name']}</b>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Vào {region['name']}", key=f"btn_{region['id']}"):
                # Thiết lập trạng thái vùng đất để chuẩn bị vào Combat
                st.session_state.selected_land_id = region['id']
                # Mặc định chọn Phase hiện tại mà học sinh đã đạt tới (hoặc Phase 1)
                prog = user_info.get('dungeon_progress', {}).get(region['id'], 1)
                st.session_state.selected_phase_id = f"phase_{prog}"
                
                # Cần lưu lại dungeon_config để hàm combat sử dụng
                # Ở đây bạn hãy gọi biến chứa dữ liệu config của phó bản
                # st.session_state.dungeon_config_data = DUNGEON_DATA_GLOBAL 
                
                # Kích hoạt trạng thái chuyển trang bằng cách thiết lập câu hỏi (giả lập để khởi động combat)
                # Hoặc đơn giản là st.rerun() để hàm chạy lại và rơi vào khối if số 1
                st.rerun()

def hien_thi_sanh_pho_ban_hoc_si(user_id):
    # Bạn cần kiểm tra xem tên trang có phải là trang phó bản không
    current_page = st.session_state.get("page", "")
    
    # Nếu KHÔNG PHẢI trang phó bản mà vẫn đang bật trạng thái đánh -> TẮT NGAY
    if "Phó bản" not in current_page and st.session_state.get("dang_danh_dungeon"):
        st.session_state.dang_danh_dungeon = False
        st.rerun()
        return
        
    from admin_module import load_dungeon_config
    d_config = load_dungeon_config()
    # --- BƯỚC 1: KIỂM TRA TRẠNG THÁI CHIẾN ĐẤU 
    if st.session_state.get("dang_danh_dungeon"):
        land_id = st.session_state.get('selected_land')
        p_id = st.session_state.get('selected_phase_id')
        from admin_module import load_dungeon_config
        d_config = load_dungeon_config()
        
        # Gọi hàm combat
        trien_khai_combat_pho_ban(user_id, land_id, p_id, d_config, save_data)
        
        # Ngắt hàm tại đây để tránh hiện chồng chéo sảnh chờ bên dưới
        return

    # --- BƯỚC 2: GIAO DIỆN SẢNH CHỜ (CHỈ HIỆN KHI CHƯA ĐÁNH) ---
    user_info = st.session_state.data.get(user_id)
    
    # Khởi tạo tiến độ nếu chưa có 
    if 'dungeon_progress' not in user_info:
        user_info['dungeon_progress'] = {"toan": 1, "van": 1, "anh": 1, "ly": 1, "hoa": 1, "sinh": 1}
    
    if 'viewing_land_id' not in st.session_state:
        st.session_state.viewing_land_id = "toan"

    from admin_module import load_dungeon_config
    d_config = load_dungeon_config()
    
    # --- HEADER SẢNH CHỜ ---
    st.markdown("""
        <div style="background: #2c3e50; padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #f1c40f;">🗺️ TRUNG TÂM THÁM HIỂM</h1>
            <p style="margin: 0; opacity: 0.8;">Hãy chọn vùng đất thử thách để bắt đầu hành trình!</p>
        </div>
    """, unsafe_allow_html=True)
    
    maps_data = [
        ("toan", "📐 Rừng Toán Học"), ("van", "📖 Thung Lũng Văn"), ("anh", "🇬🇧 Hang Động Anh"),
        ("ly", "⚡ Ngọn Núi Vật Lý"), ("hoa", "🧪 Hồ Nước Hóa Học"), ("sinh", "🌿 Vườn Sinh Học")
    ]
    
    # Grid chọn vùng đất
    row1 = st.columns(3)
    row2 = st.columns(3)
    for idx, (lid, lname) in enumerate(maps_data):
        col = row1[idx] if idx < 3 else row2[idx - 3]
        is_active = (st.session_state.viewing_land_id == lid)
        if col.button(lname, key=f"btn_map_{lid}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.viewing_land_id = lid
            st.rerun()

    land_id = st.session_state.viewing_land_id
    full_names = {m[0]: m[1] for m in maps_data}
    selected_name = full_names.get(land_id, "Vùng đất bí ẩn")

    # Kiểm tra tiến trình
    current_phase_num = user_info['dungeon_progress'].get(land_id, 1)
    if current_phase_num > 4:
        st.success(f"🏆 Bạn đã phá đảo {selected_name}!")
        if st.button("🔄 Thách thức lại Phase 4 (BOSS)"): current_phase_num = 4
        else: return

    p_id = f"phase_{current_phase_num}"
    if land_id not in d_config or p_id not in d_config[land_id]["phases"]:
        st.error("Dữ liệu phó bản đang được cập nhật.")
        return

    p_data = d_config[land_id]["phases"][p_id]
    st.divider()

    # Hiển thị Chi tiết Phase (ẢNH VÀ THÔNG TIN)
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.markdown(f"""
            <div style="border: 4px solid #2c3e50; border-radius: 15px; overflow: hidden; background: white; text-align: center; padding-top: 10px;">
                <img src="{p_data['monster_img']}" style="width: 60%; display: block; margin: 0 auto;">
                <div style="background: #2c3e50; color: white; text-align: center; padding: 8px; margin-top: 10px;">
                    <b>👾 {p_data['monster_name']}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
            <div style="background: #fdfefe; padding: 20px; border-radius: 15px; border-left: 8px solid #e74c3c; box-shadow: 2px 2px 8px rgba(0,0,0,0.05);">
                <h3 style="margin:0; color: #c0392b;">🚩 PHASE {current_phase_num}: {p_data['title']}</h3>
                <div style="margin-top: 15px;">
                    <p>⚔️ <b>Độ khó:</b> {p_data['quiz_level'].upper()}</p>
                    <p>⏳ <b>Thời gian:</b> {p_data['time_limit']} giây/câu</p>
                    <p>📝 <b>Nhiệm vụ:</b> Trả lời đúng {p_data['num_questions']} câu</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        st.markdown("##### 🎁 PHẦN THƯỞNG:")
        rew_c1, rew_c2, rew_c3 = st.columns(3)
        rew_c1.metric("KPI", f"+{p_data['reward_kpi']}")
        rew_c2.metric("EXP", f"+{p_data['reward_exp']}")
        rew_c3.markdown(f"📦 **{p_data['item_drop_id']}**")

    # NÚT BẮT ĐẦU 
    st.write("")
    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        target_phase_id = f"phase_{current_phase_num}"
        if st.button(f"⚔️ TIẾN VÀO {selected_name.upper()}", use_container_width=True, type="primary"):
            # Dọn dẹp session_state trước khi vào trận 
            for k in list(st.session_state.keys()):
                if k in ["dungeon_questions", "current_q_idx", "correct_count", "victory_processed"] or k.startswith("start_time_"):
                    del st.session_state[k]
            
            st.session_state.dang_danh_dungeon = True
            st.session_state.selected_land = land_id 
            st.session_state.selected_phase_id = target_phase_id
            st.rerun()

def xử_lý_hoàn_thành_phase(user_id, land_id, phase_id, dungeon_config, save_data_func, duration=None):
    user_info = st.session_state.data[user_id]
    p_data = dungeon_config[land_id]["phases"][phase_id]
    
    # 0. Đảm bảo dữ liệu tồn tại và lưu chỉ số cũ để so sánh
    for field in ['exp', 'level', 'kpi', 'inventory', 'hp']:
        if field not in user_info:
            user_info[field] = 0 if field != 'inventory' else []
    
    old_lv = user_info.get('level', 1)
    old_atk = tinh_atk_tong_hop(user_info)
    # Thống nhất dùng hp_max
    old_hp_max = 100 + (old_lv * 20) 
    user_info['hp_max'] = old_hp_max # Cập nhật lại vào data 
    
    # Khởi tạo cấu trúc lưu kỷ lục thời gian nếu chưa có
    if 'best_time' not in user_info:
        user_info['best_time'] = {}

    # Logic so sánh và lưu kỷ lục thời gian nhanh nhất
    if duration is not None:
        # Lấy kỷ lục cũ, nếu chưa có mặc định là 999 giây
        old_record = user_info['best_time'].get(land_id, 999)
        
        if duration < old_record:
            user_info['best_time'][land_id] = duration
            st.toast(f"🔥 KỶ LỤC MỚI: {duration}s!", icon="🏆")
        else:
            st.write(f"⏱️ Thời gian hoàn thành: {duration}s (Kỷ lục hiện tại: {old_record}s)")
    
    # 1. Trao thưởng từ Phase
    user_info['kpi'] += p_data.get('reward_kpi', 0)
    user_info['exp'] += p_data.get('reward_exp', 0)
    
    # 2. Tính toán Level mới
    new_lv = 1 + (user_info['exp'] // 100)
    user_info['level'] = new_lv
    
    # Tính toán chỉ số mới sau khi cộng EXP/Level
    new_atk = tinh_atk_tong_hop(user_info)
    new_hp_max = 100 + (new_lv * 20)
    user_info['hp'] = new_hp_max 

    # 3. Xử lý Rơi đồ (Loot System)
    loot_msg = "Không có"
    item_id = p_data.get('item_drop_id', "none")
    if item_id not in ["none", "Không rơi đồ"]:
        if random.randint(1, 100) <= p_data.get('drop_rate', 0):
            user_info['inventory'].append(item_id)
            loot_msg = f"📦 {item_id}"

    # 4. Hiển thị thông báo kết quả Phase
    st.write("---")
    st.subheader("🎁 PHẦN THƯỞNG CHIẾN THẮNG")
    c1, c2, c3 = st.columns(3)
    c1.metric("KPI Nhận", f"+{p_data.get('reward_kpi', 0)}")
    c2.metric("EXP Nhận", f"+{p_data.get('reward_exp', 0)}")
    c3.metric("Vật phẩm", loot_msg)

    # 5. HIỆU ỨNG LEVEL UP (Nếu có lên cấp)
    if new_lv > old_lv:
        st.balloons()
        st.toast(f"🎊 LEVEL UP! Bạn đã đạt Cấp {new_lv}", icon="🆙")
        
        # Tạo bảng Pop-up thông báo tăng trưởng chỉ số
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f1c40f, #f39c12); padding: 20px; border-radius: 15px; border: 3px solid #ffffff; color: white; text-align: center; box-shadow: 0px 4px 15px rgba(0,0,0,0.3);">
            <h2 style="margin: 0; font-size: 24px;">🎊 ĐỘT PHÁ CẤP ĐỘ 🎊</h2>
            <p style="font-size: 18px; font-weight: bold;">Cấp {old_lv} ➔ Cấp {new_lv}</p>
            <hr style="border: 0.5px solid rgba(255,255,255,0.3);">
            <div style="display: flex; justify-content: space-around;">
                <div>
                    <p style="margin: 0; font-size: 14px;">❤️ SINH MỆNH (HP)</p>
                    <p style="font-size: 20px; font-weight: bold;">{old_hp_max} ➔ {new_hp_max}</p>
                </div>
                <div>
                    <p style="margin: 0; font-size: 14px;">⚔️ CHIẾN LỰC (ATK)</p>
                    <p style="font-size: 20px; font-weight: bold;">{old_atk} ➔ {new_atk}</p>
                </div>
            </div>
            <p style="margin-top: 15px; font-style: italic; font-size: 13px;">💪 Sức mạnh của bạn đã tăng lên một tầm cao mới!</p>
        </div>
        """, unsafe_allow_html=True)

    # 6. Cập nhật tiến trình vào file (SỬA LẠI ĐỂ TRÁNH NHẢY PHASE)
    current_p_num = int(phase_id.split("_")[1]) # Ví dụ: "phase_1" -> 1
    
    # Lấy tiến trình hiện tại từ dữ liệu, mặc định là 1 nếu chưa có
    if 'dungeon_progress' not in user_info:
        user_info['dungeon_progress'] = {}
    
    actual_progress = user_info['dungeon_progress'].get(land_id, 1)

    # CHỈ CẬP NHẬT NẾU: Số phase vừa xong đúng bằng tiến trình hiện tại
    # Điều này ngăn chặn việc hàm bị gọi 2 lần gây nhảy phase
    if current_p_num == actual_progress:
        if current_p_num < 4:
            user_info['dungeon_progress'][land_id] = current_p_num + 1
            

def tinh_atk_tong_hop(user_info):
    """
    ATK = (Level * 5) + (Tổng điểm các bài kiểm tra)
    """
    level = user_info.get('level', 1)
    # Tổng điểm các bài kiểm tra
    diem_kt = (
        user_info.get('KTTX', 0) + 
        user_info.get('KT Sản phẩm', 0) + 
        user_info.get('KT Giữa kỳ', 0) + 
        user_info.get('KT Cuối kỳ', 0)
    )
    atk_tong = (level * 5) + diem_kt
    return atk_tong

def check_up_level(user_id):
    """
    Công thức: Level tiếp theo cần (Level hiện tại * 100) EXP.
    Tự động tăng chỉ số HP và ATK khi lên cấp.
    """
    if user_id not in st.session_state.data:
        return

    user = st.session_state.data[user_id]
    current_lvl = user.get('level', 1)
    current_exp = user.get('exp', 0)
    
    # Tính EXP cần thiết để lên cấp tiếp theo
    exp_required = current_lvl * 100
    
    if current_exp >= exp_required:
        # 1. Nâng cấp độ và trừ EXP
        user['level'] += 1
        user['exp'] = round(current_exp - exp_required, 2)
        
        # 2. Cập nhật chỉ số Máu (HP) - Đổi max_hp thành hp_max cho khớp hàm Save Sheets
        # Công thức của bạn: Máu tăng theo KPI và Level
        current_kpi = user.get('kpi', 0.0)
        user['hp_max'] = int(current_kpi + (user['level'] * 20))
        user['hp'] = user['hp_max'] # Hồi đầy máu khi lên cấp [cite: 17]
        
        # 3. Cập nhật chỉ số Tấn công (ATK) vĩnh viễn
        # Giả sử mỗi cấp tăng thêm 5 ATK cơ bản
        if 'bonus_stats' not in user:
            user['bonus_stats'] = {"hp": 0, "atk": 0}
        user['bonus_stats']['atk'] = user['bonus_stats'].get('atk', 0) + 5
        
        # Thông báo hiệu ứng
        st.toast(f"🎊 CHÚC MỪNG! Bạn đã đạt LEVEL {user['level']}!", icon="🔥")
        
        # 4. Đệ quy để kiểm tra nếu đủ EXP lên nhiều cấp liên tục
        check_up_level(user_id)
        
def tinh_chi_so_chien_dau(level):
    """
    Tính toán HP và ATK dựa trên Level. 
    Công thức này độc lập hoàn toàn với KPI.
    """
    hp_toi_da = 100 + (level * 20)
    atk_co_ban = 10 + (level * 2)
    return hp_toi_da, atk_co_ban

# Cách sử dụng trong giao diện:
# level_hien_tai = player.get("level", 1)
# max_hp, current_atk = tinh_chi_so_chien_dau(level_hien_tai)

# Đường dẫn file chung cho toàn bộ hệ thống (Đặt cố định để không bị lệch)
DATA_FILE_PATH = "data.json"


# Trong user_module.py
def save_data(data):
    """Hàm thực hiện lưu dữ liệu vào JSON và đẩy lên Google Sheets"""
    try:
        # 1. Lưu Local
        with open("data.json", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # 2. Lưu Cloud (Gọi hàm đã có sẵn trong file này)
        save_all_to_sheets(data)
        
        return True
    except Exception as e:
        print(f"Lỗi tại user_module.save_data: {e}")
        return False
        
def load_data(file_path=DATA_FILE_PATH):
    try: # Thêm try bao quát toàn bộ logic để bắt lỗi nếu có
        # --- 1. LẤY DỮ LIỆU TỪ CLOUD HOẶC LOCAL ---
        cloud_data = load_data_from_sheets()
        
        if cloud_data:
            data = cloud_data
            # Cập nhật local backup
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cloud_data, f, indent=4, ensure_ascii=False)
            except: 
                pass
        else:
            # Nếu Cloud lỗi, đọc từ Local
            if not os.path.exists(file_path):
                return {"admin": {"name": "Administrator", "password": "admin", "role": "admin", "level": 99}}
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                return {"admin": {"name": "Administrator", "password": "admin", "role": "admin", "level": 99}}

        # --- 2. [QUAN TRỌNG] CHUẨN HÓA DỮ LIỆU THÀNH DICT VỚI KEY SẠCH ---
        if isinstance(data, (list, dict)):
            new_dict = {}
            source_items = data.values() if isinstance(data, dict) else data
            
            for item in source_items:
                if isinstance(item, dict):
                    # Tìm key định danh
                    key = item.get('user_id') or item.get('u_id') or item.get('username') or item.get('name')
                    
                    if item.get('role') == 'admin':
                        key = 'admin'
                    
                    if not key:
                        continue
                    
                    # Làm sạch key: viết thường, xóa khoảng trắng
                    str_key = str(key).strip().lower().replace(" ", "")
                    new_dict[str_key] = item
            
            data = new_dict

        # Kiểm tra cuối cùng
        if not isinstance(data, dict) or "admin" not in data:
            if not isinstance(data, dict): data = {}
            data["admin"] = {"name": "Administrator", "password": "admin", "role": "admin", "level": 99}

        return data

    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng tại load_data: {e}")
        return {"admin": {"name": "Administrator", "password": "admin", "role": "admin", "level": 99}}

import random

def tinh_va_tra_thuong_global(killer_id, boss_data, all_users):
    """
    Hàm này chạy 1 lần duy nhất khi Boss chết.
    Cập nhật: Tích hợp thưởng EXP theo tỷ lệ từ Admin.
    """
    boss = boss_data['active_boss']
    contributions = boss.get("contributions", {})
    
    if not contributions:
        return [], 0

    # 1. Tìm MVP (Người gây sát thương cao nhất)
    mvp_id = max(contributions, key=contributions.get) 
    
    killer_rewards_display = [] 
    killer_total_dmg = 0

    # 2. Vòng lặp phát lương cho từng người tham gia
    for uid, damage in contributions.items():
        if uid not in all_users:
            continue
            
        player = all_users[uid]
        player_rewards = [] 

        # --- A. THƯỞNG CƠ BẢN (KPI & EXP) ---
        # Lấy rate từ cấu hình Boss (mặc định kpi_rate=1.0, exp_rate=5.0 nếu thiếu)
        k_rate = boss.get('kpi_rate', 1.0)
        e_rate = boss.get('exp_rate', 5.0)

        # Tính KPI (làm tròn 2 chữ số)
        kpi_base = round((damage / 1000) * k_rate, 2)
        if kpi_base < 0.1: kpi_base = 0.1
        
        # Tính EXP (mới thêm)
        exp_base = round((damage / 1000) * e_rate, 2)
        if exp_base < 0.5: exp_base = 0.5 # An ủi tối thiểu cho EXP

        # Cộng vào data
        player['kpi'] = round(player.get('kpi', 0) + kpi_base, 2)
        player['exp'] = round(player.get('exp', 0) + exp_base, 2)
        
        player_rewards.append(f"💰 +{kpi_base} KPI")
        player_rewards.append(f"✨ +{exp_base} EXP")

        
        
        # --- B. THƯỞNG RƠI ĐỒ (DROP CHANCE) ---
        drop_table = boss.get('drop_table', [])
        if drop_table:
            weights = [item['rate'] for item in drop_table]
            chosen = random.choices(drop_table, weights=weights, k=1)[0]
            
            if chosen['type'] != 'none':
                if chosen['type'] == 'currency':
                    target_key = chosen.get('id', 'Tri_Thuc')
                    player[target_key] = player.get(target_key, 0) + chosen['amount']
                    player_rewards.append(f"📘 +{chosen['amount']} {target_key}")
                    
                elif chosen['type'] == 'item':
                    if 'inventory' not in player: player['inventory'] = {}
                    item_id = chosen['id']
                    player['inventory'][item_id] = player['inventory'].get(item_id, 0) + chosen['amount']
                    player_rewards.append(f"📦 {item_id} (x{chosen['amount']})")

        # --- C. THƯỞNG ĐẶC BIỆT (MVP & LAST HIT) ---
        # Thưởng thêm cho MVP
        if uid == mvp_id:
            bonus_mvp_kpi = 50.0 
            bonus_mvp_exp = 100.0 # Thưởng thêm EXP cho người giỏi nhất
            player['kpi'] += bonus_mvp_kpi
            player['exp'] += bonus_mvp_exp
            player_rewards.append(f"👑 MVP: +{bonus_mvp_kpi} KPI & +{bonus_mvp_exp} EXP")
            
        # Thưởng thêm cho người kết liễu
        if uid == killer_id:
            bonus_kill_kpi = 20.0
            player['kpi'] += bonus_kill_kpi
            player_rewards.append(f"🗡️ Kết liễu: +{bonus_kill_kpi} KPI")

        # --- D. KIỂM TRA LÊN CẤP (LEVEL UP) ---
        # Gọi hàm check level up tại đây nếu bạn đã có
        # check_level_up(uid, all_users)
        check_up_level(uid)
        # Lưu log hiển thị cho người đang thực hiện cú đánh cuối (Killer)
        if uid == killer_id:
            killer_rewards_display = player_rewards
            killer_total_dmg = damage
    with open('data/boss_config.json', 'w', encoding='utf-8') as f:
        json.dump({"active_boss": None}, f, indent=4, ensure_ascii=False)        
    save_all_to_sheets(st.session_state.data)
    
    # 1. Xóa trạng thái Boss đang hoạt động (vì Boss đã chết)
    try:
        with open('data/boss_config.json', 'w', encoding='utf-8') as f:
            json.dump({"active_boss": None}, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi reset Boss Local: {e}")

    # 2. Gọi hàm lưu tổng lực để đẩy KPI/EXP mới của học sinh và trạng thái Boss lên Google Sheets
    # Giả sử all_users là bộ dữ liệu tổng của bạn
    save_all_to_sheets(all_users)
    
    return killer_rewards_display, killer_total_dmg
    
@st.dialog("🎁 KHO BÁU CHIẾN THẮNG")
def hien_thi_ruong_bau(user_id, total_dmg, rewards_from_boss):
    # --- GIAO DIỆN CHÚC MỪNG ---
    st.markdown("""
        <div style="text-align: center;">
            <img src="https://i.ibb.co/6N788P8/chest-gold.gif" width="200">
            <h2 style="color: #f1c40f; text-shadow: 2px 2px 4px #000;">CHÚC MỪNG CHIẾN BINH!</h2>
            <p style="font-size: 1.2em;">Bạn đã xuất sắc góp <b>{total_dmg} sát thương</b> vào chiến thắng!</p>
        </div>
    """.format(total_dmg=total_dmg), unsafe_allow_html=True)
    
    st.divider()
    st.write("### 💎 Vật phẩm nhận được:")

    # --- LOGIC TRUY XUẤT HÌNH ẢNH TỪ KHO ---
    kho_item_dict = {}
    if os.path.exists('data/item_inventory.json'):
        with open('data/item_inventory.json', 'r', encoding='utf-8') as f:
            # Chuyển list thành dict để tìm kiếm nhanh theo ID (Tên vật phẩm)
            kho_data = json.load(f)
            kho_item_dict = {item['id']: item for item in kho_data}

    # --- HIỂN THỊ DANH SÁCH QUÀ ---
    for r in rewards_from_boss:
        item_name = r['id']
        amount = r['amount']
        
        # Kiểm tra xem đây là tiền tệ có icon sẵn hay vật phẩm trong kho
        item_info = kho_item_dict.get(item_name)
        
        # Xác định Link ảnh: Ưu tiên ảnh từ kho, nếu không thấy thì dùng icon mặc định
        if item_info:
            icon_url = item_info['image']
            label_color = "#f1c40f" # Màu vàng cho vật phẩm
        else:
            # Nếu là tiền tệ (có icon 🔵, 📚...), dùng icon mặc định hoặc link ảnh chung
            icon_url = "https://cdn-icons-png.flaticon.com/512/272/272525.png"
            label_color = "#00d2ff" if "KPI" in item_name else "#bdc3c7"

        # Giao diện từng dòng vật phẩm
        st.markdown(f"""
            <div style="display: flex; align-items: center; background: rgba(255,255,255,0.1); 
                        padding: 10px; border-radius: 15px; margin-bottom: 10px; border-left: 5px solid {label_color};">
                <img src="{icon_url}" width="50" style="margin-right: 15px; border-radius: 8px;">
                <div>
                    <b style="font-size: 1.1em; color: white;">{item_name}</b><br>
                    <span style="color: #bdc3c7;">Số lượng: x{amount}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # --- NÚT XÁC NHẬN ---
    if st.button("🧧 XÁC NHẬN NHẬN QUÀ & RỜI KHỎI", use_container_width=True):
        # Lưu ý: Ở đây bạn cần thêm logic gọi hàm cộng tiền/đồ vào users.json trước khi rerun
        st.rerun()

def xu_ly_mo_ruong(user_id, item_id, item_data, all_users, save_data_func):
    """
    Hàm xử lý logic mở rương theo tỷ lệ rơi độc lập:
    Duyệt qua từng món trong Loot Table -> Tung xúc xắc -> Cộng tất cả món trúng.
    """
    player = all_users[user_id]
    
    # 1. Trừ 1 rương trong kho
    if item_id in player.get('inventory', {}):
        player['inventory'][item_id] -= 1
        if player['inventory'][item_id] <= 0:
            del player['inventory'][item_id]
    
    # 2. Lấy danh sách phần thưởng (Loot Table)
    props = item_data.get('properties', {})
    loot_table = props.get('loot_table', [])
    
    rewards_received = [] # Chứa các tin nhắn thông báo
    items_to_display = [] # Chứa data để hiển thị icon (nếu cần dùng cho hàm hien_thi_ruong_bau)

    if not loot_table:
        return []

    # 3. THUẬT TOÁN DROP ĐỘC LẬP (Independent Drop Rate)
    for gift in loot_table:
        rate = float(gift.get('rate', 0))
        # Tung xúc xắc ngẫu nhiên từ 0.0 đến 100.0
        roll = random.uniform(0, 100)
        
        # Nếu trúng tỷ lệ
        if roll <= rate:
            gift_type = gift.get('type')
            target_id = gift.get('id')
            amount = gift.get('amount', 1)

            if gift_type == 'currency':
                # Cộng tiền/tài nguyên
                player[target_id] = player.get(target_id, 0) + amount
                name_map = {"kpi": "KPI", "Tri_Thuc": "Tri Thức", "Chien_Tich": "Chiến Tích"}
                display_name = name_map.get(target_id, target_id)
                rewards_received.append({"type": "currency", "msg": f"💰 +{amount} {display_name}"})
                
            elif gift_type == 'item':
                # Cộng vật phẩm vào kho
                if 'inventory' not in player: player['inventory'] = {}
                player['inventory'][target_id] = player['inventory'].get(target_id, 0) + amount
                rewards_received.append({"type": "item", "msg": f"📦 Nhận: {target_id} (x{amount})"})

    # 4. Lưu dữ liệu ngay lập tức
    save_data_func(all_users)
    
    # Nếu vòng lặp xong mà không trúng món nào
    if not rewards_received:
        rewards_received.append({"type": "miss", "msg": "💨 Rương trống rỗng... Chúc may mắn lần sau!"})
    
    return rewards_received

import streamlit as st
from datetime import datetime, timedelta
# Các hàm load_data, tinh_chi_so_chien_dau, trien_khai_tran_dau... giả định đã import từ module khác

def hien_thi_san_dau_boss(user_id, save_data_func):
    st.title("⚔️ Đại chiến Giáo viên")
    
    # 1. Tải dữ liệu
    # Ưu tiên lấy từ session_state để đồng bộ nhất
    boss_data = load_data('data/boss_config.json')
    all_users = st.session_state.data if 'data' in st.session_state else load_data('data/users.json')
    
    # Kiểm tra dữ liệu Boss
    if not boss_data or boss_data.get("active_boss") is None:
        st.info("☘️ Hiện tại không có Giáo viên nào thách thức. Hãy tập luyện thêm!")
        return

    boss = boss_data["active_boss"]
    player = all_users.get(user_id)

    if not player:
        st.error("Không tìm thấy dữ liệu học sĩ.")
        return

    # 2. Tính toán chỉ số cơ bản
    level = player.get("level", 1)
    base_max_hp, base_atk = tinh_chi_so_chien_dau(level)

    # --- CHÈN LOGIC QUÉT BUFF ---
    # Hàm này trả về bonus stats từ trang bị/thuốc
    bonus_stats, updated_data = get_active_combat_stats(user_id, st.session_state.data)
    st.session_state.data = updated_data 

    # Chỉ số thực tế (Base + Buff)
    max_hp_p = base_max_hp + bonus_stats['hp']
    atk_p = base_atk + bonus_stats['atk']
    current_hp_p = player.get("hp", max_hp_p) 
    # ------------------------------------
    # ================================================================
    # 🔥 THÊM ĐOẠN NÀY: CẮT MÁU THỪA KHI HẾT THUỐC 🔥
    # Nếu buff vừa hết hạn làm Max HP tụt xuống, mà máu hiện tại đang cao hơn
    # Thì phải cắt máu hiện tại xuống bằng Max HP ngay.
    if current_hp_p > max_hp_p:
        current_hp_p = max_hp_p             # Cắt ngọn
        player['hp'] = max_hp_p             # Lưu vào biến tạm
        st.session_state.data[user_id]['hp'] = max_hp_p # Lưu vào session
        save_data_func(st.session_state.data) # Lưu xuống file ngay lập tức
    # ================================================================
    # 3. Kiểm tra trạng thái Trọng thương (Cooldown khi thua)
    if player.get("reborn_at"):
        try:
            reborn_time = datetime.strptime(player["reborn_at"], "%Y-%m-%d %H:%M:%S")
            # Chỉ hiện màn hình trọng thương nếu thời gian hiện tại vẫn chưa tới lúc hồi sinh
            if datetime.now() < reborn_time:
                time_left = reborn_time - datetime.now()
                phut_con_lai = int(time_left.total_seconds() // 60) + 1
                
                defeat_info = player.get('last_defeat', {"boss_name": "Giáo Viên", "damage_taken": "hiểm hóc"})                
                # Giao diện màn hình chờ hồi sinh
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #2c3e50, #000000); padding: 20px; border-radius: 15px; border: 1px solid #ff4b4b; text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #ff4b4b;">💀 BẠN ĐANG BỊ THƯƠNG NẶNG</h2>
                        <p style="color: #ecf0f1;">Bị hạ gục bởi: <b>{defeat_info['boss_name']}</b></p>
                        <hr>
                        <h1 style="color: white; font-size: 3em;">⏳ {phut_con_lai} phút</h1>
                        <p style="color: #bdc3c7;">nghỉ ngơi để hồi phục thể lực</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Thanh tiến trình hồi phục
                # Mặc định phạt 30 phút (1800 giây) hoặc tùy config
                total_wait = 3600 
                progress_val = 1.0 - (time_left.total_seconds() / total_wait)
                # Kẹp giá trị an toàn cho thanh chờ
                safe_prog = min(1.0, max(0.0, progress_val))
                st.progress(safe_prog)
                
                if st.button("🔄 Cập nhật tình trạng", use_container_width=True):
                    st.rerun()
                return # Dừng hàm, không hiện sàn đấu
        except Exception as e:
            # Nếu lỗi định dạng ngày tháng thì bỏ qua cooldown để tránh kẹt acc
            pass

    # 4. Hiển thị Giao diện Sàn đấu
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Ảnh Boss
        st.image(boss.get("anh", "assets/teachers/default.png"), caption=f"Boss: {boss['ten']}")
        st.error(f"💀 Sức tấn công Boss: {boss['damage']}") 

    with col2:
        # --- PHẦN CỦA BOSS ---
        # Tính % máu Boss (Kẹp giá trị an toàn)
        hp_boss_pct = min(100, max(0, int((boss['hp_current'] / boss['hp_max']) * 100)))
        
        st.write(f"**🚩 HP BOSS: {boss['hp_current']} / {boss['hp_max']}**")
        st.progress(hp_boss_pct)
        
        st.markdown("---") 

        # --- PHẦN CỦA BẠN (PLAYER) ---
        # 🔥 KHẮC PHỤC LỖI STREAMLIT EXCEPTION TẠI ĐÂY 🔥
        # Dùng min(100, ...) để đảm bảo nếu máu > 100% (do buff) thì vẫn chỉ vẽ 100%
        p_hp_pct = min(100, max(0, int((current_hp_p / max_hp_p) * 100)))
        
        # Hiển thị số thực (người chơi thấy 140/120 cho sướng)
        st.write(f"**❤️ Máu của bạn: {int(current_hp_p)} / {max_hp_p}**")
        
        # Hiển thị thanh (vẽ max 100 thôi để không lỗi)
        st.progress(p_hp_pct)
        
        # Hiển thị chỉ số tấn công
        if bonus_stats['atk'] > 0:
            st.info(f"⚔️ Sức tấn công: **{atk_p}** (Gốc: {base_atk} + Buff: {bonus_stats['atk']})")
        else:
            st.info(f"⚔️ Sức tấn công: **{atk_p}**")

    # 5. ĐIỀU KHIỂN TRẬN ĐẤU (NÚT BẤM)
    # ------------------------------------------------------------------
    if not st.session_state.get("dang_danh_boss"):
        # CHƯA VÀO TRẬN -> Hiện nút Khiêu Chiến
        if st.button("⚔️ KHIÊU CHIẾN NGAY", type="primary", use_container_width=True):
            st.session_state.dang_danh_boss = True
            st.session_state.combo = 0
            st.rerun()
    else:
        # ĐANG TRONG TRẬN -> Hiện nút Rời Khỏi + Gọi hàm Combat
        
        # 🔥 NÚT RỜI KHỎI THỦ CÔNG 🔥
        if st.button("🏳️ RỜI KHỎI CHIẾN TRƯỜNG (Thoát an toàn)", use_container_width=True):
            # Tắt trạng thái đánh
            st.session_state.dang_danh_boss = False
            # Dọn dẹp biến tạm
            keys_to_clean = ["combo", "cau_hoi_active", "thoi_gian_bat_dau"]
            for k in keys_to_clean:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
            
        # Gọi hàm xử lý trận đấu
        trien_khai_tran_dau(boss, player, atk_p, save_data_func, user_id, boss_data, all_users)
        
def trien_khai_tran_dau(boss, player, current_atk, save_data_func, user_id, boss_data, all_users):
    st.divider()
    
    # --- 1. LOAD CÂU HỎI (GIỮ NGUYÊN) ---
    path_quiz = f"quiz_data/grade_6/boss/{boss['mon']}.json"
    # Fallback: Nếu không tìm thấy file môn riêng thì lấy tạm môn Toán hoặc file chung
    try:
        all_quizzes = load_data(path_quiz)
    except:
        st.error(f"Chưa có dữ liệu câu hỏi cho môn {boss['mon']}")
        return

    pool = all_quizzes.get("easy", []) + all_quizzes.get("medium", [])
    if not pool:
        st.error("Ngân hàng câu hỏi đang trống!")
        return

    # Khởi tạo câu hỏi nếu chưa có
    if "cau_hoi_active" not in st.session_state:
        st.session_state.cau_hoi_active = random.choice(pool)
        st.session_state.thoi_gian_bat_dau = time.time()

    q = st.session_state.cau_hoi_active

    # --- 2. ĐỒNG HỒ ĐẾM NGƯỢC ---
    THOI_GIAN_GIOI_HAN = 15 
    elapsed = time.time() - st.session_state.get("thoi_gian_bat_dau", time.time())
    remaining = int(THOI_GIAN_GIOI_HAN - elapsed)

    timer_placeholder = st.empty()
    
    # Xử lý hết giờ
    if remaining <= 0:
        st.error("⏰ HẾT GIỜ! Bạn đã bị Boss tấn công.")
        
        # Trừ máu người chơi
        dmg_boss = boss.get('damage', 10)
        player['hp'] = max(0, player.get('hp', 100) - dmg_boss)
        
        # Reset combo
        st.session_state.combo = 0
        
        # Kiểm tra chết
        if player['hp'] <= 0:
            xu_ly_thua_cuoc(player, boss, save_data_func) # Hàm tách riêng cho gọn (hoặc viết thẳng vào đây)
        else:
            save_data_func() # Lưu máu bị trừ
            
        del st.session_state.cau_hoi_active # Xóa câu cũ
        time.sleep(1.5)
        st.rerun()
        return

    # Hiển thị đồng hồ
    color = "red" if remaining <= 5 else "#00d2ff"
    timer_placeholder.markdown(f"<h1 style='text-align: center; color: {color}; font-size: 40px;'>⏳ {remaining}s</h1>", unsafe_allow_html=True)

    # --- 3. HIỂN THỊ CÂU HỎI & NÚT BẤM (SỬA LẠI PHẦN NÀY) ---
    st.info(f"⚡ **COMBO HIỆN TẠI: x{st.session_state.get('combo', 0)}**")
    
    # ==============================================================================
    # 🔥 CSS TÙY BIẾN CHO THÔNG BÁO (TOAST) 🔥
    # Đoạn này sẽ biến st.toast thành một thông báo lớn, nằm giữa màn hình.
    # ==============================================================================
    st.markdown("""
        <style>
        /* 1. Định vị và thay đổi kích thước khung thông báo (Toast container) */
        div[data-testid="stToast"] {
            position: fixed !important; /* Cố định vị trí để có thể di chuyển tự do */
            top: 40% !important;        /* Đặt đỉnh ở khoảng 40% chiều cao màn hình (gần giữa) */
            left: 50% !important;       /* Đặt cạnh trái ở 50% chiều ngang */
            transform: translate(-50%, -50%) !important; /* Dịch chuyển ngược lại để căn giữa hoàn toàn */
            
            width: 60% !important;      /* Chiều rộng lớn (khoảng gấp đôi mặc định) */
            max-width: 800px !important; /* Giới hạn chiều rộng tối đa để không quá bè trên màn hình lớn */
            padding: 25px 30px !important; /* Tăng đệm bên trong làm khung to hơn */
            
            background-color: #ffebee !important; /* Màu nền đỏ/hồng nhạt cảnh báo */
            border-left: 10px solid #d32f2f !important; /* Thanh viền đỏ đậm làm điểm nhấn bên trái */
            box-shadow: 0 8px 25px rgba(0,0,0,0.3) !important; /* Đổ bóng đậm để nổi bật khỏi nền */
            border-radius: 15px !important; /* Bo tròn góc mềm mại */
            z-index: 99999 !important;   /* Đảm bảo luôn đè lên mọi thứ khác */
        }

        /* 2. Căn chỉnh icon và nội dung bên trong */
        div[data-testid="stToast"] > div {
            display: flex !important;
            align-items: center !important; /* Căn giữa icon và text theo chiều dọc */
            justify-content: flex-start !important;
        }

        /* 3. Thay đổi font chữ, màu sắc của nội dung text */
        div[data-testid="stToast"] p {
            font-size: 28px !important;  /* Chữ to ĐÙNG (gấp đôi mặc định 14px) */
            font-weight: 900 !important; /* Chữ CỰC ĐẬM (Bold) */
            color: #b71c1c !important;    /* Màu chữ đỏ đậm cho cảm giác nguy hiểm */
            margin: 0 0 0 20px !important; /* Khoảng cách giữa icon và chữ */
            line-height: 1.4 !important;
            font-family: 'Arial', sans-serif !important; /* Đảm bảo font dễ đọc */
        }
        
        /* 4. Tùy chỉnh icon (cái mặt 🤕) cho to tương xứng */
        div[data-testid="stToast"] span[role="img"] {
             font-size: 40px !important; /* Icon to gấp đôi */
             height: 40px !important;
             width: 40px !important;
             line-height: 40px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.subheader(f"❓ {q['question']}")

    # Kiểm tra xem câu hỏi có options không, nếu không có (câu tự luận) thì mới hiện ô nhập
    options = q.get('options', [])
    
    if options:
        # --- TRƯỜNG HỢP TRẮC NGHIỆM (HIỆN 4 NÚT) ---
        col_ans1, col_ans2 = st.columns(2)
        
        user_choice = None
        
        for i, option in enumerate(options):
            with (col_ans1 if i % 2 == 0 else col_ans2):
                # Mỗi nút là một đáp án
                if st.button(option, key=f"btn_boss_{i}", use_container_width=True):
                    user_choice = option

        # --- XỬ LÝ KHI NGƯỜI DÙNG BẤM NÚT ---
        if user_choice:
            # A. TRẢ LỜI ĐÚNG
            if str(user_choice).strip().lower() == str(q['answer']).strip().lower():
                st.session_state.combo = st.session_state.get('combo', 0) + 1
                he_so = 1 + (st.session_state.combo - 1) * 0.1
                final_dmg = int(current_atk * he_so)
                
                # Trừ máu Boss
                boss['hp_current'] = max(0, boss['hp_current'] - final_dmg)
                
                # Ghi nhận đóng góp
                if "contributions" not in boss: boss["contributions"] = {}
                boss["contributions"][user_id] = boss["contributions"].get(user_id, 0) + final_dmg
                
                # Lưu file Boss
                try:
                    with open('data/boss_config.json', 'w', encoding='utf-8') as f:
                        json.dump(boss_data, f, indent=4, ensure_ascii=False)
                except: pass

                st.success(f"🎯 CHÍNH XÁC! Gây {final_dmg} sát thương! (Combo x{st.session_state.combo})")
                
                # Kiểm tra Boss chết
                if boss['hp_current'] <= 0:
                    xu_ly_boss_chet(user_id, boss_data, all_users, save_data_func) # Hàm xử lý thắng
                    return

            # B. TRẢ LỜI SAI
            else:
                st.session_state.combo = 0
                dmg_boss = boss.get('damage', 10)
                player['hp'] = max(0, player.get('hp', 100) - dmg_boss)
                
                st.error(f"❌ SAI RỒI! Đáp án là: {q['answer']}")
                st.toast(f"Bị Boss phản đòn {dmg_boss} sát thương!", icon="🤕")
                
                if player['hp'] <= 0:
                    xu_ly_thua_cuoc(player, boss, save_data_func) # Hàm xử lý thua
                    return # Dừng ngay
            
            # C. CHUNG CHO CẢ 2 TRƯỜNG HỢP (Lưu & Chuyển câu)
            save_data_func()
            if "cau_hoi_active" in st.session_state:
                del st.session_state.cau_hoi_active # Xóa câu hỏi cũ
            if "thoi_gian_bat_dau" in st.session_state:
                del st.session_state.thoi_gian_bat_dau # Reset giờ
                
            # [QUAN TRỌNG] Tạm dừng 1 chút để người dùng đọc thông báo rồi mới F5
            time.sleep(1.5) 
            st.rerun()

    else:
        # Fallback cho câu hỏi không có đáp án A,B,C,D (ít dùng)
        st.warning("Câu hỏi này bị lỗi dữ liệu (thiếu đáp án). Đang bỏ qua...")
        del st.session_state.cau_hoi_active
        time.sleep(1)
        st.rerun()

# --- HÀM PHỤ TRỢ (Để code gọn hơn) ---
def xu_ly_thua_cuoc(player, boss, save_data_func):
    player['hp'] = 0
    player['reborn_at'] = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    player['last_defeat'] = {"boss_name": boss['ten'], "damage_taken": boss.get('damage', 10)}
    st.session_state.dang_danh_boss = False
    
    # Xóa các biến tạm
    if "cau_hoi_active" in st.session_state: del st.session_state.cau_hoi_active
    
    save_data_func()
    st.error("💀 BẠN ĐÃ BỊ HẠ GỤC!")
    time.sleep(2)
    st.rerun()

def xu_ly_boss_chet(user_id, boss_data, all_users, save_data_func):
    boss = boss_data['active_boss']
    
    # 1. Cập nhật trạng thái Boss
    boss['hp_current'] = 0
    boss['status'] = "defeated"
    
    # 2. Tính toán và chia thưởng cho TOÀN BỘ SERVER
    # Hàm này sẽ cập nhật trực tiếp vào biến all_users
    qua_cua_toi, dmg_cua_toi = tinh_va_tra_thuong_global(user_id, boss_data, all_users)
    
    # 3. Lưu dữ liệu Boss (đã chết)
    try:
        with open('data/boss_config.json', 'w', encoding='utf-8') as f:
            json.dump(boss_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Lỗi lưu Boss: {e}")

    # 4. Lưu dữ liệu Người dùng (đã nhận thưởng)
    # Quan trọng: Phải truyền all_users đã được cập nhật thưởng vào hàm save
    save_data_func(all_users)

    # 5. Hiệu ứng chiến thắng & Hiển thị quà
    st.balloons()
    
    # Tạo một hộp thông báo đẹp mắt giữa màn hình
    st.markdown(f"""
        <div style="background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #c3e6cb; margin-top: 20px;">
            <h1 style="margin: 0;">🏆 BOSS ĐÃ BỊ TIÊU DIỆT!</h1>
            <p style="font-size: 18px;">Người kết liễu: <b>Học sĩ {user_id}</b></p>
            <hr>
            <h3 style="color: #d35400;">🎁 PHẦN THƯỞNG CỦA BẠN</h3>
            <ul style="list-style-type: none; padding: 0; font-size: 20px; font-weight: bold;">
                {''.join([f'<li style="margin: 5px 0;">{item}</li>' for item in qua_cua_toi])}
            </ul>
            <p><i>(Tổng sát thương đóng góp: {dmg_cua_toi})</i></p>
        </div>
    """, unsafe_allow_html=True)
    
    # 6. Dọn dẹp và kết thúc
    st.session_state.dang_danh_boss = False
    
    # Dừng 5 giây để người chơi kịp đọc phần thưởng rồi mới reload
    time.sleep(5) 
    st.rerun()

def lam_bai_thi_loi_dai(match_id, match_info, current_user_id, save_data_func):
    # --- 1. KHỞI TẠO TRẠNG THÁI BAN ĐẦU (Sửa lỗi AttributeError) ---
    if "match_id_active" not in st.session_state or st.session_state.get("last_match_id") != match_id:
        st.session_state.current_q = 0
        st.session_state.user_score = 0
        st.session_state.start_time = time.time() # Khởi tạo mốc thời gian
        st.session_state.last_match_id = match_id
        st.session_state.match_id_active = match_id

    # Đảm bảo start_time luôn tồn tại trước khi chạy tiếp
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()



    # --- 3. TẢI ĐỀ THI ---
    grade = match_info.get('grade', 'grade_6')
    subject = match_info.get('subject', 'toan')
    path = f"quiz_data/{grade}/{subject}.json"
    
    if not os.path.exists(path):
        st.error(f"❌ Không tìm thấy file đề thi tại: {path}")
        return

    with open(path, "r", encoding='utf-8') as f:
        all_questions = json.load(f)
    
    level = match_info.get('level', 'easy')
    questions = all_questions.get(level, [])[:5]
    
    limit_map = {"easy": 15, "medium": 20, "hard": 25, "extreme": 30}
    time_limit = limit_map.get(level, 15)

    # --- 4. GIAO DIỆN CÂU HỎI ---
    q_idx = st.session_state.current_q
    if q_idx < len(questions):
        q = questions[q_idx]
        st.subheader(f"⚔️ CÂU HỎI {q_idx + 1}/5")
        st.info(q['question'])
        
        # TÍNH THỜI GIAN (Sử dụng session_state an toàn)
        elapsed = time.time() - st.session_state.start_time
        remaining = max(0, time_limit - int(elapsed))
        
        color = "#e74c3c" if remaining < 5 else "#2ecc71"
        st.markdown(f"<h2 style='text-align: center; color: {color};'>⏳ {remaining}s</h2>", unsafe_allow_html=True)

        with st.form(key=f"quiz_form_{q_idx}_{current_user_id}"):
            ans = st.radio("Chọn đáp án đúng:", q['options'], index=None)
            submitted = st.form_submit_button("XÁC NHẬN")

        if submitted or remaining <= 0:
            if ans == q['answer']:
                st.session_state.user_score += 1
            st.session_state.current_q += 1
            st.session_state.start_time = time.time() # Reset thời gian cho câu mới
            st.rerun()
        
        # Tự động cập nhật đồng hồ mỗi giây
        time.sleep(1)
        st.rerun()
        
    else:
        # 1. Hiển thị kết quả tạm thời
        st.success(f"🎉 Bạn đã hoàn thành bài thi với {st.session_state.user_score}/5 điểm!")
        
        # 2. Đọc lại dữ liệu lôi đài mới nhất để tránh ghi đè đè lên điểm của người kia
        ld_data = load_loi_dai()
        m = ld_data['matches'][match_id]
        
        # Lưu điểm cá nhân (score_ID)
        m[f"score_{current_user_id}"] = st.session_state.user_score
                
        # 3. Xác định danh sách tất cả người phải thi để kiểm tra xem đủ chưa
        c_team = m.get('challenger_team', [])
        if not c_team: c_team = [m.get('challenger')]
        o_team = m.get('opponent_team', [])
        if not o_team: o_team = [m.get('opponent')]
        all_p = c_team + o_team
        
        # Đếm số người thực tế đã có key "score_ID" trong trận đấu
        finished_p = [uid for uid in all_p if f"score_{uid}" in m]
        
        if len(finished_p) >= len(all_p):
            # NẾU ĐÃ ĐỦ NGƯỜI: Gọi trọng tài ngay lập tức
            # Lưu ý: Phải truyền ld_data vào để trọng tài xử lý trên dữ liệu vừa cập nhật
            trong_tai_tong_ket(match_id, ld_data, save_data_func)
            st.balloons()
            st.info("🏁 Trận đấu đã kết thúc! Đang tính toán bảng điểm...")
        else:
            # NẾU CHƯA ĐỦ: Chỉ lưu điểm của mình và chờ
            save_loi_dai(ld_data)
            st.warning(f"⏳ Đã lưu điểm. Cần thêm {len(all_p) - len(finished_p)} người hoàn thành để tổng kết.")

        # Nút thoát để xóa các biến tạm trong session
        if st.button("XÁC NHẬN & QUAY LẠI", type="primary"):
            for k in ["current_q", "user_score", "start_time", "match_id_active", "last_match_id"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()


def load_loi_dai():
    if os.path.exists("loi_dai.json"):
        with open("loi_dai.json", "r", encoding='utf-8') as f:
            try:
                data = json.load(f)
                if isinstance(data, dict) and 'matches' in data:
                    
                    # --- LOGIC DỌN DẸP TỰ ĐỘNG ---
                    now = datetime.now()
                    thirty_days_ago = now - timedelta(days=30)
                    
                    old_matches = data.get('matches', {})
                    cleaned_matches = {}
                    da_xoa = 0
                    
                    for m_id, m_info in old_matches.items():
                        try:
                            # 1. Lấy chuỗi thời gian từ key 'created_at' (Ví dụ: "26/12/2025 08:21")
                            time_str = m_info.get('created_at', "")
                            
                            # 2. Chuyển đổi định dạng Ngày/Tháng/Năm (format: %d/%m/%Y)
                            # Chúng ta chỉ lấy 10 ký tự đầu để so sánh ngày cho nhẹ
                            ngay_tran_dau = datetime.strptime(time_str[:10], "%d/%m/%Y")
                            
                            # 3. Kiểm tra nếu trận đấu trong vòng 30 ngày thì giữ lại
                            if ngay_tran_dau > thirty_days_ago:
                                cleaned_matches[m_id] = m_info
                            else:
                                da_xoa += 1
                        except:
                            # Nếu có lỗi định dạng (trận cũ quá hoặc lỗi data), giữ lại để an toàn
                            cleaned_matches[m_id] = m_info
                    
                    # Cập nhật và lưu nếu có thay đổi
                    if da_xoa > 0:
                        data['matches'] = cleaned_matches
                        save_loi_dai(data)
                    # -----------------------------

                    return data
                else:
                    return {"matches": {}, "rankings": {}}
            except:
                return {"matches": {}, "rankings": {}}
    return {"matches": {}, "rankings": {}}
# Hàm phụ để lưu dữ liệu lôi đài
def save_loi_dai(data):
    with open("loi_dai.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@st.dialog("🏁 KẾT QUẢ TRẬN ĐẤU")
def hien_thi_bang_diem_chung_cuoc(match_id, ld_data):
    # Kiểm tra an toàn xem trận đấu còn tồn tại không
    if match_id not in ld_data.get('matches', {}):
        st.error("Dữ liệu trận đấu không khả dụng.")
        if st.button("ĐÓNG"): st.rerun()
        return
        
    m = ld_data['matches'][match_id]
    hinh_thuc = m.get('type', 'Giải đề trắc nghiệm')
    the_thuc = m.get('mode', '1 vs 1')
    
    st.markdown(f"### {the_thuc.upper()} - {hinh_thuc.upper()}")
    
    # Lấy danh sách thành viên
    team1 = m.get('challenger_team', [])
    if not team1: team1 = [m.get('challenger')]
    
    team2 = m.get('opponent_team', [])
    if not team2: team2 = [m.get('opponent')]
    
    col1, col2 = st.columns(2)
    
    def render_team_stats(team_list, team_label):
        st.markdown(f"**{team_label}**")
        total_score = 0
        for uid in team_list:
            if not uid: continue
            
            # Kiểm tra an toàn sự tồn tại của user
            user_info = st.session_state.data.get(uid)
            if not isinstance(user_info, dict):
                continue
                
            name = user_info.get('name', 'Học sĩ')
            
            if hinh_thuc == "Giải đề trắc nghiệm":
                score = m.get(f"score_{uid}", 0)
                st.write(f"👤 {name}: **{score} điểm**")
            else:
                # So điểm tăng trưởng
                start_dict = m.get('start_kpi_dict', {})
                kpi_hien_tai = user_info.get('kpi', 0)
                kpi_luc_dau = start_dict.get(uid, kpi_hien_tai)
                growth = kpi_hien_tai - kpi_luc_dau
                score = max(0, growth)
                st.write(f"👤 {name}: **+{score} KPI**")
            
            total_score += score
        return total_score

    with col1:
        s1 = render_team_stats(team1, "ĐỘI THÁCH ĐẤU")
        st.markdown(f"#### Tổng: {s1}")

    with col2:
        s2 = render_team_stats(team2, "ĐỘI NHẬN KÈO")
        st.markdown(f"#### Tổng: {s2}")

    st.divider()
    
    # Hiển thị thông báo thắng thua bằng màu sắc
    if s1 > s2:
        st.success(f"🏆 CHIẾN THẮNG: ĐỘI THÁCH ĐẤU")
        st.balloons()
    elif s2 > s1:
        st.success(f"🏆 CHIẾN THẮNG: ĐỘI NHẬN KÈO")
        st.balloons()
    else:
        st.warning("🤝 KẾT QUẢ: HÒA CHUNG CUỘC")

    # NÚT BẤM QUAN TRỌNG NHẤT ĐỂ TẮT POPUP
    if st.button("XÁC NHẬN ĐÃ XEM", use_container_width=True, type="primary"):
        st.session_state[f"seen_result_{match_id}"] = True
        st.rerun()

def trong_tai_tong_ket(match_id, ld_data, save_data_func):
    if match_id not in ld_data['matches']: return
    
    m = ld_data['matches'][match_id]
    bet = m.get('bet', 0)
    
    # Lấy danh sách 2 đội
    t1 = m.get('challenger_team', [])
    if not t1: t1 = [m.get('challenger')]
    t2 = m.get('opponent_team', [])
    if not t2: t2 = [m.get('opponent')]

    # Tính điểm từng đội từ score_ID
    s1 = sum(m.get(f"score_{uid}", 0) for uid in t1 if uid)
    s2 = sum(m.get(f"score_{uid}", 0) for uid in t2 if uid)

    # Phân định thắng thua
    if s1 > s2: winner = "team1"
    elif s2 > s1: winner = "team2"
    else: winner = "Hòa"

    # Cộng/Tràn KPI
    data = st.session_state.data
    if winner == "Hòa":
        for uid in t1 + t2:
            if uid in data: data[uid]['kpi'] += bet
    else:
        winners = t1 if winner == "team1" else t2
        mode = m.get('mode', '1 vs 1')
        bonus_ct = 3 if "3 vs 3" in mode else (2 if "2 vs 2" in mode else 1)
        for uid in winners:
            if uid in data:
                data[uid]['kpi'] += (bet * 2)
                data[uid]['Chien_Tich'] = data[uid].get('Chien_Tich', 0) + bonus_ct
        
    # CẬP NHẬT TRẠNG THÁI KẾT THÚC (Để không bị treo)
    m['status'] = 'finished'
    m['winner'] = winner
    m['final_score_team1'] = s1
    m['final_score_team2'] = s2
    
    # Lưu file
    save_loi_dai(ld_data)
    save_data_func(data)
    
def hien_thi_loi_dai(current_user_id, save_data_func):
    # --- BỔ SUNG: KIỂM TRA VÀ TỰ PHỤC HỒI DỮ LIỆU RỖNG ---
    ld_data = load_loi_dai() 
    if not isinstance(ld_data, dict):
        ld_data = {"matches": {}, "rankings": {}}
    matches_dict = ld_data.get('matches', {}) 
    
    # --- BƯỚC 1: KIỂM TRA ĐIỀU HƯỚNG THI ---
    if "match_id_active" in st.session_state: 
        mid = st.session_state.match_id_active
        if mid in matches_dict:
            lam_bai_thi_loi_dai(mid, matches_dict[mid], current_user_id, save_data_func) 
            return

    # --- BƯỚC 2: VẼ GIAO DIỆN LÔI ĐÀI CHÍNH ---
    st.subheader("🏟️ ĐẤU TRƯỜNG LÔI ĐÀI") 
    
    # 1. THÔNG BÁO TOAST & TỰ ĐỘNG XỬ THUA (Giữ nguyên logic của bạn)
    for mid, m in list(ld_data['matches'].items()): 
        all_players = m.get('challenger_team', []) + m.get('opponent_team', []) 
        if not all_players: all_players = [m.get('challenger'), m.get('opponent')] 
        
        # Thông báo khi có trận đấu
        if m.get('status') == 'active' and current_user_id in all_players: 
            notif_key = f"notified_{mid}_{current_user_id}"
            if notif_key not in st.session_state:
                st.toast(f"📢 Trận đấu đã bắt đầu!", icon="⚔️") 
                st.session_state[notif_key] = True

        # Tự động xử thua sau 24h
        if m.get('status') == 'active' and 'start_time' in m: 
            try:
                start_time = datetime.strptime(m['start_time'], "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - start_time).total_seconds() > 86400:
                    trong_tai_tong_ket(mid, ld_data, save_data_func) 
            except: pass 

    # --- BƯỚC 3: XỬ LÝ LỜI MỜI THÁCH ĐẤU (FIX KEYERROR TẠI ĐÂY) ---
    for mid, m in ld_data['matches'].items():
        if m.get('status') == 'pending' and m.get('opponent') == current_user_id:
            challenger_id = m.get('challenger') 
            # Sửa lỗi lấy tên an toàn
            challenger_info = st.session_state.data.get(challenger_id, {}) 
            challenger_name = challenger_info.get('name', 'Một Cao Thủ').upper()

            notification_html = f"""
            <div style="background-color: #ffffff; border: 4px solid #d32f2f; border-radius: 15px; padding: 25px; margin-bottom: 25px; text-align: center; color: #333333;">
                <h2 style="color: #d32f2f; font-size: 30px; font-weight: 900; margin-top: 0;">🔥 CÓ LỜI TUYÊN CHIẾN! 🔥</h2>
                <p style="font-size: 20px;">Cao thủ <b>{challenger_name}</b> muốn so tài!</p>
                <div style="display: inline-block; background-color: #fff8e1; padding: 15px 40px; border-radius: 10px; border: 2px dashed #ff8f00;">
                    <div style="font-size: 18px; font-weight: bold;">📚 Môn: {m.get('subject')} | 💎 Cược: {m.get('bet')} KPI</div>
                </div>
            </div>""" 
            st.markdown(notification_html, unsafe_allow_html=True)

            col_a, col_b = st.columns(2) 
            if col_a.button("✅ CHẤP NHẬN", key=f"acc_{mid}", use_container_width=True):
                bet = m.get('bet', 0)
                if challenger_id in st.session_state.data and current_user_id in st.session_state.data: 
                    if st.session_state.data[challenger_id].get('kpi', 0) >= bet and st.session_state.data[current_user_id].get('kpi', 0) >= bet: 
                        st.session_state.data[challenger_id]['kpi'] -= bet
                        st.session_state.data[current_user_id]['kpi'] -= bet
                        m['status'] = 'active' 
                        m['start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
                        save_loi_dai(ld_data) 
                        save_data_func(st.session_state.data) 
                        st.rerun() 
            if col_b.button("❌ TỪ CHỐI", key=f"rej_{mid}", use_container_width=True): 
                m['status'] = 'cancelled' 
                save_loi_dai(ld_data)
                st.rerun()

    # --- BƯỚC 4: HIỂN THỊ CÁC TRẬN ĐANG DIỄN RA ---
    st.subheader("⚔️ TRẬN ĐẤU ĐANG DIỄN RA") 
    active_matches = [mid for mid, m in ld_data['matches'].items() if m.get('status') == 'active'] 
    if not active_matches:
        st.write("Không có trận đấu nào đang diễn ra.") 
    else:
        for mid in active_matches:
            m = ld_data['matches'][mid]
            all_players = m.get('challenger_team', [m.get('challenger')]) + m.get('opponent_team', [m.get('opponent')]) 
            if current_user_id in all_players:
                with st.expander(f"⚔️ Trận đấu môn {m['subject'].upper()}"):
                    if f"score_{current_user_id}" in m:
                        st.success("✅ Bạn đã hoàn thành phần thi.") 
                    else:
                        if st.button("🚀 VÀO THI ĐẤU", key=f"play_btn_{mid}"): 
                            st.session_state.match_id_active = mid 
                            st.rerun()

    # --- BƯỚC 5: GIAO DIỆN GỬI CHIẾN THƯ (FIX KEYERROR DÒNG 1551) ---
    st.divider() 
    with st.expander("✉️ GỬI CHIẾN THƯ / LẬP TỔ ĐỘI", expanded=False): 
        c1, c2 = st.columns(2) 
        
        # --- 🛡️ FIX TRIỆT ĐỂ: Lọc danh sách học sinh an toàn ---
        list_opps = {}
        for uid, info in st.session_state.data.items(): 
            if isinstance(info, dict) and 'name' in info and uid != current_user_id and uid not in ['admin', 'system_config']: 
                list_opps[uid] = info['name']

        with c1:
            the_thuc = st.selectbox("Thể thức:", ["1 vs 1", "2 vs 2", "3 vs 3"], key="mode_sel")
            is_team = the_thuc != "1 vs 1" 
            # Sử dụng list_opps đã lọc sạch
            target_name = st.selectbox("Chọn đối thủ:", 
                                     ["--- Đấu Đội ---"] + list(list_opps.values()) if is_team else list(list_opps.values()), 
                                     disabled=is_team) 
            sub = st.selectbox("Môn thi:", ["Toán", "Lý", "Hóa", "Văn", "Anh", "Sinh"], key="sub_sel")
            
        with c2:
            hinh_thuc = st.radio("Hình thức:", ["Giải đề trắc nghiệm", "So điểm tăng trưởng"])
            bet = st.number_input("Cược KPI:", min_value=1, max_value=5, value=1) 
            st.markdown(f"📅 Thời hạn: **{'24 Giờ' if hinh_thuc == 'Giải đề trắc nghiệm' else '7 Ngày'}**")

        if st.button("🚀 THÀNH LẬP PHÒNG CHỜ", use_container_width=True):
            new_id = f"lobby_{int(datetime.now().timestamp())}"
            match_data = {
                "challenger": current_user_id,
                "challenger_team": [current_user_id],
                "opponent_team": [],
                "subject": sub,
                "bet": bet,
                "mode": the_thuc,
                "type": hinh_thuc,
                "status": "waiting",
                "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            if not is_team:
                target_id = [uid for uid, name in list_opps.items() if name == target_name][0]
                match_data.update({"opponent": target_id, "opponent_team": [target_id], "status": "pending"})
            
            ld_data['matches'][new_id] = match_data
            save_loi_dai(ld_data)
            st.rerun()

    # --- BƯỚC 6: PHÒNG CHỜ TỔ ĐỘI (GIA CỐ AN TOÀN) ---
    st.divider()
    st.markdown("### 🏟️ PHÒNG CHỜ TỔ ĐỘI")
    for mid, m in list(ld_data['matches'].items()):
        if m.get('status') == 'waiting':
            num_required = 2 if m['mode'] == "2 vs 2" else 3
            st.info(f"Phòng: {m['mode']} - {m['type']} - Môn {m['subject'].upper()} - Cược: {m['bet']} KPI")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Đội Thách Đấu ({len(m.get('challenger_team', []))}/{num_required})**")
                for uid in m.get('challenger_team', []):
                    # Sửa lỗi: Lấy tên an toàn bằng .get()
                    u_name = st.session_state.data.get(uid, {}).get('name', 'Học sĩ ẩn danh')
                    st.write(f"👤 {u_name}")
                
                # Nút Báo danh Đội 1
                if current_user_id not in m.get('challenger_team', []) and current_user_id not in m.get('opponent_team', []) and len(m.get('challenger_team', [])) < num_required:
                    if st.button(f"Vào Đội 1", key=f"join1_{mid}"):
                        m.setdefault('challenger_team', []).append(current_user_id)
                        save_loi_dai(ld_data)
                        st.rerun()

            with col_b:
                st.write(f"**Đội Nhận Kèo ({len(m.get('opponent_team', []))}/{num_required})**")
                for uid in m.get('opponent_team', []):
                    # Sửa lỗi: Lấy tên an toàn bằng .get()
                    u_name = st.session_state.data.get(uid, {}).get('name', 'Học sĩ ẩn danh')
                    st.write(f"👤 {u_name}")
                
                # Nút Báo danh Đội 2
                if current_user_id not in m.get('challenger_team', []) and current_user_id not in m.get('opponent_team', []) and len(m.get('opponent_team', [])) < num_required:
                    if st.button(f"Vào Đội 2", key=f"join2_{mid}"):
                        m.setdefault('opponent_team', []).append(current_user_id)
                        save_loi_dai(ld_data)
                        st.rerun()

            # TỰ KÍCH HOẠT KHI ĐỦ NGƯỜI
            if len(m.get('challenger_team', [])) == num_required and len(m.get('opponent_team', [])) == num_required:
                m['status'] = 'active'
                m['start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                m['challenger'] = m['challenger_team'][0] 
                m['opponent'] = m['opponent_team'][0]
                # Lưu KPI gốc an toàn
                m['start_kpi_dict'] = {uid: st.session_state.data.get(uid, {}).get('kpi', 0) for uid in m['challenger_team'] + m['opponent_team']}
                save_loi_dai(ld_data)
                st.success("🔥 ĐỦ NGƯỜI! TRẬN ĐẤU BẮT ĐẦU!")
                st.rerun()

    # --- BƯỚC 7: NHẬT KÝ LÔI ĐÀI (TỐI ƯU HÓA & FIX LỖI) ---
    st.divider()
    st.markdown("### 📜 NHẬT KÝ LÔI ĐÀI (20 trận gần nhất)")
    
    my_matches = []
    all_matches_sorted = sorted(ld_data['matches'].items(), key=lambda x: x[1].get('created_at', ''), reverse=True)

    for mid, m in all_matches_sorted:
        challengers = m.get('challenger_team', []) + [m.get('challenger')]
        opponents = m.get('opponent_team', []) + [m.get('opponent')]
        all_participants = set(filter(None, challengers + opponents))
        
        if current_user_id in all_participants:
            is_chal = current_user_id in challengers
            
            # Xác định tên đối thủ hiển thị an toàn
            if m.get('mode') == "1 vs 1":
                opp_id = m.get('opponent') if is_chal else m.get('challenger')
                opp_name = st.session_state.data.get(opp_id, {}).get('name', 'Học sĩ ẩn danh')
            else:
                opp_name = f"Đội đối phương ({m.get('mode', 'Tổ đội')})"
            
            status = m.get('status')
            if status == 'finished':
                winner = m.get('winner')
                if winner == current_user_id or (winner == "team1" and is_chal) or (winner == "team2" and not is_chal):
                    kq = "✅ Thắng"
                elif winner == "Hòa":
                    kq = "🤝 Hòa"
                else: 
                    kq = "❌ Thua"
            elif status == 'active': kq = "⚔️ Đang đấu"
            elif status == 'waiting': kq = "🕒 Đang lập đội"
            elif status == 'pending': kq = "⏳ Chờ trả lời"
            elif status == 'cancelled': kq = "🚫 Đã hủy"
            else: kq = "❓ Khác"

            my_matches.append({
                "Ngày": m.get('created_at', '---'),
                "Thể thức": f"{m.get('mode', '1 vs 1')} ({m.get('type', 'Giải đề')})",
                "Đối thủ": opp_name,
                "Môn": m.get('subject', 'N/A').capitalize(),
                "Cược": f"{m.get('bet', 0)} KPI",
                "Trạng thái": kq
            })
            if len(my_matches) >= 20: break

    if my_matches:
        st.table(pd.DataFrame(my_matches))
    else:
        st.caption("Bạn chưa tham gia trận lôi đài nào.")

def hien_thi_giao_dien_hoc_si(user_id, save_data_func):
    page = st.session_state.get("page")
    # Lấy thông tin người dùng từ data (Sửa lỗi NameError)
    user_info = st.session_state.data.get(user_id, {})
    my_team = user_info.get('team', 'Chưa phân tổ')
    role = user_info.get('role', 'u3')
    
    # ===== 📜 CHỈ SỐ HỌC SĨ =====
    if page == "📜 Chỉ số Học sĩ":
        hien_thi_chi_so_chi_tiet(user_id)

    # ===== 👥 QUẢN LÝ NHÂN SỰ TỔ (U1) =====
    elif page == "👥 Quản lý nhân sự Tổ":
        hien_thi_nhan_su_to(user_id, my_team, save_data_func)

    # ===== 📊 KPI TỔ =====
    elif page == "📊 Quản lý KPI tổ":
        hien_thi_kpi_to(user_id, my_team, role, save_data_func)

    # ===== 🏪 TIỆM & KHO =====
    elif page == "🏪 Tiệm tạp hóa & Kho đồ":
        hien_thi_tiem_va_kho(user_id, save_data_func)
        
    # SẢNH DANH VỌNG 
    elif page == "🏆 Sảnh Danh Vọng":
        hien_thi_sanh_danh_vong_user(user_id, save_data_func)

    # ===== 🔑 ĐỔI MẬT KHẨU (NẾU CÓ MENU) =====
    elif page == "🔑 Đổi mật khẩu":
        hien_thi_doi_mat_khau(user_id, save_data_func)

    else:
        st.info("📌 Hãy chọn chức năng trong menu bên trái.")
    

# --- GIAO DIỆN CHỈ SỐ HỌC SĨ LUNG LINH ---
def hien_thi_chi_so_chi_tiet(user_id):
    user_info = st.session_state.data[user_id]
    # === 🟢 BƯỚC 0: CHÈN LOGIC DỊCH CẤP BẬC TẠI ĐÂY ===
    role_map = {
        "u1": "Tổ trưởng",
        "u2": "Tổ phó", 
        "u3": "Tổ viên",
        "admin": "Quản trị viên"
    }
    # Lấy mã role (ví dụ: 'u1'), chuyển về chữ thường cho chắc ăn
    raw_role = str(user_info.get('role', 'u3')).lower()
    # Dịch ra tiếng Việt (Lưu vào biến role_name)
    role_name = role_map.get(raw_role, "Học sĩ")
    # ===================================================
    
    # --- 1. LOGIC TÍNH TOÁN CẤP ĐỘ VÀ TIẾN TRÌNH ---
    current_exp = user_info.get('exp', 0)
    current_level = user_info.get('level', 1) 
    exp_in_level = current_exp % 100
    progress_pct = exp_in_level / 100
    
    atk = tinh_atk_tong_hop(user_info)
    base_kpi = float(user_info.get('kpi', 0.0))
    hp_current = base_kpi + (current_level * 20)

    # --- 2. GIAO DIỆN HIỂN THỊ CHÍNH ---
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        # Hiển thị Avatar (Dùng link ảnh gif/png của bạn)
        st.image("https://i.ibb.co/mVjzG7MQ/giphy-preview.gif", use_container_width=True)
        

    with col_info:
        # --- 1. Hiển thị Tên Học Sĩ ---
        st.markdown(f"<h1 style='margin-bottom:0px;'>⚔️ {user_info.get('name', 'HỌC SĨ').upper()}</h1>", unsafe_allow_html=True)
        
        # --- 2. Hiển thị Tổ đội ---
        st.markdown(f"<p style='color:#f39c12; font-size:1.2em; font-weight:bold; margin-top:0px;'>🚩 Tổ đội: {user_info.get('team', 'Chưa phân tổ')}</p>", unsafe_allow_html=True)

        # --- 3. Hiển thị Cấp bậc (MỚI THÊM VÀO) ---
        # Logic dịch tên (để đây cho tiện nếu chưa khai báo ở trên)
        role_map = {"u1": "Tổ trưởng", "u2": "Tổ phó", "u3": "Tổ viên", "admin": "Quản trị viên"}
        raw_role = str(user_info.get('role', 'u3')).lower()
        role_name = role_map.get(raw_role, "Học sĩ")
        
        # Dòng lệnh in ra màn hình (Style chữ đậm cho đẹp)
        st.markdown(f"<p style='font-size:1.1em; font-weight:bold; margin-top:5px;'>🔰 Cấp bậc: <span style='color:#3498db'>{role_name}</span></p>", unsafe_allow_html=True)
        
        # Hiển thị HP và ATK dạng text thuần cho sạch sẽ
        st.markdown(f"❤️ **SINH MỆNH (HP):** <span style='color:#ff4b4b; font-size:1.2em; font-weight:bold;'>{hp_current}</span>", unsafe_allow_html=True)
        st.markdown(f"⚔️ **CHIẾN LỰC (ATK):** <span style='color:#f1c40f; font-size:1.2em; font-weight:bold;'>{atk}</span>", unsafe_allow_html=True)
        
        st.write("") # Tạo khoảng cách

        # --- THANH KINH NGHIỆM (EXP BAR) - THIẾT KẾ BỰ VÀ NỔI BẬT ---
        st.markdown(f"✨ **CẤP ĐỘ: {current_level}** <span style='float:right; color:#3498db; font-weight:bold;'>{exp_in_level} / 100 EXP</span>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="width: 100%; background-color: #dfe6e9; border-radius: 15px; padding: 4px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);">
                <div style="width: {progress_pct*100}%; 
                            background: linear-gradient(90deg, #3498db, #9b59b6, #e84393); 
                            height: 25px; 
                            border-radius: 12px; 
                            transition: width 0.8s ease-in-out;
                            box-shadow: 0 2px 5px rgba(52, 152, 219, 0.4);">
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.caption("🔥 Hãy tích cực thám hiểm phó bản để thăng cấp sức mạnh!")
    # --- CHÈN MỚI: HIỂN THỊ KỶ LỤC THÁM HIỂM ---
        st.markdown("<p style='margin-bottom:5px; font-weight:bold; color:#f1c40f;'>🏆 KỶ LỤC THỜI GIAN NHANH NHẤT</p>", unsafe_allow_html=True)
        
        best_times = user_info.get('best_time', {})
        
        if not best_times:
            st.markdown("<small style='color:#888;'><i>Chưa có kỷ lục nào được ghi nhận.</i></small>", unsafe_allow_html=True)
        else:
            # Tạo lưới 3 cột để hiển thị các môn học
            record_cols = st.columns(3)
            # Bản đồ tên môn học có icon
            mapping_names = {
                "toan": "📐 Toán", "van": "📖 Văn", "anh": "🇬🇧 Anh",
                "ly": "⚡ Lý", "hoa": "🧪 Hóa", "sinh": "🌿 Sinh"
            }
            
            # Duyệt qua các kỷ lục và hiển thị vào các cột
            for idx, (l_id, time_val) in enumerate(best_times.items()):
                with record_cols[idx % 3]:
                    st.markdown(f"""
                        <div style="background: rgba(241, 196, 15, 0.1); 
                                    border: 1px solid #f1c40f; 
                                    border-radius: 8px; 
                                    padding: 5px; 
                                    text-align: center;
                                    margin-bottom: 5px;">
                            <div style="font-size: 11px; color: #aaa;">{mapping_names.get(l_id, l_id.upper())}</div>
                            <div style="font-size: 16px; font-weight: bold; color: #f1c40f;">{time_val}s</div>
                        </div>
                    """, unsafe_allow_html=True)
        # --------------------------------------------
    # --- 3. BẢNG THÔNG SỐ PHỤ DẠNG CARD (Dòng dưới cùng) ---
    st.write("---")
    cols = st.columns(4)
    badges = [
        ("📚 Tri Thức", user_info.get('Tri_Thuc', 0), "#3498db"),
        ("🛡️ Chiến Tích", user_info.get('Chien_Tich', 0), "#e67e22"),
        ("🎖️ Vinh Dự", user_info.get('Vinh_Du', 0), "#2ecc71"),
        ("👑 Vinh Quang", user_info.get('Vinh_Quang', 0), "#f1c40f")
    ]
    
    for i, (label, val, color) in enumerate(badges):
        with cols[i]:
            st.markdown(f"""
                <div style="text-align: center; border: 2px solid {color}; border-radius: 15px; padding: 10px; background: white;">
                    <p style="font-size: 0.85em; color: #636e72; margin-bottom: 5px; font-weight: bold;">{label}</p>
                    <h2 style="margin: 0; color: {color};">{val}</h2>
                </div>
            """, unsafe_allow_html=True)

# --- 1. QUẢN LÝ NHÂN SỰ (ONLY U1) ---
def hien_thi_nhan_su_to(user_id, my_team, save_data_func):
    st.subheader(f"👥 QUẢN TRỊ NỘI BỘ: {my_team}")
    
    # A. Kết nạp thành viên (Chỉ lấy những bạn 'Chưa phân tổ')
    # --- 🛡️ FIX LỖI: THÊM ĐIỀU KIỆN KIỂM TRA DICT 🛡️ ---
    free_agents = [
        uid for uid, info in st.session_state.data.items()
        # Chỉ lấy nếu là Dict (Học sinh) VÀ thuộc nhóm "Chưa phân tổ"
        if isinstance(info, dict) and info.get('team') == "Chưa phân tổ"
    ]
    if free_agents:
        target_join = st.selectbox("Chọn Học sĩ tự do để kết nạp:", free_agents, format_func=lambda x: st.session_state.data[x]['name'])
        if st.button("🤝 Mời vào Tổ"):
            st.session_state.data[target_join]['team'] = my_team
            save_data_func()
            st.success("Đã kết nạp thành viên mới!")
            st.rerun()

    # B. Bổ/Bãi nhiệm U2 & Reset Pass
    # --- 🛡️ FIX LỖI: LỌC LIST RA KHỎI DANH SÁCH ---
    mems = [
        uid for uid, info in st.session_state.data.items()
        # Thêm điều kiện isinstance(info, dict) vào đầu
        if isinstance(info, dict) and info.get('team') == my_team and uid != user_id
    ]
    if mems:
        target_uid = st.selectbox(
            "Chọn thành viên trong tổ:", 
            mems,
            format_func=lambda x: f"{st.session_state.data[x]['name']} ({'Tổ phó' if st.session_state.data[x]['role'] == 'u2' else ''})".strip(" ()")
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🎖️ Bổ nhiệm/Bãi nhiệm Tổ phó"):
                current_role = st.session_state.data[target_uid]['role']
                st.session_state.data[target_uid]['role'] = "u2" if current_role == "u3" else "u3"
                save_data_func()
                st.rerun()
        with c2:
            if st.button("🔑 Reset mật khẩu về 123"):
                st.session_state.data[target_uid]['password'] = "123"
                save_data_func()
                st.warning("Đã đưa mật khẩu về mặc định.")

def hien_thi_kpi_to(user_id, my_team, role, save_data_func):
    # 1. CSS TÙY CHỈNH CHO GIAO DIỆN TỔ TRƯỞNG (Tone màu xanh dương chuyên nghiệp)
    st.markdown("""
        <style>
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #1e3a8a 0%, #1e1b4b 100%);
            border: 1px solid #3b82f6;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            text-align: center;
        }
        [data-testid="stMetric"] label { color: #bfdbfe !important; font-weight: bold; font-size: 1.1rem !important; }
        [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #ffffff !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<h2 style='text-align: center; color: #3498db;'>📊 TRUNG TÂM ĐIỀU HÀNH: {my_team.upper()}</h2>", unsafe_allow_html=True)

    # 2. LẤY VÀ LỌC DỮ LIỆU THÀNH VIÊN (Sửa lỗi 'list' object has no attribute 'get')
    team_mems = {
        uid: info for uid, info in st.session_state.data.items() 
        if isinstance(info, dict) and info.get('team') == my_team
    }
    
    if not team_mems:
        st.warning("Tổ hiện chưa có thành viên nào.")
        return

    # Tạo DataFrame để tính toán
    import pandas as pd
    df_team = pd.DataFrame.from_dict(team_mems, orient='index')

    # 3. HIỂN THỊ THÔNG SỐ TỔ TRỰC QUAN (METRICS CARDS)
    m1, m2, m3, m4 = st.columns(4)
    total_kpi_team = df_team['kpi'].sum()
    avg_kpi_team = df_team['kpi'].mean()
    team_size = len(df_team)
    # Lấy Bonus cao nhất trong tổ (nếu có cột Bonus)
    max_bonus = df_team['Bonus'].max() if 'Bonus' in df_team.columns else 0

    with m1: st.metric("💰 TỔNG KPI TỔ", f"{total_kpi_team:,.0f} 🏆")
    with m2: st.metric("📈 KPI TRUNG BÌNH", f"{avg_kpi_team:.1f}")
    with m3: st.metric("⚔️ QUÂN SỐ", f"{team_size} Học sĩ")
    with m4: st.metric("🌟 BONUS MAX", f"{max_bonus}")

    st.write("")

    # 4. BIỂU ĐỒ SO SÁNH NĂNG LỰC NỘI BỘ (ĐÃ SỬA LỖI INVENTORY)
    import altair as alt
    st.markdown("##### 📊 BIỂU ĐỒ SỨC MẠNH THÀNH VIÊN")
    
    # CHỈ LẤY CỘT CẦN THIẾT ĐỂ VẼ (loại bỏ các cột phức tạp như inventory)
    chart_data = df_team[['name', 'kpi']].reset_index() 
    
    chart = alt.Chart(chart_data).mark_bar(cornerRadiusEnd=5).encode(
        x=alt.X('kpi:Q', title="Số KPI hiện có"),
        y=alt.Y('name:N', sort='-x', title=None, axis=alt.Axis(
            labelFontSize=13, 
            labelFontWeight='bold', 
            labelColor='#000000'
        )),
        color=alt.value("#3498db"),
        tooltip=['name', 'kpi']
    ).properties(height=250)
    
    st.altair_chart(chart, use_container_width=True)

    # 5. BẢNG CHI TIẾT VÀ CÔNG CỤ NHẬP LIỆU (PHẦN CŨ CỦA BẠN)
    st.markdown("### 🛠️ CÔNG CỤ QUẢN LÝ THÀNH VIÊN")
    
    # Hiển thị bảng dữ liệu thu gọn
    cols_to_show = ['name', 'kpi', 'Vi_Pham']
    if 'total_score' in df_team.columns: cols_to_show.append('total_score')
    
    st.dataframe(df_team[cols_to_show].sort_values('kpi', ascending=False), use_container_width=True)

    # 2 Cột nhập liệu (Giữ nguyên logic form của bạn nhưng làm gọn giao diện)
    col_kt, col_vp = st.columns(2)

    with col_kt:
        st.markdown("#### 📝 GHI ĐIỂM HỌC TẬP")
        with st.expander("Mở khung nhập điểm", expanded=False): # Để mặc định đóng cho gọn
            with st.form("form_diem_hoc_tap"):
                target_kt = st.selectbox("Chọn thành viên:", list(team_mems.keys()), format_func=lambda x: team_mems[x]['name'], key="sel_kt")
                loai_kt = st.selectbox("Hạng mục:", ["Kiểm tra thường xuyên", "KT Sản phẩm", "KT Giữa kỳ", "KT Cuối kỳ"])
                diem_kt = st.number_input("Số điểm (0-10):", min_value=0.0, max_value=10.0, step=0.5)
                confirm_kt = st.checkbox("Xác nhận thông tin chính xác", key="check_kt")
                
                if st.form_submit_button("🔥 CẬP NHẬT"):
                    if confirm_kt:
                        db_key = "KTTX" if loai_kt == "Kiểm tra thường xuyên" else loai_kt
                        st.session_state.data[target_kt][db_key] = diem_kt
                        # Cộng dồn tích lũy
                        current_total = st.session_state.data[target_kt].get('total_score', 0.0)
                        st.session_state.data[target_kt]['total_score'] = current_total + diem_kt
                        save_data_func()
                        st.success(f"Đã cộng điểm thành công!")
                        st.rerun()

    with col_vp:
        st.markdown("#### 💢 GHI LỖI VI PHẠM")
        with st.expander("Mở khung kỷ luật", expanded=False):
            violation_options = {"Đi trễ": -1, "Chưa thuộc bài": -2, "Chưa làm bài": -2, "Ngôn ngữ ko chuẩn": -5, "Gây gổ": -10}
            target_vp = st.selectbox("Thành viên vi phạm:", list(team_mems.keys()), format_func=lambda x: team_mems[x]['name'], key="sel_vp")
            loai_vp = st.selectbox("Hành vi:", list(violation_options.keys()))
            diem_tru = violation_options[loai_vp]
            
            with st.form("confirm_vi_pham"):
                st.error(f"Phạt dự kiến: {diem_tru} KPI")
                confirm_vp = st.checkbox("Xác nhận thực thi kỷ luật", key="check_vp")
                if st.form_submit_button("🔨 THỰC THI"):
                    if confirm_vp:
                        st.session_state.data[target_vp]['kpi'] += diem_tru
                        st.session_state.data[target_vp]['Vi_Pham'] += abs(diem_tru)
                        save_data_func() 
                        st.success("Đã ghi nhận vi phạm!")
                        st.rerun()


@st.dialog("XÁC NHẬN SỬ DỤNG")
def confirm_use_dialog(item_name, item_info, current_user_id, save_func):    # --- LỚP BẢO VỆ 1: KIỂM TRA DỮ LIỆU TỔNG ---
    # Kiểm tra xem 'data' có tồn tại trong session_state không và có bị None không
    if 'data' not in st.session_state or st.session_state.data is None:
        st.error("⚠️ Lỗi nghiêm trọng: Dữ liệu hệ thống chưa được tải!")
        if st.button("Tải lại trang"):
            st.rerun()
        return

    # --- LỚP BẢO VỆ 2: XÁC ĐỊNH ID NGƯỜI DÙNG ---
    # Ưu tiên lấy từ tham số, nếu không có thì lấy từ session, nếu không có nữa thì chịu
    safe_uid = current_user_id if current_user_id else st.session_state.get('user_id')

    if not safe_uid or safe_uid not in st.session_state.data:
        st.error("❌ Không tìm thấy thông tin người dùng trong dữ liệu!")
        return

    # --- LOGIC CHÍNH ---
    detail = get_item_info(item_name)
    if not detail:
        st.error(f"❌ Không tìm thấy thông tin vật phẩm: {item_name}")
        return

    st.write(f"Bạn có chắc chắn muốn sử dụng **{item_name}** không?")

    # Hiển thị công dụng (Code cũ của bạn ok)
    props = detail.get('properties', {})
    behavior = detail.get('type')
    if behavior == "FUNCTIONAL":
        st.info(f"✨ Công dụng: Kích hoạt đặc quyền {props.get('feature')}")
    else:
        st.info(f"✨ Công dụng: Sử dụng vật phẩm {behavior}")

    c1, c2 = st.columns(2)

    # --- XỬ LÝ NÚT XÁC NHẬN ---
    if c1.button("✅ Xác nhận", use_container_width=True):
        try:
            # 1. Áp dụng hiệu ứng
            st.session_state.data = apply_item_effect(safe_uid, detail, st.session_state.data)
            
            # 2. Truy cập an toàn vào kho đồ
            user_inv = st.session_state.data[safe_uid].get('inventory')
            
            # Xử lý trừ đồ (Hỗ trợ cả Dict và List để không bao giờ lỗi)
            if isinstance(user_inv, dict):
                if user_inv.get(item_name, 0) > 0:
                    user_inv[item_name] -= 1
                    if user_inv[item_name] <= 0:
                        del user_inv[item_name]
            elif isinstance(user_inv, list):
                if item_name in user_inv:
                    user_inv.remove(item_name)
            
            # Cập nhật ngược lại vào data tổng
            st.session_state.data[safe_uid]['inventory'] = user_inv
            
            # 3. Lưu dữ liệu
            # Đảm bảo save_data_func được import và có sẵn
            if save_func: 
                save_func() 
            
            st.success(f"✨ Đã sử dụng {item_name} thành công!")
            # --- THÊM ĐOẠN NÀY ĐỂ KÍCH HOẠT KHUNG CHAT ---
            # Kiểm tra nếu vật phẩm vừa dùng là Thẻ Chat
            if detail.get('properties', {}).get('feature') == 'world_chat':
                st.session_state.trigger_world_chat = True  # <--- BẬT CỜ HIỆU
                
            # Xóa trạng thái pending
            if "pending_use" in st.session_state:
                del st.session_state.pending_use
            st.rerun()
            
        except Exception as e:
            st.error(f"Đã xảy ra lỗi khi xử lý: {e}")

    if c2.button("❌ Hủy", use_container_width=True):
        if "pending_use" in st.session_state:
            del st.session_state.pending_use
        st.rerun()

@st.dialog("🌍 LOA PHÁT THANH THẾ GIỚI")
def show_world_chat_input(user_id):
    st.markdown("### 📣 Bạn muốn hét gì cho cả lớp nghe nào?")
    
    # Kiểm tra số lượt còn lại
    user_data = st.session_state.data.get(user_id, {})
    perm = user_data.get('special_permissions', {})
    count = perm.get('world_chat_count', 0)
    
    st.info(f"⚡ Bạn đang có: **{count}** lượt phát thanh.")
    
    if count <= 0:
        st.error("❌ Bạn đã hết lượt phát thanh! Hãy mua thêm thẻ.")
        if st.button("Đóng"):
            del st.session_state.trigger_world_chat
            st.rerun()
        return

    # Form nhập liệu
    msg_content = st.text_area("Nội dung tin nhắn:", max_chars=100, placeholder="Nhập tối đa 100 ký tự...")
    
    col1, col2 = st.columns(2)
    
    if col1.button("🚀 GỬI NGAY", use_container_width=True):
        if not msg_content.strip():
            st.warning("⚠️ Đừng gửi tin nhắn trống nhé!")
        else:
            # 1. TRỪ LƯỢT CHAT
            st.session_state.data[user_id]['special_permissions']['world_chat_count'] -= 1
            
            # 2. GHI VÀO FILE WORLD_ANNOUNCEMENTS.JSON
            new_msg = {
                "user": user_data.get('name', 'Ẩn danh'),
                "content": msg_content,
                "time": datetime.now().strftime("%H:%M %d/%m")
            }
            
            try:
                # Đọc file cũ
                try:
                    with open('data/world_announcements.json', 'r', encoding='utf-8') as f:
                        msgs = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    msgs = []
                
                # Thêm tin mới và chỉ giữ lại 20 tin gần nhất
                msgs.append(new_msg)
                if len(msgs) > 20: 
                    msgs = msgs[-20:]
                    
                # Ghi lại file
                with open('data/world_announcements.json', 'w', encoding='utf-8') as f:
                    json.dump(msgs, f, ensure_ascii=False, indent=4)
                    
                st.success("✅ Đã gửi tin nhắn thành công!")
                
                # Lưu data người dùng (đã trừ lượt)
                # (Giả sử bạn có hàm save_data_func import từ main hoặc truyền vào)
                # save_data_func() 
                
                # Tắt cờ hiệu và reload
                del st.session_state.trigger_world_chat
                st.rerun()
                
            except Exception as e:
                st.error(f"Lỗi khi gửi tin: {e}")

    if col2.button("Đóng", use_container_width=True):
        del st.session_state.trigger_world_chat
        st.rerun()

# --- 3. TIỆM TẠP HÓA & KHO ĐỒ (ALL) ---
def hien_thi_tiem_va_kho(user_id, save_data_func):
    st.subheader("🏪 TIỆM TẠP HÓA & 🎒 TÚI ĐỒ")
    
    # Lấy thông tin người dùng hiện tại
    user_info = st.session_state.data[user_id]
    
    # --- PHẦN MỚI: HIỂN THỊ SỐ DƯ TÀI SẢN ---
    st.markdown(f"""
        <div style="display: flex; justify-content: space-around; background: #3e2723; padding: 15px; border-radius: 10px; border: 2px solid #8d6e63; margin-bottom: 20px;">
            <div style="text-align: center; color: white;">
                <div style="font-size: 1.2em;">📘</div>
                <div style="font-size: 0.8em; color: #bdbdbd;">Tri Thức</div>
                <div style="font-weight: bold; color: #ffd600;">{user_info.get('Tri_Thuc', 0)}</div>
            </div>
            <div style="text-align: center; color: white;">
                <div style="font-size: 1.2em;">🏆</div>
                <div style="font-size: 0.8em; color: #bdbdbd;">KPI</div>
                <div style="font-weight: bold; color: #76ff03;">{user_info.get('kpi', 0)}</div>
            </div>
            <div style="text-align: center; color: white;">
                <div style="font-size: 1.2em;">⚔️</div>
                <div style="font-size: 0.8em; color: #bdbdbd;">Chiến Tích</div>
                <div style="font-weight: bold; color: #ff5252;">{user_info.get('Chien_Tich', 0)}</div>
            </div>
            <div style="text-align: center; color: white;">
                <div style="font-size: 1.2em;">🎖️</div>
                <div style="font-size: 0.8em; color: #bdbdbd;">Vinh Dự</div>
                <div style="font-weight: bold; color: #40c4ff;">{user_info.get('Vinh_Du', 0)}</div>
            </div>
            <div style="text-align: center; color: white;">
                <div style="font-size: 1.2em;">👑</div>
                <div style="font-size: 0.7em; color: #bdbdbd;">Vinh Quang</div>
                <div style="font-weight: bold; color: #ea80fc;">{user_info.get('Vinh_Quang', 0)}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_tiem, tab_kho = st.tabs(["🛒 Mua sắm", "🎒 Túi đồ của tôi"])
    
    label_map = {
        "kpi": "Tri Thức", 
        "Tri_Thuc": "Tri Thức", 
        "Chien_Tich": "Chiến Tích",
        "Vinh_Du": "Vinh Dự", 
        "Vinh_Quang": "Vinh Quang"
    }

    with tab_tiem:
        all_items = st.session_state.shop_items
        shop_items_visible = [(name, info) for name, info in all_items.items() if info.get('is_listed', True)]
        if not st.session_state.shop_items:
            st.info("Cửa hàng hiện đang nhập thêm hàng, bạn quay lại sau nhé!")
        else:
            label_map = {
                "kpi": "KPI Tổng", 
                "Tri_Thuc": "Tri Thức", 
                "Chien_Tich": "Chiến Tích",
                "Vinh_Du": "Vinh Dự", 
                "Vinh_Quang": "Vinh Quang"
            }
            @st.dialog("XÁC NHẬN GIAO DỊCH")
            def confirm_dialog(item_name, item_info):
                    # 1. Lấy thông tin tiền tệ và quyền giảm giá
                    currency = item_info.get('currency_buy', 'kpi')
                    u_info = st.session_state.data[user_id]
                    
                    # Lấy % giảm giá (khớp với tên biến trong item_system)
                    u_discount = u_info.get('special_permissions', {}).get('discount_percent', 0)
                    
                    # 2. Tính giá thực tế sau giảm
                    price_goc = item_info.get('price', 0)
                    actual_price = int(price_goc * (100 - u_discount) / 100)

                    st.write(f"Bạn có chắc chắn muốn mua **{item_name}** không?")
                    if u_discount > 0:
                        st.success(f"🎟️ Đang áp dụng ưu đãi giảm giá: -{u_discount}%")
                        st.info(f"Giá thanh toán: {actual_price} {label_map.get(currency, 'Điểm')} (Giá gốc: {price_goc})")
                    else:
                        st.info(f"Giá thanh toán: {actual_price} {label_map.get(currency, 'Điểm')}")
                    
                    col_ok, col_no = st.columns(2)
                    
                    if col_ok.button("✅ Xác nhận mua", use_container_width=True):
                        # Kiểm tra số dư theo giá ĐÃ GIẢM
                        if u_info.get(currency, 0) >= actual_price:
                            # THỰC HIỆN TRỪ TIỀN THEO GIÁ GIẢM
                            st.session_state.data[user_id][currency] -= actual_price
                        
                            # THÊM VẬT PHẨM VÀO KHO
                            inventory = st.session_state.data[user_id].setdefault('inventory', {})
                            if isinstance(inventory, dict):
                                inventory[item_name] = inventory.get(item_name, 0) + 1
                            elif isinstance(inventory, list):
                                inventory.append(item_name)
                            
                            save_data_func()
                            st.success(f"🎊 Chúc mừng! Bạn đã sở hữu {item_name}")
                            del st.session_state.pending_item
                            st.rerun()
                        else:
                            st.error(f"❌ Bạn không đủ {label_map.get(currency, currency)} để mua!")

                    if col_no.button("❌ Hủy bỏ", use_container_width=True):
                        del st.session_state.pending_item
                        st.rerun()
                    
            # Tạo lưới 4 cột để hiển thị vật phẩm
            cols = st.columns(4)
            shop_items = list(st.session_state.shop_items.items())
            
            for i, (name, info) in enumerate(shop_items):
                with cols[i % 4]:
                    # 1. Hiển thị Card vật phẩm (Dời sát lề trái để tránh lỗi render)
                    # --- LẤY DỮ LIỆU THÔNG MINH TỪ KHO ADMIN ---
                    item_detail = get_item_info(name)
                    if item_detail:
                        behavior = item_detail.get('type')
                        props = item_detail.get('properties', {})
                        img_url = item_detail.get('image', info.get('image', ''))

                        # Tự động tạo mô tả dựa trên loại vật phẩm (Behavior)
                        if behavior == "BUFF_STAT":
                            eff_text = f"🔥 +{props.get('value')} {props.get('target_stat', '').upper()} ({props.get('duration_type')})"
                        elif behavior == "FUNCTIONAL":
                            eff_text = f"📣 Quyền: {props.get('feature')}"
                        elif behavior == "CONSUMABLE":
                            eff_text = f"💎 Nhận: {props.get('value')} {props.get('target_type', '').upper()}"
                        else:
                            eff_text = "✨ Vật phẩm đặc biệt"
                    else:
                        # Nếu không tìm thấy trong kho Admin, dùng dữ liệu mặc định từ Shop
                        eff_text = "Chưa có định nghĩa"
                        img_url = info.get('image', '')
                    
                    c_buy = info.get('currency_buy', 'Tri_Thuc')
                    icon_buy = "📘" if c_buy == "Tri_Thuc" else "🏆"

                    st.markdown(f"""
<div style="background:#5d4037;border:2px solid #a1887f;border-radius:8px;padding:10px;text-align:center;color:white;margin-bottom:10px;">
<img src="{img_url}" style="width:50px;height:50px;object-fit:contain;margin-bottom:5px;">
<div style="font-size:0.8em;font-weight:bold;height:35px;overflow:hidden;">{name}</div>
<div style="font-size:0.7em;color:#76ff03;font-weight:bold;">{eff_text}</div>
<div style="color:#ffd600;font-size:0.85em;font-weight:bold;margin-top:5px;">{icon_buy} {info.get('price', 0)}</div>
</div>
""", unsafe_allow_html=True)

                    if st.button(f"Mua {name}", key=f"btn_buy_{name}", use_container_width=True):
                        st.session_state.pending_item = (name, info)
                        st.rerun() # Rerun để kích hoạt hiển thị dialog bên dưới

            # --- GỌI DIALOG KHI CÓ TRẠNG THÁI CHỜ MUA ---
            if "pending_item" in st.session_state:
                p_name, p_info = st.session_state.pending_item
                confirm_dialog(p_name, p_info)
                
                

    # --- PHẦN CẬP NHẬT TRONG TAB KHO ---
    with tab_kho:
        inventory = user_info.get('inventory', {})
        
        # Chuyển đổi data cũ (list) sang data mới (dict) nếu cần
        if isinstance(inventory, list):
            st.warning("⚠️ Đang nâng cấp cấu trúc túi đồ... Vui lòng chờ!")
            new_inv = {}
            for item in inventory:
                new_inv[item] = new_inv.get(item, 0) + 1
            user_info['inventory'] = new_inv
            save_data_func()
            st.rerun()

        if not inventory:
            st.info("Túi đồ của bạn đang trống. Hãy sang Tiệm tạp hóa sắm đồ nhé!")
        else:
            st.write(f"### 🎒 VẬT PHẨM ĐANG SỞ HỮU")
            
            # Lấy data Shop để biết loại item (Type)
            shop_data = st.session_state.get('shop_items', {})
            
            cols_kho = st.columns(4)
            
            # Duyệt qua từng món đồ trong kho
            for i, (item_name, count) in enumerate(inventory.items()):
                # Lấy thông tin chi tiết item
                item_info = shop_data.get(item_name, {})
                img_url = item_info.get('image', 'https://via.placeholder.com/50')
                item_type = item_info.get('type', 'UNKNOWN') # Quan trọng: Type để phân loại Rương/Item thường
                
                with cols_kho[i % 4]:
                    # Vẽ Card Item
                    st.markdown(f"""
                    <div style="background:#3e2723;border:2px solid #8d6e63;border-radius:8px;padding:10px;text-align:center;color:white;margin-bottom:5px;">
                    <img src="{img_url}" style="width:50px;height:50px;object-fit:contain;margin-bottom:5px;">
                    <div style="font-size:0.8em;font-weight:bold;height:35px;overflow:hidden;">{item_name}</div>
                    <div style="color:#76ff03;font-size:0.9em;font-weight:bold;">Số lượng: {count}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # --- NÚT BẤM XỬ LÝ (PHÂN LOẠI THEO TYPE) ---
                    
                    # CASE 1: LÀ RƯƠNG GACHA -> NÚT MỞ RƯƠNG
                    if item_type == "GACHA_BOX":
                        if st.button(f"🎲 Mở Rương", key=f"open_{item_name}_{i}", use_container_width=True):
                            # 1. Hiệu ứng chờ (Hồi hộp)
                            with st.spinner("🎲 Đang lắc rương..."):
                                time.sleep(1.5)
                            
                            # 2. Xử lý Logic (Backend)
                            rewards = xu_ly_mo_ruong(user_id, item_name, item_info, st.session_state.data, save_data_func)
                            
                            # 3. LƯU KẾT QUẢ VÀO SESSION STATE (Thay vì hiện luôn)
                            st.session_state.gacha_result = {
                                "name": item_name,
                                "rewards": rewards
                            }
                            st.rerun()

                    # CASE 2: ITEM DÙNG ĐƯỢC (Thuốc, Buff...) -> NÚT SỬ DỤNG CŨ
                    elif item_type in ["CONSUMABLE", "BUFF_STAT"]:
                        if st.button(f"⚡ Sử dụng", key=f"use_{item_name}_{i}", use_container_width=True):
                            st.session_state.pending_use = (item_name, item_info)
                            st.rerun()
                            
                    # CASE 3: ITEM KHÁC (Nguyên liệu...)
                    else:
                        st.button("🔒 Đã sở hữu", disabled=True, key=f"dis_{item_name}_{i}")

        # Gọi Popup xác nhận dùng item thường (Giữ nguyên logic cũ)
        if "pending_use" in st.session_state:
            u_name, u_info = st.session_state.pending_use
            # Đảm bảo bạn đã import hoặc định nghĩa confirm_use_dialog ở đâu đó
            confirm_use_dialog(u_name, u_info, user_id, save_data_func)
        if "gacha_result" in st.session_state:
            res = st.session_state.gacha_result
            # Gọi hàm Popup đã viết ở Bước 1
            popup_ket_qua_mo_ruong(res['name'], res['rewards'])

          
def hien_thi_doi_mat_khau(user_id, save_data_func):
    st.subheader("🔑 THAY ĐỔI MẬT MÃ")
    
    # Đảm bảo tài khoản admin có trong dữ liệu để có chỗ lưu mật khẩu
    if user_id == "admin" and "admin" not in st.session_state.data:
        st.session_state.data["admin"] = {
            "name": "Quản trị viên", 
            "role": "Admin", 
            "password": "admin" # Mật khẩu gốc ban đầu
        }

    user_data = st.session_state.data.get(user_id)
    
    with st.form("form_change_password"):
        old_password = st.text_input("Mật khẩu hiện tại:", type="password")
        new_password = st.text_input("Mật khẩu mới:", type="password")
        confirm_password = st.text_input("Xác nhận mật khẩu mới:", type="password")
        
        submit = st.form_submit_button("💾 CẬP NHẬT MẬT KHẨU")
        
        if submit:
            if not old_password or not new_password:
                st.error("Vui lòng nhập đầy đủ thông tin!")
            elif old_password != user_data['password']:
                st.error("Mật khẩu hiện tại không chính xác!")
            elif new_password != confirm_password:
                st.error("Mật khẩu mới và xác nhận không khớp!")
            elif len(new_password) < 4:
                st.warning("Mật khẩu nên có ít nhất 4 ký tự!")
            else:
                # --- THỰC HIỆN LƯU MẬT KHẨU MỚI ---
                st.session_state.data[user_id]['password'] = new_password
                save_data_func() # Lưu vào file data.json
                
                st.success("🎉 Chúc mừng! Mật mã của bạn đã được cập nhật thành công.")
                st.balloons()   
                
# --- SẢNH DANH VỌNG ---                
def hien_thi_sanh_danh_vong_user(user_id, save_data_func):
    st.subheader("🏛️ SẢNH DANH VỌNG - KHẲNG ĐỊNH VỊ THẾ")
    
    # Kiểm tra nếu Admin chưa thiết lập danh hiệu
    if 'rank_settings' not in st.session_state:
        st.info("Hệ thống danh hiệu đang được các trưởng lão thảo luận, vui lòng quay lại sau!")
        return

    user_data = st.session_state.data[user_id]
    user_kpi = user_data.get('kpi', 0)
    # Danh sách các danh hiệu user đã từng kích hoạt
    unlocked = user_data.get('unlocked_ranks', [])
    # Danh hiệu đang hiển thị hiện tại
    current_rank = user_data.get('current_rank', "Học Sĩ")

    st.markdown(f"**KPI Hiện tại của bạn:** `{user_kpi}` 🏆 | **Danh hiệu hiện tại:** `{current_rank}`")
    st.divider()

    # Hiển thị danh sách danh hiệu dưới dạng các thẻ (Cards)
    for rank in st.session_state.rank_settings:
        r_name = rank["Danh hiệu"]
        r_kpi = rank["KPI Yêu cầu"]
        r_color = rank["Màu sắc"]
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Thiết kế thẻ danh hiệu đẹp mắt bằng HTML
            st.markdown(f"""
                <div style="padding:15px; border-radius:10px; border-left: 10px solid {r_color}; 
                            background-color: #262730; margin-bottom:10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                    <h4 style="margin:0; color:{r_color};">{r_name}</h4>
                    <p style="margin:0; font-size:0.9em; color: #bdc3c7;">Yêu cầu: {r_kpi} KPI</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.write("") # Tạo khoảng trống cho nút thẳng hàng
            if r_name == current_rank:
                st.success("🌟 Đang dùng")
            elif r_name in unlocked:
                if st.button(f"SỬ DỤNG", key=f"use_{r_name}", use_container_width=True):
                    st.session_state.data[user_id]['current_rank'] = r_name
                    save_data_func()
                    st.rerun()
            elif user_kpi >= r_kpi:
                if st.button(f"KÍCH HOẠT", key=f"active_{r_name}", use_container_width=True, type="primary"):
                    # Lưu vào danh sách đã mở và đặt làm danh hiệu hiện tại
                    if 'unlocked_ranks' not in st.session_state.data[user_id]:
                        st.session_state.data[user_id]['unlocked_ranks'] = []
                    
                    st.session_state.data[user_id]['unlocked_ranks'].append(r_name)
                    st.session_state.data[user_id]['current_rank'] = r_name
                    save_data_func()
                    st.balloons()
                    st.success(f"Chúc mừng! Bạn đã đạt danh hiệu {r_name}")
                    st.rerun()
            else:
                st.info(f"🔒 Cần thêm {r_kpi - user_kpi} KPI")
                

def trien_khai_combat_pho_ban(user_id, land_id, p_id, dungeon_config, save_data_func):
    
    # 🔥 1. CẦU DAO TỰ ĐỘNG (AUTO-KILL SWITCH) 🔥
    # Lấy tên trang hiện tại (Biến này bạn dùng để điều hướng sidebar)
    current_page = st.session_state.get("page", "")
    
    # Kiểm tra: Nếu trang hiện tại KHÔNG PHẢI là trang phó bản
    # (Bạn nhớ thay chữ "Phó bản" cho đúng với tên trong menu sidebar của bạn)
    if "Phó bản" not in current_page: 
        # Tắt ngay trạng thái đang đánh
        st.session_state.dang_danh_dungeon = False
        
        # Dọn dẹp sạch sẽ rác (biến tạm) để lần sau vào không bị lỗi
        keys_to_clean = ["dungeon_questions", "current_q_idx", "correct_count", "victory_processed"]
        for k in keys_to_clean:
            if k in st.session_state: del st.session_state[k]
            
        # Xóa các mốc thời gian
        for k in list(st.session_state.keys()):
            if k.startswith("start_time_"): del st.session_state[k]
            
        # Dừng hàm ngay lập tức, không cho chạy xuống dưới nữa
        return

    # --- PHẦN 1: KHỞI TẠO TRẠNG THÁI (CHỈ CHẠY 1 LẦN) ---
    if "dungeon_questions" not in st.session_state:
        # (Giữ nguyên logic khởi tạo của bạn)
        p_data = dungeon_config[land_id]["phases"][p_id]
        p_num = int(p_id.split('_')[1])
        difficulty_map = {1: "easy", 2: "medium", 3: "hard", 4: "extreme"}
        target_diff = p_data.get('quiz_level', difficulty_map.get(p_num, "easy"))
        
        path_quiz = f"quiz_data/grade_6/{land_id}.json"
        # Thêm try-catch để tránh lỗi nếu load_data chưa import hoặc lỗi file
        try:
            # Giả định hàm load_data có sẵn
            all_quizzes = load_data(path_quiz) 
        except:
            all_quizzes = {}

        pool = all_quizzes.get(target_diff, [])
        if not pool:
            for alt in ["extreme", "hard", "medium", "easy"]:
                pool = all_quizzes.get(alt, [])
                if pool: break
        
        num_q = p_data.get('num_questions', 5) # Mặc định 5 câu nếu thiếu config
        st.session_state.dungeon_questions = random.sample(pool, min(len(pool), num_q)) if pool else []
        st.session_state.current_q_idx = 0
        st.session_state.correct_count = 0

    # --- PHẦN 2: LOGIC ĐIỀU KHIỂN VÒNG LẶP CÂU HỎI ---
    questions = st.session_state.get("dungeon_questions", [])
    idx = st.session_state.get("current_q_idx", 0)
    
    # Bảo vệ lỗi Key nếu config chưa tải kịp
    try:
        p_data = dungeon_config[land_id]["phases"][p_id]
    except:
        st.error("Dữ liệu phó bản bị lỗi. Vui lòng thử lại sau.")
        st.session_state.dang_danh_dungeon = False
        if st.button("Thoát"): st.rerun()
        return

    if idx < len(questions):
        q = questions[idx]
        
        # 1. Tính toán thời gian
        time_limit = p_data.get('time_limit', 15)
        if f"start_time_{idx}" not in st.session_state:
            st.session_state[f"start_time_{idx}"] = time.time()
        
        elapsed = time.time() - st.session_state[f"start_time_{idx}"]
        remaining = max(0, time_limit - int(elapsed))

        # 2. Giao diện làm bài
        combat_placeholder = st.empty()
        
        with combat_placeholder.container():
            st.markdown(f"### ⚔️ PHASE {p_id.split('_')[1]}: {p_data['title']}")
            st.progress((idx) / len(questions), text=f"Tiến độ: {idx}/{len(questions)} câu")
            
            t_col1, t_col2 = st.columns([1, 4])
            with t_col1:
                # Đổi màu đồng hồ khi sắp hết giờ
                color = "red" if remaining < 5 else "black"
                st.markdown(f"<h3 style='color:{color}'>⏳ {remaining}s</h3>", unsafe_allow_html=True)

            st.markdown("""
                <style>
                div.stButton > button p { font-size: 1.5rem !important; font-weight: bold !important; }
                div.stButton > button { height: 80px !important; border-radius: 12px !important; border: 2px solid #ff4b4b !important; }
                </style>
            """, unsafe_allow_html=True)

            with st.container(border=True):
                st.markdown(f"""
                    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 10px solid #ff4b4b; font-size: 1.5em; line-height: 1.3; font-weight: bold; color: #1e1e1e;'>
                        <span style='color: #ff4b4b;'>CÂU HỎI {idx + 1}:</span><br>{q['question']}
                    </div>
                """, unsafe_allow_html=True)
                
                st.write("") 
                if 'options' in q and q['options']:
                    cols_ans = st.columns(2)
                    for i, option in enumerate(q['options']):
                        with cols_ans[i % 2]:
                            if st.button(option, key=f"btn_ans_{idx}_{i}", use_container_width=True):
                                if str(option).strip().lower() == str(q['answer']).strip().lower():
                                    st.session_state.correct_count += 1
                                    st.toast("🎯 CHÍNH XÁC!", icon="✅")
                                else:
                                    st.toast(f"❌ SAI RỒI! Đáp án là: {q['answer']}", icon="⚠️")
                                
                                st.session_state.current_q_idx += 1
                                time.sleep(0.5) # Giảm sleep xuống cho mượt
                                st.rerun()

        # 3. Xử lý hết giờ
        if remaining <= 0:
            st.error("⏰ HẾT GIỜ! Quái vật đã phản đòn.")
            time.sleep(1)
            st.session_state.current_q_idx += 1
            st.rerun()
            
        # 4. Tự động Rerun (Heartbeat)
        if remaining > 0:
            time.sleep(1)
            st.rerun()
            
    else:
        # --- PHẦN 3: TỔNG KẾT ---
        correct = st.session_state.correct_count
        required = p_data['num_questions']
        
        # --- TRƯỜNG HỢP THẮNG ---
        if correct >= required:
            if "victory_processed" not in st.session_state:
                start_game_time = st.session_state.get("start_time_0", time.time())
                duration = round(time.time() - start_game_time, 2)
                
                xử_lý_hoàn_thành_phase(user_id, land_id, p_id, dungeon_config, save_data_func, duration=duration)
                save_data_func(st.session_state.data)
                st.session_state.victory_processed = True
            
            st.success("🏆 CHIẾN THẮNG! KẺ ĐỊCH ĐÃ BỊ TIÊU DIỆT.")
            if st.button("🌟 TIẾP TỤC HÀNH TRÌNH", type="primary", use_container_width=True):
                st.session_state.dang_danh_dungeon = False
                # Xóa sạch session liên quan
                for k in list(st.session_state.keys()):
                    if k.startswith("dungeon_") or k.startswith("start_time_") or k in ["current_q_idx", "correct_count", "victory_processed"]:
                        del st.session_state[k]
                st.rerun()
        
        # --- TRƯỜNG HỢP THUA (SỬA LẠI ĐỂ TRÁNH KẸT) ---
        else:
            st.error(f"💀 GỤC NGÃ! Bạn trả lời đúng {correct}/{len(questions)} câu (Cần {required} câu).")
            
            # Chia làm 2 cột nút bấm
            c1, c2 = st.columns(2)
            
            # Nút 1: Thử lại
            with c1:
                if st.button("🔄 THỬ LẠI", use_container_width=True):
                    keys_to_reset = ["dungeon_questions", "current_q_idx", "correct_count", "victory_processed"]
                    for k in keys_to_reset:
                        if k in st.session_state: del st.session_state[k]
                    
                    # Xóa mốc thời gian cũ để tránh bị tính là hết giờ ngay
                    for key in list(st.session_state.keys()):
                        if key.startswith("start_time_"): del st.session_state[key]
                    
                    st.rerun()

            # Nút 2: RỜI KHỎI (Quan trọng để thoát kẹt)
            with c2:
                if st.button("🏳️ RỜI KHỎI", use_container_width=True):
                    st.session_state.dang_danh_dungeon = False
                    # Dọn dẹp rác
                    for k in list(st.session_state.keys()):
                        if k.startswith("dungeon_") or k.startswith("start_time_") or k in ["current_q_idx", "correct_count", "victory_processed"]:
                            del st.session_state[k]
                    st.rerun()

def reset_dungeon_state():
    """Dọn dẹp triệt để bộ nhớ để bắt đầu trận đấu mới sạch sẽ"""
    # 1. Các phím trạng thái cơ bản
    keys_to_del = ["dungeon_questions", "current_q_idx", "correct_count", "dang_danh_dungeon"]
    
    # 2. Quét và xóa tất cả các phím đếm ngược thời gian (start_time_0, start_time_1,...)
    time_keys = [k for k in st.session_state.keys() if k.startswith("start_time_")]
    keys_to_del.extend(time_keys)
    
    for k in keys_to_del:
        if k in st.session_state:
            del st.session_state[k]
            

def get_dungeon_logs(land_id):
    """
    Lọc dữ liệu vinh danh dựa trên cấu trúc data.json thực tế.
    Đã bao gồm cơ chế chống lỗi AttributeError: 'list' object has no attribute 'get'
    """
    
    # 1. KHIÊN BẢO VỆ CẤP 1: Kiểm tra data tổng
    # Nếu chưa có data hoặc data bị lỗi thành List -> Trả về rỗng ngay
    data = st.session_state.get('data', {})
    if not isinstance(data, dict):
        return []

    filtered_logs = []
    
    # Chuyển đổi land_id sang string để tìm kiếm chính xác trong JSON
    str_land_id = str(land_id)

    # 2. VÒNG LẶP AN TOÀN
    for u_id, u_info in data.items():
        
        # --- 🛡️ KHIÊN BẢO VỆ CẤP 2 (QUAN TRỌNG NHẤT) 🛡️ ---
        # Lọc bỏ các key cấu hình (như 'rank_settings', 'shop_items') 
        # và bỏ qua những user bị lỗi định dạng (đang là List)
        if u_id in ['rank_settings', 'shop_items', 'events', 'admin']:
            continue
            
        if not isinstance(u_info, dict):
            continue 
        # ---------------------------------------------------

        # 3. Lấy bảng tiến độ phó bản (An toàn tuyệt đối vì u_info chắc chắn là dict)
        progress = u_info.get('dungeon_progress', {})
        
        # Nếu progress bị lỗi (là list) thì gán lại thành dict rỗng
        if not isinstance(progress, dict):
            progress = {}
        
        # 4. KIỂM TRA ĐIỀU KIỆN LỌC
        # Kiểm tra xem user có chơi map này chưa (dùng str_land_id)
        if str_land_id in progress:
            phase_val = progress[str_land_id]
            
            # Chỉ lấy nếu Phase > 1 (Đã vượt qua ít nhất 1 ải)
            # Dùng ép kiểu int để tránh lỗi so sánh chuỗi
            try:
                if int(phase_val) > 1:
                    
                    # 5. XỬ LÝ INVENTORY (Lấy vật phẩm mới nhất)
                    inventory = u_info.get('inventory', {})
                    recent_item = "Huy hiệu Tập sự" # Mặc định

                    # Nếu inventory là Dict (chuẩn mới)
                    if isinstance(inventory, dict) and inventory:
                        try:
                            # Lấy item cuối cùng trong danh sách value
                            recent_item = list(inventory.values())[-1]
                        except:
                            pass
                    # Nếu inventory là List (chuẩn cũ - phòng hờ)
                    elif isinstance(inventory, list) and inventory:
                        recent_item = inventory[-1]

                    # 6. THÊM VÀO DANH SÁCH KẾT QUẢ
                    filtered_logs.append({
                        "name": u_info.get('name', 'Học sĩ ẩn danh'),
                        "phase": phase_val,
                        "time": u_info.get('best_time', {}).get(str_land_id, 999), # 999 là chưa có time
                        "reward_recent": recent_item
                    })
            except ValueError:
                continue # Nếu phase không phải số thì bỏ qua

    return filtered_logs
    
def get_arena_logs():
    """Lấy dữ liệu Tứ đại cao thủ và Lịch sử đấu trường"""
    # Giả sử bạn lưu lịch sử đấu trường trong st.session_state.arena_history
    history = st.session_state.get('arena_history', [])
    all_users = st.session_state.data
    
    # 1. Tính toán Tứ đại cao thủ
    win_counts = {}
    for match in history:
        # match['winners'] là danh sách tên những người thắng trong trận đó
        for winner in match.get('winners', []):
            win_counts[winner] = win_counts.get(winner, 0) + 1
            
    # Sắp xếp lấy Top 4
    top_4_raw = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)[:4]
    
    # 2. Chuẩn bị dữ liệu hiển thị
    top_4_details = []
    for name, wins in top_4_raw:
        # Tìm thêm avatar hoặc role của người đó nếu cần
        top_4_details.append({"name": name, "wins": wins})
        
    return top_4_details, history[-10:] # Trả về Top 4 và 10 trận gần nhất
    

from datetime import datetime

def save_all_to_sheets(all_data):
    """
    Hàm tổng lực: Tự động phân loại dữ liệu và đẩy lên các Tab trên Google Sheets.
    Đã tích hợp: Players, Settings (Rank), Shop và Logs.
    """
    try:
        spreadsheet = CLIENT.open(SHEET_NAME)
        
        # --- 1. ĐỒNG BỘ TAB "Players" ---
        sh_players = spreadsheet.worksheet("Players")
        headers = ["user_id", "name", "team", "password", "kpi", "exp", "level", "hp", "hp_max", "stats_json", "inventory_json", "progress_json"]
        player_rows = [headers]
        
        for uid, info in all_data.items():
            # Chỉ xử lý các key là dictionary và không phải key hệ thống
            if not isinstance(info, dict) or uid in ["rank_settings", "system_config"]:
                continue
            
            stats_keys = ["Vi_Pham", "Bonus", "KTTX", "KT Sản phẩm", "KT Giữa kỳ", "KT Cuối kỳ", "Tri_Thuc", "Chien_Tich", "Vinh_Du", "Vinh_Quang", "total_score", "titles", "best_time"]
            stats_data = {k: info.get(k, 0) for k in stats_keys}
            
            row = [
                uid,
                info.get('name', ''),
                info.get('team', 'Chưa phân tổ'),
                info.get('password', '123456'),
                info.get('kpi', 0),
                info.get('exp', 0),
                info.get('level', 1),
                info.get('hp', 100),
                info.get('hp_max', 100),
                json.dumps(stats_data, ensure_ascii=False),
                json.dumps(info.get('properties', {}), ensure_ascii=False),
                json.dumps(info.get('dungeon_progress', {}), ensure_ascii=False)
            ]
            player_rows.append(row)
        
        sh_players.clear()
        sh_players.update('A1', player_rows)

        # --- 2. ĐỒNG BỘ TAB "Settings" (Lưu Sảnh Danh Vọng) ---
        if "rank_settings" in all_data:
            try:
                sh_settings = spreadsheet.worksheet("Settings")
                settings_rows = [
                    ["Config_Key", "Value"],
                    ["rank_settings", json.dumps(all_data["rank_settings"], ensure_ascii=False)]
                ]
                sh_settings.clear()
                sh_settings.update('A1', settings_rows)
            except Exception as e:
                print(f"⚠️ Lỗi tab Settings: {e}")
        # --- 2.1 ĐỒNG BỘ BOSS (Bổ sung vào Tab Settings) ---
        if os.path.exists('data/boss_config.json'):
            try:
                with open('data/boss_config.json', 'r', encoding='utf-8') as f:
                    boss_current_data = json.load(f)
                
                sh_settings = spreadsheet.worksheet("Settings")
                # Lấy dữ liệu cũ để tránh ghi đè mất các key khác như rank_settings
                existing_settings = sh_settings.get_all_values()
                
                # Tìm xem đã có dòng active_boss chưa, nếu có thì cập nhật, chưa thì thêm mới
                boss_string = json.dumps(boss_current_data, ensure_ascii=False)
                
                # Đơn giản nhất: Ghi đè hoặc nối thêm vào cột Settings
                # Ở đây ta dùng cách an toàn: Cập nhật lại toàn bộ Settings bao gồm cả Boss
                settings_rows = [["Config_Key", "Value"]]
                if "rank_settings" in all_data:
                    settings_rows.append(["rank_settings", json.dumps(all_data["rank_settings"], ensure_ascii=False)])
                
                settings_rows.append(["active_boss", boss_string])
                
                sh_settings.clear()
                sh_settings.update('A1', settings_rows)
            except Exception as e:
                print(f"⚠️ Lỗi đồng bộ Boss lên Settings: {e}")
        # --- 3. ĐỒNG BỘ TAB "Shop" (Tiệm tạp hóa) ---
        # Lấy từ session_state vì Shop thường được quản lý riêng
        if 'shop_items' in st.session_state:
            try:
                sh_shop = spreadsheet.worksheet("Shop")
                shop_headers = ["Item_ID", "Item_Name", "Price", "Stock", "Description", "Effect_JSON"]
                shop_rows = [shop_headers]
                
                for item_id, info in st.session_state.shop_items.items():
                    row = [
                        item_id,
                        info.get('name', ''),
                        info.get('price', 0),
                        info.get('stock', 0),
                        info.get('description', ''),
                        json.dumps(info.get('effects', {}), ensure_ascii=False)
                    ]
                    shop_rows.append(row)
                
                sh_shop.clear()
                sh_shop.update('A1', shop_rows)
            except Exception as e:
                print(f"⚠️ Lỗi tab Shop: {e}")

        # --- 4. GHI LOG HOẠT ĐỘNG (Tab Logs) ---
        try:
            sh_logs = spreadsheet.worksheet("Logs")
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            sh_logs.append_row([timestamp, "SYSTEM", "Đã đồng bộ toàn bộ vương quốc lên Cloud"])
        except: 
            pass

        st.success("🌟 Toàn bộ dữ liệu Vương quốc đã được bảo vệ trên Cloud!")
        return True
        
    except Exception as e:
        st.error(f"❌ Lỗi đồng bộ Cloud: {e}")
        return False
        
def load_data_from_sheets():
    """
    Truy xuất toàn bộ dữ liệu vương quốc từ Cloud:
    1. Tab Players: Dữ liệu học sĩ.
    2. Tab Settings: Danh hiệu & Cấu hình hệ thống.
    3. Tab Shop: Vật phẩm tiệm tạp hóa.
    """
    try:
        spreadsheet = CLIENT.open(SHEET_NAME)
        new_data = {}

        # --- PHẦN 1: TẢI DỮ LIỆU HỌC SĨ (Tab Players) ---
        try:
            sh_players = spreadsheet.worksheet("Players")
            player_records = sh_players.get_all_records()
            
            for r in player_records:
                uid = str(r.get('user_id', '')).strip().lower()
                if not uid: continue
                
                # Giải mã các chuỗi JSON (stats, inventory, progress)
                try:
                    stats = json.loads(r.get('stats_json', '{}'))
                    inventory = json.loads(r.get('inventory_json', '[]'))
                    progress = json.loads(r.get('progress_json', '{}'))
                except:
                    stats, inventory, progress = {}, [], {}

                # Xây dựng cấu trúc User hoàn chỉnh
                user_info = {
                    "name": r.get('name', ''),
                    "team": r.get('team', 'Chưa phân tổ'),
                    "password": str(r.get('password', '123456')),
                    "kpi": r.get('kpi', 0),
                    "exp": r.get('exp', 0),
                    "level": r.get('level', 1),
                    "hp": r.get('hp', 100),
                    "hp_max": r.get('hp_max', 100),
                    "inventory": inventory,
                    "dungeon_progress": progress
                }
                # Đổ nốt các chỉ số phụ từ stats_json vào user_info
                user_info.update(stats)
                new_data[uid] = user_info
        except Exception as e:
            print(f"⚠️ Lỗi đọc tab Players: {e}")

        # Trong PHẦN 2 của load_data_from_sheets:
        try:
            sh_settings = spreadsheet.worksheet("Settings")
            settings_records = sh_settings.get_all_records()
            for row in settings_records:
                key = row.get('Config_Key')
                value = row.get('Value')
                if key and value:
                    decoded_val = json.loads(value)
                    new_data[key] = decoded_val
                    
                    # THÊM ĐOẠN NÀY: Nếu thấy key là active_boss, ghi đè vào file local ngay
                    if key == "active_boss":
                        with open('data/boss_config.json', 'w', encoding='utf-8') as f:
                            json.dump(decoded_val, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"ℹ️ Tab Settings chưa có Boss: {e}")

        # --- PHẦN 3: TẢI TIỆM TẠP HÓA (Tab Shop) ---
        try:
            sh_shop = spreadsheet.worksheet("Shop")
            shop_records = sh_shop.get_all_records()
            shop_dict = {}
            for r in shop_records:
                item_id = str(r.get('Item_ID', ''))
                if not item_id: continue
                
                shop_dict[item_id] = {
                    "name": r.get('Item_Name', ''),
                    "price": r.get('Price', 0),
                    "stock": r.get('Stock', 0),
                    "description": r.get('Description', ''),
                    "properties": json.loads(r.get('Effect_JSON', '{}'))
                }
            # Cập nhật trực tiếp vào session_state để các module Shop sử dụng được ngay
            st.session_state.shop_items = shop_dict
        except Exception as e:
            print(f"ℹ️ Tab Shop chưa có hoặc trống: {e}")

        if not new_data:
            return None

        print(f"📥 Cloud Sync thành công: {len(new_data)} học sĩ & {len(shop_dict) if 'shop_dict' in locals() else 0} vật phẩm.")
        return new_data

    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng khi tải dữ liệu từ Cloud: {e}")
        return None