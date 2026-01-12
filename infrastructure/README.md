
# Flight On Time – Deployment na Oracle Cloud Infrastructure (OCI)

Este repositório documenta a arquitetura e a implementação do projeto **Flight On Time** implantado na **Oracle Cloud Infrastructure (OCI)**, utilizando **containers Docker** para isolar e orquestrar os serviços da aplicação.

A solução foi desenhada para ser **modular, escalável e facilmente reproduzível**, seguindo boas práticas de infraestrutura e DevOps.

---

## 📐 Visão Geral da Arquitetura

Todos os componentes da aplicação são executados em **containers Docker**, hospedados em uma **VM na OCI**.  
O acesso externo é centralizado por um **proxy reverso Caddy**, que gerencia o roteamento e, opcionalmente, certificados TLS.

```
                         ┌───────────────┐
                         │   Internet    │
                         └───────┬───────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │     Caddy       │
                        │  Proxy Reverso  │
                        └────────┬────────┘
                                 │
        ┌────────────────────────┼
        │                        │
        ▼                        ▼                         
┌─────────────────┐     ┌─────────────────┐       ┌─────────────────┐
│                 │     │                 │       │                 │
│    Frontend     │     │    Backend      │       │   Datascience   │
│     (React)     │─────│ (Java / Spring) ┼───────│    (Python)     │
│                 │     │                 │       │                 │
└─────────────────┘     └───────┬─────────┘       └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │      MySQL       │
                       │  Banco de Dados  │
                       └──────────────────┘


```


---

## 🧱 Componentes da Solução

### 🔹 Caddy (Proxy Reverso)
- Executa em container Docker
- Atua como ponto único de entrada da aplicação
- Responsável por:
    - Roteamento HTTP/HTTPS
    - Proxy reverso para os serviços internos
    - Gerenciamento automático de TLS
- Facilita a exposição dos serviços sem acoplamento direto aos containers

---

### 🔹 Frontend (React)
- Aplicação frontend desenvolvida em **React**
- Executa em container Docker
- Build gerado em ambiente controlado (`npm run build`)
- Servido via:
    - Caddy secundário (outro container)  
- Responsável por:
    - Interface do usuário
    - Consumo das APIs expostas pelo Backend Java
- Não acessa diretamente banco de dados ou serviços internos

---

### 🔹 Backend (Java)
- Aplicação Java (Spring Boot)
- Executa em container Docker baseado em **Temurin**
- Responsável por:
    - Exposição das APIs REST
    - Regras de negócio
    - Integração com o banco de dados MySQL
    - Comunicação com o serviço de Data Science
- Build realizado via **Maven** 

---

### 🔹 Datascience (Python)
- Serviço Python executando em container Docker
- Responsável por:
    - Carga e execução de modelos preditivos
    - Processamento de dados
    - Exposição de endpoints (FastAPI)
- Consumido pelo backend Java via HTTP
- Totalmente desacoplado do backend, permitindo evolução independente

---

### 🔹 MySQL
- Banco de dados relacional executando em container Docker
- Responsável pelo armazenamento de:
    - Dados operacionais
    - Dados históricos utilizados pelo modelo
- Persistência garantida via **volumes Docker**
- Não exposto diretamente à internet (acesso apenas interno)

---

## ☁️ Infraestrutura na OCI

- **Oracle Cloud Infrastructure (OCI)**
- **Compute Instance (VM Linux)**
- Docker e Docker Compose instalados na VM
- Containers executados na mesma instância
- Comunicação entre serviços via **rede Docker interna**
- Firewall da OCI permitindo acesso apenas às portas necessárias (ex: 80/443)

---

## 🐳 Containers e Orquestração

- Todos os serviços são definidos via **Docker Compose**
- Benefícios:
    - Padronização do ambiente
    - Facilidade de deploy e rollback
    - Isolamento entre serviços
    - Reprodutibilidade local e em produção

---

## 🔄 Fluxo de Comunicação

1. Usuário acessa a aplicação via navegador
2. Requisição chega ao **Caddy**
3. Caddy:
    - Serve o **Frontend React** 
4. Frontend consome APIs do **Backend Java**
5. Backend acessa:
    - MySQL para dados persistentes
    - Datascience para inferência de modelos
6. Resposta retorna ao usuário via Caddy

---

## ✅ Benefícios da Arquitetura

- Separação clara de responsabilidades
- Frontend desacoplado do backend
- Fácil manutenção e evolução dos serviços
- Possibilidade de escalar componentes individualmente
- Infraestrutura simples e de baixo custo na OCI
- Aderência a práticas modernas de cloud e containers

---

## 📌 Observações

- Nenhum serviço interno (MySQL, Datascience) é exposto diretamente
- Toda a comunicação externa passa pelo **Caddy**
- A arquitetura permite futura migração para Kubernetes sem grandes refatorações

---

## 📄 Licença

Este projeto é de uso educacional. Desenvolvido para o Hackathon NoCountry em parceria com Alura/Oracle ONE

