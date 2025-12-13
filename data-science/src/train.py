import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split # Opcional, para validar
from sklearn.metrics import recall_score, accuracy_score
import joblib
import holidays
import os

# --- IMPORTANTE: EL NUEVO MOTOR ---
from catboost import CatBoostClassifier

# --- FUNCIONES AUXILIARES ---
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcula distância em KM entre coordenadas"""
    r = 6371
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    return r * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- CONFIGURACIÓN ---
print("🚀 Iniciando treinamento V3.0-CAT (CatBoost + Limpeza Avançada)...")
current_dir = os.path.dirname(__file__)
# Ajusta este path se seu CSV estiver em outro lugar
data_path = os.path.join(current_dir, '../data/BrFlights2.csv') 
model_path = os.path.join(current_dir, 'flight_classifier_mvp.joblib')

# 1. CARGA
try:
    df = pd.read_csv(data_path, encoding='latin1', low_memory=False)
except FileNotFoundError:
    print(f"❌ Erro: Arquivo não encontrado em {data_path}")
    exit()

# 2. LIMPEZA INICIAL E FILTROS
print(f"📊 Registros iniciais: {len(df)}")
df.drop_duplicates(inplace=True)

# Garantir colunas numéricas de coordenadas
cols_coords = ['LatOrig', 'LongOrig', 'LatDest', 'LongDest']
for col in cols_coords:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df = df[df['Situacao.Voo'] == 'Realizado'].dropna(subset=['Partida.Prevista', 'Partida.Real', 'Chegada.Real'] + cols_coords)

# 3. FEATURE ENGINEERING
print("⚙️ Criando features e aplicando regras de negócio...")

# A. Distância (Re-calculando para garantir precisão)
df['distancia_km'] = haversine_distance(df['LatOrig'], df['LongOrig'], df['LatDest'], df['LongDest'])

# B. Datas e Tempos
cols_datas = ['Partida.Prevista', 'Partida.Real', 'Chegada.Real']
for col in cols_datas:
    df[col] = pd.to_datetime(df[col], errors='coerce')
df = df.dropna(subset=cols_datas)

# C. Cálculo de Atraso e Duração
df['delay_minutes'] = (df['Partida.Real'] - df['Partida.Prevista']).dt.total_seconds() / 60
df['duration_minutes'] = (df['Chegada.Real'] - df['Partida.Real']).dt.total_seconds() / 60

# D. Remoção de Outliers (Sua lógica avançada mantida ✅)
mask_clean = (df['duration_minutes'] > 0) & (df['delay_minutes'] > -60) & (df['delay_minutes'] < 1440)
df = df[mask_clean].copy()
print(f"✅ Registros limpos para treino: {len(df)}")

# E. Feriados (LÓGICA OTIMIZADA .dt.date)
print("📅 Calculando feriados...")
br_holidays = holidays.Brazil()
# Usamos .dt.date para bater exatamente com a lógica do App.py
df['data_voo'] = df['Partida.Prevista'].dt.date
df['is_holiday'] = df['data_voo'].apply(lambda x: 1 if x in br_holidays else 0)

# F. Outras Features Temporais
df['hora'] = df['Partida.Prevista'].dt.hour
df['dia_semana'] = df['Partida.Prevista'].dt.dayofweek
df['mes'] = df['Partida.Prevista'].dt.month

# G. Target (> 15 min atraso)
df['target'] = np.where(df['delay_minutes'] > 15, 1, 0)

# Renomear colunas para bater com o App.py
df = df.rename(columns={'Companhia.Aerea': 'companhia', 'Aeroporto.Origem': 'origem', 'Aeroporto.Destino': 'destino'})

# 4. ENCODING
print("🔠 Codificando variáveis categóricas...")
encoders = {}
for col in ['companhia', 'origem', 'destino']:
    le = LabelEncoder()
    df[col] = df[col].astype(str)
    df[f'{col}_encoded'] = le.fit_transform(df[col])
    encoders[col] = le

# 5. PREPARAÇÃO DO TREINO
features_finais = [
    'companhia_encoded', 'origem_encoded', 'destino_encoded', 
    'distancia_km', 'hora', 'dia_semana', 'mes', 'is_holiday'
]

X = df[features_finais]
y = df['target']

# Split opcional para ver métricas no terminal antes de salvar
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"🐱 Treinando CatBoost Classifier (O Campeão)...")
# Parâmetros vencedores do Notebook
model = CatBoostClassifier(
    iterations=100,
    learning_rate=0.1,
    depth=6,
    auto_class_weights='Balanced', # A mágica para o desbalanceamento
    random_seed=42,
    verbose=False,
    allow_writing_files=False
)

model.fit(X_train, y_train)

# Validação rápida
probs = model.predict_proba(X_val)[:, 1]
preds = (probs >= 0.40).astype(int) # Threshold 0.40
recall = recall_score(y_val, preds)
acc = accuracy_score(y_val, preds)

print(f"📊 Validação Interna -> Recall: {recall:.1%} | Acurácia: {acc:.1%}")
print("   (Treinando modelo final com todos os dados...)")

# Treino Final com TUDO para Produção
model_final = CatBoostClassifier(
    iterations=100, learning_rate=0.1, depth=6,
    auto_class_weights='Balanced', random_seed=42, verbose=False, allow_writing_files=False
)
model_final.fit(X, y)

# 6. EXPORTAR ARTEFATOS
print("💾 Salvando artefatos de produção...")
artifact = {
    'model': model_final,
    'encoders': encoders,
    'features': features_finais,
    'metadata': {
        'autor': 'Time Data Science',
        'versao': '3.0.0-CAT',
        'tecnologia': 'CatBoost',
        'threshold_recomendado': 0.40, # Vital para o App.py
        'recall_atrasos': recall 
    }
}

joblib.dump(artifact, model_path)
print(f"✅ Arquivo gerado com sucesso: {model_path}")
print("🚀 Pode subir o servidor!")