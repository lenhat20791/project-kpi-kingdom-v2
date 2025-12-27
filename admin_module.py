import re
import pandas as pd
import streamlit as st
import time
import io
import json
import os
import unicodedata
import random
import user_module
from datetime import datetime
from user_module import hien_thi_doi_mat_khau
import os
import shutil
from datetime import datetime, timedelta
import zipfile
import unidecode

def thực_hiện_auto_backup():
    """Tự động sao lưu dữ liệu data.json và loi_dai.json sau mỗi 7 ngày"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Danh sách các file cần sao lưu
    files_to_backup = ["data.json", "loi_dai.json"]
    current_time = datetime.now()
    
    # Kiểm tra xem đã đến lúc backup chưa (Dựa vào file log hoặc thời gian file cũ nhất)
    last_backup_file = os.path.join(backup_dir, "last_backup.log")
    need_backup = False
    
    if not os.path.exists(last_backup_file):
        need_backup = True
    else:
        with open(last_backup_file, "r") as f:
            last_date_str = f.read().strip()
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            if current_time - last_date >= timedelta(days=7): 
                need_backup = True

    if need_backup:
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        for file in files_to_backup:
            if os.path.exists(file):
                # Tạo tên file: backups/20251225_data.json
                shutil.copy(file, os.path.join(backup_dir, f"{timestamp}_{file}"))
        
        # Cập nhật ngày sao lưu cuối cùng
        with open(last_backup_file, "w") as f:
            f.write(current_time.strftime("%Y-%m-%d"))
        return True
    return False

def dọn_dẹp_backup_reset_năm_học():
    """Xóa toàn bộ các file trong thư mục backups khi reset năm học"""
    backup_dir = "backups"
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path) # Xóa file 
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path) # Xóa thư mục con nếu có
            except Exception as e:
                print(f"Lỗi khi xóa {file_path}: {e}")

def gui_thong_bao_admin(loai, noi_dung):
    # Cấu trúc thông báo mới
    notice = {
        "id": int(datetime.now().timestamp()),
        "type": loai, # 'marquee' hoặc 'popup'
        "content": noi_dung,
        "time": datetime.now().strftime("%H:%M %d/%m/%Y"),
        "active": True
    }
    
    # Lưu vào file
    data = []
    if os.path.exists('data/admin_notices.json'):
        with open('data/admin_notices.json', 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except: data = []
    
    # Nếu là popup, ta chỉ giữ lại 1 cái mới nhất để tránh làm phiền khách
    if loai == 'popup':
        data = [n for n in data if n['type'] != 'popup']
        
    data.append(notice)
    
    with open('data/admin_notices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def giao_dien_thong_bao_admin():
    st.subheader("📢 TRUNG TÂM PHÁT THANH ADMIN")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        msg_content = st.text_area("Nội dung thông báo:", placeholder="Nhập nội dung cập nhật hoặc thông báo...")
    with col2:
        msg_type = st.radio("Hình thức:", ["Chạy chữ (Marquee)", "Popup Khẩn cấp"])
    
    if st.button("🗑️ XÓA TẤT CẢ THÔNG BÁO (ADMIN & WORLD CHAT)"):
        # 1. Xóa thông báo của Admin
        if os.path.exists('data/admin_notices.json'):
            os.remove('data/admin_notices.json')
            
        # 2. Xóa luôn tin nhắn Loa phát thanh của người dùng
        if os.path.exists('data/world_announcements.json'):
            # Thay vì xóa file, ta ghi đè bằng một danh sách rỗng để tránh lỗi đọc file ở UI khách
            with open('data/world_announcements.json', 'w', encoding='utf-8') as f:
                json.dump([], f)
        
        st.info("🧹 Đã dọn dẹp sạch sẽ toàn bộ thông báo trên Server!")
        st.rerun()


def hien_thi_thong_bao_he_thong():
    """
    Hàm hiển thị thông báo chạy chữ (Marquee) hoặc Popup cho người dùng.
    """
    import os, json
    import streamlit as st
    
    if os.path.exists('data/admin_notices.json'):
        with open('data/admin_notices.json', 'r', encoding='utf-8') as f:
            try: 
                notices = json.load(f)
            except: 
                notices = []
            
        for n in notices:
            # 1. Hiển thị POPUP KHẨN CẤP
            if n['type'] == 'popup':
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

            # 2. Hiển thị CHẠY CHỮ (MARQUEE)
            elif n['type'] == 'marquee':
                st.markdown(f"""
                    <div style="background: #9c27b0; color: white; padding: 5px; font-weight: bold; border-radius: 5px; margin-bottom: 10px; border: 1px solid #ba68c8;">
                        <marquee behavior="scroll" direction="left" scrollamount="7">
                            🚀 [THÔNG BÁO ADMIN - {n['time']}]: {n['content']} 🚀
                        </marquee>
                    </div>
                """, unsafe_allow_html=True)

def get_reward_options_list():
    """
    Hàm lấy danh sách vật phẩm để nạp vào Drop Table của Boss/Phó bản.
    Tự động phân loại Rương Gacha và Item thường.
    """
    if 'shop_items' not in st.session_state:
        return []

    options = []
    
    # Duyệt qua kho Item (Shop)
    for item_id, item_data in st.session_state.shop_items.items():
        item_type = item_data.get('type', 'UNKNOWN')
        
        # Tạo nhãn hiển thị cho dễ nhìn
        if item_type == 'GACHA_BOX':
            prefix = "🎲 [RƯƠNG]"
        elif item_type == 'BUFF_STAT':
            prefix = "⚔️ [BUFF]"
        elif item_type == 'CONSUMABLE':
            prefix = "💎 [TIÊU THỤ]"
        elif item_type == 'FUNCTIONAL':
            prefix = "🛠️ [CHỨC NĂNG]"
        else:
            prefix = "📦 [ITEM]"
            
        # Format: "🎲 [RƯƠNG] Rương Rồng Thần"
        label = f"{prefix} {item_id}"
        options.append(label)
        
    return sorted(options)

# --- HÀM BỔ TRỢ DỮ LIỆU PHÓ BẢN ---
@st.cache_data
def load_dungeon_config():
    path = "data/dungeon_config.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Nếu chưa có file, tạo cấu trúc mặc định cho 6 vùng đất
    default_config = {}
    lands = ["toan", "van", "anh", "ly", "hoa", "sinh"]
    for land in lands:
        default_config[land] = {
            "name": land.upper(),
            "phases": {}
        }
        for p in range(1, 5):
            default_config[land]["phases"][f"phase_{p}"] = {
                "title": f"Giai đoạn {p}",
                "monster_name": "Quái vật tập sự",
                "monster_img": "https://i.ibb.co/v6m80YV/monster-placeholder.png",
                "quiz_level": "easy",
                "num_questions": 5,
                "time_limit": 15,
                "reward_kpi": 10,
                "reward_exp": 20,
                "item_drop_id": "none",
                "drop_rate": 0
            }
    return default_config

def save_dungeon_config(config):
    if not os.path.exists("data"):
        os.makedirs("data")
    with open("data/dungeon_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def hien_thi_tao_item_pho_ban(save_shop_func):
    with st.expander("🎁 CHẾ TẠO VẬT PHẨM RIÊNG CHO PHÓ BẢN", expanded=False):
        st.info("Tạo nhanh các vật phẩm rơi từ Phó bản (Rìu, Khiên, Thuốc...).")
        
        col1, col2 = st.columns(2)
        with col1:
            item_id = st.text_input("Mã vật phẩm (ID):", placeholder="VD: Riu_Toan_Hoc", help="Viết liền không dấu")
            item_name = st.text_input("Tên hiển thị:", placeholder="VD: 🪓 Rìu Toán Học")
            
            # Chọn loại theo chuẩn mới
            type_mapping = {
                "CONSUMABLE": "💎 Vật phẩm Tiêu thụ (Cộng chỉ số)",
                "BUFF_STAT": "⚔️ Trang bị/Thuốc (Buff chỉ số)",
                "GACHA_BOX": "🎲 Rương Gacha"
            }
            raw_type = st.selectbox("Loại vật phẩm:", list(type_mapping.keys()), format_func=lambda x: type_mapping[x])

        with col2:
            item_img = st.text_input("Link ảnh:", "https://cdn-icons-png.flaticon.com/512/1236/1236525.png")
            
            # Nhập thông số tùy theo loại
            props = {}
            if raw_type == "CONSUMABLE":
                target = st.selectbox("Cộng vào:", ["kpi", "hp", "Tri_Thuc", "Chien_Tich"])
                val = st.number_input("Giá trị cộng:", min_value=1, value=10)
                props = {"target_type": target, "value": val}
                
            elif raw_type == "BUFF_STAT":
                stat = st.selectbox("Buff chỉ số:", ["atk", "hp"])
                val = st.number_input("Giá trị Buff:", min_value=1, value=5)
                dur_type = st.selectbox("Thời hạn:", ["time_limit", "permanent", "one_hit"])
                dur_val = st.number_input("Phút (nếu có hạn):", value=30)
                props = {"target_stat": stat, "value": val, "duration_type": dur_type, "duration_value": dur_val}
        
        if st.button("🛠️ ĐÚC VẬT PHẨM NGAY", use_container_width=True):
            if item_id and item_name:
                # Tạo data chuẩn cấu trúc mới
                new_item = {
                    "id": item_id,
                    "name": item_name,
                    "price": 0, # Hàng drop không bán
                    "currency_buy": "kpi",
                    "image": item_img,
                    "type": raw_type,
                    "properties": props,
                    "desc": "Vật phẩm đặc biệt rơi từ Phó bản."
                }
                
                # Lưu vào kho hệ thống (shop_items)
                st.session_state.shop_items[item_id] = new_item
                save_shop_func(st.session_state.shop_items)
                st.success(f"Đã tạo '{item_name}' thành công! Giờ bạn có thể chọn nó làm phần thưởng.")
                st.rerun()
            else:
                st.error("Vui lòng nhập Mã ID và Tên vật phẩm!")
                
# --- NÂNG CẤP GIAO DIỆN ADMIN CONTROL PHÓ BẢN ---
def hien_thi_admin_control_dungeon(save_shop_func):
    st.title("🛡️ TRUNG TÂM ĐIỀU HÀNH PHÓ BẢN")
    
    # 1. Chức năng tạo đồ phó bản riêng (Gọi hàm đã sửa ở bước trước)
    hien_thi_tao_item_pho_ban(save_shop_func)
    
    config = load_dungeon_config()
    
    # 2. CHUẨN BỊ DANH SÁCH VẬT PHẨM ĐỂ CHỌN (Gồm cả Rương Gacha và Item Shop)
    shop_data = st.session_state.get('shop_items', {})
    
    # Tạo danh sách hiển thị (Label) và danh sách ID thực (Value)
    # Phần tử đầu tiên là "Không rơi đồ"
    drop_options_labels = ["❌ Không rơi đồ"]
    drop_options_ids = ["none"]
    
    for k, v in shop_data.items():
        itype = v.get('type', 'UNKNOWN')
        # Thêm icon phân loại
        if itype == 'GACHA_BOX': icon = "🎲 [RƯƠNG]"
        elif itype == 'BUFF_STAT': icon = "⚔️ [BUFF]"
        elif itype == 'CONSUMABLE': icon = "💎 [TIÊU THỤ]"
        else: icon = "📦 [ITEM]"
            
        label = f"{icon} {v.get('name', k)} ({k})"
        
        drop_options_labels.append(label)
        drop_options_ids.append(k) # ID thực tế để lưu vào file

    # 3. GIAO DIỆN CẤU HÌNH TỪNG VÙNG ĐẤT
    land_ids = ["toan", "van", "anh", "ly", "hoa", "sinh"]
    tabs = st.tabs(["📐 Toán", "📖 Văn", "🇬🇧 Anh", "⚡ Lý", "🧪 Hóa", "🌿 Sinh"])

    for i, tab in enumerate(tabs):
        land_id = land_ids[i]
        with tab:
            for p_num in range(1, 5):
                p_id = f"phase_{p_num}"
                p_data = config[land_id]["phases"][p_id]
                
                with st.expander(f"🚩 PHASE {p_num}: {p_data['title']}"):
                    c1, c2, c3 = st.columns(3)
                    
                    with c1:
                        st.markdown("**👾 Quái vật**")
                        p_data['title'] = st.text_input("Tên Phase:", p_data['title'], key=f"t_{land_id}_{p_id}")
                        p_data['monster_name'] = st.text_input("Tên Quái:", p_data['monster_name'], key=f"mn_{land_id}_{p_id}")
                        p_data['monster_img'] = st.text_input("Ảnh Quái (URL):", p_data['monster_img'], key=f"mi_{land_id}_{p_id}")
                    
                    with c2:
                        st.markdown("**📝 Thử thách**")
                        p_data['quiz_level'] = st.selectbox("Độ khó:", ["easy", "medium", "hard", "extreme"], 
                                                            index=["easy", "medium", "hard", "extreme"].index(p_data['quiz_level']),
                                                            key=f"lvl_{land_id}_{p_id}")
                        p_data['num_questions'] = st.number_input("Số câu hỏi:", 1, 20, p_data['num_questions'], key=f"nq_{land_id}_{p_id}")
                        p_data['time_limit'] = st.number_input("Giây/câu:", 5, 60, p_data['time_limit'], key=f"tl_{land_id}_{p_id}")
                                              
                    with c3:
                        st.markdown("**🎁 Phần thưởng (Loot)**")
                        p_data['reward_kpi'] = st.number_input("KPI:", value=p_data['reward_kpi'], key=f"k_{land_id}_{p_id}")
                        p_data['reward_exp'] = st.number_input("EXP:", value=p_data.get('reward_exp', 0), key=f"e_{land_id}_{p_id}")
                        
                        # --- LOGIC CHỌN VẬT PHẨM MỚI ---
                        current_drop_id = p_data.get('item_drop_id', 'none')
                        
                        # Tìm index hiện tại của item trong danh sách ID
                        try:
                            current_index = drop_options_ids.index(current_drop_id)
                        except ValueError:
                            current_index = 0 # Nếu item cũ bị xóa thì về mặc định
                        
                        # Selectbox hiển thị Label đẹp nhưng trả về Index để lấy ID thực
                        selected_idx = st.selectbox(
                            "Vật phẩm rơi:", 
                            range(len(drop_options_labels)), # Dùng index để map
                            format_func=lambda x: drop_options_labels[x],
                            index=current_index,
                            key=f"item_{land_id}_{p_id}"
                        )
                        
                        # Lưu ID thực vào data
                        p_data['item_drop_id'] = drop_options_ids[selected_idx]
                        
                        # Nhập tỷ lệ
                        p_data['drop_rate'] = st.number_input("Tỷ lệ rơi (%):", 0.0, 100.0, float(p_data['drop_rate']), key=f"dr_{land_id}_{p_id}")

            if st.button(f"💾 LƯU CẤU HÌNH {land_id.upper()}", use_container_width=True):
                save_dungeon_config(config)
                st.success(f"Đã cập nhật dữ liệu cho vùng đất {land_id.upper()}!")
                st.balloons()
                
def save_boss_data(data):
    try:
        with open('data/boss_config.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Lỗi lưu dữ liệu Boss: {e}")
        
import streamlit as st
import json
import os
import time
from datetime import datetime

# --- HÀM PHỤ TRỢ 1: HIỂN THỊ GIAO DIỆN CHỌN QUÀ ---
def hien_thi_bang_chon_qua_boss():
    """
    Hàm này lo việc: Lấy dữ liệu Shop -> Tạo list chọn -> Hiển thị Data Editor
    Trả về: Dữ liệu thô người dùng đang nhập trên bảng.
    """
    # 1. Chuẩn bị danh sách Tiền tệ & Item
    shop_items = st.session_state.get('shop_items', {})
    
    # Map tiền tệ
    currency_options = ["🔵 KPI", "📚 Tri Thức", "⚔️ Chiến Tích", "🏆 Vinh Dự", "✨ Vinh Quang"]
    
    # Map Item từ Shop
    item_options = []
    if shop_items:
        for item_id, item_data in shop_items.items():
            itype = item_data.get('type', 'UNKNOWN')
            if itype == 'GACHA_BOX': prefix = "🎲 [RƯƠNG]"
            elif itype == 'BUFF_STAT': prefix = "⚔️ [BUFF]"
            elif itype == 'CONSUMABLE': prefix = "💎 [TIÊU THỤ]"
            else: prefix = "📦 [ITEM]"
            
            # Label hiển thị: "🎲 [RƯƠNG] Rương Rồng (ruong_rong)"
            label = f"{prefix} {item_data.get('name', item_id)} ({item_id})"
            item_options.append(label)

    full_options = currency_options + item_options

    # 2. Hiển thị bảng Editor
    st.info("💡 Chọn Rương Gacha hoặc Vật phẩm từ danh sách. Tổng tỷ lệ nên là 100% nếu muốn chắc chắn rơi đồ.")

    # Dữ liệu mặc định
    default_data = [
        {"id_display": "🔵 KPI", "amount": 10, "rate": 100},
        {"id_display": "📚 Tri Thức", "amount": 5, "rate": 50}
    ]

    edited_table = st.data_editor(
        default_data, 
        num_rows="dynamic",
        column_config={
            "id_display": st.column_config.SelectboxColumn(
                "💎 Chọn Phần Thưởng",
                options=full_options, 
                required=True,
                width="large"
            ),
            "amount": st.column_config.NumberColumn("Số lượng", min_value=1, default=1),
            "rate": st.column_config.NumberColumn("Tỷ lệ rơi (%)", min_value=1, max_value=100, default=10)
        },
        key="boss_drop_editor_func", # Key riêng để tránh trùng
        use_container_width=True
    )
    
    return edited_table

# --- HÀM PHỤ TRỢ 2: XỬ LÝ DỮ LIỆU ĐỂ LƯU FILE ---
def xu_ly_du_lieu_drop(raw_table_data):
    """
    Hàm này lo việc: Nhận dữ liệu thô -> Tách chuỗi lấy ID -> Trả về List chuẩn JSON
    """
    # Map ngược lại tiền tệ để lấy key chuẩn
    currency_map_reverse = {
        "🔵 KPI": "kpi", "📚 Tri Thức": "Tri_Thuc", 
        "⚔️ Chiến Tích": "Chien_Tich", "🏆 Vinh Dự": "Vinh_Du", 
        "✨ Vinh Quang": "Vinh_Quang"
    }
    
    final_list = []
    for row in raw_table_data:
        display_str = row['id_display']
        
        # Case A: Là tiền tệ
        if display_str in currency_map_reverse:
            entry = {
                "type": "currency",
                "id": currency_map_reverse[display_str],
                "amount": row['amount'],
                "rate": row['rate']
            }
        # Case B: Là Item/Rương (Cần tách ID trong ngoặc)
        else:
            try:
                # "🎲 ... (ID_THAT)" -> Lấy ID_THAT
                real_id = display_str.split('(')[-1].replace(')', '')
            except:
                real_id = display_str
                
            entry = {
                "type": "item",
                "id": real_id,
                "amount": row['amount'],
                "rate": row['rate']
            }
        final_list.append(entry)
        
    return final_list

# --- HÀM CHÍNH: QUẢN LÝ BOSS ---
def admin_quan_ly_boss():
    st.title("👨‍🏫 QUẢN LÝ ĐẠI CHIẾN GIÁO VIÊN")

    # --- PHẦN 1: QUẢN LÝ KHO VẬT PHẨM (GIỮ NGUYÊN TỪ FILE CŨ) ---
    # Đọc kho vật phẩm đã có
    if os.path.exists('data/item_inventory.json'):
        with open('data/item_inventory.json', 'r', encoding='utf-8') as f:
            kho_item = json.load(f)
    else:
        kho_item = []
        
    # Import hàm registry nếu cần (giả sử item_system.py có sẵn)
    try:
        from item_system import get_item_behavior_registry
        registry = get_item_behavior_registry()
    except ImportError:
        registry = {} # Fallback nếu không import được

    with st.expander("🛠️ KHO VẬT PHẨM HUYỀN THOẠI (Admin Đắp Nặn)"):
        if registry:
            col1, col2 = st.columns(2)
            with col1:
                item_id = st.text_input("Tên vật phẩm mới:")
                item_type = st.selectbox("Chọn Loại Logic:", options=list(registry.keys()))
            with col2:
                item_img = st.text_input("Link ảnh Icon (URL):")
            
            # Tự động tạo ô nhập liệu dựa trên định nghĩa Registry
            properties = {}
            item_def = registry[item_type]
            params = item_def["params"]
            labels = item_def.get("labels", {})

            st.write("🔧 **Thiết lập chỉ số:**")
            cols = st.columns(len(params))
            
            for i, (p_name, p_type) in enumerate(params.items()):
                with cols[i % len(cols)]: # Tránh index out of bounds nếu params > cols
                    display_label = labels.get(p_name, p_name)
                    if isinstance(p_type, list):
                        properties[p_name] = st.selectbox(display_label, options=p_type)
                    else:
                        properties[p_name] = st.number_input(display_label, value=0)

            if st.button("➕ LƯU VẬT PHẨM VÀO KHO"):
                if item_id and item_img:
                    new_item = {
                        "id": item_id,
                        "type": item_type,
                        "image": item_img,
                        "properties": properties,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    kho_item.append(new_item)
                    with open('data/item_inventory.json', 'w', encoding='utf-8') as f:
                        json.dump(kho_item, f, indent=4, ensure_ascii=False)
                    st.success(f"✅ Đã đắp nặn thành công: {item_id}!")
                    st.rerun()
                else:
                    st.error("❌ Vui lòng nhập Tên và Link ảnh vật phẩm!")
        else:
             st.warning("Chưa tìm thấy Registry Item. Vui lòng kiểm tra file item_system.py.")
    
    st.divider()

    # --- PHẦN 2: QUẢN LÝ BOSS & ITEM POOL (ĐÃ CẬP NHẬT) ---
    # Nạp dữ liệu Boss từ file
    if os.path.exists('data/boss_config.json'):
        with open('data/boss_config.json', 'r', encoding='utf-8') as f:
            boss_data = json.load(f)
    else:
        boss_data = {"active_boss": None}

    # FORM TRIỆU HỒI BOSS
    with st.form("trieu_hoi_boss_form"):
        st.subheader("🔥 Thiết lập thông tin Boss")
        c1, c2 = st.columns(2)
        with c1:
            ten_boss = st.text_input("Tên Giáo Viên:", "Pháp Sư Toán Học")
            mon_hoc = st.selectbox("Môn Thử Thách:", ["toan", "van", "anh", "ly", "hoa", "sinh"])
            hp_boss = st.number_input("Tổng Sinh Mệnh (HP):", min_value=1000, value=10000, step=1000)
        with c2:
            damage_boss = st.number_input("Sát Thương Boss:", value=20)
            kpi_rate = st.number_input("Tỷ lệ thưởng KPI (mỗi 1000 dmg):", value=1.0)
            anh_boss = st.text_input("Ảnh Boss (URL):", f"assets/teachers/{mon_hoc}.png")

        st.divider()
        st.subheader("🎁 THIẾT LẬP ITEM POOL (Tỷ lệ rơi quà)")
        
        # ===> GỌI HÀM HIỂN THỊ TẠI ĐÂY <===
        raw_data = hien_thi_bang_chon_qua_boss()

        # Nút Submit
        submit = st.form_submit_button("🔥 PHÁT LỆNH TRIỆU HỒI NGAY")

    # XỬ LÝ SAU KHI SUBMIT
    if submit:
        # ===> GỌI HÀM XỬ LÝ DỮ LIỆU TẠI ĐÂY <===
        clean_drop_table = xu_ly_du_lieu_drop(raw_data)
        
        # Kiểm tra tổng tỷ lệ (Optional - cảnh báo nhẹ)
        total_rate = sum(item.get('rate', 0) for item in clean_drop_table)
        if total_rate != 100:
            st.warning(f"⚠️ Tổng tỷ lệ là {total_rate}%. Nếu < 100%, người chơi có thể không nhận được gì.")
        
        new_boss = {
            "ten": ten_boss,
            "mon": mon_hoc,
            "hp_max": hp_boss,
            "hp_current": hp_boss,
            "damage": damage_boss,
            "kpi_rate": kpi_rate,
            "anh": anh_boss,
            "drop_table": clean_drop_table, # <--- Dữ liệu đã sạch
            "status": "active",
            "contributions": {},
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu file
        try:
            with open('data/boss_config.json', 'w', encoding='utf-8') as f:
                json.dump({"active_boss": new_boss}, f, indent=4, ensure_ascii=False)
            st.success(f"✅ Đã triệu hồi {ten_boss} thành công!")
            st.balloons()
            time.sleep(1) # Chờ xíu rồi reload
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi lưu Boss: {e}")

    # --- PHẦN 3: HIỂN THỊ THÔNG TIN BOSS ĐANG CHẠY & LOG ---
    st.divider()
    
    if boss_data.get("active_boss"):
        boss_hien_tai = boss_data["active_boss"]
        
        # THỐNG KÊ CHIẾN TRƯỜNG
        st.subheader("📊 THỐNG KÊ CHIẾN TRƯỜNG")
        if os.path.exists('data/boss_logs.json'):
            with open('data/boss_logs.json', 'r', encoding='utf-8') as f:
                logs_data = json.load(f)
            
            current_logs = [l for l in logs_data if l.get('boss_name') == boss_hien_tai['ten']]
            
            if current_logs:
                st.dataframe(
                    current_logs,
                    column_config={
                        "user_id": "Học Sĩ",
                        "damage": st.column_config.NumberColumn("Sát Thương", format="%d ⚔️"),
                        "rewards": "Vật Phẩm Nhận Được",
                        "time": "Thời Gian"
                    },
                    use_container_width=True
                )
            else:
                st.info("Chưa có học sĩ nào tấn công con Boss này.")
        else:
            st.info("Chưa có dữ liệu lịch sử chiến đấu.")

        st.divider()

        # QUẢN LÝ & GIẢI TÁN BOSS
        st.subheader("🗑️ KHU VỰC QUẢN LÝ")
        st.warning(f"⚠️ Boss **{boss_hien_tai['ten']}** đang án ngữ tại Đấu Trường.")
        
        if st.button("❌ GIẢI TÁN BOSS HIỆN TẠI", use_container_width=True, type="secondary"):
            boss_data["active_boss"] = None
            try:
                with open('data/boss_config.json', 'w', encoding='utf-8') as f:
                    json.dump(boss_data, f, indent=4, ensure_ascii=False)
                
                st.error("💥 Đã xóa Boss! Đấu trường hiện đang trống.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi xóa Boss: {e}")
        
        st.write("") 
        
        # DỌN DẸP LOG
        if os.path.exists('data/boss_logs.json'):
            if st.button("🧹 DỌN DẸP NHẬT KÝ CHIẾN ĐẤU", use_container_width=True, help="Xóa vĩnh viễn lịch sử của Boss này"):
                try:
                    with open('data/boss_logs.json', 'r', encoding='utf-8') as f:
                        logs_data = json.load(f)
                    
                    ten_boss_hien_tai = boss_hien_tai['ten']
                    new_logs = [l for l in logs_data if l.get('boss_name') != ten_boss_hien_tai]
                    
                    with open('data/boss_logs.json', 'w', encoding='utf-8') as f:
                        json.dump(new_logs, f, indent=4, ensure_ascii=False)
                        
                    st.success(f"✨ Đã dọn dẹp sạch nhật ký của {ten_boss_hien_tai}!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi dọn dẹp log: {e}")
    else:
        st.info("☘️ Đấu trường hiện đang yên bình. Chưa có Giáo viên nào được triệu hồi.")
        
    
def hien_thi_giao_dien_admin(save_data_func, save_shop_func):
    # --- TỰ ĐỘNG BACKUP KHI ADMIN ĐĂNG NHẬP ---
    if thực_hiện_auto_backup():
        st.toast("🛡️ Hệ thống đã tự động sao lưu dữ liệu định kỳ (7 ngày).", icon="💾")

    st.title("🛡️ QUẢN TRỊ VƯƠNG QUỐC")
    # =========================================================================
    # 🛡️ CHỐT CHẶN AN TOÀN (CHÈN ĐOẠN NÀY VÀO ĐẦU HÀM)
    # =========================================================================
    # Kiểm tra nếu dữ liệu đang bị lỗi (dạng List) -> Chuyển thành Dict ngay lập tức
    if 'data' in st.session_state and isinstance(st.session_state.data, list):
        st.toast("🔧 Admin: Đang tự động cấu trúc lại dữ liệu...", icon="🛡️")
        fixed_dict = {}
        for item in st.session_state.data:
            if isinstance(item, dict):
                # Tìm key định danh (username, id, name...)
                key = item.get('username') or item.get('u_id') or item.get('id') or item.get('name')
                
                # Ưu tiên key cho admin
                if item.get('role') == 'admin': 
                    key = 'admin'
                
                if key:
                    # Làm sạch key (viết thường, xóa khoảng trắng)
                    clean_key = str(key).strip().lower().replace(" ", "")
                    fixed_dict[clean_key] = item
        
        # Cập nhật lại session_state ngay lập tức
        st.session_state.data = fixed_dict
    # ========================================================================
    page = st.session_state.get("page")

    # ===== 🔑 ĐỔI MẬT KHẨU =====
    if page == "🔑 Đổi mật khẩu":
        hien_thi_doi_mat_khau("admin", save_data_func)

    # ===== 🏠 KPI TOÀN LỚP =====
    elif page == "🏠 Thống kê KPI lớp":
        st.subheader("📊 TRUNG TÂM ĐIỀU HÀNH")
        
        if not st.session_state.data:
            st.info("Chưa có dữ liệu học sinh. Hãy vào mục Quản lý nhân sự để nạp file.")
            return

        # --- 🛠️ ĐOẠN CODE LỌC DỮ LIỆU CHUẨN (CẬP NHẬT) ---
        raw_data = st.session_state.data
        clean_users_data = {}

        # Danh sách các key cần loại bỏ khỏi thống kê
        exclude_keys = ['admin', 'system_config', 'rank_settings', 'shop_items']

        for key, value in raw_data.items():
            # Điều kiện 1: Phải là Dictionary (thông tin người dùng)
            # Điều kiện 2: Key không nằm trong danh sách loại trừ
            if isinstance(value, dict) and key not in exclude_keys:
                clean_users_data[key] = value
        
        # Tạo bảng DataFrame từ dữ liệu đã lọc sạch
        try:
            df_all = pd.DataFrame.from_dict(clean_users_data, orient='index')
        except Exception as e:
            st.error(f"Không thể tạo bảng dữ liệu: {e}")
            return


        # --- C. QUYỀN NĂNG TỐI CAO: CHỈNH SỬA TẤT CẢ ---
        st.write("### 🛠️ BẢNG ĐIỀU CHỈNH CHỈ SỐ TOÀN LỚP")
        st.caption("Nhấn trực tiếp vào ô để sửa điểm. Sau khi sửa xong NHẤN NÚT 💾 CẬP NHẬT.")
        
        # Danh sách cột cho phép Admin sửa
        edit_cols = ['name', 'team', 'kpi', 'Vi_Pham', 'KTTX', 'KT Sản phẩm', 'KT Giữa kỳ', 'KT Cuối kỳ', 'Bonus']
        
        # Đảm bảo các cột tồn tại trong DataFrame để tránh lỗi key
        for col in edit_cols:
            if col not in df_all.columns:
                df_all[col] = 0

        edited_df = st.data_editor(
            df_all[edit_cols],
            use_container_width=True,
            column_config={
                "name": st.column_config.Column("Học Sĩ", disabled=True),
                "team": "Tổ",
                "kpi": st.column_config.NumberColumn("KPI Tổng (Máu)", format="%d 🏆"),
                "Vi_Pham": "Điểm Vi Phạm",
                "Bonus": "Điểm Thưởng"
            }
        )

        if st.button("💾 CẬP NHẬT DỮ LIỆU"):
            for index, row in edited_df.iterrows():
                for col in edit_cols:
                    if col != 'name':
                        st.session_state.data[index][col] = row[col]
            save_data_func()
            st.success("Admin đã cập nhật dữ liệu thành công!")
            st.rerun()

        st.divider()

        # --- 🎨 1. CSS TÙY CHỈNH CHO THẺ METRICS CAO CẤP ---
        st.markdown("""
            <style>
            [data-testid="stMetric"] {
                background: linear-gradient(135deg, #2b2d42 0%, #1a1b2e 100%);
                border: 1px solid #45475a;
                padding: 15px;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                text-align: center;
            }
            [data-testid="stMetric"] label { 
                color: #a6adc8 !important; 
                font-weight: bold; 
                font-size: 1.1rem !important;
            }
            [data-testid="stMetric"] [data-testid="stMetricValue"] { 
                color: #f9e2af !important; 
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("<h2 style='text-align: center; color: #f9e2af;'>⚔️ TRUNG TÂM CHỈ SỐ VƯƠNG QUỐC</h2>", unsafe_allow_html=True)

        # --- 📊 2. HIỂN THỊ 4 THẺ CHỈ SỐ (ĐÃ LỌC ADMIN/SYSTEM) ---
        m1, m2, m3, m4 = st.columns(4)
        total_kpi = df_all['kpi'].sum()
        avg_kpi = df_all['kpi'].mean()
        max_vp = df_all['Vi_Pham'].max()
        
        with m1: st.metric("💰 TỔNG KPI LỚP", f"{total_kpi:,.0f} 🏆")
        with m2: st.metric("📈 KPI TRUNG BÌNH", f"{avg_kpi:.1f}")
        with m3: st.metric("⚠️ VI PHẠM MAX", f"{max_vp}", delta="- Cảnh báo", delta_color="inverse")
        with m4: st.metric("🛡️ QUÂN SỐ", f"{len(df_all)} Học sĩ")

        st.write("") 

        # --- 📈 3. BIỂU ĐỒ VỚI TÊN ĐEN ĐẬM & TO ---
        import altair as alt

        def ve_bieu_do_ngang(df, x_col, y_col, color_hex):
            chart = alt.Chart(df).mark_bar(cornerRadiusEnd=5).encode(
                x=alt.X(f'{x_col}:Q', title=None),
                y=alt.Y(f'{y_col}:N', sort='-x', title=None, axis=alt.Axis(
                    labelFontSize=14,      # Font to rõ
                    labelFontWeight='bold', # Đen đậm
                    labelColor='#000000',  # Màu đen tuyền
                    labelLimit=300         # Không bị cắt tên dài
                )),
                color=alt.value(color_hex)
            ).properties(height=280)
            return st.altair_chart(chart, use_container_width=True)

        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("<h5 style='color: #2ecc71;'>🏆 TOP 5 CHIẾN LỰC</h5>", unsafe_allow_html=True)
            df_all['Diem_KT'] = pd.to_numeric(df_all['KTTX'] + df_all['KT Sản phẩm'] + df_all['KT Giữa kỳ'] + df_all['KT Cuối kỳ'], errors='coerce').fillna(0)
            top_kt = df_all.nlargest(5, 'Diem_KT')[['name', 'Diem_KT']]
            ve_bieu_do_ngang(top_kt, 'Diem_KT', 'name', "#2ecc71")

            st.markdown("<h5 style='color: #e74c3c;'>🚨 DANH SÁCH CẦN NHẮC NHỞ</h5>", unsafe_allow_html=True)
            top_vp = df_all.nlargest(5, 'Vi_Pham')[['name', 'Vi_Pham']]
            ve_bieu_do_ngang(top_vp, 'Vi_Pham', 'name', "#e74c3c")

        with col_right:
            st.markdown("<h5 style='color: #3498db;'>🌟 TOP 5 SIÊNG NĂNG (BONUS)</h5>", unsafe_allow_html=True)
            top_bn = df_all.nlargest(5, 'Bonus')[['name', 'Bonus']]
            ve_bieu_do_ngang(top_bn, 'Bonus', 'name', "#3498db")

            st.markdown("<h5 style='color: #f39c12;'>🛡️ SỨC MẠNH TỔ ĐỘI</h5>", unsafe_allow_html=True)
            if 'team' in df_all.columns:
                team_data = df_all.groupby('team')['kpi'].sum().reset_index()
                ve_bieu_do_ngang(team_data, 'kpi', 'team', "#f39c12")

    elif page == "👥 Quản lý nhân sự":
        st.subheader("🛡️ ĐIỀU HÀNH QUÂN SỐ & PHÂN QUYỀN")
        
        # --- KHỐI: KHỞI TẠO QUÂN SỐ THÔNG MINH ---
        st.write("### 📥 KÍCH HOẠT QUÂN SỐ VƯƠNG QUỐC")
        
        with st.container(border=True):
            st.info("💡 Hệ thống tự động: Chỉ cần file có cột 'Họ và tên'. STT, Team, Role, KPI và Pass sẽ tự khởi tạo.")
            uploaded_file = st.file_uploader("Chọn file danh sách lớp (.xlsx):", type="xlsx", key="smart_activator")
            
            if uploaded_file:
                try:
                    df = pd.read_excel(uploaded_file)
                    selected_grade = st.selectbox("📌 Chọn Khối lớp cho danh sách này:", 
                                                  options=["Khối 6", "Khối 7", "Khối 8", "Khối 9"])
                    grade_folder = f"grade_{selected_grade.split()[-1]}"
                    # 1. Tự động tìm cột chứa tên (không phân biệt hoa thường, có dấu hay không)
                    name_col = next((c for c in df.columns if 'tên' in str(c).lower()), None)
                    
                    if not name_col:
                        st.error("❌ Không tìm thấy cột nào chứa thông tin 'Tên' học sinh trong file.")
                    else:
                        st.write(f"✅ Đã nhận diện danh sách tại cột: **{name_col}**")
                        
                        # Hiển thị bản xem trước dữ liệu sẽ được khởi tạo
                        if st.button("🔥 KHỞI TẠO VƯƠNG QUỐC NGAY", use_container_width=True):
                            
                            # --- [BƯỚC 1] SAO LƯU ADMIN & CẤU HÌNH CŨ (QUAN TRỌNG) ---
                            current_data = st.session_state.data if 'data' in st.session_state else {}
                            
                            # Lấy Admin cũ (nếu có), nếu không có thì dùng mặc định
                            preserved_admin = current_data.get('admin', {
                                "name": "Administrator", "password": "admin", "role": "admin",
                                "grade": "Hệ thống", "team": "Quản trị", "kpi": 0.0, "level": 99
                            })
                            
                            # Lấy Cấu hình danh hiệu cũ (nếu có)
                            preserved_ranks = current_data.get('rank_settings', [])
                            # -----------------------------------------------------------

                            # [BƯỚC 2] TẠO DỮ LIỆU MỚI (CHỈ CHỨA HỌC SINH TỪ EXCEL)
                            new_data = {}
                            
                            for i, row in df.iterrows():
                                # Tự động tạo ID theo STT (bắt đầu từ 1) - Hoặc logic cũ của bạn
                                full_name = str(row.get('Họ và tên', row.get('name', 'Học Sĩ'))).strip()
                                
                                # Nếu có hàm generate_username thì dùng, ko thì tạo tạm
                                try:
                                    u_id = user_module.generate_username(full_name)
                                except:                                   
                                    name_unsign = unidecode.unidecode(full_name).lower().replace(" ", "")
                                    u_id = f"{name_unsign}"

                                # Gán giá trị: Ưu tiên lấy từ file (nếu có), không thì dùng mặc định
                                new_data[u_id] = {
                                    "name": full_name,
                                    "team": str(row.get('team', row.get('Tổ', 'Chưa phân tổ'))),
                                    "grade": grade_folder,
                                    "role": str(row.get('role', 'u3')).lower(),
                                    "password": str(row.get('Password', '123456')), # Mật khẩu mặc định
                                    "kpi": int(row.get('KPI', 100)), # KPI mặc định 100
                                    
                                    # Các chỉ số game
                                    "Vi_Pham": 0, "Bonus": 0, "KTTX": 0, "KT Sản phẩm": 0,
                                    "KT Giữa kỳ": 0, "KT Cuối kỳ": 0, "Tri_Thuc": 0,
                                    "Chien_Tich": 0, "Vinh_Du": 0, "Vinh_Quang": 0,
                                    "titles": ["Tân Thủ Học Sĩ"],
                                    "inventory": {},
                                    "total_score": 0.0 # Reset điểm học tập
                                }
                            
                            # --- [BƯỚC 3] TRẢ LẠI ADMIN & CẤU HÌNH VÀO DATA MỚI ---
                            new_data['admin'] = preserved_admin
                            
                            if preserved_ranks:
                                new_data['rank_settings'] = preserved_ranks
                            # ------------------------------------------------------

                            # Cập nhật Session State và Lưu file JSON
                            st.session_state.data = new_data
                            save_data_func()
                            st.success(f"🎊 Chúc mừng! Đã kích hoạt {len(new_data)-1} tài khoản Học Sĩ (Admin vẫn an toàn).")
                            st.balloons()
                            time.sleep(1) # Đợi xíu cho bóng bay lên
                            st.rerun()
                            
                        st.divider()
                        st.write("🔍 **Xem trước dữ liệu:**")
                        st.dataframe(df[[name_col]].head(10), use_container_width=True)

                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")

        st.divider()
        # --- (Các phần Thiết lập tổ và Bảng chỉnh sửa chi tiết bên dưới giữ nguyên) ---

        
        # --- KHỐI 2: THIẾT LẬP CƠ CẤU TỔ ---
        with st.expander("🏗️ THIẾT LẬP CƠ CẤU TỔ", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                new_team_name = st.text_input("Tên tổ mới:", placeholder="Ví dụ: Tổ 8").strip()
                if st.button("➕ Thành lập Tổ"):
                    # Khởi tạo danh sách nếu chưa có
                    if 'team_list' not in st.session_state:
                        st.session_state.team_list = [f"Tổ {i}" for i in range(1, 8)]
                    
                    # Chuẩn hóa: "tổ 1" -> "Tổ 1"
                    normalized_name = new_team_name.capitalize() 
                    
                    # Kiểm tra trùng lặp không phân biệt hoa thường
                    existing_teams = [t.lower() for t in st.session_state.team_list]
                    
                    if normalized_name:
                        if normalized_name.lower() in existing_teams:
                            st.error(f"❌ {normalized_name} đã tồn tại!")
                        else:
                            st.session_state.team_list.append(normalized_name)
                            st.success(f"✅ Đã thành lập {normalized_name}")
                            st.rerun()
            with c2:
                if 'team_list' in st.session_state:
                    del_team = st.selectbox("Chọn tổ muốn giải tán:", st.session_state.team_list)
                    if st.button("❌ Xóa Tổ"):
                        st.session_state.team_list.remove(del_team)
                        for uid, info in st.session_state.data.items():
                            if info.get('team') == del_team:
                                st.session_state.data[uid]['team'] = "Chưa phân tổ"
                        st.warning(f"Đã giải tán {del_team}")
                        st.rerun()

        st.divider()

        # --- KHỐI 3: BẢNG ĐIỀU CHỈNH CHI TIẾT & PHÂN QUYỀN (BẢN NÂNG CẤP) ---
        if st.session_state.data:
            st.write("### 📝 DANH SÁCH CHI TIẾT & PHÂN QUYỀN")
            
            # 1. Chuyển đổi dữ liệu sang DataFrame và đưa User ID (Key) thành một cột
            # --- 🛡️ CODE FIX: LỌC BỎ CẤU HÌNH TRƯỚC KHI TẠO BẢNG ---
            raw_data = st.session_state.data
            clean_users_data = {}

            # Chỉ lấy những dòng là Dictionary (Học sinh/Admin), bỏ qua List (rank_settings)
            if raw_data:
                for key, value in raw_data.items():
                    if isinstance(value, dict):
                        clean_users_data[key] = value
            
            # Tạo bảng từ dữ liệu sạch
            try:
                df_users = pd.DataFrame.from_dict(clean_users_data, orient='index')
            except Exception as e:
                st.error(f"Lỗi tạo bảng danh sách: {e}")
                df_users = pd.DataFrame() # Tạo rỗng để không crash
            # -------------------------------------------------------
            df_users.index.name = 'User ID'
            df_users = df_users.reset_index() # Chuyển User ID từ index thành cột bình thường
            
            # 2. KIỂM TRA VÀ BỔ SUNG CỘT THIẾU (Fix lỗi KeyError)
            # Nếu vừa reset, DataFrame có thể thiếu các cột này
            required_cols = ['grade', 'team', 'role', 'name', 'password', 'kpi']
            for col in required_cols:
                if col not in df_users.columns:
                    df_users[col] = "N/A" if col in ['grade', 'team'] else 0

            # 3. Tạo cột Reset mật khẩu tạm thời
            df_users['Reset_123'] = False

            # 4. Dịch mã chức vụ sang Tiếng Việt
            role_to_vn = {"u1": "Tổ trưởng", "u2": "Tổ phó", "u3": "Tổ viên"}
            df_users['role'] = df_users['role'].map(role_to_vn).fillna("Tổ viên")

            # 5. Xử lý danh sách tổ
            raw_teams = st.session_state.get('team_list', [])
            current_teams = df_users['team'].unique().tolist()
            combined_list = [str(t) for t in (raw_teams + current_teams) if pd.notna(t) and str(t).strip() != ""]
            all_teams = sorted(list(set(combined_list + ["Chưa phân tổ"])))

            # 6. HIỂN THỊ BẢNG (Sử dụng danh sách cột an toàn)
            display_cols = ['User ID', 'name', 'grade', 'team', 'role', 'password', 'Reset_123']
            # --- 🛡️ FIX LỖI: ÉP KIỂU PASSWORD VỀ DẠNG CHỮ ---
            if 'password' in df_users.columns:
                df_users['password'] = df_users['password'].astype(str)
            # -----------------------------------------------
            # Đảm bảo chỉ lấy những cột thực sự tồn tại để tránh crash
            safe_display_cols = [c for c in display_cols if c in df_users.columns]

            edited_df = st.data_editor(
                df_users[safe_display_cols],
                column_config={
                    "User ID": st.column_config.TextColumn("ID Đăng nhập", disabled=True),
                    "name": st.column_config.TextColumn("Họ và tên", disabled=True),
                    "grade": st.column_config.SelectboxColumn("Khối", options=["grade_6", "grade_7", "grade_8", "grade_9"]),
                    "team": st.column_config.SelectboxColumn("Tổ", options=all_teams),
                    "role": st.column_config.SelectboxColumn("Chức vụ", options=["Tổ trưởng", "Tổ phó", "Tổ viên"]),
                    "password": st.column_config.TextColumn("Mật khẩu"),
                    "Reset_123": st.column_config.CheckboxColumn("Reset (123?)")
                },
                use_container_width=True,
                key="user_editor_reset_final",
                hide_index=True
            )
            
            # 6. NÚT XÁC NHẬN LƯU THAY ĐỔI
            if st.button("💾 XÁC NHẬN THAY ĐỔI TOÀN BỘ", use_container_width=True):
                role_to_code = {"Tổ trưởng": "u1", "Tổ phó": "u2", "Tổ viên": "u3"}
                
                for _, row in edited_df.iterrows():
                    u_id = str(row['User ID'])
                    
                    # Xác định mật khẩu: Nếu tích Reset thì dùng '123', nếu không thì dùng giá trị trong ô mật khẩu
                    new_password = "123" if row['Reset_123'] else str(row['password'])
                    
                    # Dịch ngược chức vụ về mã code
                    new_role = role_to_code.get(row['role'], "u3")
                    
                    # Cập nhật thông tin vào bộ nhớ hệ thống
                    st.session_state.data[u_id].update({
                        "team": row['team'],
                        "role": new_role,
                        "password": new_password
                    })
                
                # Lưu toàn bộ dữ liệu xuống file data.json
                save_data_func()
                st.success("🎉 Đã cập nhật thông tin và reset mật khẩu thành công!")
                st.rerun()
        else:
            st.info("💡 Vương quốc hiện chưa có dân cư. Hãy nạp file Excel ở trên để bắt đầu.")

    elif page == "🏪 Quản lý Tiệm tạp hóa":
        st.subheader("🛠️ CÔNG XƯỞNG CHẾ TẠO TRANG BỊ & VẬT PHẨM")

        # --- PHẦN 1: FORM TẠO VẬT PHẨM THEO LOGIC MỚI ---
        with st.expander("✨ CHẾ TẠO VẬT PHẨM MỚI (DATA-DRIVEN)", expanded=True):
            from item_system import get_item_behavior_registry
            registry = get_item_behavior_registry()

            col1, col2 = st.columns(2)
            currency_map = {
                "🏆 KPI Tổng": "kpi",
                "📚 Điểm Tri Thức": "Tri_Thuc",
                "🛡️ Điểm Chiến Tích": "Chien_Tich",
                "🎖️ Điểm Vinh Dự": "Vinh_Du",
                "👑 Điểm Vinh Quang": "Vinh_Quang"
            }

            with col1:
                name = st.text_input("Tên vật phẩm mới:")
                buy_with = st.selectbox("Bán bằng loại tiền:", list(currency_map.keys()))
                price = st.number_input("Giá bán:", min_value=0)
                img = st.text_input("Link ảnh vật phẩm (URL):")
                
                limit_type = st.selectbox("Chế độ giới hạn mua:", 
                                        ["Thông thường", "Giới hạn tháng", "Mua 1 lần duy nhất"])
                limit_amount = st.number_input("Số lượng giới hạn:", min_value=1, value=1) if limit_type == "Giới hạn tháng" else 0
            
            with col2:
                # 1. Chọn Behavior (Logic gốc)
                item_behavior = st.selectbox("Loại Logic (Behavior):", options=list(registry.keys()), 
                                             format_func=lambda x: registry[x]["name"])
                
                # 2. Tự động tạo ô nhập liệu cho Properties dựa trên Registry
                properties = {}
                item_def = registry[item_behavior]
                params = item_def["params"]
                labels = item_def.get("labels", {})

                st.write("🔧 **Thiết lập chỉ số đặc thù:**")
                # Chia nhỏ các ô nhập liệu thuộc tính
                for p_name, p_type in params.items():
                    display_label = labels.get(p_name, p_name)
                    if isinstance(p_type, list):
                        properties[p_name] = st.selectbox(display_label, options=p_type, key=f"new_{p_name}")
                    else:
                        properties[p_name] = st.number_input(display_label, value=0, key=f"new_{p_name}")
                
                desc = st.text_area("Mô tả công dụng hiển thị:")

            if st.button("📦 ĐƯA VẬT PHẨM LÊN KỆ", use_container_width=True):
                if name:
                    # Cấu trúc dữ liệu mới đồng bộ với item_system
                    st.session_state.shop_items[name] = {
                        "id": name,
                        "price": price,
                        "currency_buy": currency_map[buy_with],
                        "image": img if img else "https://cdn-icons-png.flaticon.com/512/1236/1236525.png",
                        "type": item_behavior, # Lưu loại behavior (BUFF_STAT, FUNCTIONAL...)
                        "properties": properties, # Lưu toàn bộ chỉ số đắp nặn
                        "limit_type": limit_type,
                        "limit_amount": limit_amount,
                        "desc": desc
                    }
                    save_shop_func(st.session_state.shop_items) 
                    st.success(f"✅ Đã chế tạo và đưa '{name}' lên kệ thành công!")
                    st.rerun()

        st.divider()
        
        # --- PHẦN 2: HIỂN THỊ KỆ HÀNG DUY NHẤT (ĐÃ SỬA LỖI) ---
        st.write("### 🏪 KHO HÀNG HIỆN TẠI (TRÊN KỆ)")

        if st.session_state.shop_items:
            label_map = {
                "kpi": "KPI Tổng", 
                "Tri_Thuc": "Tri Thức", 
                "Chien_Tich": "Chiến Tích",
                "Vinh_Du": "Vinh Dự",
                "Vinh_Quang": "Vinh Quang"
            }
            item_template = """
<div style="background:#5d4037;border:2px solid #a1887f;border-radius:8px;width:150px;padding:10px;text-align:center;color:white;box-shadow:2px 2px 5px rgba(0,0,0,0.5);flex-shrink:0;margin-bottom:10px;">
<img src="{img}" style="width:50px;height:50px;object-fit:contain;">
<div style="font-size:0.8em;font-weight:bold;height:35px;margin-top:5px;overflow:hidden;">{name}</div>
<div style="font-size:0.7em;color:#76ff03;">{effect}</div>
<div style="font-size:0.65em;color:#ffab40;">{limit}</div>
<div style="color:#ffd600;font-size:0.8em;font-weight:bold;margin-top:5px;border-top:1px solid #795548;padding-top:5px;">
📘 {price} {curr}
</div>
</div>
""" 

            all_items_html = ""
            for item_name, info in st.session_state.shop_items.items():
                # 1. Lấy nhãn tiền tệ mua hàng thực tế
                c_buy = info.get('currency_buy', 'kpi')
                curr_label = label_map.get(c_buy, "Điểm")
                icon_buy = "📘" if c_buy == "Tri_Thuc" else "🏆"
                
                # 2. Lấy nhãn chỉ số tác động thực tế (Khi tiêu thụ)
                t_stat = info.get('target_stat', 'kpi')
                target_label = label_map.get(t_stat, "Điểm")
                
                # 3. Xử lý Text giới hạn và Hiệu ứng
                l_type = info.get('limit_type', 'Thông thường')
                l_txt = f"Hạn mức: {info.get('limit_amount')}" if l_type == "Giới hạn tháng" else l_type
                
                val = info.get('buff_value', 0)
                # SỬA TẠI ĐÂY: Hiển thị đúng loại điểm được cộng thay vì mặc định KPI
                eff_txt = "Vật phẩm" if val == 0 else f"+{val} {target_label}"

                all_items_html += item_template.format(
                    img=info.get('image', ''),
                    name=item_name,
                    effect=eff_txt,
                    limit=l_txt,
                    price=info.get('price', 0),
                    curr=curr_label,
                    icon=icon_buy
                ) 

            # HIỂN THỊ CONTAINER CHÍNH (SÁT LỀ TRÁI)
            st.markdown(f"""
<div style="display:flex;flex-wrap:wrap;gap:10px;background:#2d1e16;padding:15px;border-radius:10px;justify-content:center;">
{all_items_html}
</div>
""", unsafe_allow_html=True)

            # --- NÚT DỠ HÀNG (GIỮ NGUYÊN LOGIC) ---
            target_del = st.selectbox("Chọn vật phẩm muốn dỡ khỏi kệ:", list(st.session_state.shop_items.keys()))
            if st.button(f"🗑️ DỠ '{target_del}' XUỐNG"):
                del st.session_state.shop_items[target_del]
                save_shop_func(st.session_state.shop_items)
                st.rerun()

        st.divider()

        # --- PHẦN 3: ĐIỀU PHỐI KHO CÁ NHÂN & TẶNG QUÀ ---
        st.subheader("🎁 ĐIỀU PHỐI VẬT PHẨM")
        tab1, tab2 = st.tabs(["Tặng quà", "Thu hồi"])
            
        with tab1:
            col_u, col_i, col_q = st.columns(3)
            
            # [cite_start]Lấy danh sách tên hiển thị từ data
            all_names = [info['name'] for uid, info in st.session_state.data.items() 
                         if isinstance(info, dict) and 'name' in info]
            
            with col_u: 
                # [cite_start]Thêm lựa chọn "TẤT CẢ HỌC SĨ" vào danh sách
                target_user = st.selectbox("Chọn Học Sĩ nhận:", ["🌟 TẤT CẢ HỌC SĨ"] + all_names)
            
            with col_i: 
                if 'shop_items' in st.session_state and st.session_state.shop_items:
                    gift_item = st.selectbox("Chọn vật phẩm:", list(st.session_state.shop_items.keys()))
                else:
                    st.warning("Chưa có vật phẩm trong Shop")
                    gift_item = None
            
            with col_q: 
                gift_qty = st.number_input("Số lượng:", min_value=1, value=1)
            
            if st.button("🚀 XÁC NHẬN PHÁT QUÀ", use_container_width=True) and gift_item:
                item_data = st.session_state.shop_items.get(gift_item)
                
                if item_data:
                    # TRƯỜNG HỢP 1: TẶNG CHO TOÀN BỘ LỚP
                    if target_user == "🌟 TẤT CẢ HỌC SĨ":
                        count_success = 0
                        for u_id, u_info in st.session_state.data.items():
                            if isinstance(u_info, dict) and 'name' in u_info:
                                # Đảm bảo inventory là Dictionary để đồng bộ logic mới
                                if 'inventory' not in u_info or not isinstance(u_info['inventory'], dict):
                                    st.session_state.data[u_id]['inventory'] = {}
                                
                                inventory = st.session_state.data[u_id]['inventory']
                                inventory[gift_item] = inventory.get(gift_item, 0) + gift_qty
                                count_success += 1
                        
                        save_data_func() # Lưu sau khi phát xong cho cả lớp [cite: 28]
                        st.success(f"🎊 Đã phát quà đại trà! {gift_qty} {gift_item} đã được gửi tới {count_success} học sĩ!")

                    # TRƯỜNG HỢP 2: TẶNG CHO CÁ NHÂN (Giữ nguyên logic cũ)
                    else:
                        u_id = next((uid for uid, info in st.session_state.data.items() 
                                     [cite_start]if isinstance(info, dict) and info.get('name') == target_user), None)
                        
                        if u_id:
                            if 'inventory' not in st.session_state.data[u_id] or not isinstance(st.session_state.data[u_id]['inventory'], dict):
                                st.session_state.data[u_id]['inventory'] = {}
                            
                            inventory = st.session_state.data[u_id]['inventory']
                            inventory[gift_item] = inventory.get(gift_item, 0) + gift_qty
                            
                            save_data_func()
                            st.success(f"🎁 Đã tặng {gift_qty} {gift_item} cho {target_user}!")
                else:
                    st.error("❌ Vật phẩm không tồn tại trong kho hệ thống!")

        with tab2:
            del_user = st.selectbox("Chọn Học Sĩ muốn xóa kho:", all_names, key="del_user")
            if st.button("🔥 XÓA SẠCH TÚI ĐỒ"):
                u_id = [uid for uid, info in st.session_state.data.items() if info['name'] == del_user][0]
                st.session_state.data[u_id]['inventory'] = []
                save_data_func() 
                st.warning(f"Đã tịch thu toàn bộ vật phẩm của {del_user}!")


        # ==============================================================================
        # 🎲 PHẦN MỚI: CÔNG XƯỞNG CHẾ TẠO RƯƠNG GACHA (LOOT BOX)
        # ==============================================================================
        with st.expander("🎲 CHẾ TẠO RƯƠNG THẦN BÍ (GACHA SYSTEM)", expanded=False):
            st.info("💡 Cơ chế: Tạo ra một vật phẩm dạng 'Rương'. Khi người dùng mở rương, hệ thống sẽ quay số dựa trên tỷ lệ bạn thiết lập để trả về vật phẩm hoặc tiền tệ.")

            # 1. Khởi tạo session state tạm để lưu danh sách item trong rương đang chế
            if 'temp_loot_table' not in st.session_state:
                st.session_state.temp_loot_table = []

            c1, c2 = st.columns([1, 1.5])

            with c1:
                st.markdown("#### 🅰️ THIẾT KẾ VỎ RƯƠNG")
                box_name = st.text_input("Tên Rương:", placeholder="Ví dụ: Rương Kho Báu Rồng", key="gacha_name")
                box_img = st.text_input("Ảnh Rương (URL):", placeholder="Link ảnh rương đóng...", key="gacha_img")
                
                # Định nghĩa độ hiếm (Chủ yếu để hiển thị màu sắc/hiệu ứng)
                rarity_opt = {
                    "common": "⚪ Phổ biến (Trắng)",
                    "rare": "🔵 Hiếm (Xanh dương)",
                    "epic": "🟣 Sử thi (Tím)",
                    "legendary": "🟠 Huyền thoại (Cam)",
                    "mythic": "🔴 Thần thoại (Đỏ)"
                }
                box_rarity = st.selectbox("Độ hiếm:", list(rarity_opt.keys()), format_func=lambda x: rarity_opt[x])
                
                # Giá bán rương
                # Dùng mapping key giống trong file codee.txt 
                currency_map = {
                    "kpi": "🏆 KPI", 
                    "Tri_Thuc": "📘 Tri Thức", 
                    "Chien_Tich": "⚔️ Chiến Tích", 
                    "Vinh_Du": "🎖️ Vinh Dự"
                }
                box_price = st.number_input("Giá bán:", min_value=0, value=100, step=10, key="gacha_price")
                box_curr = st.selectbox("Loại tiền mua:", list(currency_map.keys()), format_func=lambda x: currency_map[x], key="gacha_curr")

            with c2:
                st.markdown("#### 🅱️ NẠP RUỘT RƯƠNG (LOOT TABLE)")
                
                # Form thêm vật phẩm con
                with st.form("add_loot_form", clear_on_submit=True):
                    col_l1, col_l2, col_l3, col_l4 = st.columns([2, 1.5, 1, 1])
                    
                    # Lấy danh sách item đang có trong Shop để nhét vào rương
                    existing_items = list(st.session_state.shop_items.keys()) if 'shop_items' in st.session_state else []
                    
                    with col_l1:
                        # Chọn loại phần thưởng: Item trong shop hay là Tiền tệ trực tiếp
                        reward_type = st.selectbox("Loại quà:", ["Item (Vật phẩm)", "Currency (Tiền tệ)"])
                    
                    with col_l2:
                        if reward_type == "Item (Vật phẩm)":
                            target_id = st.selectbox("Chọn vật phẩm:", ["-- Chọn --"] + existing_items)
                        else:
                            target_id = st.selectbox("Chọn tiền tệ:", list(currency_map.keys()))

                    with col_l3:
                        drop_rate = st.number_input("Tỷ lệ %:", min_value=0.1, max_value=100.0, value=10.0, step=0.1)
                    with col_l4:
                        drop_qty = st.number_input("SL:", min_value=1, value=1)
                        
                    add_btn = st.form_submit_button("➕ Thêm")

                    if add_btn:
                        if target_id != "-- Chọn --":
                            # Thêm vào danh sách tạm
                            st.session_state.temp_loot_table.append({
                                "type": "item" if reward_type == "Item (Vật phẩm)" else "currency",
                                "id": target_id,
                                "rate": drop_rate,
                                "amount": drop_qty
                            })
                            st.success(f"Đã thêm {target_id} ({drop_rate}%)")
                        else:
                            st.warning("Vui lòng chọn vật phẩm hợp lệ!")

                # Hiển thị danh sách vật phẩm đã thêm (Preview)
                if st.session_state.temp_loot_table:
                    st.markdown("##### 📋 Danh sách tỷ lệ:")
                    total_rate = 0
                    
                    for idx, item in enumerate(st.session_state.temp_loot_table):
                        total_rate += item['rate']
                        icon = "📦" if item['type'] == 'item' else "💰"
                        st.markdown(f"{idx+1}. {icon} **{item['id']}** (x{item['amount']}) - `{item['rate']}%`")
                    
                    # Cảnh báo tổng tỷ lệ
                    if total_rate > 100:
                        st.error(f"⚠️ Tổng tỷ lệ: {total_rate:.1f}%. (Quá 100% gây lỗi logic!)")
                    elif total_rate < 100:
                        st.warning(f"ℹ️ Tổng tỷ lệ: {total_rate:.1f}%. Có {100-total_rate:.1f}% cơ hội mở ra Rương Rỗng (Miss).")
                    else:
                        st.success("✅ Tổng tỷ lệ hoàn hảo (100%).")
                    
                    if st.button("🗑️ Xóa danh sách làm lại"):
                        st.session_state.temp_loot_table = []
                        st.rerun()

            st.divider()
            
            # NÚT HOÀN TẤT CHẾ TẠO
            if st.button("🎁 ĐÓNG GÓI VÀ BÀY BÁN RƯƠNG", type="primary", use_container_width=True):
                if box_name and st.session_state.temp_loot_table:
                    # Cấu trúc dữ liệu Rương Gacha
                    new_chest_data = {
                        "id": box_name,
                        "name": box_name, # Thêm name để đồng bộ hiển thị
                        "price": box_price,
                        "currency_buy": box_curr,
                        "image": box_img if box_img else "https://cdn-icons-png.flaticon.com/512/4256/4256846.png",
                        
                        # QUAN TRỌNG: Loại item mới để hệ thống nhận diện
                        "type": "GACHA_BOX",  
                        
                        # Lưu cấu hình vào properties
                        "properties": {
                            "rarity": box_rarity,
                            "loot_table": st.session_state.temp_loot_table 
                        },
                        "limit_type": "none", 
                        "limit_value": 0,
                        "desc": f"Rương chứa {len(st.session_state.temp_loot_table)} phần thưởng bí ẩn. Mở ngay để thử vận may!"
                    }
                    
                    # Lưu vào Shop (Giả sử biến shop_items đang ở session_state)
                    st.session_state.shop_items[box_name] = new_chest_data
                    
                    # Gọi hàm save của bạn (Cần truyền đúng hàm save_shop_data từ bên ngoài vào)
                    save_shop_func(st.session_state.shop_items)
                    
                    st.session_state.temp_loot_table = [] # Reset form
                    st.balloons()
                    st.success(f"Đã tạo rương {box_name} thành công! Hãy nhớ bấm 'Lưu Dữ Liệu Shop' bên ngoài.")
                    st.rerun()
                else:
                    st.error("Thiếu tên rương hoặc danh sách vật phẩm rỗng!")

        from admin_module import hien_thi_quan_ly_shop_xoa
        hien_thi_quan_ly_shop_xoa(save_shop_func)
            
    # ===== 🏅 QUẢN LÝ DANH HIỆU =====
    elif page == "🏅 Quản lý danh hiệu":
        st.subheader("🏛️ THIẾT LẬP HỆ THỐNG DANH HIỆU")
        st.info("Admin thiết lập các cột mốc KPI để Học Sĩ vào Sảnh Danh Vọng kích hoạt.")

        # 1. Đồng bộ dữ liệu từ File vào Session State (quan trọng để hiển thị đúng cái cũ)
        if 'rank_settings' not in st.session_state:
            # Ưu tiên lấy từ dữ liệu đã lưu trong data.json
            saved_ranks = st.session_state.data.get('rank_settings', [])
            
            if saved_ranks:
                st.session_state.rank_settings = saved_ranks
            else:
                # Nếu chưa có gì thì dùng mẫu mặc định
                st.session_state.rank_settings = [
                    {"Danh hiệu": "Học Giả Tập Sự", "KPI Yêu cầu": 100, "Màu sắc": "#bdc3c7"},
                    {"Danh hiệu": "Đại Học Sĩ", "KPI Yêu cầu": 500, "Màu sắc": "#3498db"},
                    {"Danh hiệu": "Vương Giả Tri Thức", "KPI Yêu cầu": 1000, "Màu sắc": "#f1c40f"}
                ]

        # 2. Bảng Editor
        edited_ranks = st.data_editor(
            st.session_state.rank_settings, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Màu sắc": st.column_config.SelectboxColumn(
                    "Màu sắc",
                    options=["#bdc3c7", "#3498db", "#f1c40f", "#e74c3c", "#9b59b6", "#2ecc71"],
                    help="Chọn mã màu hiển thị cho danh hiệu"
                )
            }
        )
        
        # 3. NÚT LƯU (ĐÃ SỬA LOGIC)
        if st.button("💾 LƯU THIẾT LẬP DANH HIỆU"):
            # Cập nhật vào Session tạm
            st.session_state.rank_settings = edited_ranks
            
            # --- [QUAN TRỌNG] LƯU VÀO DATA CHÍNH VÀ GHI FILE JSON ---
            if 'data' in st.session_state:
                st.session_state.data['rank_settings'] = edited_ranks
                save_data_func() # Gọi hàm lưu xuống ổ cứng
            # ---------------------------------------------------------
            
            st.success("✅ Đã cập nhật và lưu hệ thống danh hiệu vĩnh viễn!")
            st.balloons()

    elif page == "🏟️ Quản lý lôi đài":
        quan_ly_loi_dai_admin(save_data_func) # Gọi hàm để hiển thị giao diện quản lý


    elif page == "⚠️ Xóa dữ liệu":
        st.subheader("♻️ KHU VỰC TỐI NGUY HIỂM: RESET NĂM HỌC")
        
        with st.expander("👉 NHẤN VÀO ĐÂY ĐỂ THỰC HIỆN"):
            confirm_text = st.text_input("Nhập chữ 'RESET' để xác nhận:", key="reset_confirm_input")
            
            if st.button("🔥 THỰC HIỆN RESET TOÀN BỘ"):
                if confirm_text == "RESET":
                    import os
                    import time
                    # 1. Thực hiện dọn dẹp backup cũ
                    try:
                        # Gọi hàm dọn dẹp đã định nghĩa ở phần đầu file admin_module
                        dọn_dẹp_backup_reset_năm_học()
                        st.info("🧹 Đã dọn dẹp kho lưu trữ sao lưu cũ.")
                    except:
                        pass

                    # 2. Sao lưu cấu hình cần giữ
                    saved_rank_settings = st.session_state.data.get('rank_settings', [])
                    current_admin_pass = st.session_state.data.get('admin', {}).get('password', 'admin')

                    # 3. Tạo dữ liệu mới
                    new_data = {}
                    new_data['admin'] = {
                        "name": "Administrator",
                        "password": current_admin_pass,
                        "role": "admin",
                        "grade": "Hệ thống", 
                        "team": "Quản trị",
                        "kpi": 0.0, 
                        "level": 99
                    }
                    
                    if saved_rank_settings:
                        new_data['rank_settings'] = saved_rank_settings

                    # 4. Reset file Lôi đài an toàn
                    path_loi_dai = "loi_dai.json" 
                    default_structure = {"matches": {}, "rankings": {}}
                    
                    try:
                        with open(path_loi_dai, 'w', encoding='utf-8') as f:
                            json.dump(default_structure, f, ensure_ascii=False, indent=4)
                            f.flush()
                            os.fsync(f.fileno())
                        st.info("📊 Đã tái tạo nhật ký Lôi đài sạch sẽ.")
                    except Exception as e:
                        st.error(f"⚠️ Lỗi reset lôi đài: {e}")

                    # 5. Cập nhật và lưu dữ liệu chính
                    st.session_state.data = new_data
                    save_data_func(new_data)

                    # 6. Dọn dẹp session để tránh xung đột
                    combat_keys = [
                        "dang_danh_dungeon", "dungeon_questions", "current_q_idx", 
                        "correct_count", "victory_processed", 
                        "match_result_notified", "arena_log", "last_match_result",
                        "match_id_active", "pending_match_join"
                    ]
                    for k in combat_keys:
                        if k in st.session_state:
                            del st.session_state[k]

                    st.success("💥 Reset thành công! Toàn bộ dữ liệu cũ đã được làm sạch.")
                    time.sleep(2)
                    st.rerun()

    elif page == "📥 Sao lưu dữ liệu":
        st.subheader("🛡️ HỆ THỐNG SAO LƯU DỮ LIỆU")
        import io, zipfile, os
        from datetime import datetime

        # 1. Đảm bảo có system_config trong session_state
        if 'system_config' not in st.session_state.data:
            st.session_state.data['system_config'] = {"last_backup": "Chưa bao giờ"}
        
        # 2. Lấy dữ liệu ngay từ đầu
        last_backup_str = st.session_state.data['system_config'].get('last_backup', "Chưa bao giờ")
        
        # 3. Tính toán trạng thái needs_backup NGAY LẬP TỨC
        needs_backup = True
        if last_backup_str != "Chưa bao giờ":
            try:
                last_date = datetime.strptime(last_backup_str, "%d/%m/%Y")
                curr_date = datetime.now()
                # Kiểm tra cùng tuần và cùng năm
                if last_date.isocalendar()[1] == curr_date.isocalendar()[1] and \
                   last_date.year == curr_date.year:
                    needs_backup = False
            except: pass

        # 4. HIỂN THỊ THÔNG BÁO (Đã được cập nhật)
        if needs_backup:
            st.warning(f"⚠️ **Nhắc nhở:** Tuần này bạn chưa thực hiện sao lưu dữ liệu. (Lần cuối: {last_backup_str})")
        else:
            st.success(f"✅ Dữ liệu tuần này đã được an toàn. (Lần cuối sao lưu: {last_backup_str})")

        # 5. TẠO ZIP
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for f in ["data.json", "shop_data.json", "market.json", "loi_dai.json"]:
                if os.path.exists(f):
                    z.write(f)
        
        st.write("Bấm nút bên dưới để tải bản sao lưu (.zip):")
        
        # Nút Download
        download_clicked = st.download_button(
            label="📥 TẢI BẢN SAO LƯU (.ZIP)",
            data=buf.getvalue(),
            file_name=f"Backup_KPI_Kingdom_{datetime.now().strftime('%d_%m_%Y')}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
            key="final_backup_btn"
        )

        # 6. LOGIC QUAN TRỌNG: Cập nhật sau khi nhấn
        if download_clicked:
            # Ghi nhận ngày mới
            current_day = datetime.now().strftime("%d/%m/%Y")
            st.session_state.data['system_config']['last_backup'] = current_day
            save_data_func(st.session_state.data)
            # Thông báo thành công và bắt rerun để logic #3 ở trên nhận diện lại màu xanh
            st.toast("Đã ghi nhận sao lưu!")
            st.rerun()


        # --- 4. KHÔI PHỤC DỮ LIỆU ---
        st.divider()
        st.subheader("⏪ KHÔI PHỤC DỮ LIỆU")
        st.info("Tải lên file bản sao lưu (.zip) để khôi phục. Lưu ý: Hành động này sẽ ghi đè hoàn toàn dữ liệu hiện tại!")

        uploaded_zip = st.file_uploader("Chọn file backup (.zip)", type="zip", key="admin_restore_uploader")

        if uploaded_zip is not None:
            if st.button("⚠️ XÁC NHẬN KHÔI PHỤC", type="secondary", use_container_width=True):
                try:
                    with zipfile.ZipFile(uploaded_zip, "r") as z:
                        # Kiểm tra file bên trong (tùy chọn) và giải nén
                        z.extractall(".") 
                        
                        st.success("🎉 Khôi phục dữ liệu thành công! Hệ thống đang khởi động lại...")
                        st.balloons()
                        import time
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi khôi phục: {e}")
    
 
def quan_ly_loi_dai_admin(save_data_func):
    st.write("### 🏟️ ĐIỀU HÀNH LÔI ĐÀI")
    
    # 1. Nhập các hàm xử lý file
    from user_module import load_loi_dai, save_loi_dai
    ld_data = load_loi_dai()
    
    # 2. LỌC TRẬN ĐẤU: Đổi 'ongoing' thành 'active' cho đồng bộ
    active_m = {k: v for k, v in ld_data.get('matches', {}).items() 
                if v.get('status') in ['pending', 'active']}
    
    if not active_m:
        st.success("✅ Hiện không có trận đấu nào đang chờ hoặc đang diễn ra.")
        return

    st.info(f"Đang có {len(active_m)} trận đấu cần giám sát.")
    
    for mid, m in active_m.items():
        # Tạo khung bao quanh mỗi trận đấu
        with st.container(border=True):
            challenger_id = m.get('challenger')
            opponent_id = m.get('opponent')
            
            challenger_name = st.session_state.data.get(challenger_id, {}).get('name', 'Ẩn danh')
            opponent_name = st.session_state.data.get(opponent_id, {}).get('name', 'Ẩn danh')
            
            # Hiển thị trạng thái chuẩn
            is_active = m.get('status') == 'active'
            status_txt = "⚔️ ĐANG ĐẤU" if is_active else "⏳ ĐANG CHỜ"
            
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Trận:** {m.get('subject', 'N/A').upper()} | **Mức cược:** {m.get('bet')} KPI")
                st.write(f"**Đối đầu:** {challenger_name} VS {opponent_name}")
                st.write(f"**Trạng thái:** {status_txt}")
            
            with c2:
                # NÚT HỦY TRẬN
                if st.button("🚫 HỦY & HOÀN KPI", key=f"admin_cancel_{mid}", use_container_width=True):
                    # CHỈ HOÀN KPI nếu trận đã ở trạng thái 'active' (đã trừ tiền người chơi)
                    if is_active:
                        # Kiểm tra an toàn trước khi cộng tiền
                        if challenger_id in st.session_state.data:
                            st.session_state.data[challenger_id]['kpi'] += m.get('bet', 0)
                        if opponent_id in st.session_state.data:
                            st.session_state.data[opponent_id]['kpi'] += m.get('bet', 0)
                        
                        # FIX LỖI: Truyền data vào hàm lưu
                        save_data_func(st.session_state.data) 
                    
                    # Xóa trận đấu khỏi file lôi đài
                    if mid in ld_data['matches']:
                        del ld_data['matches'][mid]
                        save_loi_dai(ld_data)
                    
                    st.toast(f"Đã hủy và giải phóng trận đấu {mid}")
                    st.rerun()
                    
def hien_thi_quan_ly_shop_xoa(save_shop_func):
    """
    Hàm hiển thị khu vực xóa vật phẩm/rương khỏi Shop
    """
    st.divider()
    st.subheader("🗑️ KHO HỦY (XÓA VẬT PHẨM / RƯƠNG)")
    
    # Kiểm tra dữ liệu
    if 'shop_items' not in st.session_state or not st.session_state.shop_items:
        st.info("📭 Kho hàng hiện đang trống, không có gì để xóa.")
        return

    shop_items = st.session_state.shop_items

    with st.expander("⚠️ Mở bảng điều khiển Xóa", expanded=False):
        st.warning("Cảnh báo: Hành động này không thể hoàn tác. Hãy cân nhắc kỹ trước khi xóa!")
        
        # 1. Tạo danh sách chọn (Có icon để dễ phân biệt Rương/Item)
        delete_options = []
        # Lưu mapping từ label -> id thực để xử lý
        label_to_id = {}
        
        for k, v in shop_items.items():
            itype = v.get('type', 'UNKNOWN')
            
            if itype == 'GACHA_BOX': icon = "🎲 [RƯƠNG]"
            elif itype == 'BUFF_STAT': icon = "⚔️ [BUFF]"
            elif itype == 'CONSUMABLE': icon = "💎 [TIÊU THỤ]"
            else: icon = "📦 [ITEM]"
            
            # Label: "🎲 [RƯƠNG] Rương Rồng (ruong_rong)"
            label = f"{icon} {v.get('name', k)} ({k})"
            delete_options.append(label)
            label_to_id[label] = k

        # 2. Selectbox chọn
        selected_label = st.selectbox("Chọn vật phẩm muốn xóa:", delete_options)
        
        # 3. Hiển thị thông tin chi tiết item đang chọn (để chắc chắn không xóa nhầm)
        if selected_label:
            real_id = label_to_id[selected_label]
            item_data = shop_items[real_id]
            
            st.code(f"""
            ID: {real_id}
            Tên: {item_data.get('name')}
            Giá: {item_data.get('price')} {item_data.get('currency_buy')}
            Loại: {item_data.get('type')}
            """, language="yaml")

            # 4. Nút Xóa
            col_del1, col_del2 = st.columns([1, 4])
            with col_del1:
                if st.button("🔥 XÓA NGAY", type="primary", use_container_width=True):
                    # Xóa khỏi session state
                    del st.session_state.shop_items[real_id]
                    
                    # Lưu lại file
                    save_shop_func(st.session_state.shop_items)
                    
                    st.toast(f"Đã xóa {real_id} vĩnh viễn!", icon="🗑️")
                    time.sleep(1)
                    st.rerun()