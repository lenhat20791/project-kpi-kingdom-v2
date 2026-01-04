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
from user_module import save_data
from user_module import (
    hien_thi_doi_mat_khau, 
    save_data, 
    load_loi_dai,
    save_loi_dai
)

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
    import time
    from datetime import datetime
    import user_module  # Import module chứa hàm lưu sheet
    import json
    import os

    st.subheader("📢 TRUNG TÂM PHÁT THANH ADMIN")
    
    # --- KHU VỰC NHẬP LIỆU ---
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            # Dùng key để có thể clear sau khi gửi
            msg_content = st.text_area("Nội dung thông báo:", height=100, key="input_msg_content", placeholder="Nhập nội dung cập nhật hoặc thông báo...")
        with c2:
            msg_type = st.radio("Hình thức:", ["marquee", "popup"], 
                                format_func=lambda x: "🏃 Chạy chữ" if x == "marquee" else "🚨 Popup Khẩn")
        
        # --- NÚT GỬI THÔNG BÁO (MỚI THÊM) ---
        if st.button("📡 PHÁT THANH NGAY", type="primary", use_container_width=True):
            if not msg_content:
                st.error("❌ Nội dung thông báo không được để trống!")
            else:
                # 1. Tạo cấu trúc thông báo mới
                new_notice = {
                    "id": int(time.time()), # ID duy nhất dựa theo thời gian
                    "content": msg_content,
                    "type": msg_type,
                    "time": datetime.now().strftime("%H:%M %d/%m")
                }

                # 2. Lưu vào Session State (Bộ nhớ tạm)
                if 'admin_notices' not in st.session_state.data:
                    st.session_state.data['admin_notices'] = []
                
                # Thêm vào đầu danh sách
                st.session_state.data['admin_notices'].insert(0, new_notice)

                # 3. Lưu vào File JSON (Backup cục bộ - tùy chọn)
                try:
                    with open('data/admin_notices.json', 'w', encoding='utf-8') as f:
                        json.dump(st.session_state.data['admin_notices'], f, ensure_ascii=False)
                except: pass

                # 4. 🔥 QUAN TRỌNG: LƯU LÊN GOOGLE SHEET 🔥
                with st.spinner("Đang gửi tín hiệu lên vệ tinh..."):
                    user_module.save_all_to_sheets(st.session_state.data)
                
                st.success("✅ Đã phát thông báo thành công!")
                time.sleep(1)
                st.rerun()

    # --- HIỂN THỊ DANH SÁCH THÔNG BÁO ĐANG CHẠY ---
    st.divider()
    st.write("📋 **Danh sách thông báo đang treo:**")
    current_notices = st.session_state.data.get('admin_notices', [])
    
    if current_notices:
        for i, note in enumerate(current_notices):
            with st.expander(f"{note['time']} - {note['type'].upper()}", expanded=True):
                st.write(note['content'])
                if st.button("Xóa tin này", key=f"del_note_{note['id']}"):
                    current_notices.pop(i)
                    st.session_state.data['admin_notices'] = current_notices
                    user_module.save_all_to_sheets(st.session_state.data) # Lưu lại sau khi xóa lẻ
                    st.rerun()
    else:
        st.info("Chưa có thông báo nào.")

    # --- NÚT XÓA TẤT CẢ ---
    st.divider()
    if st.button("🗑️ XÓA TOÀN BỘ THÔNG BÁO HỆ THỐNG"):
        # 1. Xóa trong dữ liệu chính
        st.session_state.data['admin_notices'] = []
        
        # 2. Xóa file cục bộ
        if os.path.exists('data/admin_notices.json'):
            os.remove('data/admin_notices.json')
            
        # 3. Lưu lên Sheet
        user_module.save_all_to_sheets(st.session_state.data)
        
        st.success("🧹 Đã dọn dẹp sạch sẽ!")
        time.sleep(1)
        st.rerun()

def hien_thi_thong_bao_he_thong():
    """
    Hàm hiển thị thông báo. Đọc trực tiếp từ st.session_state.data để đảm bảo
    đồng bộ với dữ liệu đã tải từ Google Sheet về.
    """
    import streamlit as st
    
    # Lấy danh sách thông báo từ dữ liệu tổng (đã load từ sheet khi vào app)
    # Nếu chưa có thì lấy list rỗng
    notices = st.session_state.data.get('admin_notices', [])
    
    if not notices:
        return

    # Duyệt qua các thông báo
    for n in notices:
        # 1. Hiển thị POPUP KHẨN CẤP
        if n.get('type') == 'popup':
            # Tạo key duy nhất để không hiện lại nếu đã tắt
            popup_key = f"seen_popup_{n.get('id')}"
            
            if not st.session_state.get(popup_key, False):
                @st.dialog("📢 THÔNG BÁO TỪ BAN QUẢN TRỊ")
                def show_notice_popup(content, time_sent):
                    st.warning(f"🕒 *Gửi lúc: {time_sent}*")
                    st.markdown(f"### {content}")
                    if st.button("Đã hiểu và Đóng", key=f"btn_cls_{n.get('id')}"):
                        st.session_state[popup_key] = True
                        st.rerun()
                
                show_notice_popup(n.get('content'), n.get('time'))

        # 2. Hiển thị CHẠY CHỮ (MARQUEE)
        elif n.get('type') == 'marquee':
            st.markdown(f"""
                <div style="
                    background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
                    color: white; 
                    padding: 8px; 
                    font-weight: bold; 
                    border-radius: 8px; 
                    margin-bottom: 10px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    border: 1px solid #fff;">
                    <marquee behavior="scroll" direction="left" scrollamount="8">
                        🔔 [THÔNG BÁO - {n.get('time')}]: {n.get('content')} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
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

import json
import streamlit as st
from user_module import get_gspread_client, SHEET_NAME

# --- HÀM BỔ TRỢ DỮ LIỆU PHÓ BẢN (PHIÊN BẢN GGSHEET) ---
@st.cache_data(ttl=60) # Cache 60s để đỡ gọi API liên tục
def load_dungeon_config():
    """
    Tải cấu hình phó bản từ Tab 'Dungeon' trên Google Sheet.
    Nếu chưa có, trả về cấu hình mặc định.
    """
    default_config = {}
    # Tạo cấu trúc mặc định (Dùng khi Sheet lỗi hoặc chưa có dữ liệu)
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

    try:
        client = get_gspread_client()
        sh = client.open(SHEET_NAME)
        
        try:
            wks = sh.worksheet("Dungeon")
            records = wks.get_all_records()
            
            # Nếu Sheet trống, trả về mặc định
            if not records:
                return default_config
            
            # Parse dữ liệu từ Sheet vào Dict
            loaded_config = {}
            for row in records:
                land_id = str(row.get('Land_ID', '')).strip()
                phase_id = str(row.get('Phase_ID', '')).strip()
                raw_json = str(row.get('Config_JSON', '{}'))
                
                if not land_id: continue
                
                # Khởi tạo vùng đất nếu chưa có
                if land_id not in loaded_config:
                    loaded_config[land_id] = {
                        "name": land_id.upper(),
                        "phases": {}
                    }
                
                # Parse JSON chi tiết phase
                try:
                    # Fix lỗi dấu ngoặc kép thông minh nếu copy paste
                    clean_json = raw_json.replace("“", '"').replace("”", '"').replace("’", "'")
                    phase_data = json.loads(clean_json)
                    loaded_config[land_id]["phases"][phase_id] = phase_data
                except:
                    # Nếu JSON lỗi, lấy từ default
                    if land_id in default_config and phase_id in default_config[land_id]['phases']:
                         loaded_config[land_id]["phases"][phase_id] = default_config[land_id]['phases'][phase_id]

            # Merge với default để đảm bảo không thiếu land nào (nếu sheet xóa bớt)
            final_config = default_config.copy()
            for l_id, l_data in loaded_config.items():
                if l_id in final_config:
                    final_config[l_id]['phases'].update(l_data['phases'])
            
            return final_config

        except Exception:
            # Nếu chưa có tab Dungeon thì trả về mặc định luôn
            return default_config

    except Exception as e:
        st.error(f"⚠️ Lỗi tải cấu hình Phó bản: {e}")
        return default_config


def save_dungeon_config(config):
    """
    Lưu cấu hình phó bản lên Tab 'Dungeon' trên Google Sheet.
    Tự động tạo Tab và Cột nếu chưa có.
    """
    try:
        client = get_gspread_client()
        sh = client.open(SHEET_NAME)
        
        # 1. Tìm hoặc Tạo tab Dungeon
        try:
            wks = sh.worksheet("Dungeon")
        except:
            wks = sh.add_worksheet(title="Dungeon", rows=100, cols=10)
            
        # 2. Chuẩn bị dữ liệu để lưu (Làm phẳng Dictionary)
        # Header chuẩn
        headers = ["Land_ID", "Phase_ID", "Phase_Name", "Config_JSON"]
        rows_to_write = [headers]
        
        for land_id, land_data in config.items():
            phases = land_data.get("phases", {})
            for phase_id, phase_data in phases.items():
                row = [
                    str(land_id),
                    str(phase_id),
                    str(phase_data.get('title', phase_id)),
                    json.dumps(phase_data, ensure_ascii=False) # Gom hết thuộc tính vào JSON
                ]
                rows_to_write.append(row)
        
        # 3. Ghi đè lên Sheet
        wks.clear()
        wks.update('A1', rows_to_write)
        
        # 4. Xóa Cache để lần tải sau thấy dữ liệu mới ngay
        st.cache_data.clear()
        
    except Exception as e:
        st.error(f"❌ Lỗi lưu cấu hình Phó bản: {e}")
        # Fallback: Lưu tạm xuống file local phòng hờ mất mạng
        if not os.path.exists("data"): os.makedirs("data")
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
    Nhiệm vụ: Lấy dữ liệu Shop -> Tạo danh sách chọn -> Hiển thị bảng Data Editor
    Trả về: Dữ liệu thô từ bảng nhập liệu.
    """
    # 1. Chuẩn bị danh sách
    shop_items = st.session_state.data.get('shop_items', {}) 
    
    currency_options = ["🔵 KPI", "📚 Tri Thức", "⚔️ Chiến Tích", "🏆 Vinh Dự", "✨ Vinh Quang"]
    
    item_options = []
    if shop_items:
        for item_id, item_data in shop_items.items():
            itype = item_data.get('type', 'UNKNOWN')
            # [QUAN TRỌNG] Nhận diện Rương Gacha để Admin chọn
            if itype == 'GACHA_BOX': prefix = "🎲 [RƯƠNG]"
            elif itype == 'BUFF_STAT': prefix = "⚔️ [BUFF]"
            elif itype == 'CONSUMABLE': prefix = "💎 [TIÊU THỤ]"
            else: prefix = "📦 [ITEM]"
            
            label = f"{prefix} {item_data.get('name', item_id)} ({item_id})"
            item_options.append(label)

    full_options = currency_options + item_options

    # --- LOAD DỮ LIỆU CŨ ---
    default_data = []
    system_config = st.session_state.data.get('system_config', {})
    current_boss = system_config.get('active_boss')

    if current_boss and 'drop_table' in current_boss:
        for drop in current_boss['drop_table']:
            found_label = drop['id']
            # Map ngược lại label để hiển thị đúng trên UI
            if drop['id'] == 'kpi': found_label = "🔵 KPI"
            elif drop['id'] == 'Tri_Thuc': found_label = "📚 Tri Thức"
            # ... (Các loại tiền tệ khác)
            else:
                for opt in full_options:
                    if f"({drop['id']})" in opt:
                        found_label = opt
                        break
            
            default_data.append({
                "id_display": found_label,
                "amount": drop.get('amount', 1),
                "rate": drop.get('rate', 10.0)
            })

    if not default_data:
        default_data = [{"id_display": "🔵 KPI", "amount": 10, "rate": 100.0}]

    st.info("💡 Bạn có thể chọn **Rương Gacha** vừa tạo ở phần trên để làm phần thưởng.")
    
    edited_table = st.data_editor(
        default_data, 
        num_rows="dynamic",
        column_config={
            "id_display": st.column_config.SelectboxColumn(
                "🎁 Chọn Phần Thưởng (Item/Rương/Tiền)",
                options=full_options, 
                required=True,
                width="large"
            ),
            "amount": st.column_config.NumberColumn("Số lượng", min_value=1, default=1),
            "rate": st.column_config.NumberColumn("Tỷ lệ rơi (%)", min_value=0.1, max_value=100.0, default=100.0, format="%.1f%%")
        },
        key="boss_drop_editor_final",
        use_container_width=True
    )
    return edited_table
# --- HÀM PHỤ TRỢ 2: XỬ LÝ DỮ LIỆU ĐỂ LƯU FILE ---
def xu_ly_du_lieu_drop(raw_table_data):
    """
    Nhiệm vụ: Nhận data thô -> Cắt lấy ID chuẩn -> Trả về List JSON sạch
    """
    # Map ngược key tiền tệ
    currency_map_reverse = {
        "🔵 KPI": "kpi", "📚 Tri Thức": "Tri_Thuc", 
        "⚔️ Chiến Tích": "Chien_Tich", "🏆 Vinh Dự": "Vinh_Du", "✨ Vinh Quang": "Vinh_Quang"
    }
    
    final_list = []
    for row in raw_table_data:
        display_str = row['id_display']
        if display_str in currency_map_reverse:
            entry = {"type": "currency", "id": currency_map_reverse[display_str], "amount": row['amount'], "rate": row['rate']}
        else:
            try:
                real_id = display_str.split('(')[-1].replace(')', '').strip()
            except:
                real_id = display_str
            # Lưu ý: Rương Gacha cũng là 'item' trong túi đồ user
            entry = {"type": "item", "id": real_id, "amount": row['amount'], "rate": row['rate']}
        final_list.append(entry)
    return final_list

# --- HÀM CHÍNH: QUẢN LÝ BOSS ---
import user_module
def admin_quan_ly_boss():
    import user_module
    st.title("👨‍🏫 QUẢN LÝ HỆ THỐNG (BOSS & ITEM)")
    
    # Khởi tạo config nếu chưa có
    if 'system_config' not in st.session_state.data:
        st.session_state.data['system_config'] = {}
    
    sys_config = st.session_state.data['system_config']
    
    # Khởi tạo cấu hình Rương Báu mặc định nếu chưa có
    if 'chest_rewards' not in sys_config:
        sys_config['chest_rewards'] = [
            {"type": "kpi", "val": 50, "rate": 30, "msg": "💰 50 KPI"},
            {"type": "exp", "val": 100, "rate": 30, "msg": "✨ 100 EXP"},
            {"type": "item", "val": "Thẻ X2 KPI", "rate": 10, "msg": "🎫 Thẻ X2 KPI"}
        ]

    # TẠO 3 TAB QUẢN LÝ
    tab_boss, tab_item, tab_chest = st.tabs(["👹 BOSS & DROP", "📦 KHO VẬT PHẨM", "🎰 CẤU HÌNH RƯƠNG BÁU"])

# ==========================================================================
    # TAB 1: QUẢN LÝ BOSS
    # ==========================================================================
    with tab_boss:
        boss_hien_tai = sys_config.get('active_boss')
        
        with st.form("boss_setup_form"):
            st.subheader("🔥 Cấu Hình Boss")
            c1, c2 = st.columns(2)
            
            # Load dữ liệu mặc định
            def_name = boss_hien_tai.get('ten', "Giáo Viên Mới") if boss_hien_tai else "Giáo Viên Mới"
            def_hp = boss_hien_tai.get('hp_max', 1000) if boss_hien_tai else 1000
            def_dmg = boss_hien_tai.get('damage', 30) if boss_hien_tai else 30
            def_img = boss_hien_tai.get('anh', "") if boss_hien_tai else "" 
            
            with c1:
                ten_boss = st.text_input("Tên Boss:", value=def_name)
                
                # 👇👇👇 ĐÃ CẬP NHẬT LẠI DANH SÁCH MÔN HỌC TẠI ĐÂY 👇👇👇
                # Gộp Lý, Hóa, Sinh thành KHTN
                mon_hoc = st.selectbox("Môn học:", ["Toán", "Văn", "Anh", "KHTN"]) 
                
                hp_boss = st.number_input("HP (Máu):", min_value=10, value=int(def_hp), step=100)
                anh_boss = st.text_input("Link Ảnh Boss (URL Online):", value=def_img, placeholder="https://...")
                
            with c2:
                damage_boss = st.number_input("Sát thương:", value=int(def_dmg))
                kpi_rate = st.number_input("Hệ số KPI:", value=1.0)
                exp_rate = st.number_input("Hệ số EXP:", value=5.0)
                
            st.divider()
            st.subheader("🎁 Boss chết rớt gì? (Drop List)")
            # Gọi hàm phụ trợ hiển thị bảng chọn quà
            raw_drop_data = hien_thi_bang_chon_qua_boss()

            if st.form_submit_button("💾 LƯU BOSS & DROP LIST"):
                clean_drop = xu_ly_du_lieu_drop(raw_drop_data)
                
                new_boss = {
                    "ten": ten_boss, "name": ten_boss, "mon": mon_hoc,
                    "hp_max": hp_boss, "hp_current": hp_boss,
                    "damage": damage_boss, "kpi_rate": kpi_rate, "exp_rate": exp_rate,
                    
                    "anh": anh_boss, 
                    
                    "status": "active",
                    "drop_table": clean_drop,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                sys_config['active_boss'] = new_boss
                user_module.save_all_to_sheets(st.session_state.data)
                st.success(f"✅ Đã cập nhật Boss {ten_boss} (Môn: {mon_hoc})!")
                time.sleep(1)
                st.rerun()

        # Nút xóa Boss
        if boss_hien_tai:
            st.divider()
            if st.button("❌ GIẢI TÁN BOSS", type="secondary"):
                sys_config['active_boss'] = None
                user_module.save_all_to_sheets(st.session_state.data)
                st.success("Đã xóa Boss!")
                st.rerun()

    # ==========================================================================
    # TAB 2: QUẢN LÝ KHO ITEM (Thêm Rương, Sửa item...)
    # ==========================================================================
    with tab_item: 
        st.subheader("🛠️ Chế tác Vật phẩm mới")
        with st.expander("Mở công cụ chế tác", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                new_id = st.text_input("Mã ID (VD: Rương Báu):", placeholder="Viet_Lien_Khong_Dau")
                new_type = st.selectbox("Loại:", ["ITEM", "GACHA_BOX", "CONSUMABLE"])
            with c2:
                new_name = st.text_input("Tên hiển thị:", placeholder="Rương Báu")
                new_img = st.text_input("Link ảnh (URL):")

            if st.button("➕ THÊM VÀO KHO"):
                if new_id and new_name:
                    # Logic lưu item
                    if 'shop_items' not in st.session_state.data:
                        st.session_state.data['shop_items'] = {}
                    
                    st.session_state.data['shop_items'][new_id] = {
                        "id": new_id, "name": new_name, "type": new_type,
                        "image": new_img if new_img else "https://cdn-icons-png.flaticon.com/512/1170/1170456.png"
                    }
                    user_module.save_all_to_sheets(st.session_state.data)
                    st.success(f"Đã thêm {new_name}!")
                    st.rerun()
                else:
                    st.error("Thiếu ID hoặc Tên!")

        st.divider()
        st.subheader("📦 Danh sách Vật phẩm trong Kho")
        shop_items = st.session_state.data.get('shop_items', {})
        
        if not shop_items:
            st.info("Kho trống.")
        else:
            # Lấy danh sách từ session_state cho chắc ăn
            shop_items = st.session_state.get('shop_items', {})
            
            for iid, idata in list(shop_items.items()):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 4, 1])
                    
                    # --- Cột 1: Hiển thị Ảnh (Đã sửa chuẩn) ---
                    with c1:
                        img_src = idata.get('image', '')
                        # Logic kiểm tra ảnh an toàn
                        if img_src and "http" in str(img_src):
                            try:
                                st.image(img_src, width=40)
                            except:
                                st.write("📦") # Icon thay thế khi link lỗi
                        else:
                            st.write("📦") # Icon thay thế khi không có link
                    
                    # --- Cột 2: Thông tin ---
                    with c2: 
                        st.write(f"**{idata.get('name', 'Không tên')}**")
                        st.caption(f"ID: `{iid}` | Loại: `{idata.get('type', 'Unknown')}`")
                    
                    # --- Cột 3: Nút Xóa ---
                    with c3:
                        if st.button("🗑️", key=f"del_it_{iid}"):
                            # 1. Xóa trong bộ nhớ RAM (Session State)
                            if iid in st.session_state.shop_items:
                                del st.session_state.shop_items[iid]
                            
                            # 2. Lưu lại vào Google Sheet
                            # Lưu ý: Đảm bảo hàm save_all_to_sheets của bạn có xử lý việc lưu Shop
                            # Hoặc nếu bạn có hàm save_shop_data riêng thì dùng nó:
                            # admin_module.save_shop_data(st.session_state.shop_items) 
                            
                            import user_module
                            # Nếu hàm save_all_to_sheets của bạn lưu cả Shop thì dùng dòng này:
                            user_module.save_all_to_sheets({
                                "players": st.session_state.data.get('players', []), # Giả định cấu trúc
                                "shop_items": st.session_state.shop_items,
                                "system_config": st.session_state.get('system_config', {})
                            })
                            
                            st.toast("Đã xóa vật phẩm!", icon="🗑️")
                            st.rerun()

    # ==========================================================================
    # TAB 3: CẤU HÌNH RƯƠNG BÁU (BẢN FINAL: FIX TÌM ĐỒ + GHI THẲNG SHEET)
    # ==========================================================================
    with tab_chest:
        st.subheader("🎰 Cài đặt Ruột Rương Báu")
        
        # --- NÚT CẬP NHẬT (Để tải lại dữ liệu mới nhất từ Sheet) ---
        if st.button("🔄 Cập nhật dữ liệu Shop từ Google Sheet", use_container_width=True):
            if 'shop_config' in st.session_state:
                del st.session_state.shop_config
            st.rerun()

        # --- 0. TỰ ĐỘNG TẢI DỮ LIỆU TỪ SHOP ---
        if 'shop_config' not in st.session_state:
            try:
                # 1. Kết nối & Mở file
                from user_module import get_gspread_client
                client = get_gspread_client()
                
                # Mở file Spreadsheet (Thử ID -> URL -> File đầu tiên)
                secrets_gcp = st.secrets.get("gcp_service_account", {})
                if "spreadsheet_id" in secrets_gcp:
                    sh = client.open_by_key(secrets_gcp["spreadsheet_id"])
                elif "spreadsheet_url" in secrets_gcp:
                    sh = client.open_by_url(secrets_gcp["spreadsheet_url"])
                else:
                    sh = client.openall()[0]

                # 2. Tìm tab Shop
                wks = None
                for name in ["Shop", "shop", "Cửa hàng", "Items"]:
                    try:
                        wks = sh.worksheet(name)
                        break
                    except: continue
                
                if wks:
                    st.session_state.shop_config = wks.get_all_records()
                    st.success("✅ Đã tải danh sách vật phẩm thành công!")
                else:
                    st.error("⚠️ Không tìm thấy tab 'Shop' trên Google Sheet.")
                    st.session_state.shop_config = []
                    
            except Exception as e:
                st.session_state.shop_config = []

        # --- 1. HIỂN THỊ LIST HIỆN TẠI ---
        if 'chest_rewards' not in sys_config:
            sys_config['chest_rewards'] = []
            
        current_rewards = sys_config['chest_rewards']
        if current_rewards:
            for idx, reward in enumerate(current_rewards):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([0.5, 2, 1, 0.5])
                    with c1:
                        st.write("📦" if reward['type'] == 'item' else ("💰" if reward['type'] == 'kpi' else "✨"))
                    with c2:
                        st.write(f"**{reward['msg']}**")
                        st.caption(f"Loại: `{reward['type']}` | Giá trị: `{reward['val']}`")
                    with c3:
                        st.info(f"Tỷ lệ: {reward['rate']}")
                    with c4:
                        if st.button("🗑️", key=f"del_chest_{idx}"):
                            current_rewards.pop(idx)
                            # Lưu nhanh khi xóa
                            import json
                            from user_module import get_gspread_client
                            try:
                                client = get_gspread_client()
                                secrets_gcp = st.secrets.get("gcp_service_account", {})
                                if "spreadsheet_id" in secrets_gcp: sh = client.open_by_key(secrets_gcp["spreadsheet_id"])
                                elif "spreadsheet_url" in secrets_gcp: sh = client.open_by_url(secrets_gcp["spreadsheet_url"])
                                else: sh = client.openall()[0]
                                wks_settings = sh.worksheet("Settings")
                                json_str = json.dumps(current_rewards, ensure_ascii=False)
                                cell = wks_settings.find("chest_rewards")
                                if cell: wks_settings.update_cell(cell.row, cell.col + 1, json_str)
                            except: pass
                            st.rerun()

        st.divider()
        
        # --- 2. FORM THÊM QUÀ ---
        st.write("#### ➕ Thêm quà vào Rương")
        
        # --- LOGIC ĐỌC ITEM THÔNG MINH (Code của bạn) ---
        item_source_map = {} 
        raw_shop = st.session_state.get('shop_config', [])
        
        if raw_shop:
            for item in raw_shop:
                # 🔥 Fix lỗi ID/id tại đây
                i_id = item.get('ID') or item.get('id') or item.get('Item_ID')
                i_name = item.get('Name') or item.get('name') or item.get('Item_Name') or i_id
                
                if i_id:
                    item_source_map[str(i_id).strip()] = f"{i_name} (Shop)"

        # Nguồn phụ: Kho Admin
        if 'admin' in st.session_state.data:
            for item in st.session_state.data['admin'].get('inventory', []):
                if isinstance(item, dict):
                    item_source_map[item.get('id')] = f"{item.get('name')} (Kho Admin)"
                else:
                    item_source_map[str(item)] = f"{str(item)} (Kho Admin)"
        
        # --- GIAO DIỆN NHẬP LIỆU ---
        with st.container(border=True):
            col_type, col_val = st.columns(2)
            
            with col_type:
                r_type = st.selectbox(
                    "1. Chọn Loại quà:", ["kpi", "exp", "item"],
                    format_func=lambda x: "📦 Vật Phẩm (Item)" if x == 'item' else x.upper()
                )

            with col_val:
                final_val = 0
                if r_type in ['kpi', 'exp']:
                    final_val = st.number_input("2. Số lượng:", min_value=1, value=50)
                    default_msg = f"Bạn nhận được {final_val} {r_type.upper()}!"
                else:
                    if item_source_map:
                        selected_item_id = st.selectbox(
                            "2. Chọn Vật phẩm:", list(item_source_map.keys()),
                            format_func=lambda x: f"{x} - {item_source_map.get(x)}"
                        )
                        final_val = selected_item_id
                        raw_name = item_source_map.get(selected_item_id, "").split('(')[0].strip()
                        default_msg = f"Bạn nhận được vật phẩm: {raw_name}!"
                    else:
                        st.warning("⚠️ Không tìm thấy dữ liệu Item!")
                        final_val = st.text_input("Nhập thủ công ID:")
                        default_msg = "Bạn nhận được quà!"

            c_rate, c_msg = st.columns([1, 2])
            with c_rate:
                r_rate = st.number_input("3. Tỷ lệ (Trọng số):", min_value=1, value=10)
            with c_msg:
                r_msg = st.text_input("4. Thông báo:", value=default_msg)

            st.write("")
            
            # --- 🔥 NÚT LƯU TRỰC TIẾP (QUAN TRỌNG NHẤT) 🔥 ---
            if st.button("💾 Lưu vào Rương", type="primary", use_container_width=True):
                if r_type == 'item' and not final_val:
                    st.error("❌ Thiếu thông tin vật phẩm!")
                elif not r_msg:
                    st.error("❌ Thiếu thông báo!")
                else:
                    # 1. Cập nhật Session State
                    new_reward = {
                        "type": r_type, "val": final_val, 
                        "rate": int(r_rate), "msg": r_msg
                    }
                    sys_config['chest_rewards'].append(new_reward)
                    
                    # 2. GHI THẲNG VÀO SHEET (Fix lỗi không lưu)
                    try:
                        with st.spinner("Đang ghi dữ liệu lên mây..."):
                            import json
                            from user_module import get_gspread_client
                            
                            client = get_gspread_client()
                            # Mở Sheet
                            secrets_gcp = st.secrets.get("gcp_service_account", {})
                            if "spreadsheet_id" in secrets_gcp: sh = client.open_by_key(secrets_gcp["spreadsheet_id"])
                            elif "spreadsheet_url" in secrets_gcp: sh = client.open_by_url(secrets_gcp["spreadsheet_url"])
                            else: sh = client.openall()[0]
                            
                            # Vào tab Settings
                            wks_settings = sh.worksheet("Settings")
                            json_str = json.dumps(sys_config['chest_rewards'], ensure_ascii=False)
                            
                            # Tìm dòng 'chest_rewards' để ghi đè
                            try:
                                cell = wks_settings.find("chest_rewards")
                                if cell:
                                    wks_settings.update_cell(cell.row, cell.col + 1, json_str)
                                else:
                                    wks_settings.append_row(["chest_rewards", json_str])
                            except:
                                wks_settings.append_row(["chest_rewards", json_str])
                                
                        st.success("✅ Đã lưu thành công vào Google Sheet!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Lỗi ghi Sheet: {e}")
                        
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
            # 1. Cập nhật dữ liệu từ bảng chỉnh sửa vào bộ nhớ tạm (Đoạn này giữ nguyên)
            for index, row in edited_df.iterrows():
                for col in edit_cols:
                    if col != 'name':
                        st.session_state.data[index][col] = row[col]
            
            # 2. --- [THAY ĐỔI QUAN TRỌNG] ---
            # Bỏ dòng save_data_func cũ đi. Gọi trực tiếp hàm an toàn mới:
            import user_module  # Import để tránh lỗi UnboundLocalError
            
            # Gọi hàm save_all_to_sheets (Hàm này đã có chốt chặn đếm học sinh)
            if user_module.save_all_to_sheets(st.session_state.data):
                st.success("Admin đã cập nhật dữ liệu thành công!")
                import time
                time.sleep(1) # Dừng 1 xíu để kịp nhìn thông báo
                st.rerun()
            else:
                # Nếu hàm trả về False (do dữ liệu rỗng hoặc lỗi), nó sẽ hiện lỗi đỏ
                st.error("❌ Cập nhật thất bại! Hệ thống đã chặn lệnh lưu để bảo vệ dữ liệu.")

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
                            new_data = st.session_state.data.copy() if 'data' in st.session_state else {}
                            
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
                                existing_user = new_data.get(u_id, {})
                                new_data[u_id] = {
                                    "name": full_name,
                                    "team": str(row.get('team', row.get('Tổ', 'Chưa phân tổ'))),
                                    "grade": grade_folder,
                                    "role": str(row.get('role', 'u3')).lower(),
                                    "password": str(row.get('Password', '123456')), # Mật khẩu mặc định
                                    "kpi": int(row.get('KPI', 0)), # KPI mặc định 100
                                    # --- THÊM DÒNG NÀY ĐỂ FIX LỖI MẤT CỘT ---
                                    "special_permissions": {
                                        "world_chat_count":0
                                    },    
                                    # Các chỉ số game
                                    "Vi_Pham": 0, "Bonus": 0, "KTTX": 0, "KT Sản phẩm": 0,
                                    "KT Giữa kỳ": 0, "KT Cuối kỳ": 0, "Tri_Thuc": 0,
                                    "Chien_Tich": 0, "Vinh_Du": 0, "Vinh_Quang": 0,
                                    "titles": ["Tân Thủ Học Sĩ"],
                                    "inventory": {},
                                    "total_score": 0.0 # Reset điểm học tập
                                }
                            
                            # --- [BƯỚC 3] TRẢ LẠI ADMIN & CẤU HÌNH VÀO DATA MỚI ---
                            # 1. Bảo vệ dữ liệu Admin và các quyền đặc biệt
                            if 'admin' in st.session_state.data:
                                # Lấy lại special_permissions của admin cũ nếu có, nếu không thì tạo mới
                                admin_perms = st.session_state.data['admin'].get('special_permissions', {"world_chat_count": 5})
                                preserved_admin['special_permissions'] = admin_perms

                            new_data['admin'] = preserved_admin

                            if preserved_ranks:
                                new_data['rank_settings'] = preserved_ranks

                            # 2. KIỂM TRA AN TOÀN TRƯỚC KHI LƯU
                            if len(new_data) > 1: # Ít nhất phải có Admin + 1 User
                                # Cập nhật Session State
                                st.session_state.data = new_data
                                
                                try:
                                    # Gọi hàm lưu - Hãy đảm bảo save_data của bạn nhận diện được dict lồng nhau
                                    save_data(st.session_state.data) 
                                    
                                    st.success(f"🎊 Chúc mừng! Đã kích hoạt {len(new_data)-1} tài khoản (Cột và Quyền lợi đã được bảo vệ).")
                                    st.balloons()
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Lỗi khi ghi dữ liệu lên Sheets: {e}")
                            else:
                                st.warning("⚠️ Cảnh báo: Dữ liệu mới đang trống, hệ thống đã ngăn chặn việc ghi đè để bảo vệ Sheets!")

                except Exception as e:
                    st.error(f"❌ Lỗi khi xử lý file Excel: {e}")


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
            
            # 6. NÚT XÁC NHẬN LƯU THAY ĐỔI (BẢN FIX AN TOÀN)
            if st.button("💾 XÁC NHẬN THAY ĐỔI TOÀN BỘ", use_container_width=True):
                role_to_code = {"Tổ trưởng": "u1", "Tổ phó": "u2", "Tổ viên": "u3"}
                
                # Tạo một bản sao dữ liệu hiện tại để tránh lỗi tham chiếu
                temp_data = st.session_state.data.copy()
                
                for _, row in edited_df.iterrows():
                    u_id = str(row['User ID'])
                    
                    # Xác định mật khẩu và chức vụ mới
                    new_password = "123" if row.get('Reset_123') else str(row.get('password', '123456'))
                    new_role = role_to_code.get(row.get('role'), "u3")
                    
                    if u_id in temp_data:
                        # Cập nhật thông tin cơ bản
                        temp_data[u_id]["team"] = row.get('team', temp_data[u_id].get('team', 'Chưa phân tổ'))
                        temp_data[u_id]["role"] = new_role
                        temp_data[u_id]["password"] = new_password
                        
                        # --- QUAN TRỌNG: Đảm bảo các key cần thiết cho hàm save_all_to_sheets tồn tại ---
                        # Nếu thiếu các key này, hàm lưu sẽ tạo ra dòng dữ liệu lỗi/rỗng
                        keys_to_check = ['exp', 'level', 'hp', 'hp_max', 'kpi', 'inventory', 'dungeon_progress']
                        for k in keys_to_check:
                            if k not in temp_data[u_id]:
                                if k == 'special_permissions': temp_data[u_id][k] = {"world_chat_count": 0}
                                elif k in ['inventory', 'dungeon_progress']: temp_data[u_id][k] = {}
                                elif k in ['hp', 'hp_max']: temp_data[u_id][k] = 100
                                else: temp_data[u_id][k] = 0

                # Cập nhật session và Lưu
                st.session_state.data = temp_data
                
                # Gọi hàm lưu an toàn
                if len(st.session_state.data) > 0:
                    st.info("🔄 Đang xử lý lưu trữ...")
                    import user_module
                    # Gọi hàm save_data từ user_module
                    if user_module.save_all_to_sheets(st.session_state.data):
                        st.success("🎉 Đã cập nhật thành công!")
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Lỗi khi gọi hàm lưu.")
                else:
                    st.error("⚠️ Dữ liệu rỗng, hủy thao tác.")

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
                
                # --- CHỨC NĂNG MỚI: NIÊM YẾT ---
                is_listed = st.checkbox("🏪 Niêm yết lên Tiệm tạp hóa", value=True, help="Nếu tắt, vật phẩm này chỉ dùng để làm quà Drop từ Boss/Phó bản, không hiện trong shop.")
            
            with col2:
                item_behavior = st.selectbox("Loại Logic (Behavior):", options=list(registry.keys()), 
                                             format_func=lambda x: registry[x]["name"])
                
                properties = {}
                item_def = registry[item_behavior]
                params = item_def["params"]
                labels = item_def.get("labels", {})

                st.write("🔧 **Thiết lập chỉ số đặc thù:**")
                for p_name, p_type in params.items():
                    display_label = labels.get(p_name, p_name)
                    if isinstance(p_type, list):
                        properties[p_name] = st.selectbox(display_label, options=p_type, key=f"new_{p_name}")
                    else:
                        properties[p_name] = st.number_input(display_label, value=0, key=f"new_{p_name}")
                
                desc = st.text_area("Mô tả công dụng hiển thị:")

            if st.button("📦 ĐƯA VẬT PHẨM LÊN KỆ", use_container_width=True):
                if name:
                    st.session_state.shop_items[name] = {
                        "id": name,
                        "price": price,
                        "currency_buy": currency_map[buy_with],
                        "image": img if img else "https://cdn-icons-png.flaticon.com/512/1236/1236525.png",
                        "type": item_behavior,
                        "properties": properties, 
                        "limit_type": limit_type,
                        "limit_amount": limit_amount,
                        "is_listed": is_listed, # <--- LƯU TRẠNG THÁI ẨN/HIỆN
                        "desc": desc
                    }
                    import user_module
                    user_module.save_all_to_sheets(st.session_state.data) 
        
                    st.success(f"✅ Đã lưu '{name}' thành công!")
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

            # --- NÚT DỠ HÀNG (ĐÃ SỬA LOGIC LƯU) ---
            if 'shop_items' in st.session_state and st.session_state.shop_items:
                target_del = st.selectbox("Chọn vật phẩm muốn dỡ khỏi kệ:", list(st.session_state.shop_items.keys()))
                
                if st.button(f"🗑️ DỠ '{target_del}' XUỐNG"):
                    # 1. Xóa khỏi bộ nhớ tạm (Session State)
                    del st.session_state.shop_items[target_del]
                    
                    # 2. GỌI LỆNH LƯU CHUẨN (Quan trọng)
                    # Truyền st.session_state.data để hàm save hoạt động đúng logic Admin/Players
                    # Hàm save sẽ tự động lấy shop_items mới nhất (đã xóa món kia) từ session_state để ghi đè lên Sheets
                    import user_module
                    user_module.save_all_to_sheets(st.session_state.data)
                    
                    st.success(f"Đã dỡ bỏ '{target_del}' thành công!")
                    st.rerun()
            else:
                st.info("Kệ hàng hiện đang trống.")

        st.divider()

        # --- PHẦN 3: ĐIỀU PHỐI KHO CÁ NHÂN & TẶNG QUÀ ---
        st.subheader("🎁 ĐIỀU PHỐI VẬT PHẨM")
        tab1, tab2 = st.tabs(["Tặng quà", "Thu hồi"])
            
        with tab1:
            col_u, col_i, col_q = st.columns(3)
            
            #Lấy danh sách tên hiển thị từ data
            all_names = [info['name'] for uid, info in st.session_state.data.items() 
                         if isinstance(info, dict) and 'name' in info]
            
            with col_u: 
                #Thêm lựa chọn "TẤT CẢ HỌC SĨ" vào danh sách
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
                        
                        save_data_func(st.session_state.data)
                        st.success(f"🎊 Đã phát quà đại trà! {gift_qty} {gift_item} đã được gửi tới {count_success} học sĩ!")

                    # TRƯỜNG HỢP 2: TẶNG CHO CÁ NHÂN (ĐÃ FIX LỖI SYNTAX)
                    else:
                        # Lọc tìm ID của học sinh dựa trên tên hiển thị
                        u_id = next((uid for uid, info in st.session_state.data.items() 
                                     if isinstance(info, dict) and info.get('name') == target_user), None)
                        
                        if u_id:
                            # Khởi tạo túi đồ nếu chưa có
                            if 'inventory' not in st.session_state.data[u_id] or not isinstance(st.session_state.data[u_id]['inventory'], dict):
                                st.session_state.data[u_id]['inventory'] = {}
                            
                            inventory = st.session_state.data[u_id]['inventory']
                            inventory[gift_item] = inventory.get(gift_item, 0) + gift_qty
                            
                            # CẬP NHẬT GỌI HÀM LƯU ĐÚNG CÁCH (Có truyền data)
                            save_data_func(st.session_state.data)
                            st.success(f"🎁 Đã tặng {gift_qty} {gift_item} cho {target_user}!")
                        else:
                            st.error("❌ Không tìm thấy thông tin học sĩ này trong dữ liệu!")

        with tab2:
            del_user = st.selectbox("Chọn Học Sĩ muốn xóa kho:", all_names, key="del_user")
            if st.button("🔥 XÓA SẠCH TÚI ĐỒ"):
                u_id = [uid for uid, info in st.session_state.data.items() if info['name'] == del_user][0]
                st.session_state.data[u_id]['inventory'] = []
                save_data_func(st.session_state.data) 
                st.warning(f"Đã tịch thu toàn bộ vật phẩm của {del_user}!")


        # ==============================================================================
        # 🎲 PHẦN MỚI: CÔNG XƯỞNG CHẾ TẠO RƯƠNG GACHA (LOOT BOX)
        # ==============================================================================
        with st.expander("🎲 CHẾ TẠO RƯƠNG THẦN BÍ (GACHA SYSTEM)", expanded=False):
            st.info("💡 Cơ chế mới: Tỷ lệ rơi độc lập. Mỗi vật phẩm trong rương sẽ được tung xúc xắc riêng.")

            # 1. Khởi tạo session state tạm
            if 'temp_loot_table' not in st.session_state:
                st.session_state.temp_loot_table = []

            c1, c2 = st.columns([1, 1.5])

            with c1:
                st.markdown("#### 🅰️ THIẾT KẾ VỎ RƯƠNG")
                box_name = st.text_input("Tên Rương (ID):", placeholder="Ví dụ: ruong_boss_the_gioi", key="gacha_name")
                # Thêm tên hiển thị tiếng Việt cho đẹp
                box_display_name = st.text_input("Tên Hiển Thị:", placeholder="Rương Boss Thế Giới", key="gacha_disp_name")
                
                box_img = st.text_input("Ảnh Rương (URL):", placeholder="Link ảnh rương...", key="gacha_img")
                
                rarity_opt = {
                    "common": "⚪ Phổ biến (Trắng)",
                    "rare": "🔵 Hiếm (Xanh dương)",
                    "epic": "🟣 Sử thi (Tím)",
                    "legendary": "🟠 Huyền thoại (Cam)",
                    "mythic": "🔴 Thần thoại (Đỏ)"
                }
                box_rarity = st.selectbox("Độ hiếm:", list(rarity_opt.keys()), format_func=lambda x: rarity_opt[x])
                
                currency_map = {
                    "kpi": "🏆 KPI", 
                    "Tri_Thuc": "📘 Tri Thức", 
                    "Chien_Tich": "⚔️ Chiến Tích", 
                    "Vinh_Du": "🎖️ Vinh Dự"
                }
                box_price = st.number_input("Giá bán:", min_value=0, value=100, step=10, key="gacha_price")
                box_curr = st.selectbox("Loại tiền mua:", list(currency_map.keys()), format_func=lambda x: currency_map[x], key="gacha_curr")

                # --- CHỨC NĂNG MỚI: TÙY CHỌN ẨN/HIỆN TRÊN KỆ ---
                is_listed = st.checkbox("🏪 Niêm yết lên Tiệm tạp hóa", value=True, 
                                        help="Nếu TẮT, rương này sẽ bị ẨN khỏi Shop và chuyển vào Kho Lưu Trữ (Dùng làm quà Drop).")

            with c2:
                st.markdown("#### 🅱️ NẠP RUỘT RƯƠNG (LOOT TABLE)")
                
                with st.form("add_loot_form", clear_on_submit=True):
                    col_l1, col_l2, col_l3, col_l4 = st.columns([2, 1.5, 1, 1])
                    
                    # --- CHUẨN BỊ DANH SÁCH VẬT PHẨM ĐỂ CHỌN ---
                    item_options = ["-- Chọn --"]
                    item_id_map = {"-- Chọn --": "-- Chọn --"}

                    if 'shop_items' in st.session_state.data:
                        for k, v in st.session_state.data['shop_items'].items():
                            # Không cho rương chứa chính rương
                            if v.get('type') == 'GACHA_BOX': continue
                                
                            is_hidden = not v.get('is_listed', True)
                            status_icon = "🔒 [ẨN]" if is_hidden else "🏪 [SHOP]"
                            display_label = f"{status_icon} {v.get('name', k)} ({k})"
                            
                            item_options.append(display_label)
                            item_id_map[display_label] = k

                    with col_l1:
                        reward_type = st.selectbox("Loại quà:", ["Item (Vật phẩm)", "Currency (Tiền tệ)"])
                    
                    # Khởi tạo biến
                    target_id = "-- Chọn --" 

                    with col_l2:
                        if reward_type == "Item (Vật phẩm)":
                            selected_display = st.selectbox("Chọn vật phẩm:", item_options)
                            target_id = item_id_map.get(selected_display, "-- Chọn --")
                        else:
                            currency_opts = {"KPI": "kpi", "Tri Thức": "Tri_Thuc", "Chiến Tích": "Chien_Tich", "Vinh Dự": "Vinh_Du"}
                            curr_display = st.selectbox("Loại tiền:", list(currency_opts.keys()))
                            target_id = currency_opts[curr_display]

                    with col_l3:
                        drop_rate = st.number_input("Tỷ lệ %:", min_value=0.1, max_value=100.0, value=10.0, step=0.1)
                    with col_l4:
                        drop_qty = st.number_input("SL:", min_value=1, value=1)
                        
                    add_btn = st.form_submit_button("➕ Thêm")

                    if add_btn:
                        if target_id and target_id != "-- Chọn --":
                            st.session_state.temp_loot_table.append({
                                "type": "item" if reward_type == "Item (Vật phẩm)" else "currency",
                                "id": target_id,
                                "rate": drop_rate,
                                "amount": drop_qty
                            })
                            st.success(f"Đã thêm {target_id} ({drop_rate}%)")
                        else:
                            st.error("Vui lòng chọn vật phẩm hợp lệ!")

                # HIỂN THỊ DANH SÁCH TẠM
                if st.session_state.temp_loot_table:
                    st.markdown("##### 📋 Danh sách trong rương:")
                    for idx, item in enumerate(st.session_state.temp_loot_table):
                        icon = "📦" if item['type'] == 'item' else "💰"
                        st.markdown(f"{idx+1}. {icon} **{item['id']}** (x{item['amount']}) - Tỷ lệ: `{item['rate']}%`")
                    
                    if st.button("🗑️ Xóa làm lại"):
                        st.session_state.temp_loot_table = []
                        st.rerun()

            st.divider()
            
            # --- NÚT ĐÓNG GÓI (TẠO RƯƠNG) ---
            if st.button("🎁 ĐÓNG GÓI RƯƠNG NGAY", type="primary", use_container_width=True):
                # [FIX LỖI] Import thư viện datetime với tên riêng để không bị trùng biến 'datetime' ở nơi khác
                import datetime as dt_lib 
                import time
                if box_name and st.session_state.temp_loot_table:
                    # Tạo cấu trúc dữ liệu rương mới
                    new_chest_data = {
                        "id": box_name,
                        # Ưu tiên tên hiển thị, nếu không có thì dùng ID
                        "name": box_display_name if 'box_display_name' in locals() and box_display_name else box_name, 
                        "price": box_price,
                        "currency_buy": box_curr,
                        "image": box_img if box_img else "https://cdn-icons-png.flaticon.com/512/4256/4256846.png",
                        "type": "GACHA_BOX",  
                        "is_listed": is_listed, 
                        "properties": {
                            "rarity": box_rarity,
                            "loot_table": st.session_state.temp_loot_table 
                        },
                        "limit_type": "none", 
                        "limit_value": 0,
                        "desc": f"Chứa {len(st.session_state.temp_loot_table)} loại quà. Mở để thử vận may!",
                        # [FIX LỖI] Dùng dt_lib.datetime.now() thay vì datetime.now()
                        "created_at": dt_lib.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Lưu vào Shop Items
                    if 'shop_items' not in st.session_state.data:
                        st.session_state.data['shop_items'] = {}
                        
                    st.session_state.data['shop_items'][box_name] = new_chest_data
                    
                    # Gọi hàm lưu an toàn lên Google Sheets
                    if user_module.save_all_to_sheets(st.session_state.data):
                        st.session_state.temp_loot_table = [] 
                        st.balloons()
                        status_msg = "đã được BÀY BÁN trên Shop" if is_listed else "đã được CẤT VÀO KHO ẨN"
                        # Kiểm tra an toàn biến box_display_name khi hiển thị thông báo
                        disp_name = box_display_name if 'box_display_name' in locals() and box_display_name else box_name
                        st.success(f"✅ Rương **{disp_name}** {status_msg} thành công!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Lỗi lưu trữ Cloud!")
                else:
                    st.error("❌ Thiếu tên rương hoặc danh sách vật phẩm rỗng!")
            
        # ==============================================================================
        # 📦 PHẦN MỚI: QUẢN LÝ KHO ẨN (ĐÃ CHỈNH SỬA)
        # ==============================================================================
        with st.expander("📦 KHO VẬT PHẨM LƯU TRỮ (ĐANG ẨN KHỎI SHOP)", expanded=False):
            st.write("Dưới đây là các vật phẩm/rương chỉ dùng để làm quà Drop, không hiển thị cho học sinh mua.")
            
            # Lọc danh sách item đang ẩn
            shop_items = st.session_state.data.get('shop_items', {})
            hidden_items = {k: v for k, v in shop_items.items() if not v.get('is_listed', True)}
            
            if not hidden_items:
                st.info("Hiện không có vật phẩm nào đang ẩn.")
            else:
                for tid, tinfo in hidden_items.items():
                    with st.container(border=True):
                        # Chia cột: Ảnh | Thông tin | Chức năng
                        col_a, col_b, col_c = st.columns([1, 4, 2]) 
                        
                        with col_a:
                            st.image(tinfo.get('image'), width=60)
                        
                        with col_b:
                            st.markdown(f"**{tinfo.get('name')}** (`{tid}`)")
                            st.caption(f"Loại: {tinfo.get('type')} | 💰 Giá gốc: {tinfo.get('price')}")
                            st.caption(f"📝 {tinfo.get('desc', 'Không có mô tả')}")
                        
                        with col_c:
                            # Chia nhỏ cột chức năng thành 2 nút: Hiện lại & Xóa
                            btn_col1, btn_col2 = st.columns(2)
                            
                            with btn_col1:
                                if st.button("🔓 Hiện", key=f"unhide_list_{tid}", help="Đưa vật phẩm này quay lại Shop", use_container_width=True):
                                    st.session_state.data['shop_items'][tid]['is_listed'] = True
                                    

                                    user_module.save_all_to_sheets(st.session_state.data)
                                    st.success(f"Đã niêm yết '{tinfo.get('name')}'!")
                                    st.rerun()
                            
                            with btn_col2:
                                if st.button("🗑️ Xóa", key=f"del_hidden_{tid}", help="Xóa vĩnh viễn", type="primary", use_container_width=True):
                                    del st.session_state.data['shop_items'][tid]
                                    

                                    user_module.save_all_to_sheets(st.session_state.data)
                                    st.success(f"Đã xóa vĩnh viễn '{tid}'!")
                                    st.rerun()
            
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
                save_data_func(st.session_state.data)
            # ---------------------------------------------------------
            
            st.success("✅ Đã cập nhật và lưu hệ thống danh hiệu vĩnh viễn!")
            st.balloons()

    elif page == "🏟️ Quản lý lôi đài":
        quan_ly_loi_dai_admin(save_data_func) # Gọi hàm để hiển thị giao diện quản lý


    elif page == "⚠️ Xóa dữ liệu":
        st.subheader("♻️ KHU VỰC TỐI NGUY HIỂM: RESET NĂM HỌC")
        st.warning("⚠️ CHÚ Ý: Hành động này sẽ xóa sạch dữ liệu học sinh và lịch sử đấu PVP.\n\n🛡️ Cấu hình (Boss, Rank), Shop, Market và Logs sẽ được GIỮ NGUYÊN.")

        with st.expander("👉 NHẤN VÀO ĐÂY ĐỂ THỰC HIỆN"):
            confirm_text = st.text_input("Nhập chữ 'RESET' để xác nhận:", key="reset_confirm_input")
            
            if st.button("🔥 THỰC HIỆN RESET (CHỈ PLAYERS & PVP)"):
                if confirm_text == "RESET":
                    import time
                    import json
                    import user_module # Import module chứa hàm kết nối GSheet
                    
                    status_placeholder = st.empty()
                    status_placeholder.info("⏳ Đang khởi động quy trình reset an toàn...")

                    # 1. Kết nối Google Sheet
                    try:
                        client = user_module.get_gspread_client()
                        sh = client.open(user_module.SHEET_NAME)
                    except Exception as e:
                        st.error(f"❌ Lỗi kết nối Google Sheet: {e}")
                        st.stop()

                    # =========================================================
                    # 🛠️ XỬ LÝ TAB "Players" (Chuẩn hóa)
                    # =========================================================
                    try:
                        status_placeholder.info("🧹 Đang dọn dẹp tab Players...")
                        
                        # 1.1. Xác định đúng tên tab
                        try: 
                            wks_players = sh.worksheet("Players")
                        except: 
                            st.error("❌ Không tìm thấy tab 'Players'. Hãy kiểm tra lại tên tab trên Google Sheet!")
                            st.stop()
                        
                        # 1.2. Lấy dữ liệu cũ để tìm Admin
                        all_values = wks_players.get_all_values()
                        
                        admin_row_data = []
                        
                        # Tìm dòng chứa id là 'admin'
                        if len(all_values) > 1:
                            for row in all_values[1:]: 
                                # Kiểm tra cột đầu tiên (user_id)
                                if str(row[0]).strip().lower() == 'admin':
                                    admin_row_data = row
                                    break
                        
                        # Nếu không tìm thấy, tạo Admin mặc định
                        if not admin_row_data:
                            adm = st.session_state.data.get('admin', {})
                            admin_row_data = [
                                "admin", adm.get("name", "Administrator"), "Quản trị", "admin", adm.get("password", "123"),
                                "0", "0", "99", "100", "100", "0", "{}", "{}", "{}"
                            ]

                        # 1.3. Định nghĩa Header CHUẨN
                        players_header = [
                            "user_id", "name", "team", "role", "password", 
                            "kpi", "exp", "level", "hp", "hp_max", 
                            "world_chat_count", "stats_json", "inventory_json", "progress_json"
                        ]
                        
                        # 1.4. Ghi đè dữ liệu mới
                        wks_players.clear()
                        data_to_write = [players_header, admin_row_data]
                        wks_players.update(range_name="A1", values=data_to_write)
                        
                        # 🔥 [ĐÃ SỬA] Thay icon="user" thành emoji "👤"
                        st.toast("✅ Đã reset tab Players (Giữ nguyên Admin & Cột)!", icon="👤")

                    except Exception as e:
                        st.error(f"❌ Lỗi xử lý tab Players: {e}")

                    # =========================================================
                    # 🛠️ XỬ LÝ TAB "PVP" (Chuẩn hóa)
                    # =========================================================
                    try:
                        status_placeholder.info("⚔️ Đang dọn dẹp tab PVP...")
                        try: 
                            wks_pvp = sh.worksheet("PVP")
                        except:
                            try: wks_pvp = sh.worksheet("Loi_Dai")
                            except: wks_pvp = None
                        
                        if wks_pvp:
                            wks_pvp.clear()
                            # Header chuẩn PVP
                            pvp_header = ["Match_ID", "Full_JSON_Data", "Status", "Created_At"]
                            wks_pvp.append_row(pvp_header)
                            
                            st.toast("✅ Đã reset tab PVP (Header chuẩn)!", icon="⚔️")
                        else:
                            st.warning("⚠️ Không tìm thấy tab PVP để reset.")

                    except Exception as e:
                        st.error(f"❌ Lỗi xử lý tab PVP: {e}")

                    # =========================================================
                    # 🔄 CẬP NHẬT SESSION STATE (RAM)
                    # =========================================================
                    status_placeholder.info("🔄 Đang cập nhật bộ nhớ hệ thống...")
                    
                    # Giữ lại cấu hình quan trọng
                    saved_admin = st.session_state.data.get('admin', {})
                    saved_rank = st.session_state.data.get('rank_settings', [])
                    saved_sys = st.session_state.get('system_config', {})
                    saved_shop = st.session_state.get('shop_items', {})

                    # Reset data trong RAM
                    st.session_state.data = {
                        'admin': saved_admin,
                        'players': [], 
                        'rank_settings': saved_rank
                    }
                    
                    # Khôi phục config
                    st.session_state.system_config = saved_sys
                    st.session_state.shop_items = saved_shop
                    
                    # Xóa biến tạm
                    keys_to_del = ["dang_danh_dungeon", "current_q_idx", "match_result_notified"]
                    for k in keys_to_del:
                        if k in st.session_state: del st.session_state[k]

                    status_placeholder.success("🎉 RESET HOÀN TẤT! Dữ liệu đã sạch sẽ và an toàn.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Vui lòng nhập đúng chữ 'RESET' để xác nhận.")
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