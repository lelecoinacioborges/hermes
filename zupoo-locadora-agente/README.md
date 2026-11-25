# Zupoo Locadora — Agente de Atendimento

Projeto do agente de atendimento ao cliente da Zupoo Locadora (teste).
Atende pelo **WhatsApp** usando o **Waha** (gateway HTTP) + servidor local
de webhook + túnel Cloudflare.

## Estrutura

```
zupoo-locadora-agente/
├── README.md
├── .env               ← credenciais (NÃO commitar)
├── requirements.txt
├── data/
│   ├── veiculos.md    ← catálogo de motos (R$ 29–57/semana)
│   ├── planos.md      ← plano semestral 6 meses, pagamento semanal
│   ├── faq.md         ← perguntas frequentes
│   ├── politicas.md   ← regras da locadora
│   └── clientes.json  ← clientes fictícios p/ teste
├── src/
│   ├── agente.py      ← lógica de atendimento (baseada em regras)
│   ├── waha_client.py ← cliente da API do Waha
│   └── servidor.py    ← recebe webhooks do Waha e responde
└── logs/
```

## Como rodar (fluxo WhatsApp)

1. **Servidor webhook** (escuta em `ZUPOO_WEBHOOK_PORT`, ex. 8790):
   ```
   ZUPOO_WEBHOOK_PORT=8790 python3 src/servidor.py
   ```
2. **Túnel público** (URL muda a cada reinício):
   ```
   cloudflared tunnel --url http://localhost:8790 --protocol http2
   ```
3. **No Waha (EasyPanel)**: adicionar no container do serviço
   - `WHATSAPP_HOOK_URL=https://<tunel>.trycloudflare.com/webhook/waha`
   - `WHATSAPP_HOOK_EVENTS=message,session.status`
   e reiniciar o serviço.
4. **Sessão**: se `status: FAILED`, reescanear o QR no dashboard do Waha
   (precisa do celular com o WhatsApp da loja).

## Testes sem WhatsApp

```
python3 src/agente.py          # bateria de exemplos no terminal
curl localhost:8790/health     # servidor ok
```

## Fluxo atual (sem motos em estoque → lista de espera)

- Qualquer número que chame a loja é atendido (modo leads, `ZUPOO_RESPONDER_APENAS=*`)
- Primeiro contato: saudação + aviso de que **não há motos no momento** + oferta da lista de espera
- Cliente responde **SIM** → entra em `data/lista_espera.json` (nome capturado do perfil
  do WhatsApp, data e telefone) e recebe confirmação
- Cliente responde **NÃO** → resposta educada, sem insistência
- Quem já está na lista recebe lembrete "você já está na lista" em toda interação
- Grupos / newsletters / broadcasts são ignorados
- Ver a lista: `python3 src/lista_espera.py`

## Regras atuais do agente (`.env`)

- `ZUPOO_RESPONDER_APENAS=*` — responde a **qualquer número** (modo leads).
  Para restringir, troque por uma lista (ex.: `5511983640209@c.us,5511993751000@c.us`).
- `ZUPOO_ACEITAR_SELFCHAT=true` — aceita mensagens da própria conta
  (self-chat usado nos testes).
- `ZUPOO_WEBHOOK_URL` — URL pública atual do webhook.