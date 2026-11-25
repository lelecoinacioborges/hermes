#!/bin/sh
set -e

# ── Integração Zupoo Locadora (Agente de Atendimento Webhook) ────────────────
ZUPOO_APP_DIR="/opt/zupoo-locadora-agente"
ZUPOO_SEED_DATA="${ZUPOO_APP_DIR}/data-seed"
ZUPOO_PERSIST_DIR="${HERMES_HOME:-/home/hermes/.hermes}/zupoo-locadora-agente"

mkdir -p "${ZUPOO_PERSIST_DIR}/data" "${ZUPOO_PERSIST_DIR}/logs"

# Copia catálogo/políticas iniciais na primeira subida sem sobrescrever dados persistidos
if [ -d "${ZUPOO_SEED_DATA}" ]; then
    for arquivo in "${ZUPOO_SEED_DATA}"/*; do
        [ -e "${arquivo}" ] || continue
        nome="$(basename "${arquivo}")"
        if [ ! -e "${ZUPOO_PERSIST_DIR}/data/${nome}" ]; then
            cp -a "${arquivo}" "${ZUPOO_PERSIST_DIR}/data/${nome}"
        fi
    done
fi

# Garante que data/ e logs/ do agente apontem para o volume persistente do Hermes
rm -rf "${ZUPOO_APP_DIR}/data" "${ZUPOO_APP_DIR}/logs"
ln -s "${ZUPOO_PERSIST_DIR}/data" "${ZUPOO_APP_DIR}/data"
ln -s "${ZUPOO_PERSIST_DIR}/logs" "${ZUPOO_APP_DIR}/logs"

# Ajusta dono para o mesmo UID/GID usado pelo Hermes
chown -R "${HERMES_UID:-1000}:${HERMES_GID:-1000}" "${ZUPOO_PERSIST_DIR}" 2>/dev/null || true

# Seleciona o Python disponível no container
if [ -x "${HERMES_PYTHON:-/opt/hermes/.venv/bin/python}" ]; then
    ZUPOO_PYTHON="${HERMES_PYTHON:-/opt/hermes/.venv/bin/python}"
else
    ZUPOO_PYTHON="python3"
fi

# Inicia o servidor webhook em background com reinício automático em caso de falha
(
    while true; do
        echo "[zupoo-agente] Iniciando servidor webhook na porta ${ZUPOO_WEBHOOK_PORT:-8081}..."
        "${ZUPOO_PYTHON}" -u "${ZUPOO_APP_DIR}/src/servidor.py"
        EXIT_CODE=$?
        echo "[zupoo-agente] Servidor encerrado (código ${EXIT_CODE}). Reiniciando em 2s..."
        sleep 2
    done
) &

# Delega a execução principal para o entrypoint oficial do Hermes
exec /opt/hermes/docker/entrypoint-dispatch.sh "$@"
