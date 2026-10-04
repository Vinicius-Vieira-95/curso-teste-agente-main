"""Demonstração do vídeo 2.3: provocar o erro 429 e depois se defender dele.

Uso:
    python scripts/provocar_429.py ingenuo      # dispara chamadas sem proteção (vai dar 429)
    python scripts/provocar_429.py resiliente   # mesmas chamadas com limitador + retry

Atenção: gasta cota de verdade. Use com --n pequeno (padrão: 20 chamadas).
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openai import OpenAI  # noqa: E402

from agente.config import carregar_configuracao  # noqa: E402
from agente.resiliencia import CotaEsgotadaError, LimitadorDeTaxa, com_retry  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("modo", choices=["ingenuo", "resiliente"])
parser.add_argument("--n", type=int, default=20, help="quantidade de chamadas")
args = parser.parse_args()

cfg = carregar_configuracao()
cliente = OpenAI(api_key=cfg.openai_api_key, max_retries=0)  # retry fica com o com_retry do curso


def chamar(i: int) -> str:
    r = cliente.chat.completions.create(
        model=cfg.modelo_agente,
        messages=[{"role": "user", "content": f"Responda só com o número {i}."}],
    )
    return r.choices[0].message.content.strip()


if args.modo == "resiliente":
    limitador = LimitadorDeTaxa(cfg.requisicoes_por_minuto)
    chamar_com_retry = com_retry(max_tentativas=cfg.max_tentativas)(chamar)

    def chamar_protegido(i: int) -> str:
        limitador.aguardar_vez()
        return chamar_com_retry(i)
else:
    chamar_protegido = chamar

inicio = time.monotonic()
ok = falhas = 0
for i in range(1, args.n + 1):
    t = time.monotonic() - inicio
    try:
        resposta = chamar_protegido(i)
        ok += 1
        print(f"[{t:6.1f}s] #{i:02d} ✅ {resposta}")
    except CotaEsgotadaError as erro:
        falhas += 1
        print(f"[{t:6.1f}s] #{i:02d} ⛔ {erro}")
        break
    except Exception as erro:  # noqa: BLE001
        falhas += 1
        codigo = getattr(erro, "status_code", getattr(erro, "code", "?"))
        print(f"[{t:6.1f}s] #{i:02d} ❌ {codigo} {str(erro)[:90]}")

print(f"\nTotal: {ok} ok, {falhas} falhas em {time.monotonic() - inicio:.1f}s")
