"""Cliente da API do Waha (WhatsApp HTTP API).

Fala com o Waha via REST: envia mensagens, consulta sessões e
configura webhooks. Lê as credenciais de .env (na raiz do projeto).
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

_ENV_CACHE = None


def _load_env():
    """Carrega .env da raiz do projeto (sem dependências)."""
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    env = {}
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                env[chave.strip()] = valor.strip()
    _ENV_CACHE = env
    return env


def _env(chave, padrao=""):
    valor = os.environ.get(chave)
    if valor is not None and valor != "":
        return valor
    return _load_env().get(chave, padrao)


def base_url():
    return _env("WAHA_URL", "").rstrip("/")


def api_key():
    return _env("WAHA_API_KEY", "")


def session_name():
    return _env("WAHA_SESSION", "default")


def _requisicao(metodo, caminho, body=None, timeout=30):
    url = base_url() + caminho
    dados = None
    cabecalhos = {"X-Api-Key": api_key()}
    if body is not None:
        dados = json.dumps(body).encode("utf-8")
        cabecalhos["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=dados, headers=cabecalhos, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            texto = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(texto) if texto else None
    except urllib.error.HTTPError as e:
        texto = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(texto)
        except ValueError:
            return e.code, {"erro": texto}
    except urllib.error.URLError as e:
        return 0, {"erro": f"sem conexão com o Waha: {e.reason}"}


def listar_sessoes():
    """Retorna a lista de sessões do Waha."""
    status, dados = _requisicao("GET", "/api/sessions")
    return dados


def status_sessao():
    """Status da sessão configurada (WORKING, FAILED, STOPPED...)."""
    sessoes = listar_sessoes()
    if isinstance(sessoes, list):
        for s in sessoes:
            if s.get("name") == session_name():
                return s.get("status")
    return None


_LID_CACHE = {}


def resolver_lid(lid, sessao=None):
    """Resolve um identificador @lid para o número real (<digitos>@c.us) via API do Waha.

    Consulta GET /api/{session}/lids/{lid} e mantém cache em memória.
    """
    if not lid or not str(lid).endswith("@lid"):
        return None
    if lid in _LID_CACHE:
        return _LID_CACHE[lid]
    if not base_url():
        return None
    sess = sessao or session_name()
    lid_enc = urllib.parse.quote(str(lid), safe="")
    status, dados = _requisicao("GET", f"/api/{sess}/lids/{lid_enc}", timeout=5)
    if status == 200 and isinstance(dados, dict):
        pn = dados.get("pn") or dados.get("phoneNumber") or ""
        if pn and "@" in pn:
            numero = pn.split("@")[0]
            if numero.isdigit():
                resolvido = numero + "@c.us"
                _LID_CACHE[lid] = resolvido
                return resolvido
        elif pn and str(pn).isdigit():
            resolvido = str(pn) + "@c.us"
            _LID_CACHE[lid] = resolvido
            return resolvido
        print(f"[lid] Waha retornou 200 sem pn para {lid}: {dados}", flush=True)
    else:
        print(f"[lid] falha ao resolver {lid} via Waha (status={status}, sessao={sess}): {dados}", flush=True)
    return None


def enviar_texto(chat_id, texto):
    """Envia mensagem de texto para um chat (ex.: 5511999999999@c.us).

    Nesta versão do Waha (NOWEB) o caminho é POST /api/sendText.
    """
    return _requisicao(
        "POST",
        "/api/sendText",
        {"session": session_name(), "chatId": chat_id, "text": texto},
    )


def configurar_webhooks(url, eventos=("message", "session.status")):
    """AVISO: no tier CORE desta versão do Waha (NOWEB), webhooks de sessão
    não são persistidos via API (PUT /api/sessions/{nome} devolve config
    vazio e POST /api/sessions retorna 403).

    O caminho que funciona: configurar variáveis de ambiente no container
    do Waha (EasyPanel -> serviço -> Environment):
      WHATSAPP_HOOK_URL=<url>
      WHATSAPP_HOOK_EVENTS=message,session.status
    E reiniciar o serviço.
    """
    return (0, {
        "aviso": "configure WHATSAPP_HOOK_URL / WHATSAPP_HOOK_EVENTS "
                 "no container do Waha (tier CORE não persiste webhook via API)"
    })


def iniciar_sessao():
    """Tenta (re)iniciar a sessão no Waha."""
    return _requisicao("POST", f"/api/sessions/{session_name()}/start")


if __name__ == "__main__":
    import sys

    comando = sys.argv[1] if len(sys.argv) > 1 else "status"
    if comando == "status":
        print("Sessão:", session_name(), "| Status:", status_sessao())
    elif comando == "testar-envio":
        chat = sys.argv[2] if len(sys.argv) > 2 else None
        if not chat:
            print("Uso: python3 src/waha_client.py testar-envio <chat_id>")
            sys.exit(1)
        print(enviar_texto(chat, "Teste da Zupoo Locadora 🏍️"))
    else:
        print("Comandos: status | testar-envio <chat_id>")