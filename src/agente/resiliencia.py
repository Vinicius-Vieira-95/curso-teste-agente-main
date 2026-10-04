"""Resiliência contra erro 429 (Too Many Requests) e falhas temporárias.

Três ideias, da mais simples para a mais robusta:
1. LimitadorDeTaxa  -> evita o 429: espaça as chamadas para caber no limite por minuto.
2. com_retry        -> trata o 429: espera cada vez mais (backoff exponencial + jitter)
                       e tenta de novo, respeitando o tempo sugerido pela API
                       (cabeçalho 'retry-after' na OpenAI).
3. CotaEsgotadaError -> desiste com uma mensagem clara quando não adianta insistir.
                       Na OpenAI, o 429 com código 'insufficient_quota' significa
                       SALDO ZERADO: esperar não resolve, então nem tentamos de novo.

Importante: o SDK da OpenAI também repete o 429 sozinho (max_retries=2 por padrão).
No curso criamos o cliente com max_retries=0 para que ESTA camada faça o trabalho
e o comportamento fique visível e testável.
"""
import functools
import random
import re
import threading
import time

CODIGOS_TEMPORARIOS = {429, 500, 503}  # vale a pena tentar de novo
CODIGOS_PERMANENTES = {400, 401, 403, 404}  # erro nosso: tentar de novo não resolve


CODIGO_SEM_SALDO = "insufficient_quota"  # 429 da OpenAI quando os créditos acabaram


class CotaEsgotadaError(RuntimeError):
    """Lançado quando não adianta mais tentar: saldo zerado ou tentativas esgotadas."""


def sem_saldo(erro: Exception) -> bool:
    """True se o erro é o 429 da OpenAI por falta de créditos (não por excesso de pedidos)."""
    return getattr(erro, "code", None) == CODIGO_SEM_SALDO


def codigo_http(erro: Exception) -> int | None:
    """Extrai o código HTTP do erro, qualquer que seja o SDK.

    O SDK da OpenAI expõe `.status_code` (int). Alguns SDKs (ex.: google-genai)
    expõem `.code` como o próprio status HTTP — mas na OpenAI `.code` é uma
    string do corpo do erro (ex.: 'rate_limit_exceeded'), não o status HTTP.
    Por isso só usamos `.code` quando ele já vem como int.
    """
    codigo = getattr(erro, "code", None)
    if isinstance(codigo, int):
        return codigo
    return getattr(erro, "status_code", None)


def atraso_sugerido(erro: Exception) -> float | None:
    """Quanto tempo a própria API pediu para esperar, se ela disse.

    - OpenAI: cabeçalhos HTTP 'retry-after-ms' (milissegundos) ou 'retry-after' (segundos).
    - Gemini e outras: campo 'retryDelay' (ex.: '37s') no corpo do erro.
    Se nenhuma dica vier, devolve None e usamos o backoff exponencial.
    """
    resposta = getattr(erro, "response", None)
    cabecalhos = getattr(resposta, "headers", None) or {}
    try:
        if cabecalhos.get("retry-after-ms"):
            return float(cabecalhos["retry-after-ms"]) / 1000
        if cabecalhos.get("retry-after"):
            return float(cabecalhos["retry-after"])
    except (TypeError, ValueError):
        pass  # ex.: 'retry-after' em formato de data — ignoramos e usamos o backoff
    texto = str(getattr(erro, "details", "")) + str(erro)
    achado = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", texto)
    return float(achado.group(1)) if achado else None


def calcular_espera(tentativa: int, base: float = 2.0, teto: float = 60.0) -> float:
    """Backoff exponencial com jitter: ~2s, ~4s, ~8s, ... limitado ao teto.

    O jitter (aleatoriedade) evita que vários clientes tentem de novo
    exatamente no mesmo instante e causem outro pico de 429.
    """
    espera = min(teto, base * (2 ** (tentativa - 1)))
    return espera * random.uniform(0.5, 1.0)


def com_retry(max_tentativas: int = 5, base: float = 2.0, teto: float = 60.0,
              dormir=time.sleep):
    """Decorador: repete a função quando a API devolve um erro temporário.

    `dormir` é injetável para que os testes rodem instantaneamente
    (passamos uma função falsa que só registra quanto tempo 'dormiu').
    """
    def decorador(funcao):
        @functools.wraps(funcao)
        def envolvida(*args, **kwargs):
            for tentativa in range(1, max_tentativas + 1):
                try:
                    return funcao(*args, **kwargs)
                except Exception as erro:
                    codigo = codigo_http(erro)
                    if sem_saldo(erro):
                        raise CotaEsgotadaError(
                            "Saldo de créditos da OpenAI zerado (ou limite de gasto atingido). "
                            "Esperar não resolve: adicione créditos em "
                            "platform.openai.com/settings/organization/billing."
                        ) from erro
                    if codigo not in CODIGOS_TEMPORARIOS:
                        raise  # 401, 404, bug no código... não adianta repetir
                    if tentativa == max_tentativas:
                        raise CotaEsgotadaError(
                            f"API continuou respondendo {codigo} após {max_tentativas} "
                            "tentativas. Verifique sua cota em platform.openai.com/usage."
                        ) from erro
                    espera = atraso_sugerido(erro) or calcular_espera(tentativa, base, teto)
                    print(f"[retry] erro {codigo} — tentativa {tentativa}/{max_tentativas}, "
                          f"aguardando {espera:.1f}s")
                    dormir(espera)
        return envolvida
    return decorador


class LimitadorDeTaxa:
    """Garante no máximo N chamadas por minuto (intervalo mínimo entre chamadas).

    Thread-safe, porque o DeepEval pode avaliar métricas em paralelo.
    """

    def __init__(self, requisicoes_por_minuto: int, relogio=time.monotonic,
                 dormir=time.sleep):
        self.intervalo = 60.0 / requisicoes_por_minuto
        self._ultima = None
        self._trava = threading.Lock()
        self._relogio = relogio
        self._dormir = dormir

    def aguardar_vez(self) -> float:
        """Bloqueia até ser permitido fazer a próxima chamada. Retorna quanto esperou."""
        with self._trava:
            agora = self._relogio()
            espera = 0.0
            if self._ultima is not None:
                espera = max(0.0, self._ultima + self.intervalo - agora)
            if espera:
                self._dormir(espera)
            self._ultima = agora + espera
            return espera
