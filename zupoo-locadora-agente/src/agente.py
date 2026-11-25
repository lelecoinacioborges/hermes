# Lógica de atendimento da Zupoo (locadora de motos + cadastro de restaurantes).
#
# Protótipo baseado em regras — sem IA externa. Responde usando os dados
# fictícios em data/ (catálogo, planos, políticas, FAQ e clientes).
#
# Formatação: o WhatsApp entende *negrito*, _itálico_ e ~riscado~.

import datetime
import json
import os
import re
import unicodedata
from sessions import get_session, set_session, clear_session

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

# --- Marca ------------------------------------------------------------------
#
# A marca oficial é Zupoo. A marca anterior não deve aparecer nas respostas
# nem ser usada como identificação comercial.

MARCA = "Zupoo"
MARCA_LOCADORA = "Zupoo Locadora"


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def _ler_md(nome: str) -> str:
    caminho = os.path.join(DATA, nome)
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    return ""


def _carregar_catalogo():
    """Lê a tabela de preços em data/veiculos.md."""
    catalogo = []
    for linha in _ler_md("veiculos.md").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("|"):
            linha = linha[1:]
        if linha.endswith("|"):
            linha = linha[:-1]
        partes = [p.strip() for p in linha.split("|")]
        if len(partes) >= 3:
            modelo, categoria, valor = partes[0], partes[1], partes[2]
            valor = "".join(ch for ch in valor if ch.isdigit())
            if valor.isdigit():
                catalogo.append({"modelo": modelo, "categoria": categoria, "valor": int(valor)})
    return catalogo


def _carregar_clientes():
    caminho = os.path.join(DATA, "clientes.json")
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return []


CATALOGO = _carregar_catalogo()
CLIENTES = _carregar_clientes()
FAQ = _ler_md("faq.md")
POLITICAS = _ler_md("politicas.md")
PLANOS = _ler_md("planos.md")

ARQUIVO_ESPERA = os.path.join(DATA, "lista_espera.json")

# --- Mensagens --------------------------------------------------------------

MENU = (
    "🏍️ *Alugar uma moto*\n"
    "🍽️ *Cadastrar meu restaurante*"
)

BOAS_VINDAS = (
    f"Olá! 👋 Seja bem-vindo à *{MARCA}*.\n\n"
    "Como posso te ajudar hoje?\n" + MENU
)

REDIRECIONA = "Só pra eu te direcionar certinho 😊\n\n" + MENU

RESTAURANTE_ATENDENTE = (
    "Que bom ter você com a gente! 🍽️\n\n"
    "O cadastro do seu restaurante é *gratuito* ✅\n\n"
    "Pra começar, *qual é o seu nome?*"
)

RESTAURANTE_PEDE_CIDADE = "Prazer em te conhecer! 😊\n\nDe qual *cidade* é o seu restaurante?"
RESTAURANTE_PEDE_BAIRRO = "E em qual *bairro* fica o restaurante?"
RESTAURANTE_BAIRRO_EM_ANALISE = (
    "Perfeito! ✅ Já anotei os dados do seu restaurante.\n\n"
    "Estamos expandindo a Zupoo bairro a bairro. Vou verificar se já atendemos "
    "essa região e, assim que confirmar, um atendente entra em contato para "
    "continuar o cadastro. 🍽️"
)

RESTAURANTE_TRANSFERIDO = (
    "Perfeito! ✅ O seu bairro já está na área de atendimento da Zupoo.\n\n"
    "Vou transferir seu chamado para um atendente, que vai continuar o cadastro "
    "e explicar os próximos passos. 🍽️"
)

BOAS_VINDAS_LOCADORA = (
    f"Olá! 👋 Seja bem-vindo à *{MARCA_LOCADORA}* 🏍️\n\n"
    "Pra começar, *como você se chama?*"
)

ESCOLHEU_LOCADORA = "Perfeito! 🏍️\n\nPra começar, *como você se chama?*"

NOME_NAO_ENTENDIDO = "Desculpa, não peguei 😅 *Como posso te chamar?*"

PEDE_BAIRRO = "Anotado! 📍\n\nE de qual *bairro* você é?"

AVISO_SEM_MOTO = (
    "⚠️ *Aviso importante*\n"
    "No momento estamos *sem motos disponíveis* — a procura foi muito alta e a "
    "nova frota já está a caminho 🏍️"
)

PERGUNTA_LISTA = "Quer entrar na nossa *lista de espera*? Responda *SIM* ou *NÃO*"

RECONFIRMA_LISTA = (
    "Só confirmando 😊\n\n"
    "Quer que eu te avise quando a frota chegar? Responda *SIM* ou *NÃO*"
)

RECUSOU = (
    "Sem problema! 😊\n\n"
    "Se mudar de ideia, é só me chamar por aqui — a *lista de espera* fica sempre aberta."
)

CHAMA_ATENDENTE = (
    "Vou chamar um atendente pra te ajudar melhor 😊\n\n"
    "Já já alguém fala com você por aqui."
)

JA_CADASTRADO = (
    "Você já está na nossa *lista de espera* ✅\n\n"
    "Assim que a frota chegar, você é avisado em primeira mão."
)

JA_CADASTRADO_OI = "Oi de novo! 😊\n\n" + JA_CADASTRADO

RESP_ATENDENTE = (
    "Essa informação eu ainda não tenho por aqui 😅\n\n"
    "Um atendente passa todos os detalhes assim que a frota chegar."
)

RESP_PRAZO = (
    "Ainda *não temos data definida* para a nova frota 🏍️\n\n"
    "Assim que ela chegar, você é avisado."
)

RESP_RESERVA = (
    "Não consigo *garantir reserva* enquanto a frota não chega 😔\n\n"
    "O que dá pra fazer é te colocar na *lista de espera*."
)

RESP_MODELO = (
    "Não tenho unidades disponíveis pra confirmar modelo agora 🏍️\n\n"
    "Quando a frota chegar, um atendente passa todas as opções."
)

RESP_FLEXIVEL = (
    "Isso mesmo! O *Plano Flexível* fica em *R$ 35 por dia* 👍\n\n"
    "Se preferir contrato mais longo, o *Plano Anual* sai por *R$ 29 por dia*."
)

RESP_ANUAL = (
    "Isso mesmo! O *Plano Anual* sai por *R$ 29 por dia* 👍\n\n"
    "É o nosso melhor valor — o *Plano Flexível*, sem prazo fixo, fica em *R$ 35 por dia*."
)

RESP_PRECO = (
    "Temos dois planos 💰\n"
    "🔹 *Anual* — R$ 29 por dia\n"
    "🔹 *Flexível* — R$ 35 por dia\n\n"
    "O valor final depende do *modelo* da moto."
)

# --- Lista de espera (leads) ------------------------------------------------


def _ler_espera():
    if os.path.exists(ARQUIVO_ESPERA):
        with open(ARQUIVO_ESPERA, encoding="utf-8") as f:
            return json.load(f)
    return []


def _salvar_espera(entrada):
    lista = _ler_espera()
    lista.append(entrada)
    with open(ARQUIVO_ESPERA, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def _digitos_telefone(telefone: str) -> str:
    if not telefone:
        return ""
    return re.sub(r"\D", "", telefone)


def _na_lista(telefone: str) -> bool:
    digitos = _digitos_telefone(telefone)
    if not digitos:
        return False
    return any(_digitos_telefone(e.get("telefone", "")) == digitos for e in _ler_espera())


def _adicionar_lista_espera(telefone, nome="", cidade="", bairro="", plano=None) -> bool:
    """Grava o lead. Retorna False se o telefone já estiver na lista."""
    digitos = _digitos_telefone(telefone)
    if not digitos or _na_lista(telefone):
        return False
    _salvar_espera({
        "nome": (nome or "").strip() or "—",
        "cidade": (cidade or "").strip(),
        "bairro": (bairro or "").strip(),
        "plano_interesse": plano,
        "lista_espera": True,
        "telefone": digitos,
        "chat_id": telefone,
        "data": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "origem": "whatsapp_lead",
    })
    return True


def _buscar_modelo(texto: str):
    for item in CATALOGO:
        nome = _normalizar(item["modelo"])
        variantes = {nome, nome.replace(" ", ""), " ".join(nome.split()[1:]), "".join(nome.split()[1:])}
        for v in variantes:
            if v and v in texto:
                return item
    return None


# --- Sessão -----------------------------------------------------------------
#
# set_session() substitui a sessão inteira, então toda gravação passa por aqui
# com o dicionário completo. Gravar só o campo alterado apaga o resto — foi o
# que zerava nome e cidade no meio do fluxo.

def _atualizar(telefone, sessao, **campos):
    nova = dict(sessao)
    nova.update(campos)
    set_session(telefone, nova)
    return nova


# --- Roteamento entre os dois negócios --------------------------------------
#
# Restaurante é checado antes da locadora: "motoboy" contém "moto", e um
# restaurante falando de entrega não pode cair no fluxo de aluguel.
#
# "zupoo" NÃO serve como marcador: a marca cobre os dois negócios. Por isso o
# roteamento se apoia nos nomes dos planos, que são exclusivos da locadora.

PADROES_RESTAURANTE = (
    "restaurante", "lanchonete", "pizzaria", "hamburgueria", "padaria",
    "meu estabelecimento", "estabelecimento", "cadastrar meu", "quero cadastrar",
    "ser parceiro", "sou parceiro", "lojista", "delivery", "entrega", "entregador",
    "motoboy", "frete", "coleta",
)

PADROES_LOCADORA = (
    "plano flexivel", "plano anual", "plano mensal", "plano semanal",
    "alugar", "aluguel", "locacao", "locar", "moto", "scooter",
    # A copy do site vira "a partir de 29 reais" depois da troca de marca.
    "a partir de 29", "apartir de 29", "29/dia", "29 por dia", "35/dia",
)


def _detectar_vertical(t: str):
    if any(p in t for p in PADROES_RESTAURANTE):
        return "restaurante"
    if any(p in t for p in PADROES_LOCADORA):
        return "locadora"
    return None


def _plano_citado(t: str):
    """Plano nomeado na mensagem de entrada, para a saudação reconhecer."""
    if "anual" in t:
        return "anual"
    if "flexivel" in t:
        return "flexivel"
    return None


# --- Dúvidas (interrompem o fluxo e depois ele retoma) ----------------------

RE_PRECO = re.compile(r"\b(preco|precos|quanto|valor|valores|custa|diaria|diarias)\b")


def _responder_duvida(t: str):
    """Resposta para dúvida avulsa, ou None se a mensagem não for uma dúvida.

    A ordem importa: caução casa com "valor", então vem antes de preço.
    """
    if any(p in t for p in ("caucao", "cnh", "habilitacao", "documento", "documentos",
                            "idade", "comprovante", "requisito", "requisitos", "exige")):
        return RESP_ATENDENTE

    if any(p in t for p in ("quando chega", "quando vai chegar", "quando tem", "que dia",
                            "qual data", "prazo", "previsao", "quando exatamente")):
        return RESP_PRAZO

    if any(p in t for p in ("reservar", "reserva", "garantir", "separar uma", "guardar uma")):
        return RESP_RESERVA

    if _buscar_modelo(t) or any(p in t for p in ("modelo", "modelos", "qual moto", "que moto")):
        return RESP_MODELO

    # Sem exigir o preço junto: o cliente costuma escrever só "quero o plano
    # anual", e a versão anterior deixava isso cair no fluxo e virar bairro.
    if "plano anual" in t or ("anual" in t and "plano" in t):
        return RESP_ANUAL

    if "flexivel" in t:
        return RESP_FLEXIVEL

    if RE_PRECO.search(t):
        return RESP_PRECO

    return None


# --- SIM / NÃO --------------------------------------------------------------
#
# Fronteira de palavra é obrigatória. A versão anterior testava "no" como
# substring e casava com "novo", "nome", "menos" — por isso "quando chega o
# lote novo?" era lido como recusa e derrubava a sessão.
#
# "obrigado" fica de fora do RE_NAO: sozinho ele é ambíguo e transformaria
# "sim, obrigado" em recusa. A forma negativa já está em FRASES_NAO.

RE_SIM = re.compile(r"\b(sim|claro|quero|aceito|aceita|pode|bora|ok|isso|positivo|manda|vamos|s)\b")
RE_NAO = re.compile(r"\b(nao|nem|dispenso)\b")

FRASES_SIM = ("pode colocar", "pode me colocar", "pode por", "entrar na lista",
              "quero entrar", "me adiciona", "coloca eu", "quero sim", "pode sim")
FRASES_NAO = ("nao quero", "nao obrigado", "sem interesse", "agora nao",
              "nao precisa", "ja tenho", "deixa pra la", "outra hora")


def _intencao(t: str):
    """'sim', 'nao' ou None."""
    if any(f in t for f in FRASES_NAO):
        return "nao"
    if any(f in t for f in FRASES_SIM):
        return "sim"
    if RE_NAO.search(t):
        return "nao"
    if RE_SIM.search(t):
        return "sim"
    return None


def _quer_voltar(t: str) -> bool:
    """Aceite explícito de quem já tinha recusado.

    Aqui não vale o _intencao() solto: um "ok" de quem já disse não viraria
    cadastro sem a pessoa ter pedido.
    """
    return any(f in t for f in FRASES_SIM) or bool(re.search(r"\b(sim|quero)\b", t))


# --- Captura de nome e local ------------------------------------------------

PREFIXOS_NOME = ("meu nome e ", "me chamo ", "sou o ", "sou a ", "eu sou ", "aqui e o ", "aqui e a ")

# No WhatsApp as pessoas mandam em rajada ("Ei", "Oiii", "tudo bem?"). Sem isto
# cada saudação era consumida como resposta da pergunta da vez, e já gravou
# nome="Oiii" e cidade="Olá".
SAUDACOES = {
    "oi", "oii", "oiii", "oie", "ola", "ei", "eai", "e ai", "opa", "alo",
    "bom dia", "boa tarde", "boa noite", "tudo bem", "tudo bom", "blz",
    "beleza", "salve", "fala", "ok", "boa",
}


def _extrair_nome(mensagem: str, t: str):
    """Nome limpo, ou None se a mensagem claramente não for um nome."""
    if "?" in mensagem or t in SAUDACOES or _detectar_vertical(t) or _responder_duvida(t):
        return None
    limpo = (mensagem or "").strip()
    baixo = _normalizar(limpo)
    for p in PREFIXOS_NOME:
        if baixo.startswith(p):
            limpo = limpo[len(p):].strip()
            break
    limpo = limpo.strip(".,!;:")
    if not limpo or len(limpo) > 40 or len(limpo.split()) > 5:
        return None
    return limpo


def _extrair_local(mensagem: str, t: str):
    """Cidade/bairro, ou None quando a mensagem é saudação ou pergunta."""
    if "?" in mensagem or t in SAUDACOES:
        return None
    limpo = (mensagem or "").strip().strip(".,!;:")
    if not limpo or len(limpo) > 60:
        return None
    return limpo


def _primeiro_nome(sessao):
    nome = (sessao.get("nome_usuario") or "").strip()
    return nome.split()[0] if nome else None


# --- Perguntas de cada etapa ------------------------------------------------

def _pergunta_atual(sessao) -> str:
    etapa = sessao.get("etapa")
    if etapa == "nome":
        return "*Como você se chama?*"
    if etapa == "cidade":
        return "De qual *cidade* você é?"
    if etapa == "bairro":
        return "E de qual *bairro*?"
    if etapa == "lista":
        return PERGUNTA_LISTA
    return "Como posso te ajudar?"


def _bloco_registro(sessao, telefone):
    registro = {
        "nome": sessao.get("nome_usuario"),
        "cidade": sessao.get("cidade"),
        "bairro": sessao.get("bairro"),
        "plano_interesse": sessao.get("plano"),
        "lista_espera": sessao.get("lista_espera"),
        "telefone": telefone,
    }
    return "\n\n<<<REGISTRO>>>" + json.dumps(registro, ensure_ascii=False) + "<<<FIM>>>"


def _com_registro(resposta, sessao, telefone):
    """Anexa o bloco interno assim que houver ao menos o nome.

    O servidor remove antes de enviar. Reemitido a cada mensagem para que lead
    que abandona no meio não se perca.
    """
    if sessao.get("nome_usuario"):
        return resposta + _bloco_registro(sessao, telefone)
    return resposta


def _saudacao_locadora(plano):
    """Saudação da locadora, reconhecendo o plano quando o site pré-preencheu."""
    if plano == "anual":
        return (f"Olá! 👋 Seja bem-vindo à *{MARCA_LOCADORA}* 🏍️\n\n"
                "Vi que é sobre o *Plano Anual* — R$ 29 por dia 👍\n"
                "Pra começar, *como você se chama?*")
    if plano == "flexivel":
        return (f"Olá! 👋 Seja bem-vindo à *{MARCA_LOCADORA}* 🏍️\n\n"
                "Vi que é sobre o *Plano Flexível* — R$ 35 por dia 👍\n"
                "Pra começar, *como você se chama?*")
    return BOAS_VINDAS_LOCADORA


# --- Entrada pública --------------------------------------------------------

def responder(mensagem: str, telefone: str = None, nome: str = None) -> str:
    """Resposta para o cliente. String vazia significa não enviar nada."""
    mensagem = mensagem or ""
    t = _normalizar(mensagem)
    sessao = get_session(telefone) or {}

    # 1. Primeira mensagem: roteia entre os dois negócios e só então pede o
    #    nome. A mensagem de entrada nunca vira nome — era ela que gravava
    #    todo lead vindo do site como "Quero".
    if not sessao.get("etapa"):
        vertical = _detectar_vertical(t)
        if vertical == "restaurante":
            _atualizar(telefone, sessao, vertical="restaurante", etapa="restaurante")
            return RESTAURANTE_ATENDENTE
        if vertical is None:
            _atualizar(telefone, sessao, etapa="escolher")
            return BOAS_VINDAS
        if _na_lista(telefone):
            _atualizar(telefone, sessao, vertical="locadora", etapa="cadastrado")
            return JA_CADASTRADO_OI
        plano = _plano_citado(t)
        _atualizar(telefone, sessao, vertical="locadora", etapa="nome", plano=plano)
        return _saudacao_locadora(plano)

    # 2. Escolha de negócio pendente.
    if sessao.get("etapa") == "escolher":
        vertical = _detectar_vertical(t)
        if vertical == "restaurante":
            _atualizar(telefone, sessao, vertical="restaurante", etapa="restaurante")
            return RESTAURANTE_ATENDENTE
        if vertical == "locadora":
            if _na_lista(telefone):
                _atualizar(telefone, sessao, vertical="locadora", etapa="cadastrado")
                return JA_CADASTRADO
            _atualizar(telefone, sessao, vertical="locadora", etapa="nome",
                       plano=_plano_citado(t))
            return ESCOLHEU_LOCADORA
        return REDIRECIONA

    # 3. Fluxo do restaurante: coleta nome, cidade e bairro e então transfere.
    if sessao.get("etapa") in ("restaurante", "restaurante_cidade", "restaurante_bairro"):
        if sessao.get("avisado"):
            return ""
        if sessao.get("etapa") == "restaurante":
            valor = _extrair_nome(mensagem, t)
            if not valor:
                return "Não peguei 😅 Qual é o seu *nome*?"
            _atualizar(telefone, sessao, nome_usuario=valor, etapa="restaurante_cidade")
            return RESTAURANTE_PEDE_CIDADE
        if sessao.get("etapa") == "restaurante_cidade":
            local = _extrair_local(mensagem, t)
            if not local:
                return "Não peguei 😅 De qual *cidade* é o seu restaurante?"
            _atualizar(telefone, sessao, cidade=local, etapa="restaurante_bairro")
            return RESTAURANTE_PEDE_BAIRRO
        local = _extrair_local(mensagem, t)
        if not local:
            return "Não peguei 😅 Em qual *bairro* fica o seu restaurante?"
        _atualizar(telefone, sessao, bairro=local, etapa="restaurante_transferido", avisado=True)
        return RESTAURANTE_BAIRRO_EM_ANALISE

    if sessao.get("etapa") == "restaurante_transferido":
        return ""

    # 4. Já resolvidos. Dúvida sempre tem resposta, mas o aviso de estado é
    #    dito UMA vez: repetir a cada mensagem atrapalha o atendente humano
    #    que assumiu a conversa, e é o que fazia o bot papagaiar sem parar.
    if sessao.get("etapa") in ("restaurante", "cadastrado", "recusou"):
        duvida = _responder_duvida(t)
        if duvida:
            return duvida
        if sessao.get("etapa") == "recusou" and _quer_voltar(t):
            return _finalizar_lista(sessao, telefone)
        if sessao.get("avisado"):
            return ""
        _atualizar(telefone, sessao, avisado=True)
        if sessao.get("etapa") == "cadastrado":
            return JA_CADASTRADO
        return CHAMA_ATENDENTE

    # 4. Dúvida no meio do fluxo: responde e retoma de onde parou.
    duvida = _responder_duvida(t)
    if duvida:
        return _com_registro(duvida + "\n\n" + _pergunta_atual(sessao), sessao, telefone)

    etapa = sessao.get("etapa")

    if etapa == "nome":
        nome_usuario = _extrair_nome(mensagem, t)
        if not nome_usuario:
            return NOME_NAO_ENTENDIDO
        sessao = _atualizar(telefone, sessao, nome_usuario=nome_usuario, etapa="cidade")
        return _com_registro(
            f"Prazer em te conhecer, *{_primeiro_nome(sessao)}*! 😊\n\n"
            "De qual *cidade* você é?",
            sessao, telefone)

    if etapa == "cidade":
        local = _extrair_local(mensagem, t)
        if not local:
            return _com_registro("Não peguei 😅 De qual *cidade* você é?", sessao, telefone)
        partes = [p.strip() for p in local.split(",")]
        cidade = partes[0]
        bairro = partes[1] if len(partes) >= 2 else ""
        if bairro:
            sessao = _atualizar(telefone, sessao, cidade=cidade, bairro=bairro, etapa="lista")
            return _com_registro(AVISO_SEM_MOTO + "\n\n" + PERGUNTA_LISTA, sessao, telefone)
        sessao = _atualizar(telefone, sessao, cidade=cidade, etapa="bairro")
        return _com_registro(PEDE_BAIRRO, sessao, telefone)

    if etapa == "bairro":
        local = _extrair_local(mensagem, t)
        if not local:
            return _com_registro("Não peguei 😅 E de qual *bairro*?", sessao, telefone)
        sessao = _atualizar(telefone, sessao, bairro=local, etapa="lista")
        return _com_registro(AVISO_SEM_MOTO + "\n\n" + PERGUNTA_LISTA, sessao, telefone)

    if etapa == "lista":
        intencao = _intencao(t)
        if intencao == "sim":
            return _finalizar_lista(sessao, telefone)
        if intencao == "nao":
            # Sem clear_session: zerar aqui fazia a próxima mensagem cair no
            # "Seja bem-vindo(a)" e recomeçar o atendimento do zero.
            sessao = _atualizar(telefone, sessao, lista_espera=False, etapa="recusou")
            return _com_registro(RECUSOU, sessao, telefone)

        # Não entendeu: reformula uma vez e, na segunda, chama gente.
        tentativas = sessao.get("tentativas", 0) + 1
        sessao = _atualizar(telefone, sessao, tentativas=tentativas)
        if tentativas >= 2:
            sessao = _atualizar(telefone, sessao, etapa="recusou", avisado=True)
            return _com_registro(CHAMA_ATENDENTE, sessao, telefone)
        return _com_registro(RECONFIRMA_LISTA, sessao, telefone)

    # Estado desconhecido: reinicia sem deixar o chamador sem resposta.
    clear_session(telefone)
    return BOAS_VINDAS


def _finalizar_lista(sessao, telefone):
    nome_final = sessao.get("nome_usuario", "")
    novo = _adicionar_lista_espera(
        telefone, nome_final, sessao.get("cidade", ""), sessao.get("bairro", ""),
        sessao.get("plano"))
    sessao = _atualizar(telefone, sessao, lista_espera=True, etapa="cadastrado", avisado=True)
    tratamento = _primeiro_nome(sessao)
    saudacao = f"*{tratamento}*" if tratamento else "amigo"
    if not novo:
        return _com_registro(
            f"Você já estava na lista, {saudacao} 😊\n\n"
            "Pode ficar tranquilo: assim que a frota chegar, te aviso ✅",
            sessao, telefone)
    return _com_registro(
        f"Prontinho, {saudacao}! 🎉\n\n"
        "Você está na nossa *lista de espera* ✅ Assim que a frota chegar, você é "
        "avisado em primeira mão, com prioridade na escolha do modelo.",
        sessao, telefone)
