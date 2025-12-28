import json
import os
import streamlit as st
from datetime import datetime, timedelta
def get_item_behavior_registry():
    return {
        "BUFF_STAT": {
            "name": "⚔️ Tăng Chỉ Số Chiến Đấu",
            "params": {
                "target_stat": ["atk", "hp"],
                "value": "number", 
                "duration_type": ["one_hit", "time_limit", "permanent"],
                "duration_value": "number"
            },
            # ĐÂY LÀ PHẦN DỊCH TIÊU ĐỀ
            "labels": {
                "target_stat": "Chỉ số tác động",
                "value": "Giá trị cộng thêm",
                "duration_type": "Hình thức tác dụng",
                "duration_value": "Thời gian hiệu lực (Phút)"
            }
        },
        "CONSUMABLE": {
            "name": "💎 Tiêu Thụ (Nhận tài nguyên)",
            "params": {
                "target_type": ["hp", "atk", "kpi", "vinh_du", "vinh_quang", "chien_tich", "tri_thuc"],
                "value": "number"
            },
            "labels": {
                "target_type": "Loại tài nguyên",
                "value": "Số lượng nhận"
            }
        },
        "FUNCTIONAL": {
            "name": "🛠️ Vật Phẩm Chức Năng",
            "params": {
                "feature": ["world_chat", "market_discount", "gift_announcement"],
                "power_value": "number"
            },
            "labels": {
                "feature": "Tính năng kích hoạt",
                "power_value": "Số lượt/Phần trăm"
            }
        },
        "BOSS_RESET": {
            "name": "📜 Lệnh Bài Hồi Sinh Boss",
            "params": {
                "reset_type": ["instant_reset"], # Loại bỏ thời gian chờ ngay lập tức
                "value": "number"                # Có thể dùng để reset số lượt (nếu cần)
            },
            "labels": {
                "reset_type": "Loại kích hoạt",
                "value": "Số lượt phục hồi"
            }
        }

    }

def get_item_info(item_name):
    """
    Tra cứu thông tin vật phẩm từ Shop Admin.
    Dùng phương pháp chuẩn hóa tên để tránh lỗi hoa/thường.
    """
    shop_items = st.session_state.get('shop_items', {})
    
    # 1. Thử tìm chính xác
    if item_name in shop_items:
        return shop_items[item_name]
    
    # 2. Nếu không thấy, thử tìm theo kiểu viết thường
    for key, value in shop_items.items():
        if key.lower() == item_name.lower():
            return value
            
    return None



def apply_item_effect(user_id, item_object, current_data):
    """
    Hàm xử lý TẤT CẢ tác động của vật phẩm: Thẻ thông báo, Thuốc, Tiền tệ, Boss.
    """
    if user_id not in current_data:
        return current_data

    behavior = item_object.get('type')
    props = item_object.get('properties', {})
    
    # --- 1. LOGIC VẬT PHẨM CHỨC NĂNG ---
    if behavior == "FUNCTIONAL":
        feature = props.get('feature')
        if 'special_permissions' not in current_data[user_id]:
            current_data[user_id]['special_permissions'] = {}

        if feature == "world_chat":
            if 'world_chat_count' not in current_data[user_id]['special_permissions']:
                current_data[user_id]['special_permissions']['world_chat_count'] = 0
            add_val = int(props.get('power_value', 1))
            current_data[user_id]['special_permissions']['world_chat_count'] += add_val
        
        elif feature == "market_discount":
            current_data[user_id]['special_permissions']['discount_percent'] = int(props.get('power_value', 0))

    # --- 2. LOGIC THUỐC & TRANG BỊ ---
    elif behavior == "BUFF_STAT":
        stat = props.get('target_stat', 'atk').lower()
        val = int(props.get('value', 0))
        dur_type = props.get('duration_type')
        
        if dur_type == "permanent":
            if 'bonus_stats' not in current_data[user_id]:
                current_data[user_id]['bonus_stats'] = {"hp": 0, "atk": 0, "def": 0, "speed": 0}
            if stat not in current_data[user_id]['bonus_stats']:
                current_data[user_id]['bonus_stats'][stat] = 0
            current_data[user_id]['bonus_stats'][stat] += val
            
        elif dur_type == "time_limit":
            minutes = int(props.get('duration_value', 30))
            expire_time = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
            if 'active_buffs' not in current_data[user_id]:
                current_data[user_id]['active_buffs'] = []
            current_data[user_id]['active_buffs'].append({
                "stat": stat, "value": val, "expire_at": expire_time,
                "item_name": item_object.get('id', 'Unknown Item')
            })

    # --- 3. LOGIC TIÊU THỤ TÀI NGUYÊN ---
    elif behavior == "CONSUMABLE":
        raw_target = str(props.get('target_type', 'kpi')).strip()
        val = int(props.get('value', 0))
        key_mapping = {
            "kpi": "kpi", "hp": "hp", "exp": "exp",
            "vinh_du": "Vinh_Du", "chien_tich": "Chien_Tich",
            "tri_thuc": "Tri_Thuc", "vinh_quang": "Vinh_Quang",
            "bonus": "Bonus", "vi_pham": "Vi_Pham"
        }
        real_key = key_mapping.get(raw_target.lower(), raw_target)
        if real_key not in current_data[user_id]:
            current_data[user_id][real_key] = 0
        current_data[user_id][real_key] += val

    # --- 4. LOGIC HỒI SINH BOSS (MỚI) ---
    elif behavior == "BOSS_RESET":
        # Đưa thời gian chờ về quá khứ để xóa trạng thái trọng thương [cite: 5, 6]
        past_time = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        current_data[user_id]['reborn_at'] = past_time
        
        # Đồng bộ Session State để giao diện mở ngay lập tức [cite: 19]
        if 'data' in st.session_state:
            st.session_state.data[user_id]['reborn_at'] = past_time
        st.success("✨ Vật phẩm đã được kích hoạt! Bạn có thể đấu Boss ngay.")

    # Luôn return dữ liệu đã cập nhật ở cuối hàm
    return current_data
def get_active_combat_stats(user_id, current_data):
    """
    Quét danh sách active_buffs, xóa bỏ buff hết hạn và trả về tổng chỉ số cộng thêm.
    """
    user_info = current_data.get(user_id, {})
    active_buffs = user_info.get('active_buffs', [])
    now = datetime.now()
    
    valid_buffs = []
    total_bonus = {"atk": 0, "hp": 0}
    
    # 1. Kiểm tra từng Buff trong danh sách
    for buff in active_buffs:
        expire_at = datetime.strptime(buff['expire_at'], "%Y-%m-%d %H:%M:%S")
        if now < expire_at:
            # Buff còn hạn -> Giữ lại và cộng dồn chỉ số
            valid_buffs.append(buff)
            stat_type = buff['stat'] # 'atk' hoặc 'hp'
            total_bonus[stat_type] += buff['value']
            
    # 2. Cập nhật lại danh sách Buff sạch vào data (Xóa đồ hết hạn)
    current_data[user_id]['active_buffs'] = valid_buffs
    
    # 3. Cộng thêm chỉ số từ Trang bị vĩnh viễn (bonus_stats)
    perma_stats = user_info.get('bonus_stats', {"atk": 0, "hp": 0})
    total_bonus['atk'] += perma_stats.get('atk', 0)
    total_bonus['hp'] += perma_stats.get('hp', 0)
    
    return total_bonus, current_data    