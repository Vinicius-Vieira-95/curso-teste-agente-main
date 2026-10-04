"""O agente testado no curso: um assistente acadêmico.

Fluxo de uma pergunta:
  1. busca trechos relevantes na base de conhecimento (contexto);
  2. envia pergunta + contexto ao GPT (OpenAI), que PODE chamar ferramentas
     (calcular_media, consultar_calendario);
  3. devolve uma RespostaAgente com tudo o que precisamos para testar:
     texto, contexto usado, ferramentas chamadas e a rota de decisão.
"""
import json
from dataclasses import dataclass, field

from agente.base_conhecimento import buscar_contexto
from agente.config import carregar_configuracao
from agente.ferramentas import FERRAMENTAS, FERRAMENTAS_OPENAI
from agente.resiliencia import LimitadorDeTaxa, com_retry

INSTRUCOES = (
    "Você é o assistente acadêmico do curso de Ciência da Computação. "
    "Responda em português, de forma curta e objetiva. "
    "Use SOMENTE as informações do CONTEXTO ou o resultado das ferramentas. "
    "Para cálculos de média use a ferramenta calcular_media; para datas use "
    "consultar_calendario. Se a informação não estiver disponível, diga "
    "'Não tenho essa informação.' e não invente."
)

# Diferente do Gemini, a OpenAI não devolve um "histórico de function calling"
# pronto: o próprio agente precisa executar a ferramenta e mandar o resultado
# de volta. Por isso precisamos de um mapa nome -> função Python de verdade.
FERRAMENTAS_POR_NOME = {funcao.__name__: funcao for funcao in FERRAMENTAS}

# Evita loop infinito se o modelo insistir em chamar ferramentas sem parar.
MAX_RODADAS_DE_FERRAMENTA = 5


@dataclass
class RespostaAgente:
    pergunta: str
    texto: str
    contexto: list[str] = field(default_factory=list)
    ferramentas_chamadas: list[str] = field(default_factory=list)

    @property
    def rota(self) -> str:
        """Rota de decisão tomada pelo agente — útil para testes de roteamento."""
        if self.ferramentas_chamadas:
            return "ferramenta"
        if self.contexto:
            return "conhecimento"
        return "sem_informacao"


class Agente:
    """`cliente` é injetável: em produção é o openai.OpenAI; nos testes, um dublê."""

    def __init__(self, cliente=None, modelo: str | None = None):
        cfg = carregar_configuracao() if cliente is None or modelo is None else None
        if cliente is None:
            from openai import OpenAI
            cliente = OpenAI(api_key=cfg.openai_api_key, max_retries=0)  # retry fica com o com_retry do curso
        self.cliente = cliente
        self.modelo = modelo or cfg.modelo_agente
        rpm = cfg.requisicoes_por_minuto if cfg else 60
        tentativas = cfg.max_tentativas if cfg else 5
        self._limitador = LimitadorDeTaxa(rpm)
        self._gerar = com_retry(max_tentativas=tentativas)(self._gerar_sem_retry)

    def _gerar_sem_retry(self, mensagens: list[dict]):
        self._limitador.aguardar_vez()
        return self.cliente.chat.completions.create(
            model=self.modelo,
            messages=mensagens,
            tools=FERRAMENTAS_OPENAI,
            temperature=0,
        )

    def responder(self, pergunta: str) -> RespostaAgente:
        contexto = buscar_contexto(pergunta)
        bloco = "\n".join(f"- {c}" for c in contexto) or "(vazio)"
        mensagens = [
            {"role": "system", "content": INSTRUCOES},
            {"role": "user", "content": f"CONTEXTO:\n{bloco}\n\nPERGUNTA: {pergunta}"},
        ]

        chamadas: list[str] = []
        texto = ""
        for _ in range(MAX_RODADAS_DE_FERRAMENTA):
            resposta = self._gerar(mensagens)
            mensagem = resposta.choices[0].message

            if not mensagem.tool_calls:
                texto = (mensagem.content or "").strip()
                break

            # Devolve a decisão do modelo (chamar ferramentas) + o resultado
            # de cada uma, para ele formular a resposta final na próxima rodada.
            mensagens.append({
                "role": "assistant",
                "content": mensagem.content,
                "tool_calls": [
                    {
                        "id": chamada.id,
                        "type": "function",
                        "function": {
                            "name": chamada.function.name,
                            "arguments": chamada.function.arguments,
                        },
                    }
                    for chamada in mensagem.tool_calls
                ],
            })
            for chamada in mensagem.tool_calls:
                nome = chamada.function.name
                argumentos = json.loads(chamada.function.arguments or "{}")
                resultado = FERRAMENTAS_POR_NOME[nome](**argumentos)
                chamadas.append(nome)
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })

        return RespostaAgente(
            pergunta=pergunta,
            texto=texto,
            contexto=contexto,
            ferramentas_chamadas=chamadas,
        )
