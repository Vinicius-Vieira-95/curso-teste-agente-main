"""Métricas customizadas com G-Eval: o critério é escrito em linguagem natural.

G-Eval funciona em 2 etapas:
  1. a partir do `criteria`, o juiz gera passos de avaliação (ou usamos os nossos
     `evaluation_steps`, mais estáveis);
  2. o juiz aplica esses passos ao caso de teste e devolve uma nota de 0 a 1.
"""
import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.test_case import LLMTestCase, SingleTurnParams as P


def metrica_correcao(juiz):
    """Compara a resposta com o gabarito (expected_output)."""
    return GEval(
        name="Correção",
        criteria="Verifique se a resposta real está factualmente de acordo com a resposta esperada.",
        evaluation_params=[P.INPUT, P.ACTUAL_OUTPUT, P.EXPECTED_OUTPUT],
        threshold=0.7,
        model=juiz,
        async_mode=False,
    )


def metrica_nao_inventa(juiz):
    """Honestidade: sem informação no contexto, o agente deve admitir."""
    return GEval(
        name="Não Inventa",
        evaluation_steps=[
            "Leia o contexto recuperado e a pergunta.",
            "Se o contexto NÃO contém a resposta, a resposta real deve dizer que não tem a informação.",
            "Penalize fortemente qualquer dado (número, data, nome) que não esteja no contexto.",
            "Se o contexto contém a resposta, verifique se a resposta real a usa corretamente.",
        ],
        evaluation_params=[P.INPUT, P.ACTUAL_OUTPUT, P.RETRIEVAL_CONTEXT],
        threshold=0.7,
        model=juiz,
        async_mode=False,
    )


def metrica_clareza_para_calouro(juiz):
    """Critério de 'estilo': algo que um assert clássico nunca conseguiria medir."""
    return GEval(
        name="Clareza para Calouro",
        evaluation_steps=[
            "A resposta está em português e responde diretamente à pergunta na primeira frase?",
            "Evita jargões administrativos sem explicação?",
            "Tem no máximo 3 frases?",
        ],
        evaluation_params=[P.INPUT, P.ACTUAL_OUTPUT],
        threshold=0.6,
        model=juiz,
        async_mode=False,
    )


@pytest.mark.llm
def test_correcao_com_gabarito(agente, juiz):
    pergunta = "Com qual média eu sou aprovado direto?"
    resposta = agente.responder(pergunta)
    caso = LLMTestCase(input=pergunta, actual_output=resposta.texto,
                       expected_output="A média para aprovação direta é 7,0.")
    assert_test(caso, [metrica_correcao(juiz), metrica_clareza_para_calouro(juiz)])


@pytest.mark.llm
def test_nao_inventa_quando_nao_sabe(agente, juiz):
    pergunta = "Qual o valor da mensalidade do curso?"
    resposta = agente.responder(pergunta)
    caso = LLMTestCase(input=pergunta, actual_output=resposta.texto,
                       retrieval_context=resposta.contexto or ["(nenhum documento encontrado)"])
    assert_test(caso, [metrica_nao_inventa(juiz)])


@pytest.mark.llm
def test_metrica_detecta_resposta_inventada(juiz):
    """Teste DA MÉTRICA: uma resposta alucinada precisa tirar nota baixa.

    Se este teste passar a falhar, o problema está no critério, não no agente.
    """
    caso = LLMTestCase(
        input="Qual o valor da mensalidade do curso?",
        actual_output="A mensalidade é de R$ 850,00, com desconto de 10% à vista.",
        retrieval_context=["A frequência mínima exigida em cada disciplina é de 75% das aulas."],
    )
    metrica = metrica_nao_inventa(juiz)
    metrica.measure(caso)
    print(f"nota={metrica.score:.2f} motivo={metrica.reason}")
    assert metrica.score < metrica.threshold


def metrica_clareza_rubrica(juiz):
    """Clareza com rubrica: faixas de nota descritas explicitamente para o juiz.

    O threshold foi calibrado com scripts/calibrar_clareza.py (meio do vão
    entre a pior nota dos casos bons e a melhor nota dos casos ruins).
    """
    return GEval(
        name="Clareza (rubrica)",
        criteria="Avalie se um calouro entenderia a resposta sem ajuda.",
        evaluation_params=[P.INPUT, P.ACTUAL_OUTPUT],
        rubric=[
            Rubric(score_range=(0, 3), expected_outcome="Confusa, com jargão ou sem responder."),
            Rubric(score_range=(4, 7), expected_outcome="Responde, mas é longa ou tem termos técnicos."),
            Rubric(score_range=(8, 10), expected_outcome="Direta, curta e sem jargão."),
        ],
        threshold=0.75,  # calibrado: pior bom = 0.90, melhor ruim = 0.60
        model=juiz,
        async_mode=False,
    )


@pytest.mark.llm
def test_clareza_aprova_resposta_clara(juiz):
    caso = LLMTestCase(
        input="Com qual média eu sou aprovado direto?",
        actual_output="Você é aprovado direto com média 7,0 ou mais.",
    )
    assert_test(caso, [metrica_clareza_rubrica(juiz)])


@pytest.mark.llm
def test_metrica_clareza_detecta_juridiques(juiz):
    """Teste DA MÉTRICA: uma resposta cheia de 'juridiquês' precisa tirar nota baixa."""
    caso = LLMTestCase(
        input="Com qual média eu sou aprovado direto?",
        actual_output=(
            "Nos termos do art. 42, §2º, do Regimento Geral, c/c a Resolução CONSEPE nº 17/2019, "
            "fica dispensado da verificação suplementar de aproveitamento o discente cujo "
            "coeficiente de rendimento parcial, apurado na forma do inciso III, perfaça "
            "quantitativo igual ou superior ao mínimo regimentalmente estabelecido, "
            "ressalvadas as hipóteses de trancamento e as disposições transitórias aplicáveis."
        ),
    )
    metrica = metrica_clareza_rubrica(juiz)
    metrica.measure(caso)
    print(f"nota={metrica.score:.2f} motivo={metrica.reason}")
    assert metrica.score < metrica.threshold
