"""Base de conhecimento estática do agente (um 'RAG' simplificado).

Em produção isso viria de um banco vetorial. Aqui usamos uma busca por
palavra-chave para o curso focar no que importa: TESTAR o agente.
"""

DOCUMENTOS = [
    "O curso de Ciência da Computação tem duração mínima de 8 semestres.",
    "A frequência mínima exigida em cada disciplina é de 75% das aulas.",
    "O aluno pode trancar o semestre até a data de trancamento do calendário acadêmico.",
    "A média para aprovação direta é 7,0. Com média entre 4,0 e 6,9 o aluno faz prova final.",
    "As atividades complementares somam 200 horas obrigatórias para a colação de grau.",
    "O Trabalho de Conclusão de Curso (TCC) é feito nos dois últimos semestres.",
]

STOPWORDS = {"o", "a", "os", "as", "de", "do", "da", "e", "é", "em", "no", "na",
             "um", "uma", "para", "que", "qual", "quais", "quanto", "quantas",
             "quantos", "como", "eu", "meu", "minha", "se", "com", "por"}


def _palavras(texto: str) -> set[str]:
    limpo = "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in texto)
    return {p for p in limpo.split() if p not in STOPWORDS and len(p) > 2}


def buscar_contexto(pergunta: str, k: int = 2) -> list[str]:
    """Retorna os k documentos com mais palavras em comum com a pergunta."""
    termos = _palavras(pergunta)
    pontuados = [(len(termos & _palavras(doc)), doc) for doc in DOCUMENTOS]
    pontuados = [p for p in pontuados if p[0] > 0]
    pontuados.sort(key=lambda p: p[0], reverse=True)
    return [doc for _, doc in pontuados[:k]]
