#!/bin/sh
set -e

PERSIST_DIR="${ZUPOO_PERSIST_DIR:-/hermes-data/zupoo-locadora-agente}"

mkdir -p "${PERSIST_DIR}/data" "${PERSIST_DIR}/logs"

# Copia catálogo/políticas iniciais na primeira subida sem sobrescrever dados persistidos
if [ -d /app/data-seed ]; then
    for arquivo in /app/data-seed/*; do
        [ -e "${arquivo}" ] || continue
        nome="$(basename "${arquivo}")"
        if [ ! -e "${PERSIST_DIR}/data/${nome}" ]; then
            cp -a "${arquivo}" "${PERSIST_DIR}/data/${nome}"
        fi
    done
fi

rm -rf /app/data /app/logs
ln -s "${PERSIST_DIR}/data" /app/data
ln -s "${PERSIST_DIR}/logs" /app/logs

exec python3 -u /app/src/servidor.py
