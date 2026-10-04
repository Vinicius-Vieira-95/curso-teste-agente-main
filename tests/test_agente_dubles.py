"""Testando o AGENTE sem LLM, usando um dublê (fake) do cliente OpenAI.

Isso só é possível porque o Agente recebe o cliente por injeção de dependência.
Aqui verificamos a LÓGICA ao redor do modelo: montagem do prompt, leitura das
ferramentas chamadas e a rota de decisão — tudo determinístico.
"""
import json
from types import SimpleNamespace as NS

from agente.agente import Agente


class ClienteFalso:
    """Imita `cliente.chat.completions.create` do SDK da OpenAI.

    `ferramentas` é um dict {nome_da_ferramenta: argumentos}: na 1ª chamada o
    dublê "decide" chamar essas ferramentas (como o GPT faria); depois que o
    agente as executa, a 2ª chamada devolve o texto final.
    """

    def __init__(self, texto, ferramentas: dict[str, dict] | None = None):
        self.texto = texto
        self.ferramentas = ferramentas or {}
        self.prompts = []
        self._chamou_ferramentas = False
        self.chat = NS(completions=self)

    def create(self, model, messages, tools, temperature):
        self.prompts.append(list(messages))  # snapshot: a lista real ainda cresce depois
        if self.ferramentas and not self._chamou_ferramentas:
            self._chamou_ferramentas = True
            tool_calls = [
                NS(id=f"call_{i}", function=NS(name=nome, arguments=json.dumps(args)))
                for i, (nome, args) in enumerate(self.ferramentas.items())
            ]
            mensagem = NS(content=None, tool_calls=tool_calls)
        else:
            mensagem = NS(content=self.texto, tool_calls=None)
        return NS(choices=[NS(message=mensagem)])


def test_rota_ferramenta_quando_modelo_chama_tool():
    cliente = ClienteFalso("Sua média é 8,0: aprovado.",
                            ferramentas={"calcular_media": {"notas": [7, 8, 9]}})
    resposta = Agente(cliente=cliente, modelo="falso").responder("Tirei 7, 8 e 9. Passei?")
    assert resposta.ferramentas_chamadas == ["calcular_media"]
    assert resposta.rota == "ferramenta"


def test_rota_conhecimento_usa_contexto_no_prompt():
    cliente = ClienteFalso("A frequência mínima é 75%.")
    resposta = Agente(cliente=cliente, modelo="falso").responder("Qual a frequência mínima?")
    assert resposta.rota == "conhecimento"
    assert "75%" in cliente.prompts[0][-1]["content"]  # o contexto certo foi enviado ao modelo


def test_rota_sem_informacao():
    cliente = ClienteFalso("Não tenho essa informação.")
    resposta = Agente(cliente=cliente, modelo="falso").responder("Quem ganhou a Copa?")
    assert resposta.rota == "sem_informacao"
