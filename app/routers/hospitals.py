from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import time
from requests.exceptions import RequestException
from app import models
from app.database import get_db

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals"])

# =========================================================
# 🗺️ Danh sách 34 tỉnh/thành sau sáp nhập
# =========================================================
provinces = [
    "TP Hà Nội", "TP Huế", "Quảng Ninh", "Cao Bằng", "Lạng Sơn", "Lai Châu", "Điện Biên", "Sơn La",
    "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Tuyên Quang", "Lào Cai", "Thái Nguyên", "Phú Thọ", "Bắc Ninh",
    "Hưng Yên", "TP Hải Phòng", "Ninh Bình", "Quảng Trị", "TP Đà Nẵng", "Quảng Ngãi", "Gia Lai",
    "Khánh Hòa", "Lâm Đồng", "Đắk Lắk", "TPHCM", "Đồng Nai", "Tây Ninh", "TP Cần Thơ",
    "Vĩnh Long", "Đồng Tháp", "Cà Mau", "An Giang"
]

# =========================================================
# 🌐 Biến thể tên để tìm dữ liệu OSM chính xác hơn
# =========================================================
provinces_variants = {
    "TP Hà Nội": ["Hà Nội", "Ha Noi"],
    "TP Huế": ["Huế", "Thừa Thiên Huế", "Hue", "Thua Thien Hue"],
    "Quảng Ninh": ["Quảng Ninh", "Quang Ninh"],
    "Cao Bằng": ["Cao Bằng", "Cao Bang"],
    "Lạng Sơn": ["Lạng Sơn", "Lang Son"],
    "Lai Châu": ["Lai Châu", "Lai Chau"],
    "Điện Biên": ["Điện Biên", "Dien Bien"],
    "Sơn La": ["Sơn La", "Son La"],
    "Thanh Hóa": ["Thanh Hóa", "Thanh Hoa"],
    "Nghệ An": ["Nghệ An", "Nghe An"],
    "Hà Tĩnh": ["Hà Tĩnh", "Ha Tinh"],
    "Tuyên Quang": ["Tuyên Quang", "Hà Giang", "Ha Giang", "Tuyen Quang"],
    "Lào Cai": ["Lào Cai", "Yên Bái", "Lao Cai", "Yen Bai"],
    "Thái Nguyên": ["Thái Nguyên", "Bắc Kạn", "Thai Nguyen", "Bac Kan"],
    "Phú Thọ": ["Phú Thọ", "Hòa Bình", "Vĩnh Phúc", "Phu Tho", "Hoa Binh", "Vinh Phuc"],
    "Bắc Ninh": ["Bắc Ninh", "Bắc Giang", "Bac Ninh", "Bac Giang"],
    "Hưng Yên": ["Hưng Yên", "Thái Bình", "Hung Yen", "Thai Binh"],
    "TP Hải Phòng": ["Hải Phòng", "Hải Dương", "Hai Phong", "Hai Duong"],
    "Ninh Bình": ["Ninh Bình", "Hà Nam", "Nam Định", "Ninh Binh", "Ha Nam", "Nam Dinh"],
    "Quảng Trị": ["Quảng Trị", "Quảng Bình", "Quang Tri", "Quang Binh"],
    "TP Đà Nẵng": ["Đà Nẵng", "Quảng Nam", "Da Nang", "Quang Nam"],
    "Quảng Ngãi": ["Quảng Ngãi", "Kon Tum", "Quang Ngai", "Kon Tum"],
    "Gia Lai": ["Gia Lai", "Bình Định", "Gia Lai", "Binh Dinh"],
    "Khánh Hòa": ["Khánh Hòa", "Ninh Thuận", "Khanh Hoa", "Ninh Thuan"],
    "Lâm Đồng": ["Lâm Đồng", "Đắk Nông", "Bình Thuận", "Lam Dong", "Dak Nong", "Binh Thuan"],
    "Đắk Lắk": ["Đắk Lắk", "Phú Yên", "Dak Lak", "Phu Yen"],
    "TPHCM": ["TP Hồ Chí Minh", "Thành phố Hồ Chí Minh", "Ho Chi Minh City", "Bình Dương", "Bà Rịa - Vũng Tàu", "Ba Ria - Vung Tau", "Binh Duong"],
    "Đồng Nai": ["Đồng Nai", "Bình Phước", "Dong Nai", "Binh Phuoc"],
    "Tây Ninh": ["Tây Ninh", "Long An", "Tay Ninh", "Long An"],
    "TP Cần Thơ": ["Cần Thơ", "Hậu Giang", "Sóc Trăng", "Can Tho", "Hau Giang", "Soc Trang"],
    "Vĩnh Long": ["Vĩnh Long", "Bến Tre", "Trà Vinh", "Vinh Long", "Ben Tre", "Tra Vinh"],
    "Đồng Tháp": ["Đồng Tháp", "Tiền Giang", "Dong Thap", "Tien Giang"],
    "Cà Mau": ["Cà Mau", "Bạc Liêu", "Ca Mau", "Bac Lieu"],
    "An Giang": ["An Giang", "Kiên Giang", "An Giang", "Kien Giang"],
}

# =========================================================
# 🔗 Các server Overpass API dự phòng
# =========================================================
# 🔗 Các server Overpass API nhanh và ổn định hơn
overpass_urls = [
    "https://z.overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

# =========================================================
# 🧩 Hàm đồng bộ 1 tỉnh — tối ưu tốc độ & retry
# =========================================================
def sync_one_province(province: str, db: Session, max_retries: int = 2):
    variants = provinces_variants.get(province, [province])
    total_added = 0
    print(f"\n🛰️ Bắt đầu đồng bộ {province}...")

    for variant in variants:
        for overpass_url in overpass_urls:
            for attempt in range(1, max_retries + 1):
                try:
                    query = f"""
                    [out:json][timeout:25];
                    (
                        node["amenity"="hospital"]["addr:country"="VN"]["addr:city"~"{variant}", i];
                        way["amenity"="hospital"]["addr:city"~"{variant}", i];
                        relation["amenity"="hospital"]["addr:city"~"{variant}", i];
                    );
                    out center;
                    """
                    resp = requests.get(overpass_url, params={"data": query}, timeout=30)
                    if resp.status_code != 200:
                        raise RequestException(f"HTTP {resp.status_code}")

                    data = resp.json()
                    elements = data.get("elements", [])
                    if not elements:
                        print(f"⚠️ Không có dữ liệu cho {province} ({variant}) tại {overpass_url}")
                        continue

                    hospitals_to_add = []
                    for el in elements:
                        tags = el.get("tags", {})
                        name = tags.get("name")
                        if not name:
                            continue

                        lat = el.get("lat") or el.get("center", {}).get("lat")
                        lon = el.get("lon") or el.get("center", {}).get("lon")
                        if not lat or not lon:
                            continue

                        exists = db.query(models.Hospital).filter(
                            models.Hospital.name == name,
                            models.Hospital.city == province
                        ).first()
                        if exists:
                            continue

                        hospitals_to_add.append(models.Hospital(
                            name=name,
                            address=tags.get("addr:full") or tags.get("addr:street") or "Không rõ địa chỉ",
                            city=province,
                            phone=tags.get("phone") or tags.get("contact:phone") or "",
                            email=tags.get("email") or tags.get("contact:email") or "",
                            specialties=tags.get("healthcare:speciality") or "",
                            latitude=lat,
                            longitude=lon
                        ))

                    if hospitals_to_add:
                        db.add_all(hospitals_to_add)
                        db.commit()
                        total_added = len(hospitals_to_add)
                        print(f"✅ {province}: +{total_added} bệnh viện ({variant}) từ {overpass_url}")
                        return province, total_added

                except Exception as e:
                    print(f"❌ Lỗi {province} ({variant}) tại {overpass_url}: {e}")
                    time.sleep(2 ** attempt)

    print(f"🚫 Không thể lấy dữ liệu cho {province}")
    return province, total_added


# =========================================================
# 🌏 Endpoint: Đồng bộ toàn bộ 34 tỉnh (song song 10 tỉnh)
# =========================================================
@router.get("/osm/all")
def sync_all_vietnam_hospitals(db: Session = Depends(get_db)):
    results = []
    total_added = 0
    print("🚀 Bắt đầu đồng bộ toàn quốc...\n")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(sync_one_province, p, db): p for p in provinces}
        for future in as_completed(futures):
            province, added = future.result()
            results.append({"province": province, "added": added})
            total_added += added

    print(f"\n🎉 Hoàn tất! Tổng cộng thêm mới {total_added} bệnh viện.")
    return {"message": "Đồng bộ toàn quốc hoàn tất", "total_added": total_added, "details": results}


# -------------------------------
# 🚶 Endpoint: Đồng bộ tuần tự (34 tỉnh)
# -------------------------------
@router.get("/osm/sequence")
def sync_all_vietnam_sequentially(db: Session = Depends(get_db)):
    """
    Chạy đồng bộ tuần tự từng tỉnh — tránh timeout hoặc lỗi mạng
    """
    results = []
    total_added = 0
    print("🚀 Bắt đầu đồng bộ tuần tự toàn quốc...\n")

    for province in provinces:
        print(f"\n==============================")
        print(f"📍 Đang xử lý: {province}")
        print(f"==============================")

        province_name, added = sync_one_province(province, db)
        results.append({"province": province_name, "added": added})
        total_added += added

        # Nghỉ 1s giữa các tỉnh để tránh bị chặn IP (Overpass có giới hạn request)
        time.sleep(1)

    print(f"\n🎯 Hoàn tất đồng bộ toàn quốc tuần tự — Tổng cộng thêm {total_added} bệnh viện.")
    return {
        "message": "Đồng bộ tuần tự toàn quốc hoàn tất",
        "total_added": total_added,
        "details": results
    }


# =========================================================
# 🧭 Endpoint: Đồng bộ 1 tỉnh riêng lẻ
# =========================================================
@router.get("/osm/{province}")
def sync_one(province: str, db: Session = Depends(get_db)):
    province = province.strip()
    if province not in provinces:
        return {"error": f"Tỉnh/thành '{province}' không tồn tại trong danh sách chuẩn."}

    _, added = sync_one_province(province, db)
    return {"message": f"Đã đồng bộ {province}", "added": added}

# =========================================================
# 🏥 Endpoint: Lấy toàn bộ bệnh viện từ DB
# =========================================================
@router.get("/")
def get_all_hospitals(db: Session = Depends(get_db)):
    hospitals = db.query(models.Hospital).all()
    return hospitals


# =========================================================
# ❌ Xóa 1 bệnh viện theo ID
# =========================================================
@router.delete("/{hospital_id}")
def delete_hospital(hospital_id: int, db: Session = Depends(get_db)):
    hospital = db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first()
    if not hospital:
        return {"error": f"Bệnh viện có ID {hospital_id} không tồn tại."}

    db.delete(hospital)
    db.commit()
    return {"message": f"Đã xóa bệnh viện ID {hospital_id} thành công."}

# =========================================================
# 🧾 Schema nhập liệu khi tạo bệnh viện
# =========================================================
class HospitalCreate(BaseModel):
    name: str
    address: str = "Không rõ địa chỉ"
    city: str
    phone: str = ""
    email: str = ""
    specialties: str = ""
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None

# =========================================================
# ➕ Tạo mới bệnh viện thủ công
# =========================================================
@router.post("/")
def create_hospital(hospital: HospitalCreate, db: Session = Depends(get_db)):
    # Kiểm tra trùng tên + tỉnh
    exists = db.query(models.Hospital).filter(
        models.Hospital.name == hospital.name,
        models.Hospital.city == hospital.city
    ).first()

    if exists:
        raise HTTPException(status_code=400, detail="Bệnh viện đã tồn tại trong tỉnh này.")

    new_hospital = models.Hospital(
        name=hospital.name,
        address=hospital.address,
        city=hospital.city,
        phone=hospital.phone,
        email=hospital.email,
        specialties=hospital.specialties,
        latitude=hospital.latitude,
        longitude=hospital.longitude
    )

    db.add(new_hospital)
    db.commit()
    db.refresh(new_hospital)

    return {"message": "Tạo mới bệnh viện thành công.", "data": new_hospital}

# =========================================================
# 📊 Endpoint: Đếm tổng số bệnh viện
# =========================================================
@router.get("/count")
def get_hospital_count(db: Session = Depends(get_db)):
    """
    Đếm tổng số bệnh viện trong cơ sở dữ liệu
    """
    count = db.query(models.Hospital).count()
    return {"total_hospitals": count}
