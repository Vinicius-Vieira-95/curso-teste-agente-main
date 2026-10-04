"""Configuração compartilhada dos testes.

Testes marcados com @pytest.mark.llm chamam a API de verdade.
Se não houver chave configurada (ex.: PR de um fork no GitHub),
eles são PULADOS em vez de falharem.
"""
import pytest

from agente.config import chave_configurada


def pytest_collection_modifyitems(config, items):
    if chave_configurada():
        return
    pular = pytest.mark.skip(reason="OPENAI_API_KEY ausente — teste com LLM pulado")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(pular)


@pytest.fixture(scope="session")
def agente():
    from agente.agente import Agente
    return Agente()


@pytest.fixture(scope="session")
def juiz():
    from agente.juiz import criar_juiz
    return criar_juiz()
