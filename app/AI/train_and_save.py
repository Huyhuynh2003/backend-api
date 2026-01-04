import pandas as pd
import numpy as np
import random
import pickle
import json
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# ================== CẤU HÌNH ĐƯỜNG DẪN ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_SYM = os.path.join(BASE_DIR, "disease_dataAI2.csv")
DATA_DOC = os.path.join(BASE_DIR, "Doctor_Versus_Disease.csv")
DATA_DESC = os.path.join(BASE_DIR, "disease_descriptionsAI.csv")

MODEL_PATH = os.path.join(BASE_DIR, "disease_model.pkl")
LE_PATH = os.path.join(BASE_DIR, "label_encoder.pkl")
SYMPTOM_PATH = os.path.join(BASE_DIR, "symptom_list.json")
DISEASE_MAP_PATH = os.path.join(BASE_DIR, "disease_symptom_map.json")

# ================== LOAD DATASET ==================
print("🚀 Loading data...")

df_sym = pd.read_csv(DATA_SYM)
df_doc = pd.read_csv(DATA_DOC, encoding='latin1', names=['Disease','Specialist'])
df_desc = pd.read_csv(DATA_DESC)

def clean_text(df):
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    return df

df_sym = clean_text(df_sym)
df_desc = clean_text(df_desc)

# ================== BUILD KNOWLEDGE GRAPH ==================
print("🧠 Building knowledge graph...")

symptom_cols = [col for col in df_sym.columns if 'symptom' in col.lower()]

disease_knowledge_base = {}
all_unique_symptoms = set()

for _, row in df_sym.iterrows():
    symptoms = set([str(row[col]) for col in symptom_cols if pd.notna(row[col])])
    disease_knowledge_base[row['Disease']] = list(symptoms)
    all_unique_symptoms.update(symptoms)

all_symptoms_list = sorted(list(all_unique_symptoms))
symptom_to_index = {sym: i for i, sym in enumerate(all_symptoms_list)}

print(f"✅ Total diseases: {len(disease_knowledge_base)}")
print(f"✅ Total symptoms: {len(all_symptoms_list)}")

# ================== DATA AUGMENTATION (SMART) ==================
print("🔄 Generating training data (Smart Augmentation)...")

X_data = []
y_data = []

for disease, true_syms in disease_knowledge_base.items():
    n_syms = len(true_syms)

    for _ in range(80):  # 80 samples/disease (tối ưu hiệu năng)
        vector = np.zeros(len(all_symptoms_list), dtype=int)

        k = random.randint(1, max(1, n_syms))
        sample_syms = random.sample(true_syms, k)

        for s in sample_syms:
            if s in symptom_to_index:
                vector[symptom_to_index[s]] = 1

        X_data.append(vector)
        y_data.append(disease)

X = np.array(X_data)
y = np.array(y_data)

# ================== LABEL ENCODE ==================
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# ================== TRAIN RANDOM FOREST ==================
print("🌲 Training Random Forest model...")

model = RandomForestClassifier(
    n_estimators=150,
    random_state=42,
    n_jobs=-1
)

model.fit(X, y_encoded)

print("✅ Model training completed!")

# ================== SAVE FILES ==================
print("💾 Saving model & data...")

with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

with open(LE_PATH, "wb") as f:
    pickle.dump(le, f)

with open(SYMPTOM_PATH, "w", encoding="utf-8") as f:
    json.dump(all_symptoms_list, f, ensure_ascii=False, indent=2)

with open(DISEASE_MAP_PATH, "w", encoding="utf-8") as f:
    json.dump(disease_knowledge_base, f, ensure_ascii=False, indent=2)

print("✅ ALL DONE! SYSTEM IS READY FOR PRODUCTION 🚀")
