"""Ouvinte de eventos do Waha via WebSocket — usado para depuração."""
import asyncio
import json
import os
import sys
import time

import websockets

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env():
    env = {}
    path = os.path.join(BASE, ".env")
    with open(path, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _url_ws():
    env = _env()
    base = env.get("WAHA_URL", "").replace("https://", "wss://").replace("http://", "ws://")
    return f"{base}/ws?session=*&events=message,session.status&token={env.get('WAHA_API_KEY', '')}"


async def main(duracao):
    env = _env()
    url = _url_ws()
    cab = {"X-Api-Key": env.get("WAHA_API_KEY", "")}
    print(f"Conectando em {url}", flush=True)
    fim = time.time() + duracao
    try:
        async with websockets.connect(url, additional_headers=cab, open_timeout=15) as ws:
            print("CONECTADO ao stream de eventos", flush=True)
            while time.time() < fim:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=max(1, fim - time.time()))
                    try:
                        d = json.loads(msg)
                        p = d.get("payload", {})
                        print(
                            f"EVENTO {d.get('event')} session={d.get('session')} "
                            f"from={p.get('from')} fromMe={p.get('fromMe')} "
                            f"type={p.get('type')} body={str(p.get('body') or p.get('text'))[:60]!r}",
                            flush=True,
                        )
                    except Exception:
                        print("EVENTO (bruto):", msg[:200], flush=True)
                except asyncio.TimeoutError:
                    print(".", end="", flush=True)
    except Exception as e:
        print("ERRO no websocket:", e, flush=True)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 180))