"""Testes com LLM-as-a-judge: Relevância e Fidelidade (métricas prontas do DeepEval)."""
import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

PERGUNTAS = [
    "Qual a frequência mínima exigida nas disciplinas?",
    "Quantas horas de atividades complementares preciso fazer?",
]


@pytest.mark.llm
@pytest.mark.parametrize("pergunta", PERGUNTAS)
def test_resposta_relevante_e_fiel(agente, juiz, pergunta):
    resposta = agente.responder(pergunta)
    caso = LLMTestCase(
        input=pergunta,
        actual_output=resposta.texto,
        retrieval_context=resposta.contexto,
    )
    assert_test(caso, [
        AnswerRelevancyMetric(threshold=0.7, model=juiz, async_mode=False),
        FaithfulnessMetric(threshold=0.7, model=juiz, async_mode=False),
    ])
