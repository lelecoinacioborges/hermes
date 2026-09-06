# 🚀 Hermes Agent + OmniRoute + Hermes WebUI (Docker & Easypanel)

Ambiente completo e integrado com **Hermes Agent**, **OmniRoute** e **Hermes WebUI** rodando via Docker Compose.

---

## 📌 Portas e Acessos

| Serviço | Porta | Descrição |
| :--- | :--- | :--- |
| **Hermes WebUI** | `8787` | **Interface Gráfica Moderna de Chat** |
| **OmniRoute** | `20128` | Dashboard de Provedores e Gateway de IA |
| **Hermes Dashboard** | `9119` | Painel de monitoramento nativo do Hermes |
| **Hermes Gateway API**| `8642` | API interna do agente |

---

## ⚙️ Como Subir no Easypanel (VPS)

1. No Easypanel, crie um novo **Project** (ou use um existente).
2. Adicione um novo serviço do tipo **App** -> **Docker Compose**.
3. Aponte para o repositório GitHub:
   ```text
   https://github.com/lelecoinacioborges/hermes.git
   ```
4. Configure as variáveis de ambiente necessárias (copie de `.env.example`):
   - `OMNIROUTE_PORT=20128`
   - `HERMES_WEBUI_PORT=8787`
   - `HERMES_DASHBOARD_PORT=9119`
   - `HERMES_GATEWAY_PORT=8642`
   - `OPENAI_API_KEY=sk-...` (sua chave gerada no OmniRoute)
   - `CUSTOM_API_KEY=sk-...`
5. No Easypanel, exponha a porta `8787` com o seu domínio público (ex: `hermes.seudominio.com`) para acessar o chat Web moderno.
6. Se desejar acessar o painel do OmniRoute para cadastrar chaves de IA, exponha a porta `20128` (ex: `omniroute.seudominio.com`).

---

## 🛠️ Como Subir via Docker Compose no Terminal (Linux / VPS / Local)

1. Clone o repositório:
   ```bash
   git clone https://github.com/lelecoinacioborges/hermes.git
   cd hermes
   ```
2. Crie o arquivo `.env`:
   ```bash
   cp .env.example .env
   ```
3. Suba os containers:
   ```bash
   docker compose up -d
   ```
4. Acesse:
   - **Hermes WebUI**: `http://SEU_IP:8787`
   - **OmniRoute Dashboard**: `http://SEU_IP:20128`