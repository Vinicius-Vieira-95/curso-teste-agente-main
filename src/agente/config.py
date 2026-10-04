"""Leitura centralizada das configurações do arquivo .env.

Regra de ouro: nenhum outro arquivo lê os.environ diretamente.
Assim, se faltar alguma variável, o erro aparece em UM lugar, com mensagem clara.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # procura um arquivo .env na pasta atual (ou acima) e carrega as variáveis

VALOR_DE_EXEMPLO = "cole-sua-chave-aqui"


class ConfiguracaoInvalidaError(RuntimeError):
    """Erro lançado quando o .env está ausente ou incompleto."""


@dataclass(frozen=True)
class Configuracao:
    openai_api_key: str
    modelo_agente: str
    modelo_juiz: str
    max_tentativas: int
    requisicoes_por_minuto: int


def carregar_configuracao() -> Configuracao:
    chave = os.getenv("OPENAI_API_KEY", "").strip()
    if not chave or chave == VALOR_DE_EXEMPLO:
        raise ConfiguracaoInvalidaError(
            "OPENAI_API_KEY não encontrada. Copie .env.example para .env "
            "e cole sua chave da OpenAI (https://platform.openai.com/api-keys)."
        )
    return Configuracao(
        openai_api_key=chave,
        modelo_agente=os.getenv("MODELO_AGENTE", "gpt-5.4-mini"),
        modelo_juiz=os.getenv("MODELO_JUIZ", "gpt-5.4"),
        max_tentativas=int(os.getenv("MAX_TENTATIVAS", "5")),
        requisicoes_por_minuto=int(os.getenv("REQUISICOES_POR_MINUTO", "10")),
    )


def chave_configurada() -> bool:
    """Versão 'silenciosa' usada pelos testes para decidir se pulam ou não."""
    try:
        carregar_configuracao()
        return True
    except ConfiguracaoInvalidaError:
        return False
