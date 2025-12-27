import json
import os

FILE_PATH = "data.json"

def fix_now():
    print(f"🔄 Đang kiểm tra file {FILE_PATH}...")
    
    if not os.path.exists(FILE_PATH):
        print("❌ Không tìm thấy file data.json! Bạn không cần sửa gì cả.")
        return

    try:
        # 1. Đọc dữ liệu lên
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 Loại dữ liệu hiện tại: {type(data)}")

        # 2. Kiểm tra xem có phải là List (Thủ phạm) không
        if isinstance(data, list):
            print("⚠️ PHÁT HIỆN LỖI: Dữ liệu đang là LIST -> Tiến hành chuyển đổi sang DICT...")
            
            fixed_dict = {}
            count = 0
            
            for item in data:
                if isinstance(item, dict):
                    # Cố gắng tìm ID/Username để làm Key
                    key = item.get('username') or item.get('u_id') or item.get('id') or item.get('name')
                    
                    # Nếu là Admin thì key cố định
                    if item.get('role') == 'admin':
                        key = 'admin'
                    
                    if key:
                        # Làm sạch key
                        str_key = str(key).strip().lower().replace(" ", "")
                        fixed_dict[str_key] = item
                        count += 1
            
            # 3. Ghi đè lại file với cấu trúc đúng
            with open(FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(fixed_dict, f, ensure_ascii=False, indent=4)
                
            print(f"✅ ĐÃ SỬA THÀNH CÔNG! Đã khôi phục {count} tài khoản.")
            print("👉 Bây giờ file data.json đã là Dictionary chuẩn.")
            
        elif isinstance(data, dict):
            print("✅ File data.json của bạn ĐÃ LÀ DICTIONARY (Chuẩn). Không cần sửa.")
        else:
            print("❓ Dữ liệu lạ, không phải List cũng không phải Dict.")

    except Exception as e:
        print(f"❌ Có lỗi khi đọc/ghi file: {e}")

if __name__ == "__main__":
    fix_now()