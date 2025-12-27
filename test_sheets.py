import gspread
from google.oauth2.service_account import Credentials

# 1. Cấu hình quyền truy cập
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 2. Kết nối bằng file JSON (Đảm bảo file này nằm cùng thư mục)
creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
client = gspread.authorize(creds)

# 3. Mở file Google Sheets bằng Tên file (Thay 'Data_KPI_Kingdom' bằng tên file của bạn)
try:
    # Bạn hãy thay đúng tên file Google Sheets bạn vừa tạo vào đây nhé
    sheet = client.open("Data_KPI_Kingdom").sheet1 
    
    # 4. Thử ghi một dữ liệu nhỏ vào ô A1
    sheet.update_acell('A1', "KẾT NỐI THÀNH CÔNG!")
    
    print("✅ Chúc mừng! Python đã kết nối và ghi dữ liệu thành công lên Google Sheets.")
    print("Hãy mở file Sheets của bạn lên xem ô A1 nhé!")
except Exception as e:
    print(f"❌ Lỗi rồi: {e}")