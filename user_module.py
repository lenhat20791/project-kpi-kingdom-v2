import streamlit as st
import pandas as pd
import json
import os
import math
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

# 🔥 [QUAN TRỌNG] Thêm cache để không bị connect lại liên tục gây lag
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    try:
        # Ưu tiên 1: Lấy từ Streamlit Secrets (Online)
        gcp_info = st.secrets.get("gcp_service_account")
        if gcp_info:
            creds_dict = dict(gcp_info)
            # Fix lỗi xuống dòng trong private key
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
            client = gspread.authorize(creds)
            # print("✅ Đã kết nối Google Sheets (Online Mode)")
            return client

        # Ưu tiên 2: Lấy từ file JSON (Offline/Local)
        elif os.path.exists("service_account.json"):
            creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPE)
            client = gspread.authorize(creds)
            # print("✅ Đã kết nối Google Sheets (Local JSON)")
            return client

        else:
            st.warning("⚠️ Không tìm thấy cấu hình kết nối (Secret hoặc JSON missing)")
            return None

    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối: {e}")
        return None

# 🔥 [QUAN TRỌNG] Khởi tạo biến CLIENT toàn cục tại đây
# Để các hàm bên dưới (load_loi_dai, save_loi_dai) có thể gọi CLIENT.open(...)
CLIENT = get_gspread_client()

def ghi_log_he_thong(user_id, action, detail, note=""):
    """
    Hàm ghi log tương thích với file Sheet hiện tại (3 cột: time, user_id, action)
    """
    from datetime import datetime
    import streamlit as st
    
    # 1. Lấy thời gian
    now = datetime.now().strftime("%d/%m/%Y %H:%M") # Định dạng giống trong ảnh bạn gửi
    
    # 2. Gom nội dung lại thành 1 chuỗi để nhét vào cột 'action'
    # Kết quả sẽ kiểu: "WIN_BOSS | KPI: 100->150 | CHECK NGAY!"
    full_content = f"{action} | {detail}"
    if note:
        full_content += f" | ⚠️ {note}"
    
    print(f"📝 [LOG] {user_id} : {full_content}")

    try:
        # 3. Kết nối Google Sheet
        from user_module import get_gspread_client
        client = get_gspread_client()
        
        # Mở Sheet (Code lấy ID/URL chuẩn của bạn)
        secrets_gcp = st.secrets.get("gcp_service_account", {})
        if "spreadsheet_id" in secrets_gcp: 
            sh = client.open_by_key(secrets_gcp["spreadsheet_id"])
        elif "spreadsheet_url" in secrets_gcp: 
            sh = client.open_by_url(secrets_gcp["spreadsheet_url"])
        else: 
            sh = client.openall()[0]
            
        # 4. Ghi vào tab "Logs"
        # Lưu ý: Tab tên là "Logs" (có s) như trong ảnh bạn gửi
        try:
            wks_log = sh.worksheet("Logs")
        except:
            # Phòng hờ nếu tên tab trong code khác tên tab thực tế
            wks_log = sh.worksheet("Log") 
        
        # Ghi 3 cột: [Thời gian, UserID, Nội dung gom chung]
        wks_log.append_row([now, str(user_id), full_content])
        
    except Exception as e:
        print(f"❌ Lỗi ghi log: {e}")

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
    """
    Ghi lại lịch sử đánh Boss vào cả JSON (local) và Google Sheets (Cloud).
    """
    import json
    import os
    from datetime import datetime
    import streamlit as st
    
    # Chuẩn bị dữ liệu thời gian và phần thưởng
    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Xử lý phần thưởng thành chuỗi văn bản đẹp mắt
    if isinstance(rewards, list):
        rewards_str = ", ".join(str(x) for x in rewards)
    elif isinstance(rewards, dict):
        # Ví dụ: {"kpi": 10, "exp": 50} -> "kpi: 10, exp: 50"
        rewards_str = ", ".join([f"{k}: {v}" for k, v in rewards.items()])
    else:
        rewards_str = str(rewards)

    # --- 1. LƯU VÀO FILE JSON (BACKUP DỰ PHÒNG) ---
    log_file = 'data/boss_logs.json'
    new_log = {
        "boss_name": boss_name,
        "user_id": user_id,
        "damage": int(damage),
        "rewards": rewards_str,
        "time": thoi_gian
    }
    
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except: logs = []
            
    logs.append(new_log)
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi ghi JSON: {e}")

    # --- 2. LƯU LÊN GOOGLE SHEETS (QUAN TRỌNG) ---
    try:
        # Import hàm lấy client gspread từ user_module (đảm bảo bạn đã có hàm này)
        from user_module import get_gspread_client 
        client = get_gspread_client()
        
        # Kết nối tới Spreadsheet
        secrets_gcp = st.secrets.get("gcp_service_account", {})
        if "spreadsheet_id" in secrets_gcp: 
            sh = client.open_by_key(secrets_gcp["spreadsheet_id"])
        elif "spreadsheet_url" in secrets_gcp: 
            sh = client.open_by_url(secrets_gcp["spreadsheet_url"])
        else: 
            sh = client.openall()[0]

        # Tìm Tab BossLogs
        try:
            wks = sh.worksheet("BossLogs")
        except:
            # Nếu chưa có thì tạo mới luôn (Optional)
            wks = sh.add_worksheet(title="BossLogs", rows=1000, cols=10)
            wks.append_row(["Thời gian", "Tên Boss", "User ID", "Sát thương", "Phần thưởng"])

        # Ghi dòng mới vào cuối bảng
        # Thứ tự cột: [Thời gian, Boss, User, Damage, Rewards]
        row_data = [
            thoi_gian,
            str(boss_name),
            str(user_id),
            int(damage),
            rewards_str
        ]
        
        wks.append_row(row_data)
        # print("✅ Đã ghi log Boss lên Google Sheet.")
        
    except Exception as e:
        # Nếu lỗi mạng hoặc lỗi Sheet thì chỉ báo lỗi ở server log, không làm crash game
        print(f"⚠️ Không thể ghi log lên Google Sheet: {e}")
        
# ------------------------------------------------------------------------------
# CÁC HÀM HỖ TRỢ CHỢ ĐEN (MARKET) - GOOGLE SHEETS SYNC
# ------------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def load_market():
    """
    Tải dữ liệu Chợ Đen từ Tab 'Market' trên Google Sheets.
    """
    default_data = {"listings": {}}
    
    try:
        # 1. Kết nối Google Sheets
        try:
            sh = CLIENT.open(SHEET_NAME).worksheet("Market")
        except:
            # Nếu chưa có tab Market, tạo mới
            sh = CLIENT.open(SHEET_NAME).add_worksheet(title="Market", rows=100, cols=10)
            sh.append_row(["Listing_ID", "Full_JSON_Data", "Status", "Created_At"])
            return default_data

        # 2. Lấy dữ liệu
        rows = sh.get_all_values()
        if len(rows) <= 1:
            return default_data

        listings = {}
        # Cấu trúc: [0] ID | [1] JSON | [2] Status | [3] Date
        for r in rows[1:]:
            try:
                if len(r) < 2: continue
                lid = r[0]
                # Giải nén JSON
                l_info = json.loads(r[1])
                listings[lid] = l_info
            except Exception as e:
                print(f"Lỗi đọc dòng Market ({lid}): {e}")
                continue
        
        return {"listings": listings}

    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối Chợ Đen Cloud: {e}")
        return default_data

def save_market(market_data):
    """
    Lưu dữ liệu Chợ Đen lên Tab 'Market' & Xóa Cache.
    """
    try:
        sh = CLIENT.open(SHEET_NAME).worksheet("Market")
        
        # Chuẩn bị dữ liệu
        rows_to_write = [["Listing_ID", "Full_JSON_Data", "Status", "Created_At"]]
        listings = market_data.get('listings', {})
        
        for lid, info in listings.items():
            json_str = json.dumps(info, ensure_ascii=False)
            status = "active"
            created = info.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            rows_to_write.append([str(lid), json_str, status, created])
            
        # Ghi đè & Xóa Cache
        sh.clear()
        sh.update('A1', rows_to_write)
        
        # Xóa cache để lần load sau thấy dữ liệu mới
        load_market.clear()
        
    except Exception as e:
        st.error(f"❌ Không thể lưu Chợ Đen lên Cloud: {e}")

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
    # Import thư viện cần thiết ngay trong hàm
    import uuid
    from datetime import datetime
    
    # 1. Tải dữ liệu từ Cloud (có Cache)
    market_data = load_market()
    user_data = st.session_state.data.get(current_user_id, {})
    
    # Giả định hàm lấy map ảnh đã có trong user_module (hoặc định nghĩa tạm ở đây)
    try:
        item_image_map = get_item_image_map() 
    except:
        item_image_map = {} # Fallback nếu hàm chưa tồn tại

    # --- 2. CSS (Giữ nguyên giao diện đẹp của bạn) ---
    st.markdown("""
        <style>
        .market-card {
            background: linear-gradient(135deg, #1e1e2e 0%, #252538 100%);
            border: 1px solid #45475a; border-radius: 20px; padding: 20px;
            margin-bottom: 20px; position: relative; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: all 0.3s ease; overflow: hidden;
        }
        .market-card:hover { transform: translateY(-5px); border-color: #f9e2af; box-shadow: 0 10px 20px rgba(249, 226, 175, 0.15); }
        .item-real-image { width: 100px; height: 100px; object-fit: contain; border-radius: 10px; margin: 0 auto 10px auto; display: block; background-color: rgba(255,255,255,0.05); padding: 5px; border: 1px dashed #585b70; }
        .item-fallback-icon { font-size: 80px; text-align: center; margin-bottom: 10px; filter: drop-shadow(0 0 5px rgba(255,255,255,0.2)); }
        .item-title { color: #cdd6f4; font-size: 18px; font-weight: 800; text-align: center; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }
        .seller-info { color: #bac2de; font-size: 13px; text-align: center; margin-bottom: 15px; }
        .price-badge { background: rgba(249, 226, 175, 0.1); color: #f9e2af; border: 1px solid #f9e2af; padding: 5px 20px; border-radius: 50px; font-weight: bold; font-size: 16px; }
        .my-item-badge { position: absolute; top: 10px; right: 10px; background: linear-gradient(45deg, #a6da95, #8bd5ca); color: #1e1e2e; font-size: 10px; font-weight: 900; padding: 4px 8px; border-radius: 6px; z-index: 5; }
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
            # Chuyển listings thành list để enumerate dễ dàng
            listing_items = list(listings.items())
            
            for idx, (item_id, info) in enumerate(listing_items):
                is_mine = info['seller_id'] == current_user_id
                item_name = info.get('item_name', 'Vật phẩm')
                
                # --- XỬ LÝ ẢNH ---
                real_image_url = item_image_map.get(item_name)
                
                if real_image_url:
                    image_html = f'<img src="{real_image_url}" class="item-real-image" alt="{item_name}">'
                else:
                    # Fallback icon đơn giản nếu chưa có hàm get_fallback_icon
                    try:
                        fallback = get_fallback_icon(item_name)
                    except:
                        fallback = "📦"
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
                                # Trả đồ về kho
                                st.session_state.data[current_user_id].setdefault('inventory', []).append(item_name)
                                # Xóa listing
                                del market_data['listings'][item_id]
                                
                                # LƯU ĐỒNG BỘ CLOUD
                                save_market(market_data)
                                save_data_func(st.session_state.data)
                                st.rerun()
                    else:
                        if st.button(f"💸 MUA NGAY", key=f"buy_{item_id}", use_container_width=True, type="primary"):
                            price = float(info['price'])
                            if user_data.get('kpi', 0) >= price:
                                # 1. Trừ tiền người mua
                                st.session_state.data[current_user_id]['kpi'] -= price
                                
                                # 2. Cộng tiền người bán (90%)
                                seller_id = info['seller_id']
                                if seller_id in st.session_state.data:
                                    st.session_state.data[seller_id]['kpi'] += (price * 0.9)
                                
                                # 3. Chuyển đồ
                                st.session_state.data[current_user_id].setdefault('inventory', []).append(item_name)
                                del market_data['listings'][item_id]
                                
                                # 4. LƯU ĐỒNG BỘ CLOUD (Cả Market và Player Data)
                                save_market(market_data)
                                save_data_func(st.session_state.data)
                                
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Không đủ KPI!")

    # --- TAB 2: TREO BÁN ---
    with tab2:
        st.markdown("### 🎒 Kho đồ & Niêm yết")
        # Xử lý inventory: hỗ trợ cả List và Dict
        raw_inv = user_data.get('inventory', [])
        inventory_list = []
        if isinstance(raw_inv, list):
            inventory_list = raw_inv
        elif isinstance(raw_inv, dict):
            inventory_list = list(raw_inv.values())

        if not inventory_list:
            st.info("Kho đồ trống.")
        else:
            from collections import Counter
            counts = Counter(inventory_list)
            
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.write("**Vật phẩm đang có:**")
                for item, count in counts.items():
                    img_url = item_image_map.get(item)
                    
                    if img_url:
                        icon_display = f'<img src="{img_url}" style="width:30px; height:30px; object-fit:contain; vertical-align:middle; margin-right:10px; border-radius:4px;">'
                    else:
                        try:
                            fallback = get_fallback_icon(item)
                        except:
                            fallback = "📦"
                        icon_display = f'<span style="font-size: 24px; vertical-align:middle; margin-right:10px;">{fallback}</span>'
                    
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #45475a; display: flex; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center;">
                            {icon_display}
                            <b style="color: #e0e0e0; font-size: 15px;">{item}</b>
                        </div>
                        <span style="background: #313244; color: #a6adc8; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: bold;">x{count}</span>
                    </div>
                    """, unsafe_allow_html=True)
            
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
                        
                        # Xóa 1 item khỏi kho (Hỗ trợ list)
                        # Nếu dùng Dict inventory, logic sẽ phức tạp hơn chút, ở đây giả định list
                        if item_to_sell in st.session_state.data[current_user_id].setdefault('inventory', []):
                             st.session_state.data[current_user_id]['inventory'].remove(item_to_sell)
                        
                        # LƯU ĐỒNG BỘ CLOUD
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
    # 1. Load Config
    if 'dungeon_config_data' in st.session_state:
        dungeon_config = st.session_state.dungeon_config_data
    else:
        dungeon_config = st.session_state.get('system_config', {}).get('dungeon_data', {}) 

    user_info = st.session_state.data[user_id]
    
    # 2. TẠO MỘT KHUNG CHỨA DUY NHẤT (QUAN TRỌNG)
    # Mọi thứ sẽ chỉ được vẽ vào trong khung này.
    main_placeholder = st.empty()

    # =========================================================================
    # TRƯỜNG HỢP A: ĐANG ĐÁNH QUÁI (COMBAT)
    # =========================================================================
    if st.session_state.get("dang_danh_dungeon") is True:
        with main_placeholder.container(): # <--- Vẽ vào khung
            land_id = st.session_state.get('selected_land')
            p_id = st.session_state.get('selected_phase_id')
            
            # Gọi hàm chiến đấu
            trien_khai_combat_pho_ban(user_id, land_id, p_id, dungeon_config, save_data_func)
            
            # Nút Rút lui
            if st.sidebar.button("🚩 RÚT LUI KHỎI PHÓ BẢN"):
                st.session_state.dang_danh_dungeon = False
                st.rerun()

    # =========================================================================
    # TRƯỜNG HỢP B: ĐANG CHỌN PHÓ BẢN (MENU)
    # =========================================================================
    else:
        with main_placeholder.container(): # <--- Vẽ vào khung (sẽ đè mất cái cũ nếu có)
            st.title("🏹 PHIÊU LƯU PHÓ BẢN")
            
            # Hiển thị chỉ số
            atk = tinh_atk_tong_hop(user_info)
            col1, col2, col3 = st.columns(3)
            col1.metric("Cấp độ", f"Lv.{user_info.get('level', 1)}")
            col2.metric("Sức mạnh (ATK)", atk)
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

            # Callback chuyển trạng thái
            def vao_tran_callback(r_id):
                st.session_state.dang_danh_dungeon = True
                st.session_state.selected_land = r_id
                if 'dungeon_progress' not in user_info: user_info['dungeon_progress'] = {}
                prog = user_info['dungeon_progress'].get(r_id, 1)
                st.session_state.selected_phase_id = f"phase_{prog}"

            # Vẽ nút chọn
            cols = st.columns(3)
            for i, region in enumerate(vung_dat):
                with cols[i % 3]:
                    st.markdown(f"""
                        <div style="background:{region['color']}; padding:15px; border-radius:10px; text-align:center; color:white; margin-bottom: 10px;">
                            <h1 style='margin:0;'>{region['icon']}</h1>
                            <b>{region['name']}</b>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.button(
                        f"Vào {region['name']}", 
                        key=f"btn_{region['id']}", 
                        use_container_width=True,
                        on_click=vao_tran_callback,
                        args=(region['id'],)
                    )
            

def hien_thi_sanh_pho_ban_hoc_si(user_id, save_data_func): # <--- Thêm tham số save_data_func
    # Kiểm tra trạng thái trang để tắt combat nếu cần
    current_page = st.session_state.get("page", "")
    if "Phó bản" not in current_page and st.session_state.get("dang_danh_dungeon"):
        st.session_state.dang_danh_dungeon = False
        st.rerun()
        return

    # Load Config (Cách an toàn)
    from admin_module import load_dungeon_config
    d_config = load_dungeon_config()
    
    # --- 🔥 TẠO KHUNG CHỨA DUY NHẤT (CHÌA KHÓA FIX LỖI) 🔥 ---
    # Mọi giao diện sẽ được vẽ vào trong 'main_placeholder' này.
    # Khi trạng thái đổi, cái cũ sẽ bị xóa sạch, không bao giờ bị chồng.
    main_placeholder = st.empty()

    # ==========================================================
    # TRƯỜNG HỢP A: ĐANG CHIẾN ĐẤU (COMBAT MODE)
    # ==========================================================
    if st.session_state.get("dang_danh_dungeon"):
        with main_placeholder.container(): # Vẽ vào khung
            land_id = st.session_state.get('selected_land')
            p_id = st.session_state.get('selected_phase_id')
            
            # Gọi hàm combat (Dùng save_data_func đã truyền vào)
            trien_khai_combat_pho_ban(user_id, land_id, p_id, d_config, save_data_func)

    # ==========================================================
    # TRƯỜNG HỢP B: ĐANG Ở SẢNH CHỜ (MENU MODE)
    # ==========================================================
    else:
        with main_placeholder.container(): # Vẽ vào khung (Cái cũ tự mất)
            user_info = st.session_state.data.get(user_id)
            
            # Khởi tạo tiến độ
            if 'dungeon_progress' not in user_info:
                user_info['dungeon_progress'] = {"toan": 1, "van": 1, "anh": 1, "ly": 1, "hoa": 1, "sinh": 1}
            
            if 'viewing_land_id' not in st.session_state:
                st.session_state.viewing_land_id = "toan"

            # --- HEADER ---
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
            
            # Grid chọn vùng đất (Callback để chuyển tab mượt mà)
            def change_land_callback(lid):
                st.session_state.viewing_land_id = lid

            row1 = st.columns(3)
            row2 = st.columns(3)
            for idx, (lid, lname) in enumerate(maps_data):
                col = row1[idx] if idx < 3 else row2[idx - 3]
                is_active = (st.session_state.viewing_land_id == lid)
                
                # Dùng on_click để xử lý mượt hơn
                col.button(
                    lname, 
                    key=f"btn_map_{lid}", 
                    use_container_width=True, 
                    type="primary" if is_active else "secondary",
                    on_click=change_land_callback,
                    args=(lid,)
                )

            land_id = st.session_state.viewing_land_id
            full_names = {m[0]: m[1] for m in maps_data}
            selected_name = full_names.get(land_id, "Vùng đất bí ẩn")

            # --- THÔNG TIN PHASE ---
            current_phase_num = user_info['dungeon_progress'].get(land_id, 1)
            
            # Xử lý khi phá đảo
            if current_phase_num > 4:
                st.success(f"🏆 Bạn đã phá đảo {selected_name}!")
                if st.button("🔄 Thách thức lại Phase 4 (BOSS)"): 
                    current_phase_num = 4
                else:
                    return # Dừng vẽ nếu đã phá đảo và không muốn đánh lại

            p_id = f"phase_{current_phase_num}"
            
            # Kiểm tra dữ liệu config
            if land_id not in d_config or p_id not in d_config[land_id]["phases"]:
                st.warning(f"🚧 Dữ liệu {selected_name} đang được xây dựng. Vui lòng quay lại sau!")
                return # Dừng vẽ để không lỗi

            p_data = d_config[land_id]["phases"][p_id]
            st.divider()

            # Hiển thị Chi tiết (Ảnh & Info)
            col1, col2 = st.columns([1, 1.5])
            with col1:
                st.markdown(f"""
                    <div style="border: 4px solid #2c3e50; border-radius: 15px; overflow: hidden; background: white; text-align: center; padding-top: 10px;">
                        <img src="{p_data.get('monster_img', '')}" style="width: 60%; display: block; margin: 0 auto;">
                        <div style="background: #2c3e50; color: white; text-align: center; padding: 8px; margin-top: 10px;">
                            <b>👾 {p_data.get('monster_name', 'Quái Vật')}</b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                    <div style="background: #fdfefe; padding: 20px; border-radius: 15px; border-left: 8px solid #e74c3c; box-shadow: 2px 2px 8px rgba(0,0,0,0.05);">
                        <h3 style="margin:0; color: #c0392b;">🚩 PHASE {current_phase_num}: {p_data.get('title', 'Thử thách')}</h3>
                        <div style="margin-top: 15px;">
                            <p>⚔️ <b>Độ khó:</b> {str(p_data.get('quiz_level', 'easy')).upper()}</p>
                            <p>⏳ <b>Thời gian:</b> {p_data.get('time_limit', 15)} giây/câu</p>
                            <p>📝 <b>Nhiệm vụ:</b> Trả lời đúng {p_data.get('num_questions', 5)} câu</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.write("")
                st.markdown("##### 🎁 PHẦN THƯỞNG:")
                rew_c1, rew_c2, rew_c3 = st.columns(3)
                rew_c1.metric("KPI", f"+{p_data.get('reward_kpi', 0)}")
                rew_c2.metric("EXP", f"+{p_data.get('reward_exp', 0)}")
                rew_c3.markdown(f"📦 **{p_data.get('item_drop_id', 'Không')}**")

            # --- NÚT BẮT ĐẦU (Callback) ---
            st.write("")
            _, col_btn, _ = st.columns([1, 2, 1])
            
            def start_combat_callback(lid, pid):
                # Dọn dẹp session
                for k in list(st.session_state.keys()):
                    if k in ["dungeon_questions", "current_q_idx", "correct_count", "victory_processed"] or k.startswith("start_time_"):
                        del st.session_state[k]
                
                # Set trạng thái
                st.session_state.dang_danh_dungeon = True
                st.session_state.selected_land = lid 
                st.session_state.selected_phase_id = pid
            
            with col_btn:
                target_phase_id = f"phase_{current_phase_num}"
                st.button(
                    f"⚔️ TIẾN VÀO {selected_name.upper()}", 
                    use_container_width=True, 
                    type="primary",
                    on_click=start_combat_callback,
                    args=(land_id, target_phase_id)
                )
def xử_lý_hoàn_thành_phase(user_id, land_id, phase_id, dungeon_config, save_data_func, duration=None):
    import random
    
    # 1. Lấy data người chơi
    if user_id not in st.session_state.data: return
    user_info = st.session_state.data[user_id]
    
    # Lấy thông tin phase an toàn
    try:
        p_data = dungeon_config[land_id]["phases"][phase_id]
    except:
        return 

    # 2. Đảm bảo các chỉ số cơ bản tồn tại
    for field in ['exp', 'level', 'kpi', 'inventory', 'hp']:
        if field not in user_info:
            user_info[field] = 0 if field != 'inventory' else []
    
    old_lv = user_info.get('level', 1)
    old_atk = tinh_atk_tong_hop(user_info)
    old_hp_max = 100 + (old_lv * 20) 
    user_info['hp_max'] = old_hp_max 
    
    # ==========================================================
    # 🔥 KHẮC PHỤC LỖI Attribute Error (QUAN TRỌNG NHẤT) 🔥
    # ==========================================================
    # Bước 1: Lấy dữ liệu ra một biến tạm
    raw_best_time = user_info.get('best_time')

    # Bước 2: Kiểm tra kiểu dữ liệu của biến tạm
    # Nếu nó không phải là Dict (nó là None, hoặc List, hoặc rỗng...) -> Reset ngay
    if not isinstance(raw_best_time, dict):
        raw_best_time = {} 
        user_info['best_time'] = raw_best_time # Lưu ngược lại vào data gốc để sửa lỗi vĩnh viễn
    
    # Từ giờ, ta chỉ thao tác với biến 'raw_best_time' (chắc chắn là Dict)
    # ==========================================================

    # 3. Logic so sánh và lưu kỷ lục
    if duration is not None:
        # Dùng raw_best_time thay vì user_info['best_time'] để tránh lỗi
        old_record = raw_best_time.get(land_id, 999)
        
        if duration < old_record:
            raw_best_time[land_id] = duration # Cập nhật vào biến tạm (nó tham chiếu tới data gốc)
            st.toast(f"🔥 KỶ LỤC MỚI: {duration}s!", icon="🏆")
        else:
            st.write(f"⏱️ Thời gian hoàn thành: {duration}s (Kỷ lục hiện tại: {old_record}s)")
    
    # 4. Cộng thưởng
    user_info['kpi'] += p_data.get('reward_kpi', 0)
    user_info['exp'] += p_data.get('reward_exp', 0)
    
    # 5. Tính Level mới
    new_lv = 1 + (user_info['exp'] // 100)
    user_info['level'] = new_lv
    new_atk = tinh_atk_tong_hop(user_info)
    new_hp_max = 100 + (new_lv * 20)
    user_info['hp'] = new_hp_max 

    # 6. Loot đồ
    loot_msg = "Không có"
    item_id = p_data.get('item_drop_id', "none")
    if item_id not in ["none", "Không rơi đồ"]:
        if random.randint(1, 100) <= p_data.get('drop_rate', 0):
            inv = user_info.get('inventory')
            if not isinstance(inv, list): 
                inv = []
                user_info['inventory'] = inv
            inv.append(item_id)
            loot_msg = f"📦 {item_id}"

    # 7. Hiển thị kết quả
    st.write("---")
    st.subheader("🎁 PHẦN THƯỞNG CHIẾN THẮNG")
    c1, c2, c3 = st.columns(3)
    c1.metric("KPI Nhận", f"+{p_data.get('reward_kpi', 0)}")
    c2.metric("EXP Nhận", f"+{p_data.get('reward_exp', 0)}")
    c3.metric("Vật phẩm", loot_msg)

    # 8. Hiệu ứng Level Up
    if new_lv > old_lv:
        st.balloons()
        st.toast(f"🎊 LEVEL UP! Cấp {new_lv}", icon="🆙")
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f1c40f, #f39c12); padding: 15px; border-radius: 10px; color: white; text-align: center;">
            <h3>🎊 LÊN CẤP {new_lv} 🎊</h3>
            <p>HP: {old_hp_max} ➔ {new_hp_max} | ATK: {old_atk} ➔ {new_atk}</p>
        </div>
        """, unsafe_allow_html=True)

    # 9. Cập nhật tiến trình
    try: current_p_num = int(phase_id.split("_")[1]) 
    except: current_p_num = 1
    
    # Fix luôn lỗi tiềm ẩn cho dungeon_progress
    raw_prog = user_info.get('dungeon_progress')
    if not isinstance(raw_prog, dict):
        raw_prog = {}
        user_info['dungeon_progress'] = raw_prog
    
    actual_progress = raw_prog.get(land_id, 1)

    if current_p_num == actual_progress:
        if current_p_num < 4:
            raw_prog[land_id] = current_p_num + 1
    # ======================================================
    # 🕵️‍♂️ ĐẶT MÁY GHI ÂM TẠI ĐÂY (LOGGING)
    # ======================================================
    kpi_sau = user_info.get('kpi', 0)
    bonus_sau = user_info.get('Bonus', 0)
    
    log_detail = f"KPI: {kpi_truoc}->{kpi_sau} (+{kpi_nhan}) | EXP: +{exp_nhan} | Item: {loot_msg}"
    log_note = ""
    
    # BẮT QUẢ TANG NẾU BONUS TĂNG
    if bonus_sau > bonus_truoc:
        log_detail += f" | ⚠️ BONUS TĂNG BẤT THƯỜNG: {bonus_truoc}->{bonus_sau}"
        log_note = "CHECK NGAY! Có code lạ cộng Bonus."
    else:
        log_detail += f" | Bonus giữ nguyên: {bonus_sau}"

    # Ghi log
    ghi_log_he_thong(user_id, f"WIN_PHASE_{land_id}", log_detail, log_note)
    # ======================================================
    # Lưu dữ liệu
    save_data_func(st.session_state.data)

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
        


# Đường dẫn file backup (đảm bảo biến này đã được khai báo ở đầu file user_module)
# DATA_FILE_PATH = 'data/data.json' 

def load_data(file_path=DATA_FILE_PATH):
    try:
        # Chỉ tải từ Sheets
        cloud_data = load_data_from_sheets()
        
        if cloud_data:
            st.session_state['data_source'] = 'cloud'
            # KHÔNG tự tạo thêm bất kỳ "Administrator" nào ở đây nữa
            return cloud_data
        else:
            st.error("⛔ Dữ liệu từ Google Sheets đang trống hoặc lỗi kết nối!")
            return {} # Trả về rỗng để hệ thống dừng lại

    except Exception as e:
        st.error(f"❌ Lỗi load_data: {e}")
        return {}
        
@st.dialog("🏆 CHIẾN THẮNG VINH QUANG!", width="large")
def hien_thi_popup_chien_thang():
    """Hiển thị Popup nhận thưởng bắt buộc"""
    
    # Lấy dữ liệu từ session
    data = st.session_state.get("boss_victory_data", {})
    rewards = data.get("rewards", [])
    dmg = data.get("damage", 0)
    
    st.balloons()
    
    st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/512/744/744922.png" width="120" style="margin-bottom: 20px;">
            <h2 style="color: #2ecc71; margin: 0;">BOSS ĐÃ BỊ HẠ GỤC!</h2>
            <p style="color: #bdc3c7; font-size: 18px;">Bạn đã tung đòn kết liễu xuất sắc!</p>
            <hr>
            <h3 style="color: #f1c40f;">🎁 PHẦN THƯỞNG CỦA BẠN</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Hiển thị danh sách quà đẹp mắt
    if rewards:
        for item in rewards:
            st.markdown(f"""
                <div style="background: #2c3e50; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 5px solid #f1c40f; color: white; font-weight: bold;">
                    {item}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Không có phần thưởng nào được ghi nhận.")
        
    st.markdown(f"<p style='text-align: center; color: #95a5a6; margin-top: 15px;'>Tổng sát thương đóng góp: <b>{dmg}</b></p>", unsafe_allow_html=True)

    # Nút xác nhận duy nhất để đóng popup
    if st.button("✅ NHẬN VẬT PHẨM VÀO TÚI", type="primary", use_container_width=True):
        # Xóa dữ liệu popup để không hiện lại
        if "boss_victory_data" in st.session_state:
            del st.session_state.boss_victory_data
        st.rerun()

def tinh_va_tra_thuong_global(killer_id, all_data):
    """
    Tính thưởng Boss.
    [FIX FINAL] Bỏ Top 5 + Fix lỗi Inventory (Dict -> List).
    """
    import random
    
    sys_conf = all_data.get('system_config', {})
    boss = sys_conf.get('active_boss')
    if not boss: return [], 0
    
    contributions = boss.get("contributions", {})
    if not contributions: return [], 0

    # Tìm MVP (Người gây sát thương cao nhất)
    mvp_id = max(contributions, key=contributions.get) 

    killer_rewards_display = [] 
    killer_total_dmg = 0

    # Duyệt qua từng người tham gia
    for uid, damage in contributions.items():
        if uid not in all_data: continue
        player = all_data[uid]
        player_rewards = [] 

        # =========================================================
        # 🔥 1. CHUẨN HÓA TÚI ĐỒ (FIX LỖI APPEND)
        # =========================================================
        if 'inventory' not in player or player['inventory'] is None:
            player['inventory'] = []
            
        # Nếu đang là Dict (kiểu cũ) -> Ép sang List (kiểu mới)
        if isinstance(player['inventory'], dict):
            flat_list = []
            for item_name, count in player['inventory'].items():
                try:
                    # Nhân bản item theo số lượng (VD: {'Tao': 2} -> ['Tao', 'Tao'])
                    flat_list.extend([item_name] * int(count))
                except: pass
            player['inventory'] = flat_list
            
        # Đảm bảo chắc chắn là List
        if not isinstance(player['inventory'], list):
            player['inventory'] = []
        # =========================================================

        # --- 2. TÍNH KPI/EXP CƠ BẢN ---
        k_rate = boss.get('kpi_rate', 1.0)
        e_rate = boss.get('exp_rate', 5.0)
        
        kpi_bonus = round((damage / 1000) * k_rate, 2)
        exp_bonus = round((damage / 1000) * e_rate, 2)
        
        if kpi_bonus < 0.1: kpi_bonus = 0.1
        if exp_bonus < 0.5: exp_bonus = 0.5

        player['kpi'] = round(player.get('kpi', 0) + kpi_bonus, 2)
        player['exp'] = round(player.get('exp', 0) + exp_bonus, 2)
        
        player_rewards.append(f"💰 +{kpi_bonus} KPI")
        player_rewards.append(f"✨ +{exp_bonus} EXP")

        # --- 3. QUÀ KẾT LIỄU (LAST HIT) ---
        # Chỉ người kết liễu mới nhận được Rương Báu
        if str(uid) == str(killer_id):
            player['inventory'].append("Rương Báu")
            player_rewards.append("🎁 Rương Báu (Thưởng Kết Liễu)")

        # --- 4. DROP NGẪU NHIÊN (Cho tất cả) ---
        drop_table = boss.get('drop_table', [])
        if drop_table:
            weights = [item.get('rate', 0) for item in drop_table]
            if weights and sum(weights) > 0:
                chosen = random.choices(drop_table, weights=weights, k=1)[0]
                
                if chosen.get('type') == 'item':
                    amt = chosen.get('amount', 1)
                    iname = chosen.get('id', 'Vật phẩm')
                    for _ in range(amt):
                        player['inventory'].append(iname)
                    player_rewards.append(f"📦 {iname} (x{amt})")
                    
                elif chosen.get('type') == 'currency':
                     target = chosen.get('id', 'Tri_Thuc')
                     player[target] = player.get(target, 0) + chosen.get('amount', 1)
                     player_rewards.append(f"📘 +{chosen['amount']} {target}")

        # --- 5. THƯỞNG DANH HIỆU MVP ---
        if str(uid) == str(mvp_id):
            player['kpi'] += 50
            player['exp'] += 100
            player_rewards.append(f"👑 MVP: +50 KPI & +100 EXP")

        # Bonus KPI thêm cho Last Hit
        if str(uid) == str(killer_id):
            bonus_kill_kpi = 20.0
            player['kpi'] += bonus_kill_kpi
            player_rewards.append(f"🗡️ Bonus Last Hit: +{bonus_kill_kpi} KPI")

        # Check level
        try: check_up_level(player) 
        except: pass

        # Lưu log hiển thị Popup
        if str(uid) == str(killer_id):
            killer_rewards_display = player_rewards
            killer_total_dmg = damage

    sys_conf['active_boss'] = None 
    return killer_rewards_display, killer_total_dmg

# ==============================================================================
# 1. POPUP KẾT QUẢ MỞ RƯƠNG (Giao diện của bạn + Logic mới)
# ==============================================================================
@st.dialog("🎁 KHO BÁU VẬT PHẨM")
def popup_ket_qua_mo_ruong(chest_name, rewards):
    """
    Hiển thị kết quả mở rương.
    """
    # Header đẹp mắt
    st.markdown(f"""
        <div style="text-align: center; padding-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/512/9336/9336056.png" width="120">
            <h2 style="color: #f1c40f; margin: 10px 0;">CHÚC MỪNG!</h2>
            <p style="font-size: 1.1em; color: #bdc3c7;">Bạn đã mở <b>{chest_name}</b> thành công!</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.write("### 💎 Phần thưởng nhận được:")

    # Lấy thông tin shop để map ảnh (nếu có)
    shop_data = st.session_state.data.get('shop_items', {})

    if not rewards:
        st.warning("💨 Rương trống rỗng... Chúc may mắn lần sau!")
    else:
        for r in rewards:
            # Xử lý thông tin hiển thị
            msg = r['msg']
            r_type = r['type']
            r_val = r['val']
            
            # Mặc định icon
            icon_url = "https://cdn-icons-png.flaticon.com/512/1170/1170456.png"
            label_color = "#f1c40f" # Vàng

            # Nếu là tiền tệ
            if r_type in ['kpi', 'exp']:
                if r_type == 'kpi': 
                    icon_url = "https://cdn-icons-png.flaticon.com/512/272/272525.png"
                    label_color = "#00d2ff" # Xanh
                else:
                    icon_url = "https://cdn-icons-png.flaticon.com/512/616/616490.png"
                    label_color = "#9b59b6" # Tím
            
            # Nếu là Item -> Lấy ảnh từ Shop Data
            elif r_type == 'item':
                if str(r_val) in shop_data:
                    icon_url = shop_data[str(r_val)].get('image', icon_url)
                label_color = "#e67e22" # Cam

            # Render Card
            st.markdown(f"""
                <div style="display: flex; align-items: center; background: rgba(255,255,255,0.05); 
                            padding: 12px; border-radius: 12px; margin-bottom: 10px; border-left: 5px solid {label_color};">
                    <img src="{icon_url}" width="45" style="margin-right: 15px; border-radius: 8px; object-fit: contain;">
                    <div>
                        <b style="font-size: 1.1em; color: {label_color};">{msg}</b><br>
                        <span style="color: #95a5a6; font-size: 0.9em;">Đã thêm vào túi đồ</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.divider()
    if st.button("🧧 NHẬN QUÀ & ĐÓNG", use_container_width=True, type="primary"):
        if "gacha_result" in st.session_state:
            del st.session_state.gacha_result
        st.rerun()

# ==============================================================================
# 2. LOGIC MỞ RƯƠNG (Backend - Dùng Admin Config)
# ==============================================================================
def xu_ly_mo_ruong(user_id, item_name, item_info, all_data, save_func):
    """
    Xử lý mở rương: Trừ kho -> Random quà từ System Config -> Cộng quà -> Lưu.
    """
    user_info = all_data[user_id]
    sys_config = all_data.get('system_config', {})
    
    # 1. Trừ 1 rương khỏi kho (Hỗ trợ cả List và Dict)
    inventory = user_info.get('inventory', {})
    
    # Chuyển List -> Dict nếu cần (Backward compatibility)
    if isinstance(inventory, list):
        temp = {}
        for i in inventory: temp[i] = temp.get(i, 0) + 1
        inventory = temp
        
    # Trừ rương
    if inventory.get(item_name, 0) > 0:
        inventory[item_name] -= 1
        if inventory[item_name] <= 0:
            del inventory[item_name]
    
    # Lưu lại inventory dạng Dict chuẩn
    user_info['inventory'] = inventory
    
    # 2. Lấy cấu hình quà (Loot Table) từ Admin
    rewards_pool = sys_config.get('chest_rewards', [])
    
    # Fallback nếu chưa có cấu hình
    if not rewards_pool:
        rewards_pool = [
            {"type": "kpi", "val": 10, "rate": 50, "msg": "💰 10 KPI"},
            {"type": "exp", "val": 50, "rate": 50, "msg": "✨ 50 EXP"}
        ]
    
    # 3. Quay thưởng (Weighted Random - Chọn 1 món)
    # Nếu bạn muốn Rương mở ra nhiều món, có thể dùng logic loop như code cũ của bạn.
    # Ở đây tôi dùng logic "Chọn 1 món theo trọng số" (Gacha chuẩn).
    weights = [int(r.get('rate', 1)) for r in rewards_pool]
    
    # Chọn ngẫu nhiên 1 phần thưởng dựa trên tỷ lệ
    chosen = random.choices(rewards_pool, weights=weights, k=1)[0]
    
    # 4. Cộng quà
    r_type = chosen['type']
    r_val = chosen['val']
    
    if r_type == 'kpi':
        user_info['kpi'] = user_info.get('kpi', 0) + int(r_val)
    elif r_type == 'exp':
        user_info['exp'] = user_info.get('exp', 0) + int(r_val)
    elif r_type == 'item':
        # Cộng item vào túi
        iname = str(r_val)
        inventory[iname] = inventory.get(iname, 0) + 1
        
    # 5. Lưu dữ liệu
    save_func(all_data)
    
    # Trả về list chứa món quà đã nhận để hiển thị
    return [chosen]
import streamlit as st
from datetime import datetime, timedelta
# Các hàm load_data, tinh_chi_so_chien_dau, trien_khai_tran_dau... giả định đã import từ module khác

def hien_thi_san_dau_boss(user_id, save_data_func):
    # =========================================================
    # 🚨 ƯU TIÊN SỐ 1: KIỂM TRA POPUP CHIẾN THẮNG
    # =========================================================
    if "boss_victory_data" in st.session_state:
        # Gọi hàm hiển thị Popup (Hàm này đã có ở câu trả lời trước)
        hien_thi_popup_chien_thang() 
        return # Dừng hàm ngay, không render sàn đấu nữa

    # =========================================================
    # NẾU KHÔNG CÓ POPUP THÌ MỚI CHẠY TIẾP
    # =========================================================
    
    # --- 1. LẤY DỮ LIỆU TỪ RAM ---
    if 'data' not in st.session_state:
        st.warning("⏳ Đang tải dữ liệu...")
        return

    all_data = st.session_state.data
    player = all_data.get(user_id)
    
    # Lấy thông tin Boss
    system_config = all_data.get('system_config', {})
    boss = system_config.get('active_boss')

    # Nếu không có Boss -> Báo nghỉ
    if not boss or boss.get('status') != 'active':
        st.title("⚔️ ĐẠI CHIẾN GIÁO VIÊN")
        st.info("☘️ Hiện tại không có Giáo viên nào thách thức. Hãy tập luyện thêm!")
        return

    if not player:
        st.error("❌ Không tìm thấy dữ liệu người chơi.")
        return

    # --- 2. TÍNH CHỈ SỐ (Để biết Max HP bao nhiêu mà hồi) ---
    level = player.get("level", 1)
    base_max_hp, base_atk = tinh_chi_so_chien_dau(level)
    
    # Lấy Buff
    bonus_stats, updated_data = get_active_combat_stats(user_id, all_data)
    st.session_state.data = updated_data 
    
    max_hp_p = base_max_hp + bonus_stats['hp']
    atk_p = base_atk + bonus_stats['atk']
    current_hp_p = player.get("hp", max_hp_p)

    # ==============================================================================
    # 🤖 AUTO CHECK: XỬ LÝ HỒI SINH TỰ ĐỘNG
    # ==============================================================================
    if player.get("reborn_at"):
        try:
            reborn_time = datetime.strptime(player["reborn_at"], "%Y-%m-%d %H:%M:%S")
            
            # TRƯỜNG HỢP 1: ĐÃ HẾT GIỜ PHẠT (Người chơi quay lại sau khi nghỉ đủ)
            if datetime.now() >= reborn_time:
                # 1. Hồi đầy máu
                player['hp'] = max_hp_p  
                current_hp_p = max_hp_p # Cập nhật biến tạm để hiển thị đúng ngay bên dưới
                
                # 2. Xóa án phạt
                del player['reborn_at']
                if 'last_defeat' in player: del player['last_defeat']
                
                # 3. Lưu ngay lập tức để đồng bộ Sheets
                save_data_func(st.session_state.data)
                
                # 4. Tự động reload trang để vào giao diện đánh Boss ngay
                st.rerun()
            
            # TRƯỜNG HỢP 2: VẪN CÒN ÁN PHẠT (Chưa hết giờ)
            else:
                # Tính thời gian còn lại
                time_left = reborn_time - datetime.now()
                phut_con_lai = int(time_left.total_seconds() // 60) + 1
                defeat_info = player.get('last_defeat', {})
                
                st.title("💀 BẠN ĐANG TRỌNG THƯƠNG")
                
                st.markdown(f"""
                    <div style="background-color: #2c3e50; padding: 30px; border-radius: 15px; border: 2px solid #e74c3c; text-align: center;">
                        <h3 style="color: #e74c3c; margin: 0;">🛑 KHU VỰC NGUY HIỂM</h3>
                        <p style="color: #bdc3c7;">Bạn vừa bị hạ gục bởi: <b>{defeat_info.get('boss_name', 'Giáo viên')}</b></p>
                        <hr style="border-color: #7f8c8d;">
                        <p style="font-size: 18px; color: white;">Thời gian hồi phục còn lại:</p>
                        <h1 style="color: #f1c40f; font-size: 60px; margin: 10px 0;">{phut_con_lai} phút</h1>
                        <p style="color: #95a5a6; font-style: italic;">(Hãy quay lại sau khi hết thời gian)</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # DỪNG HÀM TẠI ĐÂY -> Không hiện giao diện đánh Boss bên dưới
                return 

        except Exception as e:
            # Nếu lỗi ngày tháng, xóa luôn cho người chơi chơi tiếp (Fallback an toàn)
            if 'reborn_at' in player: del player['reborn_at']
            pass

    # ==============================================================================
    # 👇 NẾU CHẠY XUỐNG ĐÂY NGHĨA LÀ ĐÃ KHỎE MẠNH (HOẶC VỪA ĐƯỢC HỒI SINH) 👇
    # ==============================================================================

    st.title("⚔️ ĐẠI CHIẾN GIÁO VIÊN")

    # 4. Hiển thị Giao diện Sàn đấu (Code cũ giữ nguyên từ đây trở xuống)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        b_name = boss.get('ten', boss.get('name', 'Boss Ẩn Danh'))
        b_img = boss.get("anh", "")
        b_dmg = boss.get('damage', 10)
        
        # --- CƠ CHẾ HIỂN THỊ ẢNH AN TOÀN (ANTI-CRASH) ---
        if b_img: # Nếu Admin có điền link
            try:
                # Cố gắng hiển thị ảnh
                st.image(b_img, caption=f"👿 Boss: {b_name}")
            except Exception:
                # Nếu lỗi (bất cứ lỗi gì: link hỏng, file local...) -> Chỉ hiện thông báo
                st.warning(f"⚠️ Link ảnh lỗi: {b_name}")
                # Không hiển thị ảnh mặc định, để trống theo yêu cầu.
        else:
            # Nếu Admin bỏ trống link -> Chỉ hiện tên
            st.info(f"👿 Boss: {b_name}")
        # -------------------------------------------------

        st.error(f"💀 Sức tấn công: {b_dmg}") 

    with col2:
        try:
            b_hp_curr = float(boss.get('hp_current', 0))
            b_hp_max = float(boss.get('hp_max', 100))
            if b_hp_max <= 0: b_hp_max = 100
            
            hp_boss_pct = min(100, max(0, int((b_hp_curr / b_hp_max) * 100)))
            
            st.write(f"**🚩 HP BOSS: {int(b_hp_curr)} / {int(b_hp_max)}**")
            st.progress(hp_boss_pct)
        except:
            st.warning("⚠️ Đang tải máu Boss...")
        
        st.markdown("---") 

        # --- PHẦN CỦA BẠN (PLAYER) ---
        p_hp_pct = min(100, max(0, int((current_hp_p / max_hp_p) * 100)))
        
        st.write(f"**❤️ Máu của bạn: {int(current_hp_p)} / {max_hp_p}**")
        st.progress(p_hp_pct)
        
        if bonus_stats['atk'] > 0:
            st.info(f"⚔️ Sức tấn công: **{atk_p}** (Gốc: {base_atk} + Buff: {bonus_stats['atk']})")
        else:
            st.info(f"⚔️ Sức tấn công: **{atk_p}**")

    # 5. ĐIỀU KHIỂN TRẬN ĐẤU
    if not st.session_state.get("dang_danh_boss"):
        if st.button("⚔️ KHIÊU CHIẾN NGAY", type="primary", use_container_width=True):
            st.session_state.dang_danh_boss = True
            st.session_state.combo = 0
            st.rerun()
    else:
        if st.button("🏳️ RỜI KHỎI CHIẾN TRƯỜNG (Thoát an toàn)", use_container_width=True):
            st.session_state.dang_danh_boss = False
            keys_to_clean = ["combo", "cau_hoi_active", "thoi_gian_bat_dau"]
            for k in keys_to_clean:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
            
        # Gọi hàm xử lý trận đấu
        trien_khai_tran_dau(boss, player, atk_p, save_data_func, user_id, all_data)        


def trien_khai_tran_dau(boss, player, current_atk, save_data_func, user_id, all_data):
    import os
    import json
    import time
    import random
    
    st.divider()

    # --- 1. XÁC ĐỊNH FILE CÂU HỎI (THÔNG MINH) ---
    mon_boss = boss.get('mon', 'Toán')
    map_mon = {
        "Toán": "toan", "Văn": "van", "Ngữ Văn": "van",
        "Anh": "anh", "Tiếng Anh": "anh",
        "KHTN": "khtn", "Khoa Học Tự Nhiên": "khtn", 
        "Sử": "su", "Lịch Sử": "su"
    }
    target_name = map_mon.get(mon_boss, mon_boss.lower()) + ".json" 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        os.path.join(base_dir, "quiz_data", "grade_6", "boss"),
        os.path.join(base_dir, "quiz_data", "grade_6")
    ]
    path_quiz = None
    for directory in search_dirs:
        if os.path.exists(directory):
            try:
                files_in_dir = os.listdir(directory)
                for f in files_in_dir:
                    if f.lower() == target_name.lower():
                        path_quiz = os.path.join(directory, f)
                        break 
            except Exception: continue
        if path_quiz: break

    if not path_quiz:
        st.error(f"❌ Không tìm thấy dữ liệu câu hỏi môn {mon_boss}")
        return

    # --- 2. ĐỌC VÀ GOM CÂU HỎI ---
    try:
        with open(path_quiz, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        st.error(f"❌ Lỗi đọc file JSON: {e}")
        return

    pool = []
    if isinstance(raw_data, list): pool = raw_data
    elif isinstance(raw_data, dict):
        for key in raw_data: 
            if isinstance(raw_data[key], list): pool.extend(raw_data[key])
    
    if not pool:
        st.warning(f"⚠️ File rỗng.")
        return

    # --- 3. KHỞI TẠO CÂU HỎI ---
    if "cau_hoi_active" not in st.session_state:
        st.session_state.cau_hoi_active = random.choice(pool)
        st.session_state.thoi_gian_bat_dau = time.time()

    q = st.session_state.cau_hoi_active
    
    # --- 4. ĐỒNG HỒ ĐẾM NGƯỢC (ĐÃ CHỈNH 30S) ---
    THOI_GIAN = 30  # <--- 🔥 Đã sửa thành 30 giây
    elapsed = time.time() - st.session_state.get("thoi_gian_bat_dau", time.time())
    remaining = int(THOI_GIAN - elapsed)
    
    # UI Thời gian
    # Sắp hết giờ (dưới 10s) thì chuyển màu đỏ cho kịch tính
    color_timer = "#ff4b4b" if remaining <= 10 else "#00d2ff"
    
    st.markdown(f"<h1 style='text-align: center; color: {color_timer}; font-size: 40px;'>⏳ {max(0, remaining)}s</h1>", unsafe_allow_html=True)

    # XỬ LÝ HẾT GIỜ
    if remaining <= 0:
        st.error("⏰ Hết giờ! Boss tấn công!")
        dmg_boss = boss.get('damage', 10)
        player['hp'] = max(0, player.get('hp', 100) - dmg_boss)
        st.session_state.combo = 0
        
        save_data_func(st.session_state.data)
        
        if "cau_hoi_active" in st.session_state: del st.session_state.cau_hoi_active
        if "thoi_gian_bat_dau" in st.session_state: del st.session_state.thoi_gian_bat_dau
        
        if player['hp'] <= 0:
             xu_ly_thua_cuoc(player, boss, save_data_func, user_id, all_data)
        else:
            time.sleep(1.5)
            st.rerun()
        return

    # --- 5. HIỂN THỊ CÂU HỎI & NÚT BẤM ---
    st.info(f"🔥 **COMBO: x{st.session_state.get('combo', 0)}**")
    st.markdown(f"### ❓ {q['question']}")
    
    options = q.get('options', [])
    user_choice = None

    if options:
        c1, c2 = st.columns(2)
        for i, opt in enumerate(options):
            col = c1 if i % 2 == 0 else c2
            
            # Key cố định theo ID câu hỏi hoặc index (Không dùng remaining để tránh lỗi nút)
            btn_key = f"ans_{q.get('id', 'unknown')}_{i}"
            
            if col.button(opt, key=btn_key, use_container_width=True):
                user_choice = opt
        
        # --- 6. XỬ LÝ ĐÁP ÁN ---
        if user_choice:
            user_key = str(user_choice).strip()[0].upper()
            raw_ans = q.get('answer', q.get('correct_answer', ''))
            ans_key = str(raw_ans).strip()[0].upper()
            
            if user_key == ans_key:
                # --- ĐÚNG ---
                st.session_state.combo = st.session_state.get('combo', 0) + 1
                he_so = 1 + (st.session_state.combo - 1) * 0.1
                dmg_deal = int(current_atk * he_so)
                
                boss['hp_current'] = max(0, boss['hp_current'] - dmg_deal)
                if "contributions" not in boss: boss["contributions"] = {}
                boss["contributions"][user_id] = boss["contributions"].get(user_id, 0) + dmg_deal
                
                save_data_func(st.session_state.data)
                st.success(f"🎯 Chính xác! Gây {dmg_deal} sát thương!")
                
                if boss['hp_current'] <= 0:
                    del st.session_state.cau_hoi_active
                    xu_ly_boss_chet(user_id, all_data, save_data_func)
                else:
                    del st.session_state.cau_hoi_active
                    del st.session_state.thoi_gian_bat_dau
                    time.sleep(0.5) 
                    st.rerun()
            else:
                # --- SAI ---
                st.session_state.combo = 0
                dmg_boss = boss.get('damage', 10)
                player['hp'] = max(0, player.get('hp', 100) - dmg_boss)
                save_data_func(st.session_state.data)
                
                real_ans = q.get('answer', q.get('correct_answer', '...'))
                st.error(f"❌ Sai rồi! Đáp án: {real_ans}")
                st.warning(f"🛡️ Boss đánh trả: -{dmg_boss} HP")
                
                if player['hp'] <= 0:
                    if "cau_hoi_active" in st.session_state: del st.session_state.cau_hoi_active
                    xu_ly_thua_cuoc(player, boss, save_data_func, user_id, all_data)
                else:
                    if "cau_hoi_active" in st.session_state: del st.session_state.cau_hoi_active
                    if "thoi_gian_bat_dau" in st.session_state: del st.session_state.thoi_gian_bat_dau
                    time.sleep(2.0)
                    st.rerun()
            return

    # --- 7. CƠ CHẾ TỰ ĐỘNG ĐẾM NGƯỢC (AUTO-RERUN) ---
    if remaining > 0 and not user_choice:
        time.sleep(1) 
        st.rerun()        
# --- HÀM PHỤ TRỢ (Để code gọn hơn) ---
def xu_ly_thua_cuoc(player, boss, save_data_func, user_id, all_data):
    # 1. Cập nhật thông tin trọng thương
    player['hp'] = 0
    # Thời gian hồi sinh: Hiện tại + 30 phút
    player['reborn_at'] = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Ghi lại lịch sử ai đánh bại
    player['last_defeat'] = {
        "boss_name": boss.get('ten', 'Boss'),
        "damage_taken": boss.get('damage', 10),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 2. Reset trạng thái chiến đấu cục bộ
    st.session_state.dang_danh_boss = False
    if "cau_hoi_active" in st.session_state: del st.session_state.cau_hoi_active
    
    # --- [FIX QUAN TRỌNG] ĐỒNG BỘ DỮ LIỆU ---
    # Đảm bảo thông tin player mới nhất được gán vào biến tổng all_data
    all_data[user_id] = player
    
    # Cập nhật ngược lại vào session state để chắc chắn UI hiển thị đúng
    st.session_state.data = all_data
    
    # Gọi hàm lưu ngay lập tức lên Google Sheets
    save_data_func(all_data) 

    # 3. Hiển thị thông báo
    st.error(f"💀 BẠN ĐÃ BỊ {boss.get('ten', 'Boss')} HẠ GỤC!")
    st.warning(f"⏳ Bạn cần nghỉ ngơi hồi sức đến: {player['reborn_at']}")
    
    time.sleep(3) 
    st.rerun()

def xu_ly_boss_chet(user_id, all_data, save_data_func):
    """
    Xử lý Boss chết -> Lưu quà -> Kích hoạt Popup.
    """
    # 1. Tính thưởng (đã fix lỗi inventory bên trong hàm này)
    qua_cua_toi, dmg_cua_toi = tinh_va_tra_thuong_global(user_id, all_data)
    
    # 2. Đồng bộ dữ liệu mới nhất vào Session State (Quan trọng!)
    st.session_state.data = all_data
    
    # 3. Lưu lên Google Sheets
    save_data_func(all_data)

    # 4. Gắn cờ Popup
    st.session_state.boss_victory_data = {
        "rewards": qua_cua_toi,
        "damage": dmg_cua_toi,
        "boss_name": "Giáo Viên (Boss)"
    }
    
    # 5. Dọn dẹp trạng thái chiến đấu
    st.session_state.dang_danh_boss = False
    if "cau_hoi_active" in st.session_state: del st.session_state.cau_hoi_active
    
    # 6. Reload ngay lập tức để hiện Popup
    st.rerun()    

def lam_bai_thi_loi_dai(match_id, match_info, current_user_id, save_data_func):


    # --- 1. KHỞI TẠO TRẠNG THÁI (FIX LỖI TEST TRÊN 1 MÁY) ---
    # Điều kiện reset: 
    # 1. Chưa có ID trận đấu active.
    # 2. Hoặc ID trận đấu đã thay đổi.
    # 3. [MỚI] Hoặc NGƯỜI CHƠI đã thay đổi (Khắc phục lỗi login ra vào bị nhớ trạng thái cũ).
    if ("match_id_active" not in st.session_state or 
        st.session_state.get("last_match_id") != match_id or 
        st.session_state.get("last_user_id") != current_user_id):
        
        # Reset toàn bộ về 0 cho người mới
        st.session_state.current_q = 0
        st.session_state.user_score = 0
        st.session_state.start_time = time.time()
        
        # Lưu lại dấu vết để kiểm tra cho lần sau
        st.session_state.last_match_id = match_id
        st.session_state.last_user_id = current_user_id # <--- Quan trọng
        st.session_state.match_id_active = match_id

    # Đảm bảo biến thời gian luôn tồn tại
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()

    # --- 2. XỬ LÝ ĐƯỜNG DẪN FILE (THÔNG MINH) ---
    grade = match_info.get('grade', 'grade_6')
    raw_subject = match_info.get('subject', 'toan') 
    
    # Bộ từ điển map tên môn -> tên file (Bất chấp có dấu/không dấu)
    file_map = {
        "toán": "toan", "toan": "toan",
        "lý": "ly",     "ly": "ly", "vật lý": "ly",
        "hóa": "hoa",   "hoa": "hoa", "hóa học": "hoa",
        "văn": "van",   "van": "van", "ngữ văn": "van",
        "anh": "anh",   "anh": "anh", "tiếng anh": "anh",
        "sinh": "sinh", "sinh": "sinh", "sinh học": "sinh",
        "sử": "su",     "su": "su", "lịch sử": "su",
        "địa": "dia",   "dia": "dia", "địa lý": "dia",
        "gdcd": "gdcd", "giáo dục công dân": "gdcd",
        "khtn": "khtn", "khoa học tự nhiên": "khtn"
    }
    
    # Chuyển tên môn về chữ thường để tra cứu
    subject_key = raw_subject.lower().strip()
    file_name = file_map.get(subject_key, subject_key) # Nếu không tìm thấy thì dùng luôn tên gốc
    
    # Tạo đường dẫn tuyệt đối (Tránh lỗi không tìm thấy file trên Server)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "quiz_data", grade, f"{file_name}.json")
    
    # --- 3. ĐỌC FILE CÂU HỎI ---
    if not os.path.exists(path):
        st.error(f"❌ **LỖI HỆ THỐNG:** Không tìm thấy bộ đề thi!")
        st.code(f"Thiếu file: {path}")
        st.warning(f"Vui lòng báo Admin kiểm tra file: `quiz_data/{grade}/{file_name}.json`")
        if st.button("🔙 Quay lại sảnh"):
             del st.session_state.match_id_active
             st.rerun()
        return

    try:
        with open(path, "r", encoding='utf-8') as f:
            all_questions = json.load(f)
    except Exception as e:
        st.error(f"❌ File dữ liệu bị lỗi cấu trúc JSON: {e}")
        return

    # --- LẤY CÂU HỎI THEO ĐỘ KHÓ ---
    # Lấy độ khó từ thông tin trận đấu (Mặc định là Medium)
    raw_level = match_info.get('difficulty', 'Medium') 
    level = raw_level.lower() # Chuyển về chữ thường: "Medium" -> "medium"
    
    # Logic dự phòng: Nếu chọn Extreme mà chưa có file thì lấy tạm Hard
    if level not in all_questions and level == 'extreme':
         level = 'hard'
    
    questions = all_questions.get(level, [])
    
    # Trộn câu hỏi để mỗi lần thi khác nhau (Tùy chọn)
    # import random
    # random.shuffle(questions) 
    
    # Lấy 5 câu hỏi đầu tiên
    questions = questions[:5]
    
    if not questions:
        st.error(f"⚠️ Bộ đề `{file_name}` chưa có câu hỏi mức độ `{raw_level}`.")
        if st.button("🔙 Quay lại sảnh"):
             del st.session_state.match_id_active
             st.rerun()
        return

    # Thời gian giới hạn mỗi câu theo độ khó
    limit_map = {"easy": 15, "medium": 20, "hard": 25, "extreme": 30}
    time_limit = limit_map.get(level, 20)

    # --- 4. GIAO DIỆN LÀM BÀI ---
    q_idx = st.session_state.current_q
    
    if q_idx < len(questions):
        q = questions[q_idx]
        
        # Thanh tiến độ
        progress = (q_idx / len(questions))
        st.progress(progress, text=f"Tiến độ: Câu {q_idx + 1}/{len(questions)}")
        
        st.subheader(f"⚔️ CÂU HỎI {q_idx + 1}")
        st.caption(f"🔥 Độ khó: {raw_level} | 📚 Môn: {raw_subject}")
        
        # Hiển thị nội dung câu hỏi đẹp hơn
        st.info(f"❓ {q['question']}")
        
        # --- ĐỒNG HỒ ĐẾM NGƯỢC ---
        elapsed = time.time() - st.session_state.start_time
        remaining = max(0, int(time_limit - elapsed))
        
        # Cờ kiểm tra tự nộp bài
        force_submit = False
        if remaining <= 0:
            force_submit = True
        
        # Màu sắc đồng hồ (Đỏ khi sắp hết giờ)
        timer_color = "#e74c3c" if remaining <= 5 else "#2ecc71" 
        st.markdown(
            f"""<div style="text-align: center; font-size: 24px; font-weight: bold; color: {timer_color}; 
            border: 2px solid {timer_color}; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
            ⏳ Thời gian còn lại: {remaining}s
            </div>""", 
            unsafe_allow_html=True
        )

        # Form trả lời (Dùng key unique để tránh lỗi state)
        with st.form(key=f"quiz_form_{match_id}_{q_idx}_{current_user_id}"):
            ans = st.radio("Lựa chọn của bạn:", q['options'], index=None)
            submitted = st.form_submit_button("CHỐT ĐÁP ÁN 🚀", type="primary", use_container_width=True)

        # --- XỬ LÝ KẾT QUẢ ---
        if submitted or force_submit:
            # 1. Lấy đáp án đúng (Hỗ trợ cả key 'answer' và 'correct_answer')
            raw_correct_ans = q.get('answer', q.get('correct_answer', ''))
            
            # 2. Chuẩn hóa để so sánh (Lấy ký tự đầu A,B,C,D và viết hoa)
            user_key = str(ans).strip()[0].upper() if ans else ""
            ans_key = str(raw_correct_ans).strip()[0].upper()
            
            # 3. Kiểm tra đúng sai
            is_correct = (user_key == ans_key)
            
            if force_submit and not ans:
                 st.warning(f"⏰ HẾT GIỜ! Bạn chưa kịp chọn đáp án.")
                 st.error(f"✅ Đáp án đúng là: {raw_correct_ans}")
            elif is_correct:
                st.balloons()
                st.success("🎉 CHÍNH XÁC! +1 Điểm")
                st.session_state.user_score += 1
            else:
                st.error("❌ SAI RỒI!")
                st.info(f"✅ Đáp án đúng là: {raw_correct_ans}")
            
            # Hiển thị giải thích (Nếu có trong data)
            if 'explanation' in q:
                with st.expander("💡 Xem giải thích chi tiết"):
                    st.write(q['explanation'])
            
            # 4. Tạm dừng để học sinh đọc kết quả
            with st.spinner("Đang chuyển câu hỏi tiếp theo..."):
                time.sleep(2.5) 
            
            # 5. Chuyển câu
            st.session_state.current_q += 1
            st.session_state.start_time = time.time() # Reset đồng hồ
            st.rerun()
        
        # Tự động refresh để chạy đồng hồ (chỉ khi chưa nộp)
        if remaining > 0:
            time.sleep(1)
            st.rerun()
            
    else:
        # --- 5. KẾT THÚC BÀI THI ---
        st.balloons()
        final_score = st.session_state.user_score
        total_q = len(questions)
        
        st.success(f"🎉 BẠN ĐÃ HOÀN THÀNH BÀI THI!")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Điểm số", f"{final_score}/{total_q}")
        col2.metric("Độ khó", raw_level)
        col3.metric("Môn thi", raw_subject)
        
        # --- LƯU KẾT QUẢ (QUAN TRỌNG) ---
        with st.spinner("💾 Đang lưu kết quả lên hệ thống..."):
            
            # 1. Tải dữ liệu mới nhất (Tránh ghi đè điểm người khác)
            # Lưu ý: Hàm load_loi_dai phải có sẵn trong file này (đã copy ở bước trước)
            ld_data = load_loi_dai()
            
            if match_id in ld_data['matches']:
                m = ld_data['matches'][match_id]
                
                # 2. Lưu điểm cá nhân
                m[f"score_{current_user_id}"] = final_score
                
                # 3. [FIX LOGIC ĐẾM NGƯỜI] Tính toán chính xác tổng số người chơi
                # Lấy danh sách team 1 (Nếu danh sách rỗng thì lấy cá nhân đội trưởng)
                c_team = m.get('challenger_team', [])
                if not c_team: c_team = [m.get('challenger')]
                
                # Lấy danh sách team 2
                o_team = m.get('opponent_team', [])
                if not o_team: o_team = [m.get('opponent')]
                
                # Tổng hợp tất cả người chơi trong trận
                all_players = c_team + o_team
                
                # 4. Lọc danh sách những người ĐÃ CÓ ĐIỂM
                finished_players = [uid for uid in all_players if f"score_{uid}" in m]
                
                # 5. Kiểm tra điều kiện kết thúc (Số người xong >= Tổng số người)
                if len(finished_players) >= len(all_players):
                    # TẤT CẢ ĐÃ XONG -> GỌI TRỌNG TÀI TỔNG KẾT
                    trong_tai_tong_ket(match_id, ld_data, save_data_func)
                    st.success("🏁 TẤT CẢ ĐÃ THI XONG! ĐÃ CÓ KẾT QUẢ CHUNG CUỘC.")
                else:
                    # CHƯA XONG HẾT -> LƯU TẠM THỜI TRẠNG THÁI
                    save_loi_dai(ld_data)
                    remaining_players = len(all_players) - len(finished_players)
                    st.info(f"⏳ Đã lưu điểm của bạn. Đang chờ {remaining_players} người chơi khác hoàn thành...")
            else:
                st.error("⚠️ Trận đấu không tồn tại hoặc đã bị hủy.")

        # Nút thoát
        st.divider()
        if st.button("🔙 QUAY VỀ SẢNH LÔI ĐÀI", type="primary", use_container_width=True):
            # Dọn dẹp session state
            keys_to_clear = ["current_q", "user_score", "start_time", "match_id_active", "last_match_id"]
            for k in keys_to_clear:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
            
@st.cache_data(ttl=60, show_spinner=False)
def load_loi_dai():
    """
    Tải dữ liệu Lôi Đài từ Tab 'PVP' trên Google Sheets.
    Tự động dọn dẹp các trận đấu cũ quá 30 ngày.
    """
    default_data = {"matches": {}, "rankings": {}}
    
    # Cần đảm bảo CLIENT và SHEET_NAME có sẵn. 
    # Nếu không, hãy truyền chúng vào hàm hoặc import ở đầu file.
    if 'CLIENT' not in globals() or 'SHEET_NAME' not in globals():
        st.error("Lỗi cấu hình: CLIENT hoặc SHEET_NAME chưa được định nghĩa.")
        return default_data

    try:
        # 1. Kết nối Google Sheets và mở Tab PVP
        try:
            sh = CLIENT.open(SHEET_NAME).worksheet("PVP")
        except:
            # Nếu chưa có tab PVP, tạo mới luôn với Header chuẩn
            sh = CLIENT.open(SHEET_NAME).add_worksheet(title="PVP", rows=100, cols=10)
            sh.append_row(["Match_ID", "Full_JSON_Data", "Status", "Created_At"])
            return default_data

        # 2. Lấy toàn bộ dữ liệu (bỏ qua dòng tiêu đề)
        rows = sh.get_all_values()
        if len(rows) <= 1:
            return default_data

        matches = {}
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        need_save = False 

        # 3. Duyệt từng dòng
        for r in rows[1:]:
            try:
                if len(r) < 2: continue
                
                mid = r[0]
                m_data = json.loads(r[1]) 
                
                # --- LOGIC DỌN DẸP TỰ ĐỘNG ---
                created_at_str = m_data.get('created_at', "")
                if created_at_str:
                    try:
                        # Xử lý linh hoạt hơn cho ngày tháng nếu cần
                        match_date = datetime.strptime(created_at_str[:10], "%d/%m/%Y")
                        
                        if match_date < thirty_days_ago:
                            need_save = True 
                            continue 
                    except ValueError:
                         # Log nhẹ để biết dòng nào lỗi ngày tháng nhưng không crash app
                        print(f"Lỗi định dạng ngày tháng trận {mid}: {created_at_str}")
                        pass 

                matches[mid] = m_data
                
            except Exception as e:
                print(f"Lỗi đọc dòng PVP ({mid}): {e}")
                continue
        
        final_data = {"matches": matches, "rankings": {}}

        # 4. Lưu lại nếu có dọn dẹp
        if need_save:
            save_loi_dai(final_data)

        return final_data

    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối Lôi Đài Cloud: {e}")
        return default_data

def save_loi_dai(data):
    """
    Lưu dữ liệu Lôi Đài & Xóa Cache để cập nhật ngay lập tức.
    """
    if 'CLIENT' not in globals() or 'SHEET_NAME' not in globals():
        st.error("Lỗi cấu hình: CLIENT hoặc SHEET_NAME chưa được định nghĩa.")
        return

    try:
        sh = CLIENT.open(SHEET_NAME).worksheet("PVP")
        
        rows_to_write = [["Match_ID", "Full_JSON_Data", "Status", "Created_At"]]
        matches = data.get('matches', {})
        for mid, m_info in matches.items():
            json_str = json.dumps(m_info, ensure_ascii=False)
            status = m_info.get('status', 'unknown')
            created = m_info.get('created_at', '')
            rows_to_write.append([str(mid), json_str, status, created])
            
        sh.clear()
        sh.update('A1', rows_to_write)
        
        # Xóa cache để đảm bảo lần load sau lấy dữ liệu mới
        load_loi_dai.clear()
        
    except Exception as e:
        st.error(f"❌ Không thể lưu Lôi Đài lên Cloud: {e}")

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
    
    # ... (Logic tính điểm giữ nguyên như cũ) ...
    t1 = m.get('challenger_team', [])
    if not t1: t1 = [m.get('challenger')]
    t2 = m.get('opponent_team', [])
    if not t2: t2 = [m.get('opponent')]

    s1 = sum(m.get(f"score_{uid}", 0) for uid in t1 if uid)
    s2 = sum(m.get(f"score_{uid}", 0) for uid in t2 if uid)

    if s1 > s2: winner = "team1"
    elif s2 > s1: winner = "team2"
    else: winner = "Hòa"

    # Cộng/Trừ KPI cho người chơi (Dữ liệu Player)
    data = st.session_state.data
    
    # --- LOGIC CỘNG ĐIỂM GIỮ NGUYÊN [cite: 33-34] ---
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
        
    # CẬP NHẬT TRẠNG THÁI TRẬN ĐẤU
    m['status'] = 'finished'
    m['winner'] = winner
    m['final_score_team1'] = s1
    m['final_score_team2'] = s2
    
    # 1. Lưu dữ liệu TRẬN ĐẤU lên tab PVP
    save_loi_dai(ld_data)
    
    # 2. Lưu dữ liệu NGƯỜI CHƠI (KPI) lên tab Players
    save_data_func(data)    

def hien_thi_loi_dai(current_user_id, save_data_func):
    import pandas as pd
    from datetime import datetime
    
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
    
    # 1. THÔNG BÁO TOAST & TỰ ĐỘNG XỬ THUA
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

    # --- BƯỚC 3: XỬ LÝ LỜI MỜI THÁCH ĐẤU ---
    for mid, m in ld_data['matches'].items():
        if m.get('status') == 'pending' and m.get('opponent') == current_user_id:
            challenger_id = m.get('challenger') 
            challenger_info = st.session_state.data.get(challenger_id, {}) 
            challenger_name = challenger_info.get('name', 'Một Cao Thủ').upper()
            
            # [CẬP NHẬT] Hiển thị thêm Độ khó trong lời mời
            difficulty_badge = {
                "Easy": "#4caf50", "Medium": "#ff9800", "Hard": "#f44336", "Extreme": "#9c27b0"
            }.get(m.get('difficulty', 'Medium'), "#333")

            notification_html = f"""
            <div style="background-color: #ffffff; border: 4px solid #d32f2f; border-radius: 15px; padding: 25px; margin-bottom: 25px; text-align: center; color: #333333;">
                <h2 style="color: #d32f2f; font-size: 30px; font-weight: 900; margin-top: 0;">🔥 CÓ LỜI TUYÊN CHIẾN! 🔥</h2>
                <p style="font-size: 20px;">Cao thủ <b>{challenger_name}</b> muốn so tài!</p>
                <div style="display: inline-block; background-color: #fff8e1; padding: 15px 40px; border-radius: 10px; border: 2px dashed #ff8f00;">
                    <div style="font-size: 18px; font-weight: bold;">
                        📚 Môn: {m.get('subject')} | 💎 Cược: {m.get('bet')} KPI <br>
                        <span style="color: {difficulty_badge}">🔥 Độ khó: {m.get('difficulty', 'Medium').upper()}</span>
                    </div>
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
            
            # [FIX QUAN TRỌNG] Logic lấy danh sách người chơi chuẩn xác
            c_team = m.get('challenger_team', [])
            if not c_team: c_team = [m.get('challenger')]
            
            o_team = m.get('opponent_team', [])
            if not o_team: o_team = [m.get('opponent')]
            
            all_players = c_team + o_team
            
            if current_user_id in all_players:
                diff_label = m.get('difficulty', 'Medium')
                with st.expander(f"⚔️ Trận đấu môn {m.get('subject', '').upper()} ({diff_label})", expanded=True):
                    
                    # --- DEBUG (Nếu vẫn lỗi thì bỏ comment dòng dưới để xem nó đang lưu cái gì) ---
                    st.write(f"🔍 Key Debug: {list(m.keys())}")
                    st.write(f"👤 Bạn là: {current_user_id}")
                    
                    # Kiểm tra xem ID của bạn đã có điểm chưa
                    if f"score_{current_user_id}" in m:
                        st.success("✅ Bạn đã hoàn thành phần thi.")
                        st.info("⏳ Đang chờ đồng đội và đối thủ hoàn thành...")
                    else:
                        st.markdown(f"**Thể thức:** {m.get('mode')} | **Cược:** {m.get('bet')} KPI")
                        if st.button("🚀 VÀO THI ĐẤU", key=f"play_btn_{mid}", type="primary"): 
                            st.session_state.match_id_active = mid 
                            st.rerun()

    # --- BƯỚC 5: GIAO DIỆN GỬI CHIẾN THƯ (ĐÃ THÊM CHỌN ĐỘ KHÓ) ---
    st.divider() 
    with st.expander("✉️ GỬI CHIẾN THƯ / LẬP TỔ ĐỘI", expanded=False): 
        c1, c2 = st.columns(2) 
        
        # Lọc danh sách học sinh an toàn
        list_opps = {}
        for uid, info in st.session_state.data.items(): 
            if isinstance(info, dict) and 'name' in info and uid != current_user_id and uid not in ['admin', 'system_config']: 
                list_opps[uid] = info['name']

        with c1:
            the_thuc = st.selectbox("Thể thức:", ["1 vs 1", "2 vs 2", "3 vs 3"], key="mode_sel")
            is_team = the_thuc != "1 vs 1" 
            target_name = st.selectbox("Chọn đối thủ:", 
                                     ["--- Đấu Đội ---"] + list(list_opps.values()) if is_team else list(list_opps.values()), 
                                     disabled=is_team) 
            sub = st.selectbox("Môn thi:", ["Toán", "Lý", "Hóa", "Văn", "Anh", "Sinh", "Sử", "Địa", "GDCD", "KHTN"], key="sub_sel")
            
        with c2:
            hinh_thuc = st.radio("Hình thức:", ["Giải đề trắc nghiệm", "So điểm tăng trưởng"])
            bet = st.number_input("Cược KPI:", min_value=1, max_value=5, value=1) 
            
            # 🔥 [MỚI] Thêm phần chọn Độ khó
            do_kho = st.select_slider("🔥 Chọn cấp độ:", 
                                     options=["Easy", "Medium", "Hard", "Extreme"],
                                     value="Medium")
            
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
                "difficulty": do_kho, # <--- Lưu độ khó vào đây
                "status": "waiting",
                "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            if not is_team:
                # Nếu đấu đơn thì target người cụ thể
                target_ids = [uid for uid, name in list_opps.items() if name == target_name]
                if target_ids:
                    target_id = target_ids[0]
                    match_data.update({"opponent": target_id, "opponent_team": [target_id], "status": "pending"})
                else:
                    st.error("Chưa chọn đối thủ!")
                    return
            
            ld_data['matches'][new_id] = match_data
            save_loi_dai(ld_data)
            st.rerun()

    # --- BƯỚC 6: PHÒNG CHỜ TỔ ĐỘI ---
    st.divider()
    st.markdown("### 🏟️ PHÒNG CHỜ TỔ ĐỘI")
    for mid, m in list(ld_data['matches'].items()):
        if m.get('status') == 'waiting':
            num_required = 2 if m['mode'] == "2 vs 2" else 3
            # [CẬP NHẬT] Hiển thị thêm độ khó
            st.info(f"Phòng: {m['mode']} - {m['type']} - Môn {m['subject'].upper()} ({m.get('difficulty', 'Medium')}) - Cược: {m['bet']} KPI")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Đội Thách Đấu ({len(m.get('challenger_team', []))}/{num_required})**")
                for uid in m.get('challenger_team', []):
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
                m['start_kpi_dict'] = {uid: st.session_state.data.get(uid, {}).get('kpi', 0) for uid in m['challenger_team'] + m['opponent_team']}
                save_loi_dai(ld_data)
                st.success("🔥 ĐỦ NGƯỜI! TRẬN ĐẤU BẮT ĐẦU!")
                st.rerun()

    # --- BƯỚC 7: NHẬT KÝ LÔI ĐÀI ---
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
                "Môn": f"{m.get('subject', 'N/A').capitalize()} ({m.get('difficulty', 'M')})", # Hiển thị ngắn gọn độ khó
                "Thể thức": f"{m.get('mode', '1 vs 1')}",
                "Đối thủ": opp_name,
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
    
    # === 🟢 BƯỚC 0: CHÈN LOGIC DỊCH CẤP BẬC ===
    role_map = {
        "u1": "Tổ trưởng",
        "u2": "Tổ phó", 
        "u3": "Tổ viên",
        "admin": "Quản trị viên"
    }
    raw_role = str(user_info.get('role', 'u3')).lower()
    role_name = role_map.get(raw_role, "Học sĩ")
    # ==========================================
    
    # --- 1. LOGIC TÍNH TOÁN CẤP ĐỘ VÀ TIẾN TRÌNH ---
    # A. EXP
    raw_exp = user_info.get('exp', 0)
    try:
        current_exp = float(raw_exp)
        if current_exp != current_exp: current_exp = 0 
    except:
        current_exp = 0
    
    # B. LEVEL
    current_level = int(current_exp // 100) 
    if current_level < 1: current_level = 1 
    
    # C. PROGRESS BAR
    exp_in_level = current_exp % 100
    progress_pct = exp_in_level / 100
    
    # D. KPI (Dùng cho tính toán máu và hiển thị)
    raw_kpi = user_info.get('kpi', 0)
    try:
        base_kpi = float(raw_kpi)
        if base_kpi != base_kpi: base_kpi = 0
    except:
        base_kpi = 0

    # E. ATK & HP
    atk = tinh_atk_tong_hop(user_info)
    hp_current = base_kpi + (current_level * 20)

    # --- 2. GIAO DIỆN HIỂN THỊ CHÍNH ---
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        st.image("https://i.ibb.co/mVjzG7MQ/giphy-preview.gif", use_container_width=True)

    with col_info:
        # Tên & Tổ đội
        st.markdown(f"<h1 style='margin-bottom:0px;'>⚔️ {user_info.get('name', 'HỌC SĨ').upper()}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#f39c12; font-size:1.2em; font-weight:bold; margin-top:0px;'>🚩 Tổ đội: {user_info.get('team', 'Chưa phân tổ')}</p>", unsafe_allow_html=True)

        # Cấp bậc
        st.markdown(f"<p style='font-size:1.1em; font-weight:bold; margin-top:5px;'>🔰 Cấp bậc: <span style='color:#3498db'>{role_name}</span></p>", unsafe_allow_html=True)
        
        # HP & ATK
        st.markdown(f"❤️ **SINH MỆNH (HP):** <span style='color:#ff4b4b; font-size:1.2em; font-weight:bold;'>{hp_current}</span>", unsafe_allow_html=True)
        st.markdown(f"⚔️ **CHIẾN LỰC (ATK):** <span style='color:#f1c40f; font-size:1.2em; font-weight:bold;'>{atk}</span>", unsafe_allow_html=True)
        
        st.write("") 

        # EXP Bar
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
        
        # Kỷ lục (Best Time)
        st.markdown("<p style='margin-bottom:5px; font-weight:bold; color:#f1c40f;'>🏆 KỶ LỤC THỜI GIAN NHANH NHẤT</p>", unsafe_allow_html=True)
        best_times = user_info.get('best_time', {})
        if not best_times:
            st.markdown("<small style='color:#888;'><i>Chưa có kỷ lục nào được ghi nhận.</i></small>", unsafe_allow_html=True)
        else:
            record_cols = st.columns(3)
            mapping_names = {"toan": "📐 Toán", "van": "📖 Văn", "anh": "🇬🇧 Anh", "ly": "⚡ Lý", "hoa": "🧪 Hóa", "sinh": "🌿 Sinh"}
            for idx, (l_id, time_val) in enumerate(best_times.items()):
                with record_cols[idx % 3]:
                    st.markdown(f"""
                        <div style="background: rgba(241, 196, 15, 0.1); border: 1px solid #f1c40f; border-radius: 8px; padding: 5px; text-align: center; margin-bottom: 5px;">
                            <div style="font-size: 11px; color: #aaa;">{mapping_names.get(l_id, l_id.upper())}</div>
                            <div style="font-size: 16px; font-weight: bold; color: #f1c40f;">{time_val}s</div>
                        </div>
                    """, unsafe_allow_html=True)

    # --- 3. BẢNG THÔNG SỐ PHỤ DẠNG CARD (ĐÃ THÊM KPI) ---
    st.write("---")
    
    # [CẬP NHẬT] Đổi thành 5 cột để đủ chỗ cho KPI
    cols = st.columns(5)
    
    # Danh sách thẻ bài (Thêm KPI vào vị trí đầu tiên hoặc thứ 2)
    badges = [
        ("🏆 KPI Tổng", base_kpi, "#e74c3c"),       # <-- THÊM MỚI Ở ĐÂY
        ("📚 Tri Thức", user_info.get('Tri_Thuc', 0), "#3498db"),
        ("🛡️ Chiến Tích", user_info.get('Chien_Tich', 0), "#e67e22"),
        ("🎖️ Vinh Dự", user_info.get('Vinh_Du', 0), "#2ecc71"),
        ("👑 Vinh Quang", user_info.get('Vinh_Quang', 0), "#f1c40f")
    ]
    
    for i, (label, val, color) in enumerate(badges):
        with cols[i]:
            st.markdown(f"""
                <div style="text-align: center; border: 2px solid {color}; border-radius: 15px; padding: 10px; background: white; min-height: 100px; display: flex; flex-direction: column; justify-content: center;">
                    <p style="font-size: 0.85em; color: #636e72; margin-bottom: 5px; font-weight: bold; white-space: nowrap;">{label}</p>
                    <h2 style="margin: 0; color: {color}; font-size: 1.8em;">{val}</h2>
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
            shop_items = shop_items_visible
            
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
                
                

    # --- TAB 2: TÚI ĐỒ (CẬP NHẬT SỬA LỖI KHÓA RƯƠNG) ---
    with tab_kho:
        inventory = user_info.get('inventory', {})
        
        # 1. Tự động chuyển đổi List -> Dict (Fix lỗi dữ liệu cũ)
        if isinstance(inventory, list):
            new_inv = {}
            for item in inventory:
                new_inv[item] = new_inv.get(item, 0) + 1
            inventory = new_inv
            user_info['inventory'] = inventory
            save_data_func(st.session_state.data)
            st.rerun()

        if not inventory:
            st.info("🎒 Túi đồ trống trơn. Hãy ghé Tiệm tạp hóa nhé!")
        else:
            st.write(f"### 📦 Đồ đạc của bạn")
            
            shop_data = st.session_state.data.get('shop_items', {})
            cols_kho = st.columns(4)
            
            for i, (item_name, count) in enumerate(inventory.items()):
                # Lấy thông tin item
                item_info = shop_data.get(item_name, {})
                
                # Mặc định lấy loại từ DB, nếu không có thì là ITEM
                item_type = item_info.get('type', 'ITEM') 
                
                # Lấy ảnh
                img_url = item_info.get('image', '')
                if not img_url:
                    img_url = "https://cdn-icons-png.flaticon.com/512/9630/9630454.png" # Ảnh mặc định

                # 🔥🔥🔥 [FIX QUAN TRỌNG] ÉP BUỘC RƯƠNG BÁU LÀ GACHA_BOX 🔥🔥🔥
                # Dù trong Admin bạn lỡ để là ITEM hay gì, code này sẽ sửa lại hết.
                if "Rương" in item_name or "ruong" in item_name.lower(): 
                    item_type = "GACHA_BOX"
                    # Fix luôn ảnh nếu bị lỗi (như trong hình của bạn)
                    if "via.placeholder" in img_url or not img_url: 
                         img_url = "https://cdn-icons-png.flaticon.com/512/9336/9336056.png"
                # -------------------------------------------------------------

                with cols_kho[i % 4]:
                    # Card hiển thị
                    st.markdown(f"""
                        <div style="background:#3e2723; border:2px solid #8d6e63; border-radius:10px; padding:10px; text-align:center; position:relative; height: 160px; display: flex; flex-direction: column; justify-content: space-between;">
                            <div style="position:absolute; top:5px; right:5px; background:#e74c3c; color:white; border-radius:50%; width:25px; height:25px; line-height:25px; font-weight:bold; font-size:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">{count}</div>
                            <div style="flex-grow: 1; display: flex; align-items: center; justify-content: center;">
                                <img src="{img_url}" style="width:60px; height:60px; object-fit:contain;">
                            </div>
                            <div style="font-weight:bold; color:#f1c40f; font-size:14px; margin-top: 5px; height:40px; overflow:hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">{item_name}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Nút bấm hành động (Đã được mở khóa nhờ đoạn Fix ở trên)
                    if item_type == "GACHA_BOX":
                        if st.button("🎲 MỞ NGAY", key=f"open_{i}", use_container_width=True, type="primary"):
                            rewards = xu_ly_mo_ruong(user_id, item_name, item_info, st.session_state.data, save_data_func)
                            st.session_state.gacha_result = {"name": item_name, "rewards": rewards}
                            st.rerun()
                            
                    elif item_type in ["CONSUMABLE", "BUFF_STAT"]:
                        if st.button("⚡ SỬ DỤNG", key=f"use_{i}", use_container_width=True):
                             st.toast("Chức năng đang phát triển", icon="🔨")
                    else:
                        st.button("🔒 Đã sở hữu", disabled=True, key=f"lock_{i}")

        # Kiểm tra Popup kết quả
        if "gacha_result" in st.session_state:
            res = st.session_state.gacha_result
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
    unlocked = user_data.get('unlocked_ranks', [])
    current_rank = user_data.get('current_rank', "Học Sĩ")

    st.markdown(f"**KPI Hiện tại của bạn:** `{user_kpi}` 🏆 | **Danh hiệu hiện tại:** `{current_rank}`")
    st.divider()

    # Hiển thị danh sách danh hiệu
    for rank in st.session_state.rank_settings:
        r_name = rank["Danh hiệu"]
        r_kpi = rank["KPI Yêu cầu"]
        r_color = rank["Màu sắc"]
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
                <div style="padding:15px; border-radius:10px; border-left: 10px solid {r_color}; 
                            background-color: #262730; margin-bottom:10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                    <h4 style="margin:0; color:{r_color};">{r_name}</h4>
                    <p style="margin:0; font-size:0.9em; color: #bdc3c7;">Yêu cầu: {r_kpi} KPI</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.write("") 
            if r_name == current_rank:
                st.success("🌟 Đang dùng")
            elif r_name in unlocked:
                if st.button(f"SỬ DỤNG", key=f"use_{r_name}", use_container_width=True):
                    st.session_state.data[user_id]['current_rank'] = r_name
                    
                    # [FIX] Gọi hàm lưu đúng chuẩn (truyền data vào)
                    save_data_func(st.session_state.data)
                    
                    st.rerun()
            elif user_kpi >= r_kpi:
                if st.button(f"KÍCH HOẠT", key=f"active_{r_name}", use_container_width=True, type="primary"):
                    if 'unlocked_ranks' not in st.session_state.data[user_id]:
                        st.session_state.data[user_id]['unlocked_ranks'] = []
                    
                    st.session_state.data[user_id]['unlocked_ranks'].append(r_name)
                    st.session_state.data[user_id]['current_rank'] = r_name
                    
                    # [FIX] Gọi hàm lưu đúng chuẩn (truyền data vào)
                    save_data_func(st.session_state.data)
                    
                    st.balloons()
                    st.success(f"Chúc mừng! Bạn đã đạt danh hiệu {r_name}")
                    st.rerun()
            else:
                st.info(f"🔒 Cần thêm {r_kpi - user_kpi} KPI")                

def trien_khai_combat_pho_ban(user_id, land_id, p_id, dungeon_config, save_data_func):

    # 🔥 1. CẦU DAO TỰ ĐỘNG (AUTO-KILL SWITCH) 🔥
    current_page = st.session_state.get("page", "")
    
    # Kiểm tra: Nếu trang hiện tại KHÔNG PHẢI là trang phó bản
    if "Phó bản" not in current_page: 
        st.session_state.dang_danh_dungeon = False
        keys_to_clean = ["dungeon_questions", "current_q_idx", "correct_count", "victory_processed"]
        for k in keys_to_clean:
            if k in st.session_state: del st.session_state[k]
        for k in list(st.session_state.keys()):
            if k.startswith("start_time_"): del st.session_state[k]
        return

    # --- PHẦN 1: KHỞI TẠO TRẠNG THÁI (CHỈ CHẠY 1 LẦN) ---
    if "dungeon_questions" not in st.session_state:
        p_data = dungeon_config[land_id]["phases"][p_id]
        p_num = int(p_id.split('_')[1])
        difficulty_map = {1: "easy", 2: "medium", 3: "hard", 4: "extreme"}
        target_diff = p_data.get('quiz_level', difficulty_map.get(p_num, "easy"))
        
        # [FIX] ĐỌC FILE AN TOÀN TRỰC TIẾP
        path_quiz = f"quiz_data/grade_6/{land_id}.json"
        all_quizzes = {}
        
        if os.path.exists(path_quiz):
            try:
                with open(path_quiz, 'r', encoding='utf-8') as f:
                    all_quizzes = json.load(f)
            except Exception as e:
                st.error(f"Lỗi đọc file câu hỏi {land_id}: {e}")
        else:
            # Fallback logic (nếu cần)
            pass

        pool = all_quizzes.get(target_diff, [])
        
        # Nếu mức độ khó này hết câu hỏi, lấy mức độ khác bù vào
        if not pool:
            for alt in ["extreme", "hard", "medium", "easy"]:
                pool = all_quizzes.get(alt, [])
                if pool: break
        
        # 🔥 [UPDATE QUAN TRỌNG] CHUẨN HÓA DỮ LIỆU (NORMALIZE)
        # Duyệt qua pool để đảm bảo mọi câu hỏi đều có key 'answer'
        # Giúp logic phía sau không bị lỗi dù file json cũ hay mới
        if pool:
            for q in pool:
                # Nếu thiếu 'answer' nhưng có 'correct_answer' -> Copy sang
                if "answer" not in q and "correct_answer" in q:
                    q["answer"] = q["correct_answer"]

        # Nếu vẫn không có câu hỏi -> Dùng câu hỏi mẫu
        if not pool:
             pool = [{"question": "1+1=?", "options": ["2","3"], "answer": "2"}]

        num_q = p_data.get('num_questions', 5)
        st.session_state.dungeon_questions = random.sample(pool, min(len(pool), num_q)) if pool else []
        st.session_state.current_q_idx = 0
        st.session_state.correct_count = 0

    # --- PHẦN 2: LOGIC ĐIỀU KHIỂN VÒNG LẶP CÂU HỎI ---
    questions = st.session_state.get("dungeon_questions", [])
    idx = st.session_state.get("current_q_idx", 0)
    
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
        # Key thời gian độc nhất cho mỗi câu hỏi để tránh conflict
        time_key = f"start_time_{land_id}_{p_id}_{idx}"
        
        if time_key not in st.session_state:
            st.session_state[time_key] = time.time()
        
        elapsed = time.time() - st.session_state[time_key]
        remaining = max(0, time_limit - int(elapsed))

        # Xử lý hết giờ (Timeout)
        if remaining == 0:
            st.toast(f"⏰ HẾT GIỜ! Đáp án là: {q.get('answer', 'Unknown')}", icon="⚠️")
            st.session_state.current_q_idx += 1
            time.sleep(1)
            st.rerun()

        # 2. Giao diện làm bài
        combat_placeholder = st.empty()
        
        with combat_placeholder.container():
            st.markdown(f"### ⚔️ PHASE {p_id.split('_')[1]}: {p_data['title']}")
            st.progress((idx) / len(questions), text=f"Tiến độ: {idx}/{len(questions)} câu")
            
            t_col1, t_col2 = st.columns([1, 4])
            with t_col1:
                color = "red" if remaining < 5 else "black"
                # Thêm key để force rerender thời gian
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
                            # Thêm 'remaining' vào key để tránh lỗi Duplicate Widget ID khi Rerun
                            if st.button(option, key=f"btn_ans_{idx}_{i}_{remaining}", use_container_width=True):
                                
                                # --- [FIX] LOGIC SO SÁNH ĐÁP ÁN THÔNG MINH ---
                                # Lấy chữ cái đầu (A, B, C, D) để so sánh cho chắc chắn
                                user_key = str(option).strip()[0].upper()
                                # Vì đã normalize ở trên, ta an tâm dùng q['answer']
                                ans_key = str(q['answer']).strip()[0].upper()
                                
                                if user_key == ans_key:
                                    st.session_state.correct_count += 1
                                    st.toast("🎯 CHÍNH XÁC!", icon="✅")
                                else:
                                    # Lấy full đáp án đúng để hiển thị thông báo
                                    full_ans = q['answer']
                                    st.toast(f"❌ SAI RỒI! Đáp án là: {full_ans}", icon="⚠️")
                                
                                st.session_state.current_q_idx += 1
                                time.sleep(0.5)
                                st.rerun()

        # 3. Xử lý hết giờ
        if remaining <= 0:
            st.error("⏰ HẾT GIỜ! Quái vật đã phản đòn.")
            time.sleep(1)
            st.session_state.current_q_idx += 1
            st.rerun()
            
        # 4. Tự động Rerun
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
                
                # Gọi hàm xử lý nội bộ (cộng tiền, mở khóa phase sau)
                xử_lý_hoàn_thành_phase(user_id, land_id, p_id, dungeon_config, save_data_func, duration=duration)
                
                # [FIX QUAN TRỌNG] GỌI LƯU CLOUD ĐÚNG CÚ PHÁP
                save_data_func(st.session_state.data)
                
                st.session_state.victory_processed = True
            
            st.success("🏆 CHIẾN THẮNG! KẺ ĐỊCH ĐÃ BỊ TIÊU DIỆT.")
            if st.button("🌟 TIẾP TỤC HÀNH TRÌNH", type="primary", use_container_width=True):
                st.session_state.dang_danh_dungeon = False
                for k in list(st.session_state.keys()):
                    if k.startswith("dungeon_") or k.startswith("start_time_") or k in ["current_q_idx", "correct_count", "victory_processed"]:
                        del st.session_state[k]
                st.rerun()
        
        # --- TRƯỜNG HỢP THUA ---
        else:
            st.error(f"💀 GỤC NGÃ! Bạn trả lời đúng {correct}/{len(questions)} câu (Cần {required} câu).")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 THỬ LẠI", use_container_width=True):
                    keys_to_reset = ["dungeon_questions", "current_q_idx", "correct_count", "victory_processed"]
                    for k in keys_to_reset:
                        if k in st.session_state: del st.session_state[k]
                    for key in list(st.session_state.keys()):
                        if key.startswith("start_time_"): del st.session_state[key]
                    st.rerun()

            with c2:
                if st.button("🏳️ RỜI KHỎI", use_container_width=True):
                    st.session_state.dang_danh_dungeon = False
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
    Lấy log thám hiểm (Đã tích hợp cơ chế 'Khiên bảo vệ' của bạn và xử lý đa định dạng dữ liệu)
    """
    # 1. KHIÊN BẢO VỆ CẤP 1
    data = st.session_state.get('data', {})
    if not isinstance(data, dict):
        return []

    filtered_logs = []
    str_land_id = str(land_id)

    # 2. VÒNG LẶP AN TOÀN
    for u_id, u_info in data.items():
        # 🛡️ KHIÊN BẢO VỆ CẤP 2: Lọc bỏ key hệ thống & lỗi format
        if u_id in ['rank_settings', 'shop_items', 'events', 'admin', 'system_config']:
            continue
        if not isinstance(u_info, dict):
            continue 

        # 3. Lấy tiến độ (Xử lý linh hoạt int hoặc dict)
        progress_data = u_info.get('dungeon_progress', {})
        if not isinstance(progress_data, dict):
            progress_data = {}
            
        if str_land_id in progress_data:
            entry = progress_data[str_land_id]
            
            # --- XỬ LÝ ĐA ĐỊNH DẠNG (Quan trọng) ---
            # Dữ liệu có thể là số nguyên (Phase) hoặc Dict (Phase + Time)
            if isinstance(entry, dict):
                phase_val = entry.get('phase', 0)
                last_time_str = entry.get('last_run', '') # Dùng để sort nếu cần
                reward_info = entry.get('last_reward', 'Tài nguyên bí ẩn')
                # Chuyển đổi time string sang timestamp để sort chính xác
                try:
                    import datetime
                    sort_time = datetime.datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S").timestamp()
                except:
                    sort_time = 0
            else:
                # Trường hợp cũ: chỉ lưu số phase (int hoặc str)
                try:
                    phase_val = int(entry)
                except:
                    phase_val = 0
                sort_time = 0
                reward_info = "Tài nguyên cơ bản"

            # 4. LỌC VÀ LẤY QUÀ TỪ INVENTORY
            if phase_val > 0: # Chỉ lấy nếu đã chơi
                # Nếu chưa có reward trong dungeon_progress, thử lấy từ inventory (logic của bạn)
                if reward_info == "Tài nguyên cơ bản":
                    inventory = u_info.get('inventory', {})
                    if isinstance(inventory, dict) and inventory:
                        try:
                            reward_info = list(inventory.values())[-1]
                        except: pass
                    elif isinstance(inventory, list) and inventory:
                        reward_info = inventory[-1]

                filtered_logs.append({
                    "name": u_info.get('name', 'Học sĩ ẩn danh'),
                    "phase": phase_val,
                    "time": sort_time, # Dùng để sắp xếp người mới nhất
                    "reward_recent": reward_info
                })

    return filtered_logs

def get_arena_logs():
    """
    Lấy dữ liệu Tứ đại cao thủ và Lịch sử đấu trường TỪ GOOGLE SHEETS (thông qua load_loi_dai)
    """
    try:
        # [QUAN TRỌNG] Gọi hàm này để lấy dữ liệu thật từ Sheets (đã cache)
        # Thay vì lấy st.session_state.arena_history rỗng tuếch
        ld_data = load_loi_dai() 
        matches = ld_data.get('matches', {})
    except:
        return [], []

    win_counts = {}
    recent_matches = []
    
    # Sắp xếp trận đấu mới nhất lên đầu
    sorted_matches = sorted(matches.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)

    for mid, m in sorted_matches:
        if m.get('status') == 'finished':
            # --- 1. TÍNH ĐIỂM CAO THỦ ---
            winner = m.get('winner')
            winners_list = []
            
            # Xác định danh sách người thắng (Team hoặc Solo)
            if winner == 'team1':
                winners_list = m.get('challenger_team', [])
                winner_text = "Đội Thách Đấu"
            elif winner == 'team2':
                winners_list = m.get('opponent_team', [])
                winner_text = "Đội Nhận Kèo"
            elif winner and winner != 'Hòa':
                winners_list = [winner]
                # Lấy tên hiển thị
                w_name = st.session_state.data.get(winner, {}).get('name', 'Ẩn danh')
                winner_text = w_name
            else:
                winner_text = "Hòa"

            # Cộng điểm thắng
            for uid in winners_list:
                if uid: win_counts[uid] = win_counts.get(uid, 0) + 1

            # --- 2. TẠO LOG NHẬT KÝ (Lấy 10 trận) ---
            if len(recent_matches) < 10:
                p1_id = m.get('challenger')
                p1_name = st.session_state.data.get(p1_id, {}).get('name', 'Người bí ẩn')
                
                p2_id = m.get('opponent')
                p2_name = st.session_state.data.get(p2_id, {}).get('name', 'Đối thủ')
                
                # Format tỷ số
                score = f"{m.get('final_score_team1', 0)} - {m.get('final_score_team2', 0)}"
                
                recent_matches.append({
                    "p1": p1_name,
                    "p2": p2_name,
                    "score": score,
                    "bet": m.get('bet', 0),
                    "winner_name": winner_text
                })

    # --- 3. XỬ LÝ TOP 4 ---
    sorted_winners = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)[:4]
    top_4_details = []
    
    for uid, wins in sorted_winners:
        u_name = st.session_state.data.get(uid, {}).get('name', uid)
        top_4_details.append({"name": u_name, "wins": wins})
        
    return top_4_details, recent_matches    

from datetime import datetime

def save_all_to_sheets(all_data):
    """
    PHIÊN BẢN FINAL (CẬP NHẬT ĐẦY ĐỦ):
    1. Lưu Players (Bảo tồn Admin).
    2. Lưu Settings & Boss.
    3. Lưu Shop.
    4. [MỚI] Lưu Admin Notices (Thông báo hệ thống).
    """
    import streamlit as st
    import json
    from datetime import datetime
    
    # -----------------------------------------------------------
    # HÀM PHỤ TRỢ: CHUYỂN ĐỔI SỐ AN TOÀN
    # -----------------------------------------------------------
    def safe_int(val):
        try:
            if val is None or str(val).strip() == "":
                return 0
            clean_str = str(val).replace(',', '.')
            return int(float(clean_str))
        except:
            return 0
    # -----------------------------------------------------------

    # --- [BƯỚC 0] ĐẢM BẢO ADMIN LUÔN TỒN TẠI ---
    if 'admin' not in all_data:
        # Nếu đang có trong session thì lấy ra, không thì tạo mới
        if 'data' in st.session_state and 'admin' in st.session_state.data:
            all_data['admin'] = st.session_state.data['admin']
        else:
            all_data['admin'] = {
                "name": "Administrator", "password": "admin", "role": "admin",
                "grade": "Hệ thống", "team": "Quản trị", "kpi": 0, "level": 99,
                "hp": 9999, "hp_max": 9999
            }
            
    if not all_data or len(all_data) < 1: 
        st.error("⛔ Dữ liệu rỗng. Hủy lệnh lưu!")
        return False

    with st.expander("🕵️ NHẬT KÝ ĐỒNG BỘ (DEBUG)", expanded=False):
        try:
            from user_module import get_gspread_client
            client = get_gspread_client()
            
            # Mở Sheet
            secrets_gcp = st.secrets.get("gcp_service_account", {})
            if "spreadsheet_id" in secrets_gcp: 
                sh = client.open_by_key(secrets_gcp["spreadsheet_id"])
            elif "spreadsheet_url" in secrets_gcp: 
                sh = client.open_by_url(secrets_gcp["spreadsheet_url"])
            else: 
                sh = client.openall()[0]

            # =========================================================
            # --- 1. ĐỒNG BỘ TAB "Players" ---
            # =========================================================
            try:
                try: wks_players = sh.worksheet("Players")
                except: wks_players = sh.sheet1
                
                headers = ["user_id", "name", "team", "role", "password", "kpi", "exp", "level", "hp", "hp_max", "world_chat_count", "stats_json", "inventory_json", "progress_json"]
                player_rows = [headers]
                count_student = 0 
                
                # Các key hệ thống cần bỏ qua khi lưu vào danh sách học sinh
                system_keys = ["rank_settings", "system_config", "shop_items", "temp_loot_table", "admin_notices"]

                for uid, info in all_data.items():
                    # Bỏ qua nếu không phải dict hoặc là key hệ thống
                    if not isinstance(info, dict) or uid in system_keys:
                        continue
                        
                    # Logic đếm: Chỉ đếm học sinh
                    if str(info.get('role')) != 'admin':
                        count_student += 1
                    
                    # --- CHUẨN BỊ DATA ---
                    stats_keys = [
                        "Vi_Pham", "Bonus", "KTTX", "KT Sản phẩm", "KT Giữa kỳ", "KT Cuối kỳ", 
                        "Tri_Thuc", "Chien_Tich", "Vinh_Du", "Vinh_Quang", 
                        "total_score", "titles", "best_time",
                        "reborn_at", "last_defeat"
                    ]
                    
                    stats_data = {}
                    for k in stats_keys:
                        if k in info:
                            stats_data[k] = info[k]
                            
                    special_perms = info.get('special_permissions', {}) if isinstance(info.get('special_permissions'), dict) else {}
                    
                    # --- TẠO DÒNG ---
                    row = [
                        str(uid), 
                        info.get('name', ''), 
                        info.get('team', 'Chưa phân tổ'), 
                        info.get('role', 'u3'),
                        str(info.get('password', '123456')), 
                        
                        safe_int(info.get('kpi', 0)),    
                        safe_int(info.get('exp', 0)),    
                        safe_int(info.get('level', 1)), 
                        safe_int(info.get('hp', 100)),  
                        safe_int(info.get('hp_max', 100)), 
                        
                        special_perms.get('world_chat_count', 0),
                        
                        json.dumps(stats_data, ensure_ascii=False),
                        json.dumps(info.get('inventory', {}), ensure_ascii=False),
                        json.dumps(info.get('dungeon_progress', {}), ensure_ascii=False)
                    ]
                    player_rows.append(row)

                # Ghi đè lên Sheet
                if len(player_rows) > 1: 
                    wks_players.clear()
                    wks_players.update('A1', player_rows) 
                    st.write(f"✅ Tab Players: Đã lưu {len(player_rows)-1} dòng (Bao gồm Admin).")
                else:
                    st.warning("⚠️ Danh sách rỗng.")
                    
            except Exception as e:
                st.error(f"❌ Lỗi tab Players: {e}")
                return False

            # =========================================================
            # --- 2. ĐỒNG BỘ SETTINGS & BOSS ---
            # =========================================================
            try:
                try: wks_settings = sh.worksheet("Settings")
                except: wks_settings = None

                if wks_settings:
                    settings_rows = [["Config_Key", "Value"]]
                    
                    if "rank_settings" in all_data:
                        settings_rows.append(["rank_settings", json.dumps(all_data["rank_settings"], ensure_ascii=False)])
                    
                    sys_conf = all_data.get('system_config', {})
                    for key, val in sys_conf.items():
                        if key == 'active_boss':
                            if val: 
                                final_boss_json = {"active_boss": val}
                                settings_rows.append(["active_boss", json.dumps(final_boss_json, ensure_ascii=False)])
                        else:
                            settings_rows.append([key, json.dumps(val, ensure_ascii=False)])
                    
                    if len(settings_rows) >= 1: 
                        wks_settings.clear()
                        wks_settings.update('A1', settings_rows)
                        
            except Exception as e:
                st.warning(f"⚠️ Lỗi tab Settings: {e}")

            # =========================================================
            # --- 3. ĐỒNG BỘ SHOP ---
            # =========================================================
            try:
                wks_shop = sh.worksheet("Shop")
                shop_items = all_data.get('shop_items', {})
                shop_rows = [["ID", "Name", "Type", "Price", "Currency", "Full_Data_JSON"]]
                
                if shop_items:
                    for item_id, info in shop_items.items():
                        if isinstance(info, dict):
                            full_json_str = json.dumps(info, ensure_ascii=False)
                            shop_rows.append([
                                str(item_id), 
                                str(info.get('name', item_id)), 
                                str(info.get('type', 'COMMON')), 
                                info.get('price', 0), 
                                str(info.get('currency_buy', 'kpi')), 
                                full_json_str 
                            ])
                wks_shop.clear()
                wks_shop.update('A1', shop_rows)
            except Exception as e:
                st.warning(f"⚠️ Lỗi tab Shop: {e}")

            # =========================================================
            # --- 4. [MỚI] ĐỒNG BỘ ADMIN NOTICES (THÔNG BÁO) ---
            # =========================================================
            if 'admin_notices' in all_data:
                try:
                    wks_notices = sh.worksheet("admin_notices")
                    
                    # Chuẩn bị dữ liệu (Dòng 2 trở đi, giữ lại header dòng 1)
                    rows_to_write = []
                    for note in all_data['admin_notices']:
                        row = [
                            str(note.get('id', '')),
                            note.get('content', ''),
                            note.get('type', 'marquee'),
                            note.get('time', '')
                        ]
                        rows_to_write.append(row)
                    
                    # Xóa dữ liệu cũ (chỉ xóa nội dung, giữ header)
                    wks_notices.batch_clear(["A2:D1000"]) 
                    
                    # Ghi dữ liệu mới
                    if rows_to_write:
                        wks_notices.update(range_name="A2", values=rows_to_write)
                        st.write(f"✅ Tab admin_notices: Đã lưu {len(rows_to_write)} thông báo.")
                        
                except Exception as e:
                    # Lỗi này thường do chưa tạo tab admin_notices, báo nhẹ nhàng thôi
                    st.caption(f"⚠️ Không thể lưu thông báo (Kiểm tra xem đã tạo tab 'admin_notices' chưa): {e}")

            # =========================================================
            # --- 5. GHI LOG ---
            # =========================================================
            try:
                try: wks_log = sh.worksheet("Logs")
                except: wks_log = sh.worksheet("Log")
                wks_log.append_row([datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "SYSTEM", "Đồng bộ thành công"])
            except: pass

            st.balloons()
            return True
            
        except Exception as e:
            st.error(f"❌ LỖI KẾT NỐI: {e}")
            return False

def load_data_from_sheets():
    """
    Truy xuất toàn bộ dữ liệu vương quốc từ Cloud:
    1. Tab Players: Dữ liệu học sĩ.
    2. Tab Settings: Cấu hình hệ thống (Boss, Rank).
    3. Tab Shop: Vật phẩm tiệm tạp hóa.
    4. [MỚI] Tab admin_notices: Thông báo hệ thống.
    """
    try:
        print("☁️ Đang kết nối tới Google Sheets...")
        import json
        import streamlit as st
        from user_module import get_gspread_client
        
        client = get_gspread_client()
        
        # Mở file Sheet
        secrets_gcp = st.secrets.get("gcp_service_account", {})
        if "spreadsheet_id" in secrets_gcp: 
            spreadsheet = client.open_by_key(secrets_gcp["spreadsheet_id"])
        elif "spreadsheet_url" in secrets_gcp: 
            spreadsheet = client.open_by_url(secrets_gcp["spreadsheet_url"])
        else: 
            spreadsheet = client.openall()[0]
        
        # Biến chứa toàn bộ dữ liệu trả về (RAM)
        loaded_data = {
            "system_config": {}, 
            "shop_items": {},
            "rank_settings": [],
            "admin_notices": [] # [MỚI] Khởi tạo list rỗng
        }

        # --- BẢNG MÃ KHỬ DẤU TIẾNG VIỆT ---
        vietnamese_map = {
            'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a', 'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
            'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
            'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o', 'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
            'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u', 'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
            'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
            'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
            'đ': 'd', ' ': '' 
        }

        # =========================================================
        # 1. TẢI DỮ LIỆU HỌC SĨ (Tab Players)
        # =========================================================
        try:
            try: sh_players = spreadsheet.worksheet("Players")
            except: sh_players = spreadsheet.sheet1
                
            player_records = sh_players.get_all_records()
            
            for r in player_records:
                raw_uid = str(r.get('user_id') or r.get('u_id') or r.get('name', '')).strip().lower()
                if not raw_uid: continue

                # Chuẩn hóa ID
                if str(r.get('role', '')).lower() == 'admin':
                    uid = 'admin'
                else:
                    temp_uid = raw_uid
                    for char, replacement in vietnamese_map.items():
                        temp_uid = temp_uid.replace(char, replacement)
                    uid = temp_uid
                
                # Parse JSON
                try: stats = json.loads(str(r.get('stats_json', '{}')))
                except: stats = {}
                try: inventory = json.loads(str(r.get('inventory_json', '[]')))
                except: inventory = {}
                try: progress = json.loads(str(r.get('progress_json', '{}')))
                except: progress = {}

                # Hàm làm sạch số
                def clean_int(val):
                    try: return int(float(str(val).replace(',', '.')))
                    except: return 0

                # Build User Object
                user_info = {
                    "name": r.get('name', ''),
                    "team": r.get('team', 'Chưa phân tổ'),
                    "password": str(r.get('password', '123456')).strip().replace(".0", ""),
                    "role": str(r.get('role', 'player')).strip().lower(),
                    "kpi": clean_int(r.get('kpi', 0)),
                    "exp": clean_int(r.get('exp', 0)),
                    "level": r.get('level', 1),
                    "hp": clean_int(r.get('hp', 100)),
                    "hp_max": r.get('hp_max', 100),
                    "inventory": inventory,
                    "dungeon_progress": progress
                }
                
                # Bảo vệ chỉ số gốc khỏi bị stats_json ghi đè
                forbidden_keys = ["kpi", "exp", "level", "hp", "hp_max", "name", "role", "user_id"]
                if isinstance(stats, dict):
                    for k, v in stats.items():
                        if k not in forbidden_keys:
                            user_info[k] = v
                
                loaded_data[uid] = user_info

        except Exception as e:
            print(f"⚠️ Lỗi đọc tab Players: {e}")

        # =========================================================
        # 2. TẢI CẤU HÌNH (Tab Settings) - BOSS & RANK
        # =========================================================
        try:
            sh_settings = spreadsheet.worksheet("Settings")
            settings_records = sh_settings.get_all_records()

            for row in settings_records:
                key = str(row.get('Config_Key', '')).strip()
                raw_value = str(row.get('Value', ''))
                
                if key and raw_value:
                    try:
                        clean_value = raw_value.replace("“", '"').replace("”", '"').replace("’", "'")
                        decoded_val = json.loads(clean_value)
                        
                        if key == "active_boss":
                            if isinstance(decoded_val, dict) and "active_boss" in decoded_val:
                                    loaded_data['system_config']['active_boss'] = decoded_val["active_boss"]
                            else:
                                    loaded_data['system_config']['active_boss'] = decoded_val
                        else:
                            loaded_data['system_config'][key] = decoded_val
                            if key == 'rank_settings':
                                loaded_data['rank_settings'] = decoded_val

                    except Exception as json_error:
                        print(f"❌ Lỗi JSON Settings '{key}': {json_error}")

        except Exception as e:
            print(f"⚠️ Lỗi tab Settings: {e}")

        # =========================================================
        # 3. TẢI TIỆM TẠP HÓA (Tab Shop)
        # =========================================================
        try:
            sh_shop = spreadsheet.worksheet("Shop")
            shop_records = sh_shop.get_all_records()
            shop_dict = {}
            
            for r in shop_records:
                item_id = str(r.get('ID', '') or r.get('Item_ID', '')).strip()
                if not item_id: continue
                
                raw_json = str(r.get('Full_Data_JSON') or r.get('Effect_JSON') or '{}')
                try:
                    clean_json = raw_json.replace("“", '"').replace("”", '"').replace("’", "'")
                    full_item_data = json.loads(clean_json)
                    if not full_item_data: raise Exception("Empty JSON")
                    full_item_data['id'] = item_id
                    shop_dict[item_id] = full_item_data
                except:
                     shop_dict[item_id] = {
                         "id": item_id, 
                         "name": r.get('Name', '') or r.get('Item_Name', ''), 
                         "price": r.get('Price', 0), 
                         "type": r.get('Type', 'COMMON'),
                         "currency_buy": r.get('Currency', 'kpi')
                     }

            loaded_data['shop_items'] = shop_dict

        except Exception as e:
            print(f"ℹ️ Lỗi tải Shop: {e}")

        # =========================================================
        # 4. [MỚI] TẢI THÔNG BÁO (Tab admin_notices)
        # =========================================================
        try:
            # Kiểm tra xem tab có tồn tại không trước khi đọc
            try:
                sh_notices = spreadsheet.worksheet("admin_notices")
                notice_records = sh_notices.get_all_records()
                
                # Convert list of dicts thành list chuẩn
                # Sheet trả về: [{'id': 123, 'content': 'abc', ...}, ...]
                # Đúng format chúng ta cần luôn!
                loaded_data['admin_notices'] = notice_records
                print(f"📢 Đã tải {len(notice_records)} thông báo.")
                
            except:
                # Nếu chưa có tab admin_notices thì thôi, không báo lỗi đỏ
                loaded_data['admin_notices'] = []
                print("ℹ️ Chưa có tab 'admin_notices', bỏ qua.")
                
        except Exception as e:
            print(f"⚠️ Lỗi tải Admin Notices: {e}")


        # --- KẾT THÚC ---
        if not loaded_data: return None

        # 5. CẬP NHẬT SESSION STATE
        
        # Shop
        if 'shop_items' not in st.session_state: st.session_state.shop_items = {}
        st.session_state.shop_items = loaded_data['shop_items']
        
        # System Config
        if 'system_config' not in st.session_state: st.session_state.system_config = {}
        st.session_state.system_config = loaded_data['system_config']
        
        # Rank Settings
        st.session_state.rank_settings = loaded_data['rank_settings']

        # [MỚI] Admin Notices
        # Không cần gán vào st.session_state riêng biệt vì nó nằm trong loaded_data (all_data) rồi
        
        return loaded_data

    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng Load Data: {e}")
        return None