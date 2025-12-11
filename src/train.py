import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import recall_score, accuracy_score
import joblib
import holidays  # <--- NUEVA LIBRERÍA
import os

# --- FUNCIONES AUXILIARES ---
def haversine_distance(lat1, lon1, lat2, lon2):
    r = 6371
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    return r * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def eh_feriado(data, calendario):
    """Retorna 1 se for feriado, 0 caso contrário"""
    return 1 if data in calendario else 0

# --- CONFIGURACIÓN ---
print("🚀 Iniciando treinamento V3 (Com Feriados + Distância)...")
current_dir = os.path.dirname(__file__)
data_path = os.path.join(current_dir, '../data/BrFlights2.csv')
model_path = os.path.join(current_dir, 'flight_classifier_mvp.joblib')

# 1. CARGA
try:
    df = pd.read_csv(data_path, encoding='latin1', low_memory=False)
except FileNotFoundError:
    print("❌ Erro: BrFlights2.csv não encontrado.")
    exit()

# 2. LIMPIEZA
df = df[df['Situacao.Voo'] == 'Realizado'].dropna(subset=['Partida.Prevista', 'Partida.Real', 'LatOrig', 'LongDest'])

# 3. FEATURE ENGINEERING
print("⚙️ Criando features (Feriados, Distância, Tempo)...")

# A. Distância
df['distancia_km'] = haversine_distance(df['LatOrig'], df['LongOrig'], df['LatDest'], df['LongDest'])

# B. Datas e Feriados
df['Partida.Prevista'] = pd.to_datetime(df['Partida.Prevista'])
df['Partida.Real'] = pd.to_datetime(df['Partida.Real'])

# Calendário Brasil
br_holidays = holidays.Brazil()
df['is_holiday'] = df['Partida.Prevista'].apply(lambda x: eh_feriado(x, br_holidays))

# Features Temporais
df['hora'] = df['Partida.Prevista'].dt.hour
df['dia_semana'] = df['Partida.Prevista'].dt.dayofweek
df['mes'] = df['Partida.Prevista'].dt.month

# C. Target (> 15 min atraso)
df['delay_minutes'] = (df['Partida.Real'] - df['Partida.Prevista']).dt.total_seconds() / 60
df['target'] = np.where(df['delay_minutes'] > 15, 1, 0)

# Renomear
df = df.rename(columns={'Companhia.Aerea': 'companhia', 'Aeroporto.Origem': 'origem', 'Aeroporto.Destino': 'destino'})

# 4. ENCODING
print("🔠 Codificando variáveis categóricas...")
encoders = {}
for col in ['companhia', 'origem', 'destino']:
    le = LabelEncoder()
    df[col] = df[col].astype(str)
    df[f'{col}_encoded'] = le.fit_transform(df[col])
    encoders[col] = le

# 5. TREINO
# Lista ATUALIZADA de features
features = [
    'companhia_encoded', 'origem_encoded', 'destino_encoded', 
    'distancia_km', 'hora', 'dia_semana', 'mes', 'is_holiday'
]

X = df[features]
y = df['target']

print(f"🧠 Treinando Random Forest (n=100, depth=15) com {len(X)} registros...")
# Usamos class_weight='balanced' para lidar com o desbalanceamento
model = RandomForestClassifier(n_estimators=100, max_depth=15, class_weight='balanced', random_state=42, n_jobs=-1)
model.fit(X, y)

# 6. EXPORTAR ARTEFATOS
print("💾 Salvando modelo e metadados...")
artifact = {
    'model': model,
    'encoders': encoders,
    'features': features,
    'metadata': {
        'version': '3.0',
        'threshold': 0.40,  # O limite otimizado que você descobriu no notebook
        'author': 'Dragos Team'
    }
}
joblib.dump(artifact, model_path)
print(f"✅ Modelo V3 salvo em: {model_path}")