"""Teste de sanidade do repositório: roda em segundos, sem internet, sem chave.

Se algum destes falhar, NADA mais vai funcionar — conserte primeiro.
"""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def test_pacote_do_agente_importa():
    import agente.agente  # noqa: F401
    import agente.ferramentas  # noqa: F401
    import agente.resiliencia  # noqa: F401


def test_bibliotecas_instaladas():
    import deepeval  # noqa: F401
    import openai  # noqa: F401


def test_env_example_tem_as_variaveis_obrigatorias():
    conteudo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    for variavel in ["OPENAI_API_KEY", "MODELO_AGENTE", "MODELO_JUIZ"]:
        assert variavel in conteudo


def test_env_esta_no_gitignore():
    linhas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in linhas, "O .env PRECISA estar no .gitignore para a chave não vazar!"


def test_config_reclama_quando_chave_falta(monkeypatch):
    from agente.config import ConfiguracaoInvalidaError, carregar_configuracao
    monkeypatch.setenv("OPENAI_API_KEY", "cole-sua-chave-aqui")
    with pytest.raises(ConfiguracaoInvalidaError):
        carregar_configuracao()
