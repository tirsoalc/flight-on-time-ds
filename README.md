#  FlightOnTime - Motor de Inteligência Artificial

> **Status:**  Em Produção (v3.0.0-CAT) | **Recall de Segurança:** 89.4%

Este repositório contém o **Core de Data Science** do projeto FlightOnTime. Nossa missão é prever atrasos em voos comerciais no Brasil utilizando Machine Learning avançado, focando na segurança e planejamento do passageiro.

---

##  A Evolução do Modelo (Do MVP ao State-of-the-Art)

Nosso maior desafio foi lidar com o **desbalanceamento severo** dos dados (apenas 11% dos voos atrasam). Um modelo comum teria 89% de acurácia apenas dizendo "Nenhum voo vai atrasar", o que seria inútil.

Para resolver isso, realizamos uma bateria de testes com diferentes algoritmos de **Boosting** e **Ensemble**, priorizando a métrica de **Recall** (Capacidade de detectar o perigo).

| Versão | Modelo | Tecnologia | Recall (Detecção) | Status |
| :--- | :--- | :--- | :--- | :--- |
| v1.0 | **Random Forest** | Bagging Ensemble | 87.0% | Descontinuado |
| v2.0 | **XGBoost** | Gradient Boosting | 87.2% | Testado |
| **v3.0** | **CatBoost** | **Categorical Boosting** | **89.4% ** | **Em Produção** |

**Por que CatBoost?**
O algoritmo da Yandex demonstrou superioridade ao lidar com as variáveis categóricas complexas (centenas de rotas e companhias aéreas) e nos permitiu atingir quase **90% de detecção de atrasos** sem sacrificar a performance da API.

---

##  Engenharia de Features e Arquitetura

O modelo não olha apenas para o passado. Enriquecemos os dados brutos com inteligência de calendário e geolocalização:

1.  **Detector de Feriados Nacionais:**
    * Utilizamos a biblioteca `holidays` para cruzar a data do voo com o calendário oficial brasileiro.
    * *Insight:* Voos em feriados possuem padrões de tráfego aéreo radicalmente diferentes.
2.  **Georreferenciamento:**
    * Cálculo preciso da distância (`distancia_km`) entre coordenadas de aeroportos, não apenas a rota teórica.
3.  **Decomposição Temporal:**
    * Análise granular de Hora, Dia da Semana e Sazonalidade (Mês).

### Stack Tecnológico
* **Linguagem:** Python 3.10+
* **ML Core:** CatBoost, Scikit-Learn
* **Data Processing:** Pandas, Numpy, Holidays
* **API:** FastAPI (Interface de baixa latência)
* **Serialização:** Joblib

---

##  Regra de Negócio: O Semáforo de Risco

Para traduzir a probabilidade matemática (0.0 a 1.0) em uma experiência útil para o usuário, criamos uma lógica de **Risco Escalonado**.

> **Nota Técnica:** Definimos o *Threshold* (Limiar de Decisão) em **0.40**.
> *Por que 40% e não 50?* Nossos testes mostraram que subir a régua para 41% causava uma queda crítica na detecção de atrasos. Preferimos pecar pelo excesso de zelo (alerta preventivo) do que deixar um passageiro perder seu voo.

* 🟢 **PONTUAL (Risco Baixo < 40%):**
    * O voo apresenta condições operacionais normais.
* 🟡 **ALERTA (Risco Médio 40% - 60%):**
    * O modelo detectou instabilidade. Recomendamos monitorar o painel, mas não há certeza de atraso.
* 🔴 **ATRASADO (Risco Alto > 60%):**
    * Alta probabilidade de problemas. O usuário deve se planejar para contingências.

---

##  Instalação e Execução Local

### 1. Preparar o Ambiente
Clone o repositório e instale as dependências (incluindo `catboost` e `holidays`):

```bash
# Criação do ambiente virtual (opcional mas recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalação
pip install -r requirements.txt
```

### 2. Treinar o "Cérebro" (Opcional)
O repositório já inclui o modelo treinado. Mas se desejar retreinar com novos dados:

```bash
python src/train.py
```

*Isso gerará um novo arquivo `flight_classifier_mvp.joblib` com a lógica mais recente.*

### 3. Subir a API
Inicie o servidor de predição localmente:

```bash
python -m uvicorn src.app:app --reload
```

Acesse a documentação automática em: `http://127.0.0.1:8000/docs`

---

##  Documentação da API

A API foi desenhada para ser consumida por qualquer Front-End ou Back-End.

**Endpoint:** `POST /predict`

**Payload de Entrada (Exemplo):**

```json
{
  "companhia": "TAM",
  "origem": "Guarulhos - Governador Andre Franco Montoro",
  "destino": "Eduardo Gomes",
  "data_partida": "2025-12-25T20:00:00",
  "distancia_km": 2689.0
}
```

**Resposta da API (Exemplo Real):**

```json
{
  "previsao": "🔴 ATRASADO",
  "nivel_risco": "ALTO",
  "probabilidade": 0.8942,
  "is_feriado": true,
  "mensagem": "Alta probabilidade de atraso (89.4%). Planeje-se."
}
```

---

##  Deploy em Produção (Oracle Cloud)

Graças à infraestrutura configurada na OCI, a API já está disponível publicamente para integração via internet.

* **Base URL:** `http://flight-on-time.ds.vm3.arbly.com`
* **Endpoint de Predição:** `POST /predict`
* **Documentação Interativa (Swagger):** [Acessar Docs](http://flight-on-time.ds.vm3.arbly.com/docs)

**Teste rápido via Terminal (cURL):**

```bash
curl -X POST "http://flight-on-time.ds.vm3.arbly.com/predict" \
-H "Content-Type: application/json" \
-d '{"companhia": "AZUL", "origem": "Guarulhos", "destino": "Recife", "data_partida": "2025-12-25T14:30:00", "distancia_km": 2100.5}'
```

---

## Próximos Passos (Roadmap)

Embora o modelo atual seja robusto (89% Recall), identificamos oportunidades para a versão 2.0:

1. **Integração Meteorológica em Tempo Real:** Conectar com APIs de clima (OpenWeather) para considerar chuvas/tempestades no momento da predição.
2. **Monitoramento de Tráfego Aéreo:** Incluir variáveis sobre congestionamento de pistas em tempo real.

---
