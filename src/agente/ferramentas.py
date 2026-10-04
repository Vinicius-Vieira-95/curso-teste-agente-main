"""Ferramentas (tools) que o agente pode chamar.

São funções Python comuns e 100% determinísticas: a mesma entrada
sempre gera a mesma saída. Por isso são testadas com asserts clássicos
(tests/test_ferramentas.py), sem LLM nenhum.
"""

CALENDARIO = {
    "inicio_aulas": "02/03/2026",
    "fim_semestre": "10/07/2026",
    "prova_final": "03/07/2026",
    "trancamento": "15/04/2026",
}

MEDIA_APROVACAO = 7.0
MEDIA_MINIMA_FINAL = 4.0


def calcular_media(notas: list[float]) -> dict:
    """Calcula a média aritmética das notas e informa a situação do aluno.

    Args:
        notas: lista de notas entre 0 e 10.

    Returns:
        dict com 'media' (arredondada em 2 casas) e 'situacao'
        ('aprovado', 'prova final' ou 'reprovado').
    """
    if not notas:
        raise ValueError("A lista de notas não pode ser vazia.")
    if any(n < 0 or n > 10 for n in notas):
        raise ValueError("Todas as notas devem estar entre 0 e 10.")

    media = round(sum(notas) / len(notas), 2)
    if media >= MEDIA_APROVACAO:
        situacao = "aprovado"
    elif media >= MEDIA_MINIMA_FINAL:
        situacao = "prova final"
    else:
        situacao = "reprovado"
    return {"media": media, "situacao": situacao}


def consultar_calendario(evento: str) -> dict:
    """Consulta a data de um evento do calendário acadêmico.

    Args:
        evento: um de 'inicio_aulas', 'fim_semestre', 'prova_final', 'trancamento'.

    Returns:
        dict com 'evento' e 'data', ou 'erro' se o evento não existir.
    """
    chave = evento.strip().lower()
    if chave not in CALENDARIO:
        return {"erro": f"Evento '{evento}' não encontrado.", "eventos_validos": list(CALENDARIO)}
    return {"evento": chave, "data": CALENDARIO[chave]}


FERRAMENTAS = [calcular_media, consultar_calendario]

# A API da OpenAI (diferente da do Gemini) não lê docstring/type hints para
# descobrir como chamar a ferramenta: precisamos declarar o JSON Schema à mão.
FERRAMENTAS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "calcular_media",
            "description": (
                "Calcula a média aritmética das notas e informa a situação do "
                "aluno ('aprovado', 'prova final' ou 'reprovado')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "notas": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Lista de notas entre 0 e 10.",
                    },
                },
                "required": ["notas"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_calendario",
            "description": "Consulta a data de um evento do calendário acadêmico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "evento": {
                        "type": "string",
                        "description": (
                            "Um de: 'inicio_aulas', 'fim_semestre', 'prova_final', "
                            "'trancamento'."
                        ),
                    },
                },
                "required": ["evento"],
            },
        },
    },
]
