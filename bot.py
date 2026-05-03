# Tối ưu hóa hàm xác định Dụng Thần với logic phản biện (Counter-logic)
def xac_dinh_dung_than_pro(ls):
    diem_tuong_tro, diem_that_tho, chi_tiet_hanh = dinh_luong_nang_luong(ls)
    nc_hanh = NGU_HANH[ls["nhat_chu"]]
    
    # 1. Kiểm tra Cách cục Đặc biệt (Tòng Cách)
    # Nếu năng lượng hỗ trợ quá yếu (< 15% tổng) -> Tòng
    if diem_tuong_tro <= 1.65: # 1.65 = 15% của 11.0
        target_hanh = max(chi_tiet_hanh, key=chi_tiet_hanh.get)
        return [target_hanh], f"Tòng {target_hanh} (Cực nhược)"

    # 2. Kiểm tra Thân Vượng/Nhược thông thường
    # Thăng cấp logic: Không chỉ nhìn điểm, mà nhìn vào sự cân bằng (Balance)
    if diem_tuong_tro > 5.5:
        # Thân vượng: Cần Khắc (Quan), Tiết (Thực/Thương), hoặc Hao (Tài)
        # Ưu tiên hành có điểm thấp nhất để điều hòa
        possible_dung = [h for h, d in chi_tiet_hanh.items() if h not in [nc_hanh, next(k for k, v in TUONG_SINH.items() if v == nc_hanh)]]
        return sorted(possible_dung, key=lambda x: chi_tiet_hanh[x]), "Vượng"
    else:
        # Thân nhược: Cần Sinh (Ấn) hoặc Trợ (Tỷ/Kiếp)
        tro = nc_hanh
        sinh = next(k for k, v in TUONG_SINH.items() if v == nc_hanh)
        return [sinh, tro], "Nhược"
