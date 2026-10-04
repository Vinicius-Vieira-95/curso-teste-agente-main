"""Calibra o threshold da métrica "Clareza (rubrica)".

Roda a métrica em 10 respostas boas e 10 ruins e sugere o threshold no meio
do vão entre a PIOR nota dos bons e a MELHOR nota dos ruins.

Uso (faz ~20 chamadas ao juiz):
    python scripts/calibrar_clareza.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

from deepeval.test_case import LLMTestCase  # noqa: E402

from agente.juiz import criar_juiz  # noqa: E402
from test_geval import metrica_clareza_rubrica  # noqa: E402

BONS = [
    ("Com qual média eu sou aprovado direto?", "Você é aprovado direto com média 7,0 ou mais."),
    ("Qual a frequência mínima?", "Você precisa ir a pelo menos 75% das aulas de cada disciplina."),
    ("Posso trancar a matrícula?", "Pode, sim. É só pedir na secretaria dentro do prazo do calendário."),
    ("Onde vejo minhas notas?", "Suas notas ficam no portal do aluno, na aba 'Boletim'."),
    ("Quantas faltas posso ter?", "Você pode faltar até 25% das aulas de cada disciplina."),
    ("Tem prova de recuperação?", "Tem. Se sua média ficar entre 4,0 e 6,9, você faz a prova final."),
    ("Como peço segunda chamada?", "Faça o pedido na secretaria em até 3 dias depois da prova, com atestado."),
    ("Quando começam as aulas?", "As aulas começam na primeira semana de março."),
    ("Preciso de nota mínima na final?", "Sim. Depois da prova final, sua média precisa ser 5,0 ou mais."),
    ("Posso cursar matéria em outro turno?", "Pode, se tiver vaga. Peça a inclusão na coordenação."),
]

RUINS = [
    ("Com qual média eu sou aprovado direto?",
     "Nos termos do art. 42, §2º, do Regimento Geral, c/c a Resolução CONSEPE nº 17/2019, fica "
     "dispensado da verificação suplementar o discente cujo coeficiente perfaça o mínimo regimental."),
    ("Qual a frequência mínima?",
     "A assiduidade discente submete-se ao quantum percentual preconizado pela normativa "
     "acadêmica vigente, sob pena de reprovação por insuficiência de frequência (RF)."),
    ("Posso trancar a matrícula?",
     "O sobrestamento do vínculo acadêmico é facultado ao requerente, observados os "
     "interstícios do calendário e o disposto no art. 58 do RG, ex vi da Portaria 3/2020."),
    ("Onde vejo minhas notas?",
     "Depende. Há vários sistemas e cada coordenação adota procedimentos próprios, "
     "conforme a legislação e as normas internas aplicáveis a cada caso concreto."),
    ("Quantas faltas posso ter?",
     "O cômputo de ausências obedece ao limite inferior ao complemento do percentual "
     "mínimo de presença exigido, aferido por componente curricular, nos termos regimentais."),
    ("Tem prova de recuperação?",
     "A avaliação substitutiva/suplementar (AS) incide sobre discentes com MP em intervalo "
     "intermediário, consoante a sistemática de verificação de aprendizagem (SVA) vigente."),
    ("Como peço segunda chamada?",
     "Mediante requerimento protocolado tempestivamente, instruído com documentação "
     "comprobatória idônea, à instância competente, que deliberará ad referendum do colegiado."),
    ("Quando começam as aulas?",
     "O calendário acadêmico é homologado pelo Conselho Superior e pode sofrer alterações "
     "supervenientes em razão de deliberações institucionais, recomendando-se consulta."),
    ("Preciso de nota mínima na final?",
     "A aprovação pós-exame final condiciona-se à média ponderada entre a MP e a nota do EF "
     "atingir o patamar regimental, aplicando-se os pesos previstos na resolução pertinente."),
    ("Posso cursar matéria em outro turno?",
     "A matrícula em componente curricular de turno diverso sujeita-se à disponibilidade de "
     "vagas remanescentes e ao deferimento da instância coordenadora, observada a precedência."),
]


def avaliar(metrica, casos):
    notas = []
    for pergunta, resposta in casos:
        metrica.measure(LLMTestCase(input=pergunta, actual_output=resposta))
        notas.append(metrica.score)
        print(f"  {metrica.score:.2f}  {resposta[:70]}")
    return notas


def main():
    metrica = metrica_clareza_rubrica(criar_juiz())
    print("Casos BONS:")
    bons = avaliar(metrica, BONS)
    print("Casos RUINS:")
    ruins = avaliar(metrica, RUINS)

    pior_bom, melhor_ruim = min(bons), max(ruins)
    print(f"\nPior nota dos bons:   {pior_bom:.2f}")
    print(f"Melhor nota dos ruins: {melhor_ruim:.2f}")
    if pior_bom <= melhor_ruim:
        print("⚠️  Os grupos se sobrepõem: ajuste a rubrica/critério antes de escolher o threshold.")
        sys.exit(1)
    print(f"✅ Threshold sugerido (meio do vão): {(pior_bom + melhor_ruim) / 2:.2f}")


if __name__ == "__main__":
    main()
