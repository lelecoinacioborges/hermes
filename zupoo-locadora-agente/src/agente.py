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
ARQUIVO_RESTAURANTES = os.path.join(DATA, "restaurantes.json")
ARQUIVO_SUPORTE = os.path.join(DATA, "suporte.json")

# --- Mensagens --------------------------------------------------------------

MENU = (
    "1️⃣ 🏍️ *Alugar uma moto*\n"
    "2️⃣ 🍽️ *Cadastrar meu restaurante*\n"
    "3️⃣ 💬 *Dúvidas ou suporte*"
)

BOAS_VINDAS = (
    f"Olá! 👋 Seja bem-vindo à *{MARCA}*.\n\n"
    "Como posso te ajudar hoje?\n" + MENU
)

REDIRECIONA = "Só pra eu te direcionar certinho 😊 Responda *1*, *2* ou *3*:\n\n" + MENU

SUPORTE_INICIO = (
    "Claro! 💬 Pode me contar qual é a sua *dúvida* ou o que você precisa?\n\n"
    "Vou te ajudar ou já encaminhar direto para um atendente humano."
)

SUPORTE_TRANSFERIDO = (
    "Anotado! ✅ Já encaminhei sua mensagem para o nosso time de suporte.\n\n"
    "Um atendente humano vai continuar por aqui em instantes. 💬"
)

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

RESP_DUVIDA_RESTAURANTE = (
    "O cadastro do seu restaurante é *100% gratuito* e sem taxa de adesão ✅\n\n"
    "Os detalhes de taxas e entregas da sua região são passados pelo nosso "
    "atendente assim que confirmarmos seu bairro."
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

# --- Lista de espera (leads) e Restaurantes ---------------------------------


def _ler_json_lista(caminho):
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return []


def _salvar_json_lista(caminho, entrada):
    lista = _ler_json_lista(caminho)
    lista.append(entrada)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def _ler_espera():
    return _ler_json_lista(ARQUIVO_ESPERA)


def _salvar_espera(entrada):
    _salvar_json_lista(ARQUIVO_ESPERA, entrada)


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
    """Grava o lead da locadora. Retorna False se o telefone já estiver na lista."""
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


def _adicionar_restaurante(telefone, nome="", cidade="", bairro="") -> bool:
    """Grava o lead de restaurante em data/restaurantes.json."""
    digitos = _digitos_telefone(telefone)
    if not digitos:
        return False
    existentes = _ler_json_lista(ARQUIVO_RESTAURANTES)
    if any(_digitos_telefone(e.get("telefone", "")) == digitos for e in existentes):
        return False
    _salvar_json_lista(ARQUIVO_RESTAURANTES, {
        "nome": (nome or "").strip() or "—",
        "cidade": (cidade or "").strip(),
        "bairro": (bairro or "").strip(),
        "telefone": digitos,
        "chat_id": telefone,
        "data": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "origem": "whatsapp_restaurante",
    })
    return True


def _adicionar_suporte(telefone, mensagem="", nome="") -> bool:
    """Grava chamado de suporte em data/suporte.json."""
    digitos = _digitos_telefone(telefone)
    if not digitos:
        return False
    _salvar_json_lista(ARQUIVO_SUPORTE, {
        "nome": (nome or "").strip() or "—",
        "assunto": (mensagem or "").strip(),
        "telefone": digitos,
        "chat_id": telefone,
        "data": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "origem": "whatsapp_suporte",
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
# Restaurante é checado antes da locadora na entrada inicial: "motoboy" contém
# "moto", e um restaurante falando de entrega não pode cair no fluxo de aluguel.
#
# Porém, na TROCA de vertical (quando o usuário JÁ está alugando uma moto),
# palavras como "delivery", "motoboy" ou "entrega" NÃO podem expulsar o
# entregador para o cadastro de restaurante — só termos inequívocos de
# estabelecimento fazem a troca.

PADROES_TROCA_RESTAURANTE = (
    "restaurante", "lanchonete", "pizzaria", "hamburgueria", "padaria",
    "meu estabelecimento", "estabelecimento", "cadastrar meu", "quero cadastrar",
    "ser parceiro", "sou parceiro", "lojista", "ifood",
)

PADROES_RESTAURANTE = PADROES_TROCA_RESTAURANTE + (
    "delivery", "entrega", "entregador", "motoboy", "frete", "coleta",
)

PADROES_LOCADORA = (
    "plano flexivel", "plano anual", "plano mensal", "plano semanal",
    "plano de 29", "plano de 35", "alugar", "aluguel", "locacao", "locar",
    "moto", "scooter",
    # A copy do site vira "a partir de 29 reais" depois da troca de marca.
    "a partir de 29", "apartir de 29", "29/dia", "29 por dia", "35/dia",
)


PADROES_SUPORTE = (
    "suporte", "duvida", "duvidas", "atendente", "falar com alguem",
    "falar com humano", "humano", "ajuda", "problema", "reclamacao",
    "financeiro", "boleto", "pagamento", "fatura", "manutencao", "sinistro",
)


def _detectar_vertical(t: str):
    if any(p in t for p in PADROES_RESTAURANTE):
        return "restaurante"
    if any(p in t for p in PADROES_LOCADORA):
        return "locadora"
    if any(p in t for p in PADROES_SUPORTE):
        return "suporte"
    return None


def _detectar_troca_vertical(vertical_atual: str, t: str):
    """Detecta pedido explícito de troca de vertical sem falsos positivos."""
    if vertical_atual == "locadora":
        if any(p in t for p in PADROES_TROCA_RESTAURANTE):
            return "restaurante"
        return None
    if vertical_atual == "restaurante":
        if any(p in t for p in PADROES_LOCADORA) and not any(p in t for p in PADROES_TROCA_RESTAURANTE):
            return "locadora"
        return None
    if vertical_atual == "suporte":
        if any(p in t for p in ("cadastrar meu", "quero cadastrar", "cadastrar restaurante")):
            return "restaurante"
        if any(p in t for p in ("quero alugar", "alugar uma moto", "alugar moto")):
            return "locadora"
        return None
    return None


def _detectar_escolha_menu(mensagem: str, t: str):
    """Reconhece '1', '2', '3', variações ('1.', 'a 2', 'op 3'), emojis e escrita preguiçosa."""
    bruto = mensagem or ""
    if "🏍" in bruto:
        return "locadora"
    if "🍽" in bruto:
        return "restaurante"
    if "💬" in bruto:
        return "suporte"

    limpo = re.sub(r"[^\w\s]", " ", t or "").strip()
    limpo = re.sub(r"\s+", " ", limpo)

    if re.match(r"^(?:a |o |op |opcao |numero |num |n |quero |quero a )?(1|um)$", limpo):
        return "locadora"
    if re.match(r"^(?:a |o |op |opcao |numero |num |quero |quero a )?(2|dois)$", limpo):
        return "restaurante"
    if re.match(r"^(?:a |o |op |opcao |numero |num |quero |quero a )?(3|tres)$", limpo):
        return "suporte"

    # Radicais e erros comuns de digitação na escolha do menu
    if re.search(r"\b(cadastr\w*|cadatr\w*|rest\w*|lanch\w*|pizz\w*|hamburg\w*|padar\w*|loja|comercio|parceir\w*)\b", limpo):
        if not any(p in limpo for p in PADROES_LOCADORA):
            return "restaurante"
    if re.search(r"\b(alug\w*|loca\w*|mot\w*|mto)\b", limpo):
        return "locadora"
    if re.search(r"\b(suport\w*|duv\w*|atend\w*|ajud\w*|human\w*)\b", limpo) or "fala c " in limpo or "falar c " in limpo:
        return "suporte"

    return _detectar_vertical(t)


def _plano_citado(t: str):
    """Plano nomeado na mensagem de entrada, para a saudação reconhecer."""
    if "anual" in t or "plano de 29" in t or "29/dia" in t or "29 por dia" in t:
        return "anual"
    if "flexivel" in t or "plano de 35" in t or "35/dia" in t or "35 por dia" in t:
        return "flexivel"
    return None


# --- Dúvidas (interrompem o fluxo e depois ele retoma) ----------------------

RE_PRECO = re.compile(r"\b(preco|precos|quanto|qto|qnt|qnto|valor|valores|custa|diaria|diarias)\b")


def _responder_duvida(t: str):
    """Resposta para dúvida avulsa da locadora, ou None se não for dúvida.

    A ordem importa: caução casa com "valor", então vem antes de preço.
    """
    if any(p in t for p in ("caucao", "cnh", "habilitacao", "documento", "documentos",
                            "idade", "comprovante", "requisito", "requisitos", "exige")):
        return RESP_ATENDENTE

    if any(p in t for p in ("quando chega", "quando vai chegar", "quando tem", "que dia",
                            "qual data", "prazo", "previsao", "quando exatamente",
                            "qnd chega", "qndo chega", "qnd vai", "qnd tem")):
        return RESP_PRAZO

    if any(p in t for p in ("reservar", "reserva", "garantir", "separar uma", "guardar uma")):
        return RESP_RESERVA

    if _buscar_modelo(t) or any(p in t for p in ("modelo", "modelos", "qual moto", "que moto")):
        return RESP_MODELO

    # Sem exigir o preço junto: o cliente costuma escrever só "quero o plano
    # anual" ou "quero o plano de 29".
    if "plano anual" in t or ("anual" in t and "plano" in t) or "plano de 29" in t or "29 reais" in t:
        return RESP_ANUAL

    if "flexivel" in t or "plano de 35" in t or "35 reais" in t:
        return RESP_FLEXIVEL

    if RE_PRECO.search(t):
        return RESP_PRECO

    return None


def _responder_duvida_restaurante(t: str):
    """Resposta para dúvidas comuns durante o cadastro de restaurante."""
    if any(p in t for p in ("taxa", "adesao", "comissao", "mensalidade", "custo",
                            "quanto cobra", "quanto custa", "valor da entrega",
                            "valor entrega", "gratis", "gratuito", "pago", "pagar")):
        return RESP_DUVIDA_RESTAURANTE
    return None


# --- SIM / NÃO --------------------------------------------------------------
#
# Fronteira de palavra é obrigatória. A versão anterior testava "no" como
# substring e casava com "novo", "nome", "menos" — por isso "quando chega o
# lote novo?" era lido como recusa e derrubava a sessão.
#
# "obrigado" fica de fora do RE_NAO: sozinho ele é ambíguo e transformaria
# "sim, obrigado" em recusa. A forma negativa já está em FRASES_NAO.

RE_SIM = re.compile(r"\b(si+m+|s+|claro|quero|qro|aceito|aceita|pode|pd|pdc|bora|ok+|isso|positivo|manda|vamos|topo|fechou)\b")
RE_NAO = re.compile(r"\b(na+o+|n+|nem|dispenso|negativo)\b")

FRASES_INDECISO = (
    "nao sei", "n sei", "nn sei", "ainda nao sei", "nao tenho certeza",
    "vou pensar", "talvez", "sei la", "sl", "sla",
)
FRASES_SIM = ("pode colocar", "pode me colocar", "pode por", "entrar na lista",
              "quero entrar", "me adiciona", "coloca eu", "quero sim", "pode sim", "manda ver")
FRASES_NAO = ("nao quero", "n quero", "nn quero", "nao obrigado", "nao obg", "n obg",
              "sem interesse", "agora nao", "agora n", "hj n", "hoje nao",
              "nao precisa", "n precisa", "ja tenho", "deixa pra la", "outra hora")

DESPEDIDAS = {
    "ok", "okk", "blz", "beleza", "obrigado", "obrigada", "obg", "valeu", "vlw",
    "tchau", "ate", "ate mais", "flw", "ta bom", "certo", "combinado",
    "show", "tranquilo", "de boa",
}


def _intencao(t: str, mensagem: str = ""):
    """'sim', 'nao' ou None. Aceita abreviações ('ss', 'nn', 'qro', 'pd') e emojis."""
    if "👎" in (mensagem or "") or "👎" in (t or ""):
        return "nao"
    if "👍" in (mensagem or "") or "👍" in (t or ""):
        return "sim"
    if any(f in t for f in FRASES_INDECISO):
        return None
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
PREFIXOS_LOCAL = (
    "sou motoboy em ", "trabalho em ", "moro em ", "moro no ", "moro na ",
    "sou de ", "sou da ", "sou do ", "fico em ", "estou em ",
    "cidade de ", "cidade ", "no bairro ", "na bairro ", "bairro ",
)
PALAVRAS_NAO_NOME = {
    "quero", "plano", "preciso", "gostaria", "valor", "quanto",
    "qual", "como", "tem", "onde", "quando", "alugar", "cadastrar",
}

# No WhatsApp as pessoas mandam em rajada ("Ei", "Oiii", "tudo bem?"). Sem isto
# cada saudação era consumida como resposta da pergunta da vez, e já gravou
# nome="Oiii" e cidade="Olá".
SAUDACOES = {
    "oi", "oii", "oiii", "oie", "ola", "ei", "eai", "e ai", "opa", "alo",
    "bom dia", "boa tarde", "boa noite", "tudo bem", "tudo bom", "blz",
    "beleza", "salve", "fala", "ok", "boa",
}


def _extrair_nome(mensagem: str, t: str, permitir_estabelecimento: bool = False):
    """Nome limpo, ou None se a mensagem claramente não for um nome."""
    if "?" in mensagem or t in SAUDACOES or _responder_duvida(t):
        return None
    # Se o cliente mandou "Gabriel, trabalho com delivery", extrai só o nome antes da vírgula
    bruto = (mensagem or "").strip()
    if "," in bruto and not permitir_estabelecimento:
        candidato = bruto.split(",", 1)[0].strip()
        if candidato:
            bruto = candidato
            t = _normalizar(bruto)
    if not permitir_estabelecimento and _detectar_vertical(t):
        return None
    limpo = bruto
    baixo = _normalizar(limpo)
    for p in PREFIXOS_NOME:
        if baixo.startswith(p):
            limpo = limpo[len(p):].strip()
            baixo = _normalizar(limpo)
            break
    limpo = limpo.strip(".,!;:")
    if not limpo or len(limpo) > 40 or len(limpo.split()) > 5:
        return None
    # Nomes pessoais não contêm dígitos nem começam com verbos de pedido
    if re.search(r"\d", limpo):
        return None
    primeira = _normalizar(limpo.split()[0])
    if primeira in PALAVRAS_NAO_NOME:
        return None
    return limpo


def _extrair_local(mensagem: str, t: str):
    """Cidade/bairro limpos, ou None quando a mensagem é saudação ou pergunta."""
    if "?" in mensagem or t in SAUDACOES:
        return None
    limpo = (mensagem or "").strip().strip(".,!;:")
    baixo = _normalizar(limpo)
    for p in PREFIXOS_LOCAL:
        if baixo.startswith(p):
            limpo = limpo[len(p):].strip()
            baixo = _normalizar(limpo)
            break
    limpo = limpo.strip(".,!;:")
    if not limpo or len(limpo) > 60:
        return None
    return limpo


def _separar_cidade_bairro(local: str):
    """Separa 'Cidade, Bairro', 'Cidade - Bairro' ou 'Cidade / Bairro'."""
    for sep in (",", " - ", " / ", "|"):
        if sep in local:
            partes = [p.strip() for p in local.split(sep, 1)]
            if len(partes) == 2 and partes[0] and partes[1]:
                return partes[0], partes[1]
    return local, ""


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
    if etapa == "restaurante":
        return "Qual é o seu *nome*?"
    if etapa == "restaurante_cidade":
        return "De qual *cidade* é o seu restaurante?"
    if etapa == "restaurante_bairro":
        return "Em qual *bairro* fica o seu restaurante?"
    return "Como posso te ajudar?"


def _bloco_registro(sessao, telefone):
    registro = {
        "vertical": sessao.get("vertical") or "locadora",
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
    mensagem = (mensagem or "").strip()
    if not mensagem:
        return ""
    t = _normalizar(mensagem)

    # Comando utilitário para reiniciar a sessão durante testes no WhatsApp
    if t in ("#reset", "/reset"):
        clear_session(telefone)
        return "🔄 Sessão reiniciada! Pode mandar uma nova mensagem para começar do zero."

    sessao = get_session(telefone) or {}

    # Se o cliente mudar explicitamente de assunto, troca de fluxo sem manter
    # cidade/bairro/plano do atendimento anterior. Usa regras estritas para não
    # confundir motoboy/entregador com dono de restaurante.
    vertical_atual = sessao.get("vertical")
    troca = _detectar_troca_vertical(vertical_atual, t)
    if troca == "restaurante":
        sessao = {}
        _atualizar(telefone, sessao, vertical="restaurante", etapa="restaurante")
        return RESTAURANTE_ATENDENTE
    if troca == "locadora":
        sessao = {}
        plano = _plano_citado(t)
        _atualizar(telefone, sessao, vertical="locadora", etapa="nome", plano=plano)
        return _saudacao_locadora(plano)

    # 1. Primeiro contato: detecta vertical ou apresenta menu.
    #    A mensagem de entrada nunca vira nome — era ela que gravava
    #    todo lead vindo do site como "Quero".
    if not sessao.get("etapa"):
        vertical = _detectar_vertical(t)
        if vertical == "restaurante":
            _atualizar(telefone, sessao, vertical="restaurante", etapa="restaurante")
            return RESTAURANTE_ATENDENTE
        if vertical == "suporte":
            _atualizar(telefone, sessao, vertical="suporte", etapa="suporte_assunto")
            return SUPORTE_INICIO
        if vertical is None:
            _atualizar(telefone, sessao, etapa="escolher")
            return BOAS_VINDAS
        if _na_lista(telefone):
            _atualizar(telefone, sessao, vertical="locadora", etapa="cadastrado")
            return JA_CADASTRADO_OI
        plano = _plano_citado(t)
        _atualizar(telefone, sessao, vertical="locadora", etapa="nome", plano=plano)
        return _saudacao_locadora(plano)

    # 2. Escolha de negócio pendente (aceita 1, 2, 3, emojis ou texto).
    if sessao.get("etapa") == "escolher":
        vertical = _detectar_escolha_menu(mensagem, t)
        if vertical == "restaurante":
            _atualizar(telefone, sessao, vertical="restaurante", etapa="restaurante")
            return RESTAURANTE_ATENDENTE
        if vertical == "suporte":
            _atualizar(telefone, sessao, vertical="suporte", etapa="suporte_assunto")
            return SUPORTE_INICIO
        if vertical == "locadora":
            if _na_lista(telefone):
                _atualizar(telefone, sessao, vertical="locadora", etapa="cadastrado")
                return JA_CADASTRADO
            _atualizar(telefone, sessao, vertical="locadora", etapa="nome",
                       plano=_plano_citado(t))
            return ESCOLHEU_LOCADORA
        return REDIRECIONA

    # 2b. Fluxo de dúvidas / suporte: tenta responder dúvida conhecida ou encaminha ao humano.
    if sessao.get("etapa") == "suporte_assunto":
        if t in SAUDACOES:
            return "Pode mandar sua dúvida por aqui 😊 Como posso te ajudar?"
        duvida_loc = _responder_duvida(t)
        if duvida_loc:
            return duvida_loc + "\n\nSe precisar de mais alguma coisa ou quiser falar com um atendente, é só me escrever aqui 😊"
        duvida_rest = _responder_duvida_restaurante(t)
        if duvida_rest:
            return duvida_rest + "\n\nSe precisar falar com um atendente, é só me escrever aqui 😊"
        sessao = _atualizar(telefone, sessao, nome_usuario=nome or sessao.get("nome_usuario"), etapa="suporte_transferido", avisado=True)
        _adicionar_suporte(telefone, mensagem, nome=nome or "")
        return _com_registro(SUPORTE_TRANSFERIDO, sessao, telefone)

    if sessao.get("etapa") == "suporte_transferido":
        return ""

    # 3. Fluxo do restaurante: coleta nome, cidade e bairro, persiste e transfere.
    if sessao.get("etapa") in ("restaurante", "restaurante_cidade", "restaurante_bairro"):
        if sessao.get("avisado"):
            return ""
        duvida_rest = _responder_duvida_restaurante(t)
        if duvida_rest:
            return _com_registro(duvida_rest + "\n\n" + _pergunta_atual(sessao), sessao, telefone)
        if sessao.get("etapa") == "restaurante":
            valor = _extrair_nome(mensagem, t, permitir_estabelecimento=True)
            if not valor:
                return "Não peguei 😅 Qual é o seu *nome*?"
            sessao = _atualizar(telefone, sessao, nome_usuario=valor, etapa="restaurante_cidade")
            return _com_registro(RESTAURANTE_PEDE_CIDADE, sessao, telefone)
        if sessao.get("etapa") == "restaurante_cidade":
            local = _extrair_local(mensagem, t)
            if not local:
                return _com_registro("Não peguei 😅 De qual *cidade* é o seu restaurante?", sessao, telefone)
            cidade, bairro = _separar_cidade_bairro(local)
            if bairro:
                sessao = _atualizar(telefone, sessao, cidade=cidade, bairro=bairro, etapa="restaurante_transferido", avisado=True)
                _adicionar_restaurante(telefone, sessao.get("nome_usuario", ""), cidade, bairro)
                return _com_registro(RESTAURANTE_BAIRRO_EM_ANALISE, sessao, telefone)
            sessao = _atualizar(telefone, sessao, cidade=cidade, etapa="restaurante_bairro")
            return _com_registro(RESTAURANTE_PEDE_BAIRRO, sessao, telefone)
        local = _extrair_local(mensagem, t)
        if not local:
            return _com_registro("Não peguei 😅 Em qual *bairro* fica o seu restaurante?", sessao, telefone)
        sessao = _atualizar(telefone, sessao, bairro=local, etapa="restaurante_transferido", avisado=True)
        _adicionar_restaurante(telefone, sessao.get("nome_usuario", ""), sessao.get("cidade", ""), local)
        return _com_registro(RESTAURANTE_BAIRRO_EM_ANALISE, sessao, telefone)

    if sessao.get("etapa") == "restaurante_transferido":
        return ""

    # 4. Já resolvidos. Dúvida sempre tem resposta, mas o aviso de estado é
    #    dito UMA vez: repetir a cada mensagem atrapalha o atendente humano
    #    que assumiu a conversa, e é o que fazia o bot papagaiar sem parar.
    if sessao.get("etapa") in ("cadastrado", "recusou"):
        duvida = _responder_duvida(t)
        if duvida:
            return duvida
        if sessao.get("etapa") == "recusou" and _quer_voltar(t):
            return _finalizar_lista(sessao, telefone)
        if sessao.get("etapa") == "recusou" and t in DESPEDIDAS:
            return ""
        if sessao.get("avisado"):
            return ""
        _atualizar(telefone, sessao, avisado=True)
        if sessao.get("etapa") == "cadastrado":
            return JA_CADASTRADO
        return CHAMA_ATENDENTE

    # 5. Dúvida no meio do fluxo da locadora: responde e retoma de onde parou.
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
        cidade, bairro = _separar_cidade_bairro(local)
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
        intencao = _intencao(t, mensagem)
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
