import joblib
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import holidays
import catboost
from sklearn.base import BaseEstimator, TransformerMixin

# --- 1. DEFINIÇÃO DA CLASSE SAFE ENCODER (DEVE SER IDÊNTICA AO TREINO) ---
class SafeLabelEncoder(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.classes_ = {}
        self.unknown_token = -1

    def fit(self, y):
        unique_labels = pd.Series(y).unique()
        self.classes_ = {str(label): idx for idx, label in enumerate(unique_labels)}
        return self

    def transform(self, y):
        return pd.Series(y).apply(lambda x: self.classes_.get(str(x), self.unknown_token))

app = FastAPI(title="FlightOnTime AI Service (V4 - Weather Aware)")

# --- 2. CARGA DE ARTEFATOS ---
MODEL_FILENAME = "flight_classifier_v4.joblib"
current_dir = os.path.dirname(__file__)
model_path = os.path.join(current_dir, MODEL_FILENAME)

artifacts = None
br_holidays = holidays.Brazil()

try:
    print(f"📦 Carregando artefatos de produção: {model_path}")
    artifacts = joblib.load(model_path)
    
    model = artifacts['model']
    encoders = artifacts['encoders']
    expected_features = artifacts['features']
    metadata = artifacts.get('metadata', {})
    
    # Recupera o threshold de segurança (0.40)
    THRESHOLD = metadata.get('threshold', 0.40)
    
    print(f"✅ Modelo V4 Carregado com Sucesso!")
    print(f"   -> Versão: {metadata.get('versao')}")
    print(f"   -> Recall Validado: {metadata.get('recall_validado')}")
    print(f"   -> Threshold Operacional: {THRESHOLD}")

except Exception as e:
    print(f"❌ ERRO CRÍTICO ao carregar artefatos: {e}")
    model = None

# --- 3. MODELO DE DADOS (INPUT) ---
class FlightInput(BaseModel):
    companhia: str
    origem: str
    destino: str
    data_partida: str  
    distancia_km: float
    precipitation: float = 0.0
    wind_speed: float = 5.0

# --- 4. ENDPOINT DE PREDIÇÃO ---
@app.post("/predict")
def predict_flight(flight: FlightInput):
    if not model:
        raise HTTPException(status_code=500, detail="Modelo não disponível no servidor.")

    try:
        # A. Processamento de Data e Calendário
        dt = pd.to_datetime(flight.data_partida)
        is_holiday = 1 if dt.date() in br_holidays else 0

        # B. Engenharia de Features em Tempo Real
        input_dict = {
            'companhia': [str(flight.companhia)],
            'origem': [str(flight.origem)],
            'destino': [str(flight.destino)],
            'distancia_km': [float(flight.distancia_km)],
            'hora': [dt.hour],
            'dia_semana': [dt.dayofweek],
            'mes': [dt.month],
            'is_holiday': [is_holiday],
            'precipitation': [float(flight.precipitation)],
            'wind_speed': [float(flight.wind_speed)],
            'clima_imputado': [0]  
        }
        df_input = pd.DataFrame(input_dict)

        # C. Transformação Categórica (Encoding Seguro)
        for col in ['companhia', 'origem', 'destino']:
            if col in encoders:
                df_input[f'{col}_encoded'] = encoders[col].transform(df_input[col])
            else:
                df_input[f'{col}_encoded'] = -1

        # D. Alinhamento de Features (Ordem exata do CatBoost)
        X_final = df_input[expected_features]
        
        # E. Predição de Probabilidade
        prob = float(model.predict_proba(X_final)[0][1])
        
        # F. Lógica de Semáforo de Risco (Regra de Negócio 40/70)
        if prob < THRESHOLD:
            status = "🟢 PONTUAL"
            risco = "BAIXO"
            cor = "VERDE"
            msg = "Voo com alta probabilidade de pontualidade."
        elif THRESHOLD <= prob < 0.70:
            status = "🟡 ALERTA"
            risco = "MÉDIO"
            cor = "AMARELO"
            msg = f"Risco moderado de atraso ({prob:.1%}). Monitore o status do portão."
        else: 
            status = "🔴 ATRASADO"
            risco = "ALTO"
            cor = "VERMELHO"
            msg = f"Alta probabilidade de atraso ({prob:.1%}). Condições operacionais/climáticas adversas."

        return {
            "id_voo": f"{flight.companhia}-{dt.strftime('%H%M')}",
            "previsao_final": status,
            "probabilidade_atraso": round(prob, 4),
            "classificacao_risco": {
                "nivel": risco,
                "cor": cor
            },
            "insight": msg,
            "metadados_modelo": {
                "versao": metadata.get('versao'),
                "threshold_aplicado": THRESHOLD,
                "clima_detectado": {
                    "chuva": flight.precipitation,
                    "vento": flight.wind_speed
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)