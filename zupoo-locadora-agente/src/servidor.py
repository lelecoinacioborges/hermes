"""Servidor de webhook que recebe as mensagens do Waha e responde via agente.

- Recebe eventos "message" do Waha em POST /webhook/waha
- Só responde para números na lista ZUPOO_RESPONDER_APENAS (.env)
- Ignora as próprias mensagens (eco) para evitar loop
- Resposta é enviada de volta pelo Waha (sendText)
"""
import re, json, os, threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket

import agente
import waha_client

_RE_REGISTRO = re.compile(r"<<<REGISTRO>>>(.*?)<<<FIM>>>", re.S)

def _separar_registro(resposta):
    """Tira o bloco interno do texto que vai pro cliente."""
    if not resposta:
        return "", None
    m = _RE_REGISTRO.search(resposta)
    if not m:
        return resposta.strip(), None
    try:
        registro = json.loads(m.group(1))
    except json.JSONDecodeError:
        registro = None
    return _RE_REGISTRO.sub("", resposta).strip(), registro

# --- Configuração -----------------------------------------------------------

def _env(chave, padrao=""):
    return os.environ.get(chave, padrao)

def _carregar_env_variaveis():
    """Lê variáveis do .env sem depender de source (útil fora do shell)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho = os.path.join(base, ".env")
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith("#") and "=" in linha:
                    chave, valor = linha.split("=", 1)
                    os.environ.setdefault(chave.strip(), valor.strip())

_carregar_env_variaveis()

PORTA = int(_env("ZUPOO_WEBHOOK_PORT", "8081"))

# Números autorizados a falar com o agente (apenas o próprio número por enquanto)
_SEM_FORMATO = re.compile(r"\D")
def _digitos(chat_id):
    return _SEM_FORMATO.sub("", chat_id or "")

AUTORIZADOS = [c.strip() for c in _env("ZUPOO_RESPONDER_APENAS", "").split(",") if c.strip()]
AUTORIZADOS_DIGITOS = {_digitos(c) for c in AUTORIZADOS}
ACEITAR_SELFCHAT = _env("ZUPOO_ACEITAR_SELFCHAT", "true").lower() == "true"
ADMIN_CHAT = _env("ZUPOO_ADMIN_CHAT", "").strip()

AVISO_AUDIO = (
    "Ainda não consigo ouvir áudios por aqui 😅\n\n"
    "Pode me mandar por *texto*? Assim consigo te ajudar rapidinho!"
)

# ids das mensagens que O AGENTE enviou (para não responder ao próprio eco)
# Persistido em logs/ids.json para sobreviver a reinícios do servidor.
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAMINHO_IDS = os.path.join(_BASE, "logs", "ids.json")
_IDS_ENVIADOS = deque(maxlen=2000)
_LOCK = threading.Lock()
# Agrupa mensagens enviadas em sequência pelo mesmo chat antes de processar.
# Isso evita responder separadamente a cada mensagem de uma rajada.
_AGRUPAMENTO_SEGUNDOS = 3.0
_AGRUPAMENTO_MAX_MENSAGENS = 5
_AGRUPAMENTO_MAX_CARACTERES = 1000
_PENDENTES = {}


def _carregar_ids():
    global _IDS_ENVIADOS
    try:
        if os.path.exists(_CAMINHO_IDS):
            with open(_CAMINHO_IDS, encoding="utf-8") as f:
                ids = json.load(f)
            _IDS_ENVIADOS = deque(ids, maxlen=2000)
    except Exception:
        pass


def _salvar_ids():
    try:
        os.makedirs(os.path.dirname(_CAMINHO_IDS), exist_ok=True)
        with open(_CAMINHO_IDS, "w", encoding="utf-8") as f:
            json.dump(list(_IDS_ENVIADOS)[-1500:], f)
    except Exception:
        pass


def _marcar_enviado(msg_id):
    if not msg_id:
        return
    with _LOCK:
        _IDS_ENVIADOS.append(msg_id)
        _salvar_ids()


_carregar_ids()


def _permitido(remetente):
    # Nunca responde a newsletters/broadcast/grupos
    if any(remetente.endswith(sfx) for sfx in ("@newsletter", "@broadcast", "@g.us")):
        return False
    # "*" = libera qualquer mensageiro (modo leads: qualquer número pode chamar)
    if "*" in AUTORIZADOS:
        return True
    if remetente in AUTORIZADOS:
        return True
    return _digitos(remetente) in AUTORIZADOS_DIGITOS and bool(_digitos(remetente))


def _ja_enviamos(msg_id):
    if not msg_id:
        return False
    with _LOCK:
        return msg_id in _IDS_ENVIADOS


def _resolver_remetente(evento):
    """Resolve o remetente real do evento, convertendo @lid para <digitos>@c.us.

    Ordem de resolução:
    1. Campos alternativos do payload (_data.key.participantAlt, remoteJidAlt, senderPn)
    2. Campo me.lid / me.id (quando for self-chat ou próprio número da sessão)
    3. Consulta à API do Waha GET /api/{session}/lids/{lid} (com cache)
    """
    payload = evento.get("payload", {}) or {}
    _data = payload.get("_data", {}) or {}
    chave = _data.get("key", {}) or {}
    remetente = payload.get("from") or payload.get("chatId") or ""

    if not remetente.endswith("@lid"):
        return remetente

    # 1. Campos alternativos no próprio payload
    alt = (
        chave.get("participantAlt")
        or chave.get("remoteJidAlt")
        or payload.get("remoteJidAlt")
        or _data.get("senderPn")
        or ""
    )
    if alt:
        numero = _digitos(alt.split("@")[0])
        if numero:
            return numero + "@c.us"

    # 2. Mapeamento do próprio número da sessão (me.lid -> me.id)
    me = evento.get("me") or {}
    if me.get("lid") == remetente and me.get("id"):
        numero = _digitos(str(me.get("id")).split("@")[0])
        if numero:
            return numero + "@c.us"

    # 3. API oficial do Waha NOWEB para resolver @lid -> pn
    resolvido = waha_client.resolver_lid(remetente, sessao=evento.get("session"))
    if resolvido:
        print(f"[lid] resolvido {remetente} -> {resolvido}", flush=True)
        return resolvido

    return remetente


def _eh_audio(evento) -> bool:
    payload = evento.get("payload", {}) or {}
    tipo = (payload.get("type") or payload.get("messageType") or "").lower()
    if tipo in ("audio", "ptt"):
        return True
    msg = (payload.get("_data", {}) or {}).get("message") or {}
    return "audioMessage" in msg


def _tentar_transcrever_audio(evento):
    """Se o WAHA entregar media.url (ex.: WAHA Plus), tenta transcrever via OmniRoute."""
    payload = evento.get("payload", {}) or {}
    media = payload.get("media") or {}
    media_url = media.get("url") if isinstance(media, dict) else None
    base_ai = _env("OPENAI_BASE_URL", "").rstrip("/")
    if not media_url or not base_ai:
        return None
    try:
        import urllib.request
        headers_dl = {}
        if waha_client.api_key():
            headers_dl["X-Api-Key"] = waha_client.api_key()
        req_dl = urllib.request.Request(media_url, headers=headers_dl)
        with urllib.request.urlopen(req_dl, timeout=15) as r:
            audio_bytes = r.read()
        boundary = "----ZupooAudioBoundary7MA4YWxkTrZu0gW"
        partes = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nwhisper-1\r\n".encode("utf-8"),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\npt\r\n".encode("utf-8"),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"audio.ogg\"\r\nContent-Type: audio/ogg\r\n\r\n".encode("utf-8"),
            audio_bytes,
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
        corpo = b"".join(partes)
        headers_ai = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        if _env("OPENAI_API_KEY", ""):
            headers_ai["Authorization"] = f"Bearer {_env('OPENAI_API_KEY', '')}"
        req_ai = urllib.request.Request(f"{base_ai}/audio/transcriptions", data=corpo, headers=headers_ai, method="POST")
        with urllib.request.urlopen(req_ai, timeout=25) as r:
            res = json.loads(r.read().decode("utf-8", "replace"))
            texto = (res.get("text") or "").strip()
            if texto:
                print(f"[audio] transcrito com sucesso: {texto[:80]!r}", flush=True)
                return texto
    except Exception as e:
        print(f"[audio] transcrição indisponível ({e}); usando aviso de texto", flush=True)
    return None


def _notificar_admin(registro):
    """Envia resumo automático para o WhatsApp do admin quando entra novo lead/suporte."""
    if not ADMIN_CHAT or not isinstance(registro, dict) or not registro.get("novo_registro"):
        return
    tipo = registro.get("tipo_registro") or registro.get("vertical") or "lead"
    nome = registro.get("nome") or "—"
    tel = _digitos(registro.get("telefone") or "")
    loc = " - ".join(p for p in (registro.get("cidade"), registro.get("bairro")) if p) or "—"
    if tipo == "locadora":
        plano = registro.get("plano_interesse") or "não informado"
        msg = (
            "🔔 *Novo lead — Lista de Espera (Moto)*\n"
            f"👤 Nome: {nome}\n"
            f"📍 Local: {loc}\n"
            f"📋 Plano: {plano}\n"
            f"📱 Tel: {tel}"
        )
    elif tipo == "restaurante":
        msg = (
            "🔔 *Novo cadastro — Restaurante*\n"
            f"👤 Nome: {nome}\n"
            f"📍 Local: {loc}\n"
            f"📱 Tel: {tel}"
        )
    else:
        assunto = registro.get("assunto") or "—"
        msg = (
            "🔔 *Novo chamado — Suporte*\n"
            f"👤 Nome: {nome}\n"
            f"💬 Assunto: {assunto}\n"
            f"📱 Tel: {tel}"
        )
    try:
        st, dados = waha_client.enviar_texto(ADMIN_CHAT, msg)
        print(f"[alerta-admin] tipo={tipo} -> {ADMIN_CHAT}, Waha={st}", flush=True)
        if isinstance(dados, dict):
            chave_resp = dados.get("key") or {}
            _marcar_enviado(chave_resp.get("id") or dados.get("id"))
    except Exception as e:
        print(f"[erro] falha ao notificar admin: {e}", flush=True)


def _processar_mensagem(evento):
    """Lida com um evento 'message' do Waha. Retorna (relevante, resposta, registro)."""
    payload = evento.get("payload", {}) or {}
    _data = payload.get("_data", {}) or {}
    remetente_bruto = payload.get("from") or payload.get("chatId") or ""
    msg_id = payload.get("id")
    corpo = payload.get("body") or payload.get("text") or ""
    from_me = payload.get("fromMe") is True
    tipo = payload.get("type") or payload.get("messageType") or "chat"
    nome = _data.get("pushName") or payload.get("senderName") or ""
    eh_audio = _eh_audio(evento)

    # Resolve @lid para o telefone real (<digitos>@c.us)
    remetente = _resolver_remetente(evento)
    telefone_ident = remetente

    # Só mensagens de texto ou áudio (ignora imagem, vídeo, figurinha, ack, etc.)
    TIPOS_NAO_TEXTO = {
        "image", "video", "document", "sticker", "location", "contact",
        "poll", "reaction", "ack", "protocol", "protocolmessage", "notification",
        "revoked", "edited", "ciphertext", "newsletter", "event",
    }
    if not eh_audio and (not corpo or (tipo and tipo.lower() in TIPOS_NAO_TEXTO)):
        return False, None, None

    # Nunca responde ao próprio eco (mensagens que o agente enviou)
    if _ja_enviamos(msg_id):
        print(f"[eco] ignorando msg_id já processado: {msg_id}", flush=True)
        return False, None, None

    # Marca como processada independente do desfecho (evita re-resposta em retries)
    _marcar_enviado(msg_id)

    # Responde apenas aos números autorizados (".env" -> ZUPOO_RESPONDER_APENAS)
    if not _permitido(remetente):
        print(
            f"[ignorado] remetente={remetente} (bruto={remetente_bruto}) não está em ZUPOO_RESPONDER_APENAS={AUTORIZADOS}",
            flush=True,
        )
        return False, None, None

    # Mensagem enviada pela própria conta (self-chat de teste): só com permissão
    if from_me and not ACEITAR_SELFCHAT:
        print(f"[ignorado] fromMe=True e ACEITAR_SELFCHAT=False para {remetente}", flush=True)
        return False, None, None

    # Tratamento de áudio: tenta transcrever via OmniRoute; se não houver mídia (WAHA CORE), pede texto
    if eh_audio and not corpo:
        transcrito = _tentar_transcrever_audio(evento)
        if transcrito:
            corpo = transcrito
        else:
            return True, AVISO_AUDIO, None

    resposta_bruta = agente.responder(corpo, telefone=telefone_ident, nome=nome)
    texto, registro = _separar_registro(resposta_bruta)
    if not texto:
        print(f"[silencio] agente retornou resposta vazia para {remetente} (sessão já finalizada/avisada; envie #reset para reiniciar)", flush=True)
        return False, None, None
    return True, texto, registro


def _processar_lote(eventos):
    """Processa uma rajada como uma única mensagem e envia uma resposta."""
    if not eventos:
        return
    primeiro = eventos[0]
    textos = [((e.get("payload", {}) or {}).get("body") or (e.get("payload", {}) or {}).get("text") or "").strip() for e in eventos]
    textos = [t for t in textos if t]
    tem_audio = any(_eh_audio(e) for e in eventos)
    if not textos and not tem_audio:
        return
    combinado = dict(primeiro)
    combinado["payload"] = dict(primeiro.get("payload", {}) or {})
    if textos:
        combinado["payload"]["body"] = "\n".join(textos)
    relevante, resposta, registro = _processar_mensagem(combinado)
    if not relevante:
        return
    remetente = _resolver_remetente(combinado)
    entrada_txt = (combinado["payload"].get("body") or "[áudio]").replace("\n", " | ")
    saida_txt = resposta.replace("\n", " | ")
    try:
        status, dados = waha_client.enviar_texto(remetente, resposta)
        print(f"[conversa] IN  ({remetente}): {entrada_txt}", flush=True)
        print(f"[conversa] OUT ({remetente}) [Waha={status}]: {saida_txt}", flush=True)
        if status not in (200, 201):
            print(f"[erro] detalhe Waha ({status}): {dados}", flush=True)
        if isinstance(dados, dict):
            chave_resp = dados.get("key") or {}
            _marcar_enviado(chave_resp.get("id") or dados.get("id"))
        if registro and registro.get("novo_registro"):
            _notificar_admin(registro)
    except Exception as e:
        print(f"[erro] falha ao enviar lote: {e}", flush=True)


def _agendar_lote(evento):
    chat = _resolver_remetente(evento)
    msg_id = (evento.get("payload", {}) or {}).get("id")
    with _LOCK:
        item = _PENDENTES.get(chat)
        if item:
            # Ignora entrega duplicada do mesmo msg_id enviada pelo WAHA na mesma janela
            if msg_id and any((e.get("payload", {}) or {}).get("id") == msg_id for e in item["eventos"]):
                return
            item["eventos"].append(evento)
            if item["timer"]:
                item["timer"].cancel()
        else:
            item = {"eventos": [evento], "timer": None}
            _PENDENTES[chat] = item
        if sum(len(((e.get("payload", {}) or {}).get("body") or "")) for e in item["eventos"]) >= _AGRUPAMENTO_MAX_CARACTERES or len(item["eventos"]) >= _AGRUPAMENTO_MAX_MENSAGENS:
            timer = None
        else:
            timer = threading.Timer(_AGRUPAMENTO_SEGUNDOS, _despachar_lote, args=(chat,))
            timer.daemon = True
        item["timer"] = timer
        if timer:
            timer.start()
            return
    _despachar_lote(chat)


def _despachar_lote(chat):
    with _LOCK:
        item = _PENDENTES.pop(chat, None)
    if item:
        try:
            _processar_lote(item["eventos"])
        except Exception as e:
            import traceback
            print(f"[erro] exceção ao processar lote de {chat}: {e}", flush=True)
            traceback.print_exc()
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # logs mais curtos
        print("  [http]", fmt % args, flush=True)

    def _enviar_json(self, status, obj):
        corpo = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/health":
            self._enviar_json(200, {"status": "ok"})
        else:
            self._enviar_json(404, {"erro": "não encontrado"})

    def do_POST(self):
        if self.path != "/webhook/waha":
            self._enviar_json(404, {"erro": "não encontrado"})
            return

        try:
            tamanho = int(self.headers.get("Content-Length", 0))
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8", "replace"))
        except Exception:
            self._enviar_json(400, {"erro": "json inválido"})
            return

        evento = dados.get("event", "")
        sessao_ev = dados.get("session") or ""
        sessao_esperada = waha_client.session_name()
        # Ignora silenciosamente eventos de outras sessões configuradas no mesmo WAHA
        if sessao_esperada and sessao_ev and sessao_ev != sessao_esperada:
            self._enviar_json(200, {"recebido": True, "ignorado": "outra_sessao"})
            return

        # Depuração: registra TODO payload recebido da sessão do agente e salva o último
        payload_bruto = dados.get("payload", {})
        print(
            f"[debug] evento={evento} session={dados.get('session')} "
            f"from={payload_bruto.get('from')} fromMe={payload_bruto.get('fromMe')} "
            f"type={payload_bruto.get('type')} body={str(payload_bruto.get('body') or payload_bruto.get('text'))[:40]!r}",
            flush=True,
        )
        try:
            caminho_payload = os.path.join(_BASE, "logs", "ultimo_payload.json")
            os.makedirs(os.path.dirname(caminho_payload), exist_ok=True)
            with open(caminho_payload, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        # Responde 200 na hora para o Waha não reenviar; resposta sai via API
        self._enviar_json(200, {"recebido": True, "evento": evento})

        if evento == "session.status":
            payload = dados.get("payload", {})
            print(f"[sessão] status: {payload.get('status')}", flush=True)
            return

        if evento != "message":
            return

        _agendar_lote(dados)
        return

        relevante, resposta = _processar_mensagem(dados)
        if not relevante:
            return

        payload_envio = dados.get("payload", {}) or {}
        remetente = payload_envio.get("from") or ""
        # O Waha NOWEB entrega @lid no campo from, mas o envio precisa usar
        # o telefone real em remoteJidAlt.
        chave_envio = payload_envio.get("_data", {}).get("key", {}) or {}
        alt_envio = chave_envio.get("participantAlt") or chave_envio.get("remoteJidAlt") or payload_envio.get("remoteJidAlt") or ""
        if remetente.endswith("@lid") and alt_envio:
            remetente = alt_envio.split("@")[0] + "@c.us"
        print(f"[msg] de {remetente}: {resposta.splitlines()[0][:60]}...")

        try:
            status, dados = waha_client.enviar_texto(remetente, resposta)
            # Marca o id da resposta enviada para ignorar o eco dela
            if isinstance(dados, dict):
                chave = dados.get("key") or {}
                id_enviado = chave.get("id") or dados.get("id")
                if id_enviado:
                    _marcar_enviado(id_enviado)
            if status not in (200, 201):
                print(f"[erro] Waha respondeu {status} ao enviar resposta", flush=True)
        except Exception as e:
            print(f"[erro] falha ao enviar resposta: {e}", flush=True)


def iniciar():
    print(f"Zupoo agente webhook escutando na porta {PORTA}", flush=True)
    print(f"Números autorizados: {AUTORIZADOS or '(nenhum — use ZUPOO_RESPONDER_APENAS no .env)'}", flush=True)
    print(f"Self-chat (teste) aceito: {ACEITAR_SELFCHAT}", flush=True)
    servidor = ThreadingHTTPServer(("0.0.0.0", PORTA), Handler)
    servidor.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.serve_forever()


if __name__ == "__main__":
    iniciar()