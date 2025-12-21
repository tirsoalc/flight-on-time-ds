import pandas as pd
import numpy as np
import joblib
import holidays
import os
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import recall_score, accuracy_score
from sklearn.base import BaseEstimator, TransformerMixin

# --- 1. DEFINIÇÃO DA CLASSE SAFE ENCODER (ANTI-LEAKAGE) ---
class SafeLabelEncoder(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.classes_ = {}
        self.unknown_token = -1

    def fit(self, y):
        # Garante que as chaves sejam strings desde o fit para robustez total
        unique_labels = pd.Series(y).unique()
        self.classes_ = {str(label): idx for idx, label in enumerate(unique_labels)}
        return self

    def transform(self, y):
        # Mapeia para o índice aprendido ou retorna -1 para novos dados
        return pd.Series(y).apply(lambda x: self.classes_.get(str(x), self.unknown_token))

# --- FUNÇÕES AUXILIARES ---
def haversine_distance(lat1, lon1, lat2, lon2):
    r = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    return np.round(r * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)), 2)

# --- CONFIGURAÇÃO ---
print(" Iniciando Treinamento V4.0 (Weather-Aware)...")
current_dir = os.path.dirname(__file__)

# Caminhos de arquivos
data_path = os.path.join(current_dir, '../data/BrFlights_Enriched_v4.csv') 
model_path = os.path.join(current_dir, 'flight_classifier_v4.joblib')

# 2. CARGA DE DADOS
try:
    df = pd.read_csv(data_path, low_memory=False)
    print(f"✅ Registros carregados: {len(df):,}")
except FileNotFoundError:
    print(f" Erro: Dataset não encontrado em {data_path}")
    exit()

# 3. LIMPEZA E ENGENHARIA DE FEATURES
print("🛠️  Aplicando Pipeline de Saneamento e Clima...")

# A. Distância e Coordenadas
for col in ['LatOrig', 'LongOrig', 'LatDest', 'LongDest']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['distancia_km'] = haversine_distance(df['LatOrig'], df['LongOrig'], df['LatDest'], df['LongDest'])

# B. Tratamento Temporal (Merge já foi feito com Prevista no Notebook 1)
cols_datas = ['Partida.Prevista', 'Partida.Real', 'Chegada.Real']
for col in cols_datas:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# C. Filtragem de Escopo (Apenas Realizados conforme MVP)
if 'Situacao.Voo' in df.columns:
    df_clean = df[df['Situacao.Voo'] == 'Realizado'].copy()
else:
    df_clean = df.copy()

df_clean = df_clean.dropna(subset=cols_datas + ['distancia_km'])

# D. Métricas de Tempo
df_clean['delay_minutes'] = (df_clean['Partida.Real'] - df_clean['Partida.Prevista']).dt.total_seconds() / 60
df_clean['duration_minutes'] = (df_clean['Chegada.Real'] - df_clean['Partida.Real']).dt.total_seconds() / 60

# E. Filtro de Consistência Física (Outliers do MVP)
mask_clean = (df_clean['duration_minutes'] > 0) & \
             (df_clean['delay_minutes'] > -60) & \
             (df_clean['delay_minutes'] < 1440)
df_clean = df_clean[mask_clean].copy()

# F. Definição do Target (> 15 min)
df_clean['target'] = np.where(df_clean['delay_minutes'] > 15, 1, 0)

# G. Variáveis Exógenas (Clima e Calendário)
br_holidays = holidays.Brazil()
df_clean['is_holiday'] = df_clean['Partida.Prevista'].dt.date.apply(lambda x: 1 if x in br_holidays else 0)
df_clean['hora'] = df_clean['Partida.Prevista'].dt.hour
df_clean['dia_semana'] = df_clean['Partida.Prevista'].dt.dayofweek
df_clean['mes'] = df_clean['Partida.Prevista'].dt.month

# H. Garantia de Integridade Climática
for col in ['precipitation', 'wind_speed']:
    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)

if 'clima_imputado' not in df_clean.columns:
    df_clean['clima_imputado'] = 0

# Padronização de nomes
df_clean.rename(columns={'Companhia.Aerea': 'companhia', 'Aeroporto.Origem': 'origem', 'Aeroporto.Destino': 'destino'}, inplace=True)

# 4. PREPARAÇÃO PARA MODELAGEM
print("  Realizando Split Estratificado e Encoding...")

cols_base = ['companhia', 'origem', 'destino', 'distancia_km', 'hora', 'dia_semana', 'mes', 'is_holiday', 'precipitation', 'wind_speed', 'clima_imputado']
X = df_clean[cols_base]
y = df_clean['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Encoding Seguro (Anti-Leakage)
encoders = {}
cat_features = ['companhia', 'origem', 'destino']

for col in cat_features:
    le = SafeLabelEncoder()
    X_train[col] = X_train[col].astype(str)
    X_test[col] = X_test[col].astype(str)
    
    X_train[f'{col}_encoded'] = le.fit(X_train[col]).transform(X_train[col])
    X_test[f'{col}_encoded'] = le.transform(X_test[col])
    encoders[col] = le

features_model = [f'{c}_encoded' if c in cat_features else c for c in cols_base]

# 5. TREINAMENTO E VALIDAÇÃO
print(" Treinando CatBoost Classifier V4 (Balanced)...")
model = CatBoostClassifier(
    iterations=300,
    learning_rate=0.1,
    depth=6,
    auto_class_weights='Balanced', # Vital para combater o desbalanceamento de 11%
    random_seed=42,
    verbose=50,
    allow_writing_files=False
)

model.fit(X_train[features_model], y_train)

# 6. MÉTRICAS DE OPERAÇÃO
THRESHOLD = 0.40 
probs = model.predict_proba(X_test[features_model])[:, 1]
preds = (probs >= THRESHOLD).astype(int)

final_recall = recall_score(y_test, preds)
print("-" * 50)
print(f" PERFORMANCE VALIDADA (Threshold {THRESHOLD}):")
print(f"   -> Recall de Segurança: {final_recall:.2%}")
print("-" * 50)

# 7. EXPORTAÇÃO E RETREINAMENTO FINAL
print(" Gerando Artefato de Produção Final (X_full)...")

# Preparamos o dataset completo para o treinamento final de deploy
X_full = X.copy()
for col in cat_features:
    X_full[col] = X_full[col].astype(str)
    X_full[f'{col}_encoded'] = encoders[col].transform(X_full[col])

model_final = CatBoostClassifier(
    iterations=300, learning_rate=0.1, depth=6,
    auto_class_weights='Balanced', random_seed=42, verbose=False, allow_writing_files=False
)
model_final.fit(X_full[features_model], y)

# Salvamento do pacote completo
artifact = {
    'model': model_final,
    'encoders': encoders,
    'features': features_model,
    'metadata': {
        'versao': '4.0.0-WeatherAware',
        'threshold': THRESHOLD,
        'recall_validado': f"{final_recall:.2%}"
    }
}

joblib.dump(artifact, model_path)
print(f"✅ Sucesso! Modelo exportado para: {model_path}")