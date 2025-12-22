# data-science/src/app.py
import joblib
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import holidays
import sys

app = FastAPI(title="FlightOnTime AI Service (V4.2 Auto-Distance)")

# --- CARGA E FUNÇÕES AUXILIARES ---
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "flight_classifier_v4.joblib")

model = None
features_list = []
airport_coords = {} # Dicionário para lookup de lat/long
THRESHOLD = 0.35

# Função Haversine (Matemática pura)
def calculate_distance(lat1, lon1, lat2, lon2):
    r = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return r * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

if os.path.exists(model_path):
    try:
        print(f"📦 Carregando: {model_path}")
        artifact = joblib.load(model_path)
        model = artifact['model']
        features_list = artifact['features']
        # Carregamos o mapa de aeroportos do arquivo
        airport_coords = artifact.get('airport_coords', {})
        meta = artifact.get('metadata', {})
        THRESHOLD = meta.get('threshold', 0.35)
        print(f"✅ V4.2 Online | Aeroportos Mapeados: {len(airport_coords)}")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
else:
    print(f"⚠️ Modelo não encontrado.")

class FlightInput(BaseModel):
    companhia: str
    origem: str
    destino: str
    data_partida: str  
    # Agora é opcional (Optional), pode ser None
    distancia_km: Optional[float] = None 
    precipitation: float = 0.0
    wind_speed: float = 5.0

@app.post("/predict")
def predict(flight: FlightInput):
    if not model: raise HTTPException(status_code=503, detail="Service Unavailable")
    
    try:
        # 1. Lógica de Distância Automática
        dist_final = flight.distancia_km
        
        # Se o usuário não mandou a distância, calculamos nós mesmos
        if dist_final is None or dist_final == 0:
            if flight.origem in airport_coords and flight.destino in airport_coords:
                orig = airport_coords[flight.origem]
                dest = airport_coords[flight.destino]
                dist_final = calculate_distance(
                    orig['lat'], orig['long'],
                    dest['lat'], dest['long']
                )
            else:
                # Fallback: Se não acharmos o aeroporto, usamos uma média nacional (800km)
                # ou retornamos erro. Vamos usar média para não quebrar.
                dist_final = 800.0 

        # 2. Resto do Pipeline
        dt = pd.to_datetime(flight.data_partida)
        is_holiday = 1 if dt.date() in holidays.Brazil() else 0
        
        input_df = pd.DataFrame([{
            'companhia': str(flight.companhia),
            'origem': str(flight.origem),
            'destino': str(flight.destino),
            'distancia_km': float(dist_final), # Usamos o calculado
            'hora': dt.hour,
            'dia_semana': dt.dayofweek,
            'mes': dt.month,
            'is_holiday': is_holiday,
            'precipitation': float(flight.precipitation),
            'wind_speed': float(flight.wind_speed),
            'clima_imputado': 0
        }])
        
        if features_list:
            input_df = input_df[features_list]
        
        prob = float(model.predict_proba(input_df)[0][1])
        
        if prob < THRESHOLD:
            status, color = "🟢 PONTUAL", "green"
        elif prob < 0.70:
            status, color = "🟡 ALERTA CLIMÁTICO/OPERACIONAL", "yellow"
        else:
            status, color = "🔴 ALTA PROBABILIDADE DE ATRASO", "red"
            
        return {
            "previsao": status,
            "probabilidade": round(prob, 4),
            "cor": color,
            "distancia_calculada": round(dist_final, 1), # Devolvemos para ele ver
            "clima": f"Chuva: {flight.precipitation}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)