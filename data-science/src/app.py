import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import holidays
import catboost # <--- 1. CRÍTICO: Necessário para carregar o modelo

app = FastAPI(title="FlightOnTime AI Service (V3 - CatBoost)")

# --- 1. CARGA DE ARTEFATOS ---
MODEL_FILENAME = "flight_classifier_mvp.joblib"
current_dir = os.path.dirname(__file__)
model_path = os.path.join(current_dir, MODEL_FILENAME)

artifacts = None
br_holidays = holidays.Brazil() # Cargar calendario una vez al inicio

try:
    print(f"🔄 Carregando modelo de: {model_path}")
    artifacts = joblib.load(model_path)
    
    model = artifacts['model']
    encoders = artifacts['encoders']
    expected_features = artifacts.get('features', [])
    metadata = artifacts.get('metadata', {})
    
    # 2. Ler o threshold salvo no Notebook (ou usar 0.40 se não achar)
    THRESHOLD = metadata.get('threshold_recomendado', 0.40)
    
    print(f"✅ Modelo V3 ({metadata.get('tecnologia', 'Unknown')}) carregado com sucesso!")
    print(f"📊 Recall Esperado: {metadata.get('recall_atrasos', '?')}")
    print(f"⚙️ Threshold de decisão configurado: {THRESHOLD}")

except Exception as e:
    print(f"⚠️ ERRO CRÍTICO ao carregar modelo: {e}")
    # Valores de fallback para não derrubar a API imediatamente
    model = None
    THRESHOLD = 0.40

# --- 2. INPUT DATA MODEL ---
class FlightInput(BaseModel):
    companhia: str
    origem: str
    destino: str
    data_partida: str
    distancia_km: float

# --- 3. HELPER FUNCTIONS ---
def safe_encode(encoder, value):
    """Trata valores novos (nunca vistos) como 'Outros/0'"""
    try:
        return int(encoder.transform([str(value)])[0])
    except:
        return 0 

# --- 4. ENDPOINT PREDICT ---
@app.post("/predict")
def predict_flight(flight: FlightInput):
    if not model:
        raise HTTPException(status_code=500, detail="Modelo não carregado no servidor")

    try:
        # A. Processar Data e Feriado
        dt = pd.to_datetime(flight.data_partida)
        
        # <--- 3. CORREÇÃO CRÍTICA: Usar .date() para ignorar a hora --->
        # Isso garante que '2025-12-25 14:00' seja visto como feriado
        is_holiday = 1 if dt.date() in br_holidays else 0

        # B. Criar DataFrame (Exatamente igual ao treino)
        input_data = pd.DataFrame([{
            'companhia_encoded': safe_encode(encoders['companhia'], flight.companhia),
            'origem_encoded': safe_encode(encoders['origem'], flight.origem),
            'destino_encoded': safe_encode(encoders['destino'], flight.destino),
            'distancia_km': float(flight.distancia_km),
            'hora': dt.hour,
            'dia_semana': dt.dayofweek,
            'mes': dt.month,
            'is_holiday': is_holiday
        }])
        
        # Garantir ordem das colunas (Segurança extra)
        if expected_features:
            input_data = input_data[expected_features]
        
        # C. Predição
        # CatBoost retorna [prob_classe_0, prob_classe_1] -> pegamos o indice 1
        prob = float(model.predict_proba(input_data)[0][1])
        
        # D. Lógica de Semáforo (Regra de Negócio)
        if prob < THRESHOLD:
            status = "PONTUAL"
            risco = "BAIXO"
            msg = "Voo com boas condições operacionais."
        elif THRESHOLD <= prob < 0.60:
            status = "ALERTA"
            risco = "MEDIO"
            msg = "Risco moderado. Recomendamos monitorar o status."
        else: # >= 0.60
            status = "ATRASADO"
            risco = "ALTO"
            msg = f"Alta probabilidade de atraso ({prob:.1%}). Planeje-se."

        return {
            "previsao": status,
            "probabilidade": round(prob, 4),
            "nivel_risco": risco,
            "mensagem": msg,
            "detalles": {
                "is_feriado": bool(is_holiday),
                "distancia_km": flight.distancia_km,
                "limiar_usado": THRESHOLD
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc() # Imprime o erro no terminal do servidor
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)