from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import json
import pickle
import os
import pandas as pd

router = APIRouter(prefix="/api/predict-disease", tags=["Predict Disease"])

# ==============================
# PATH
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "disease_model.pkl")
LE_PATH = os.path.join(BASE_DIR, "label_encoder.pkl")
SYMPTOM_PATH = os.path.join(BASE_DIR, "symptom_list.json")
DISEASE_MAP_PATH = os.path.join(BASE_DIR, "disease_symptom_map.json")

DATA_DESC = os.path.join(BASE_DIR, "disease_descriptionsAI.csv")

# ==============================
# LOAD FILES
# ==============================

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

with open(LE_PATH, "rb") as f:
    le = pickle.load(f)

with open(SYMPTOM_PATH, "r", encoding="utf-8") as f:
    all_symptoms_list = json.load(f)

with open(DISEASE_MAP_PATH, "r", encoding="utf-8") as f:
    disease_knowledge_base = json.load(f)

desc_df   = pd.read_csv(DATA_DESC)

desc_df['Disease'] = desc_df['Disease'].str.strip()

symptom_to_index = {s: i for i, s in enumerate(all_symptoms_list)}

# ====== Specialist map (tiếng Việt) ======
specialist_map = {
    'Tiểu đường': 'Khoa Nội tiết', 
    'Cường giáp': 'Khoa Nội tiết', 
    'Suy giáp': 'Khoa Nội tiết',
    'Hạ đường huyết': 'Khoa Nội tiết', 
    'Trào ngược dạ dày thực quản (GERD)': 'Khoa Tiêu hóa',
    'Loét dạ dày tá tràng': 'Khoa Tiêu hóa', 
    'Vàng da': 'Khoa Tiêu hóa', 
    'Viêm dạ dày ruột': 'Khoa Tiêu hóa',
    'Hội chứng ruột kích thích': 'Khoa Tiêu hóa', 
    'Trĩ': 'Khoa Hậu môn - Trực tràng',
    'Viêm gan A': 'Khoa Truyền nhiễm', 
    'Viêm gan B': 'Khoa Truyền nhiễm', 
    'Viêm gan C': 'Khoa Truyền nhiễm',
    'Viêm gan D': 'Khoa Truyền nhiễm', 
    'Viêm gan E': 'Khoa Truyền nhiễm', 
    'Sốt xuất huyết': 'Khoa Truyền nhiễm',
    'Sởi': 'Khoa Truyền nhiễm', 
    'Sốt rét': 'Khoa Truyền nhiễm', 
    'Thương hàn': 'Khoa Truyền nhiễm',
    'AIDS': 'Khoa Truyền nhiễm', 
    'Dại': 'Khoa Truyền nhiễm', 
    'Nhiễm nấm': 'Khoa Da liễu',
    'Dị ứng': 'Khoa Dị ứng miễn dịch', 
    'Phản ứng thuốc': 'Khoa Dị ứng miễn dịch', 
    'Mụn trứng cá': 'Khoa Da liễu',
    'Bệnh vẩy nến': 'Khoa Da liễu', 
    'Chốc lở': 'Khoa Da liễu', 
    'Tăng huyết áp': 'Khoa Tim mạch',
    'Nhồi máu cơ tim': 'Khoa Tim mạch', 
    'Suy tĩnh mạch': 'Khoa Tim mạch', 
    'Đau nửa đầu': 'Khoa Thần kinh',
    'Thoái hóa đốt sống cổ': 'Khoa Thần kinh / Cơ xương khớp', 
    'Liệt (xuất huyết não)': 'Khoa Cấp cứu / Thần kinh',
    'Đột quỵ': 'Khoa Cấp cứu / Thần kinh', 
    'Động kinh': 'Khoa Thần kinh',
    'Parkinson': 'Khoa Thần kinh', 
    'Viêm khớp': 'Khoa Cơ xương khớp',
    'Hen phế quản': 'Khoa Hô hấp', 
    'Viêm phổi': 'Khoa Hô hấp', 
    'Lao': 'Khoa Hô hấp'
}


# ==============================
# UTILS
# ==============================

def get_disease_info(disease_name):
    spec = specialist_map.get(disease_name, "Khoa Nội tổng hợp")

    try:
        desc_rows = desc_df[desc_df['Disease'].str.strip() == disease_name.strip()]
        if not desc_rows.empty:
            desc = desc_rows.iloc[0]['Description']
        else:
            desc = "Hiện chưa có mô tả cho bệnh này."
    except:
        desc = "Lỗi mô tả."

    return spec, desc




def get_related_symptoms_from_map(selected_symptoms, top_n=7):
    related = []

    for symptoms in disease_knowledge_base.values():
        if any(sym in symptoms for sym in selected_symptoms):
            related += symptoms

    related = list(set(related) - set(selected_symptoms))
    return related[:top_n]


# ==============================
# CORE AI ENGINE
# ==============================

def hybrid_prediction_engine(selected_symptoms):

    input_vec = np.zeros((1, len(all_symptoms_list)), dtype=int)

    for s in selected_symptoms:
        if s in symptom_to_index:
            input_vec[0, symptom_to_index[s]] = 1

    probs = model.predict_proba(input_vec)[0]
    top_indices = np.argsort(probs)[::-1][:3]

    final_results = []

    for idx in top_indices:
        disease = le.inverse_transform([idx])[0]
        confidence = float(probs[idx] * 100)

        true_symptoms = set(disease_knowledge_base.get(disease, []))

        # ✅ HALLUCINATION FILTER
        #if not set(selected_symptoms).issubset(true_symptoms):
            #continue

        missing = list(true_symptoms - set(selected_symptoms))

        spec, desc = get_disease_info(disease)

        final_results.append({
            "Disease": disease,
            "Confidence": round(confidence, 2),
            "Specialist": spec,
            "Description": desc,
            "Missing": missing[:7]
        })

    return final_results


# ==============================
# REQUEST MODEL
# ==============================

class SymptomsRequest(BaseModel):
    symptoms: list[str]


# ==============================
# ROUTES (KHỚP FE)
# ==============================

@router.get("/") 
def root(): 
    return {"status": "Disease AI running"}

@router.post("/predict")
def predict_disease(data: SymptomsRequest):

    if not data.symptoms:
        raise HTTPException(status_code=400, detail="No symptoms provided")

    user_symptoms = [s.strip() for s in data.symptoms]

    results = hybrid_prediction_engine(user_symptoms)

    return {
        "results": results,
        "related": get_related_symptoms_from_map(user_symptoms)
    }


@router.post("/related")
def get_related(data: dict):
    input_symptoms = set([s.strip().lower() for s in data["symptoms"]])

    possible_diseases = [
        d for d, s in disease_knowledge_base.items()
        if input_symptoms.issubset(set(s))
    ]

    valid_next_symptoms = set()
    for d in possible_diseases:
        valid_next_symptoms.update(disease_knowledge_base[d])

    suggestions = sorted(list(valid_next_symptoms - input_symptoms))

    return {
        "count": len(suggestions),
        "related": suggestions
    }


@router.get("/all")
def get_all_symptoms():
    return {
        "related": sorted(all_symptoms_list)
    }
