import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI(title="FlightOnTime MVP API")

# --- 1. CONFIGURACIÓN Y CARGA ---
# Asegúrate de que el nombre del archivo coincida con el exportado en el notebook
MODEL_FILENAME = "flight_classifier_mvp.joblib" 

current_dir = os.path.dirname(__file__)
model_path = os.path.join(current_dir, MODEL_FILENAME)

artifacts = None

try:
    artifacts = joblib.load(model_path)
    model = artifacts['model']
    encoders = artifacts['encoders']
    # Recuperamos las features esperadas para asegurar el orden correcto
    expected_features = artifacts.get('features', [
        'companhia_encoded', 'origem_encoded', 'destino_encoded', 
        'distancia_km', 'hora', 'dia_semana', 'mes'
    ])
    print(f"✅ Modelo cargado: {MODEL_FILENAME}")
    print(f"📋 Features esperadas: {expected_features}")
except Exception as e:
    print(f"⚠️ CRÍTICO: Error cargando modelo. Verifique que el archivo {MODEL_FILENAME} existe.")
    print(f"Error detalle: {e}")

# --- 2. DEFINICIÓN DEL INPUT (Contrato JSON) ---
class FlightInput(BaseModel):
    companhia: str
    origem: str
    destino: str
    data_partida: str
    distancia_km: float  # <--- NUEVO: Campo obligatorio para el nuevo modelo

# --- 3. FUNCIONES AUXILIARES ---
def safe_encode(encoder, value):
    """Maneja valores desconocidos (nuevas aerolíneas/aeropuertos)"""
    try:
        # Convertimos a string por seguridad
        return int(encoder.transform([str(value)])[0])
    except:
        # Si no existe en el entrenamiento, usamos la clase 0 o moda
        return 0 

# --- 4. ENDPOINT DE PREDICCIÓN ---
@app.post("/predict")
def predict_flight(flight: FlightInput):
    if not artifacts:
        raise HTTPException(status_code=500, detail="Modelo no cargado en el servidor")

    try:
        # A. Feature Engineering (Tiempo)
        dt = pd.to_datetime(flight.data_partida)
        
        # B. Construcción del DataFrame (Inputs + Encoding)
        # Es CRÍTICO que el orden de las columnas sea exacto al del entrenamiento
        input_data = pd.DataFrame([{
            'companhia_encoded': safe_encode(encoders['companhia'], flight.companhia),
            'origem_encoded': safe_encode(encoders['origem'], flight.origem),
            'destino_encoded': safe_encode(encoders['destino'], flight.destino),
            'distancia_km': float(flight.distancia_km), # <--- El dato nuevo
            'hora': dt.hour,
            'dia_semana': dt.dayofweek,
            'mes': dt.month
        }])
        
        # Reordenamos columnas para garantizar coincidencia con el modelo
        input_data = input_data[expected_features]
        
        # C. Predicción
        prob = float(model.predict_proba(input_data)[0][1]) # Probabilidad de clase 1 (Atraso)
        
        # D. Definición de Status (Regla de negocio)
        status = "Atrasado" if prob > 0.5 else "Pontual"

        # E. Respuesta (Formato Hackathon)
        return {
            "previsao": status,
            "probabilidade": round(prob, 4),
            # Extras útiles para depuración
            "detalles": {
                "distancia": flight.distancia_km,
                "hora": dt.hour
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc() # Imprime el error real en la consola
        raise HTTPException(status_code=500, detail=f"Error procesando solicitud: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)