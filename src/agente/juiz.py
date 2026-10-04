"""Cria o modelo 'juiz' usado pelas métricas do DeepEval (LLM-as-a-judge)."""
from agente.config import carregar_configuracao


def criar_juiz():
    from deepeval.models import OpenAIModel

    cfg = carregar_configuracao()
    # temperature=0: queremos o juiz o mais consistente possível entre execuções
    return OpenAIModel(model=cfg.modelo_juiz, api_key=cfg.openai_api_key, temperature=0)
