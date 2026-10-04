"""Testes clássicos (determinísticos) das ferramentas: entrada X -> saída exatamente Y."""
import pytest

from agente.ferramentas import calcular_media, consultar_calendario


@pytest.mark.parametrize("notas, media, situacao", [
    ([8, 9, 10], 9.0, "aprovado"),
    ([7, 7, 7], 7.0, "aprovado"),          # limite exato: 7,0 aprova
    ([6.9, 6.9, 6.9], 6.9, "prova final"),
    ([4, 4], 4.0, "prova final"),          # limite exato: 4,0 vai para final
    ([3.9, 3.9], 3.9, "reprovado"),
])
def test_calcular_media(notas, media, situacao):
    resultado = calcular_media(notas)
    assert resultado == {"media": media, "situacao": situacao}


@pytest.mark.parametrize("notas", [[], [11], [-1, 5]])
def test_calcular_media_rejeita_entrada_invalida(notas):
    with pytest.raises(ValueError):
        calcular_media(notas)


def test_consultar_calendario_evento_existente():
    assert consultar_calendario("prova_final") == {"evento": "prova_final", "data": "03/07/2026"}


def test_consultar_calendario_evento_inexistente():
    assert "erro" in consultar_calendario("ferias")
