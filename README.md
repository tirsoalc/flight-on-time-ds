# 🛫 FlightOnTime - Sistema Inteligente de Previsão de Voos

> **Status do Projeto:** Em Produção (v5.0.0-LiveWeather)  
> **Arquitetura:** Monorepo (Frontend + Backend + Data Science)

O **FlightOnTime** é uma solução completa para prever atrasos em voos comerciais no Brasil. O sistema combina Inteligência Artificial avançada, dados meteorológicos em tempo real e uma arquitetura robusta de microserviços para garantir a segurança e o planejamento dos passageiros.

---

##  Estrutura do Repositório

Este repositório agrupa todas as camadas da aplicação:

* 📁 **data-science/** (Core de ML, Python, CatBoost)
* 📁 **back-end/** (API Gateway, Java, Spring Boot)
* 📁 **front-end/** (Interface Web, React, Vite)

---

## 1. Data Science & Inteligência Artificial
**Diretório:** `/data-science`

[**📄 Ver Documentação Técnica (Data Science)**](./data-science/README.md)

O "cérebro" do projeto. Responsável por calcular a probabilidade matemática de um atraso.

* **Modelo:** CatBoost Classifier (Gradient Boosting).
* **Recursos (v5.0):** Integração **Live Weather** (OpenMeteo) para considerar chuva e vento em tempo real.
* **Pesquisa Acadêmica:** Experimentamos arquiteturas de **Deep Learning (Embeddings)** para variáveis de alta cardinalidade. Embora funcional, o CatBoost manteve uma superioridade de ~10% no ROC-AUC, sendo escolhido para produção.
* **API:** FastAPI (Python).

## 2. Backend API
**Diretório:** `/back-end`

[**📄 Ver Documentação Técnica (Backend)**](./back-end/README.md)

O orquestrador do sistema. Gerencia as requisições, conecta-se ao motor de IA e aplica regras de negócio.

* **Tecnologia:** Java 21 + Spring Boot 3.5.4.
* **Banco de Dados:** MySQL (com Flyway).
* **Funcionalidade:** Recebe os dados do voo e padroniza a resposta.

## 3. Frontend Dashboard
**Diretório:** `/front-end`

[**📄 Ver Documentação Técnica (Frontend)**](./front-end/README.md)

A interface visual para o usuário final.

* **Tecnologia:** React + Vite + Tailwind CSS.
* **UX:** Autocomplete inteligente e validação de códigos IATA.

---

## Como Executar o Projeto Completo

Para rodar a aplicação inteira localmente, você precisará de 3 terminais abertos.

### Passo 1: Iniciar o Motor de IA (Data Science)
```bash
cd data-science
# Ativar venv e instalar dependências...
python -m uvicorn src.app:app --reload --port 8000
Passo 2: Iniciar o Backend (Java)

Bash
cd back-end
./mvnw spring-boot:run
Passo 3: Iniciar o Frontend (React)

Bash
cd front-end
npm run dev
🚦 Regra de Negócio: O Semáforo de Risco
O sistema traduz a probabilidade matemática em uma experiência visual:

🟢 PONTUAL (Risco < 35%): Boas condições.

🟡 ALERTA (Risco 35% - 70%): Instabilidade detectada.

🔴 ATRASO PROVÁVEL (Risco > 70%): Condições críticas (Tempestade, Feriados).