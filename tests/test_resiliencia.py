"""Testes da camada de resiliência — SEM chamar a API.

Simulamos o erro 429 com uma exceção falsa e trocamos o time.sleep por uma
função que só anota os tempos. Resultado: testes instantâneos e determinísticos.
"""
from types import SimpleNamespace

import pytest

from agente.resiliencia import (CotaEsgotadaError, LimitadorDeTaxa, atraso_sugerido,
                                calcular_espera, com_retry)


class ErroApiFalso(Exception):
    def __init__(self, code, details=""):
        super().__init__(f"{code} erro simulado")
        self.code = code
        self.details = details


def test_repete_ate_dar_certo():
    esperas = []
    tentativas = {"n": 0}

    @com_retry(max_tentativas=5, dormir=esperas.append)
    def chamada_instavel():
        tentativas["n"] += 1
        if tentativas["n"] < 3:
            raise ErroApiFalso(429)
        return "sucesso"

    assert chamada_instavel() == "sucesso"
    assert tentativas["n"] == 3
    assert len(esperas) == 2  # esperou antes da 2ª e da 3ª tentativa


def test_desiste_com_mensagem_clara_quando_cota_acaba():
    @com_retry(max_tentativas=3, dormir=lambda s: None)
    def sempre_429():
        raise ErroApiFalso(429)

    with pytest.raises(CotaEsgotadaError, match="3 tentativas"):
        sempre_429()


def test_nao_repete_erro_de_chave_invalida():
    chamadas = []

    @com_retry(max_tentativas=5, dormir=lambda s: None)
    def chave_errada():
        chamadas.append(1)
        raise ErroApiFalso(401)

    with pytest.raises(ErroApiFalso):
        chave_errada()
    assert len(chamadas) == 1  # 401 não é temporário: tentar de novo é desperdício


def test_respeita_retry_delay_da_api():
    erro = ErroApiFalso(429, details={"retryDelay": "37s"})
    assert atraso_sugerido(erro) == 37.0


@pytest.mark.parametrize("tentativa, maximo", [(1, 2), (2, 4), (3, 8), (10, 60)])
def test_backoff_exponencial_com_teto(tentativa, maximo):
    espera = calcular_espera(tentativa, base=2, teto=60)
    assert maximo / 2 <= espera <= maximo


def test_limitador_espaca_as_chamadas():
    relogio = {"t": 0.0}
    esperas = []

    def dormir(s):
        esperas.append(s)
        relogio["t"] += s

    limitador = LimitadorDeTaxa(30, relogio=lambda: relogio["t"], dormir=dormir)  # 1 a cada 2s
    for _ in range(3):
        limitador.aguardar_vez()
    assert esperas == [2.0, 2.0]


# --- Erros no formato do SDK da OpenAI -------------------------------------------
# A OpenAI usa .status_code (int) para o HTTP, .code (str) para o motivo
# e manda o tempo de espera no cabeçalho 'retry-after' da resposta.

class ErroOpenAIFalso(Exception):
    def __init__(self, status_code, code=None, cabecalhos=None):
        super().__init__(f"Error code: {status_code} - {code}")
        self.status_code = status_code
        self.code = code
        self.response = SimpleNamespace(headers=cabecalhos or {})


def test_sem_saldo_desiste_na_hora_sem_retry():
    chamadas = []

    @com_retry(max_tentativas=5, dormir=lambda s: None)
    def sem_credito():
        chamadas.append(1)
        raise ErroOpenAIFalso(429, code="insufficient_quota")

    with pytest.raises(CotaEsgotadaError, match="créditos"):
        sem_credito()
    assert len(chamadas) == 1  # esperar não traz saldo de volta


def test_rate_limit_da_openai_repete_respeitando_retry_after():
    esperas = []
    tentativas = {"n": 0}

    @com_retry(max_tentativas=5, dormir=esperas.append)
    def instavel():
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            raise ErroOpenAIFalso(429, code="rate_limit_exceeded",
                                  cabecalhos={"retry-after": "3"})
        return "ok"

    assert instavel() == "ok"
    assert esperas == [3.0]


def test_retry_after_ms_tem_prioridade():
    erro = ErroOpenAIFalso(429, cabecalhos={"retry-after-ms": "1500", "retry-after": "2"})
    assert atraso_sugerido(erro) == 1.5
