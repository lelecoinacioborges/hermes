"""Consulta a lista de espera de leads (data/lista_espera.json)."""
import json
import os

CAMINHO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lista_espera.json")


def listar():
    if not os.path.exists(CAMINHO):
        print("Lista de espera vazia (arquivo ainda não existe).")
        return
    with open(CAMINHO, encoding="utf-8") as f:
        lista = json.load(f)
    print(f"Total na lista de espera: {len(lista)}\n")
    for i, e in enumerate(lista, 1):
        print(f"{i:>2}. {e.get('nome', '—')} | {e.get('telefone', '—')} | {e.get('data', '—')}")


if __name__ == "__main__":
    listar()