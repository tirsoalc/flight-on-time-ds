import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# --- FUNCIONES AUXILIARES ---
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcula distancia entre coordenadas (km)"""
    r = 6371
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    return r * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- CONFIGURACIÓN ---
print("🚀 Iniciando entrenamiento V2 (Con Distancia)...")
current_dir = os.path.dirname(__file__)
data_path = os.path.join(current_dir, '../data/BrFlights2.csv')
model_path = os.path.join(current_dir, 'flight_classifier_mvp.joblib') # Nombre actualizado

# 1. CARGA
try:
    df = pd.read_csv(data_path, encoding='latin1', low_memory=False)
except FileNotFoundError:
    print("❌ Error: BrFlights2.csv no encontrado en data/")
    exit()

# 2. LIMPIEZA Y FILTROS
df = df[df['Situacao.Voo'] == 'Realizado'].dropna(subset=['Partida.Prevista', 'Partida.Real', 'LatOrig', 'LongDest'])

# 3. FEATURE ENGINEERING
print("⚙️ Calculando distancias y fechas...")
# Distancia
df['distancia_km'] = haversine_distance(
    df['LatOrig'], df['LongOrig'],
    df['LatDest'], df['LongDest']
)

# Fechas
df['Partida.Prevista'] = pd.to_datetime(df['Partida.Prevista'])
df['Partida.Real'] = pd.to_datetime(df['Partida.Real'])
df['hora'] = df['Partida.Prevista'].dt.hour
df['dia_semana'] = df['Partida.Prevista'].dt.dayofweek
df['mes'] = df['Partida.Prevista'].dt.month

# Target
df['delay_minutes'] = (df['Partida.Real'] - df['Partida.Prevista']).dt.total_seconds() / 60
df['target'] = np.where(df['delay_minutes'] > 15, 1, 0)

# Renombrar
df = df.rename(columns={
    'Companhia.Aerea': 'companhia',
    'Aeroporto.Origem': 'origem',
    'Aeroporto.Destino': 'destino'
})

# 4. ENCODING
print("🔠 Codificando...")
encoders = {}
for col in ['companhia', 'origem', 'destino']:
    le = LabelEncoder()
    df[col] = df[col].astype(str)
    df[f'{col}_encoded'] = le.fit_transform(df[col])
    encoders[col] = le

# 5. ENTRENAMIENTO
features = ['companhia_encoded', 'origem_encoded', 'destino_encoded', 'distancia_km', 'hora', 'dia_semana', 'mes']
X = df[features]
y = df['target']

print(f"🧠 Entrenando Random Forest con {len(X)} vuelos...")
model = RandomForestClassifier(n_estimators=100, max_depth=15, class_weight='balanced', random_state=42, n_jobs=-1)
model.fit(X, y)

# 6. GUARDAR
print("💾 Guardando modelo...")
artifact = {
    'model': model,
    'encoders': encoders,
    'features': features
}
joblib.dump(artifact, model_path)
print(f"✅ ¡Modelo V2 guardado en {model_path}!")