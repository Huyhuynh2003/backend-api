# backend/app/AI/generate_symptoms.py
import pandas as pd
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "disease_dataAI2.csv")
json_path = os.path.join(BASE_DIR, "symptom_list.json")

df = pd.read_csv(csv_path)
# Giả sử các cột triệu chứng bắt đầu từ cột thứ 1
symptoms = set()
for col in df.columns[1:]:
    symptoms.update(df[col].dropna().str.strip().str.lower().tolist())

symptoms = sorted(list(symptoms))

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(symptoms, f, ensure_ascii=False, indent=2)

print(f"Đã tạo {len(symptoms)} triệu chứng vào {json_path}")
