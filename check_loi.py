import sys
import traceback

print("🔍 Đang kiểm tra file admin_module.py ...")

try:
    import admin_module
    print("✅ File NGON! Không có lỗi cú pháp.")
except SyntaxError as e:
    print("\n❌ PHÁT HIỆN LỖI CÚ PHÁP (SYNTAX ERROR)!")
    print(f"📂 File: {e.filename}")
    print(f"🔢 Dòng số: {e.lineno}")
    print(f"📍 Tại vị trí: {e.offset}")
    print(f"📝 Nội dung dòng lỗi: {e.text}")
    print(f"⚠️ Chi tiết: {e.msg}")
except Exception as e:
    print("\n⚠️ Có lỗi khác xảy ra:")
    print(traceback.format_exc())