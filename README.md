# Testes de Agentes baseados em LLM — Repositório do Curso

Assistente acadêmico (OpenAI/GPT) + suíte de testes em duas camadas:

| Camada | Arquivos | Precisa de chave? | Roda em |
|---|---|---|---|
| Determinística | `test_sanidade.py`, `test_ferramentas.py`, `test_resiliencia.py`, `test_agente_dubles.py` | Não | segundos |
| LLM-as-a-judge (DeepEval) | `test_llm_relevancia.py`, `test_geval.py` (marcados `@pytest.mark.llm`) | Sim | minutos |

## Setup rápido

```bash
git clone <url-do-repo> && cd curso-testes-agentes
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
# edite o .env e cole sua OPENAI_API_KEY (https://platform.openai.com/api-keys)
python scripts/verificar_ambiente.py
```

## Usando no PyCharm

1. **Clone Repository** (ou File → Open na pasta descompactada) → Trust Project.
2. Barra de status → interpretador → **Add New Interpreter → Add Local Interpreter → Virtualenv**,
   Base Python 3.10+, Location `.venv` dentro do projeto.
3. Abra o `requirements.txt` → **Install requirements** (ou `pip install -r requirements.txt` no terminal, Alt+F12).
4. Botão direito em `src` → **Mark Directory as → Sources Root**.
5. Settings → Tools → Python Integrated Tools → **Default test runner: pytest**.
6. Copie `.env.example` para `.env` e cole sua chave da OpenAI.
7. Botão direito em `scripts/verificar_ambiente.py` → **Run**.
8. Run → Edit Configurations → **+ → Python tests → pytest**, pasta `tests`:
   - *Testes rápidos*: Additional Arguments `-m "not llm"`
   - *Testes LLM*: `-m llm -s -v`
   - *Tudo*: vazio

## Rodando os testes

```bash
pytest -m "not llm"                # rápidos, grátis, sem internet
pytest -m llm -v                   # chamam a OpenAI (consomem cota)
deepeval test run tests -m llm     # mesmo que acima, com relatório do DeepEval
```

## CI (GitHub Actions)

`.github/workflows/testes.yml` roda os testes determinísticos em todo push/PR e a
avaliação com LLM depois deles. Cadastre a chave em
**Settings → Secrets and variables → Actions → New repository secret** com o nome `OPENAI_API_KEY`.

## Estrutura

```
src/agente/
  config.py            # lê o .env (único lugar que toca em variáveis de ambiente)
  ferramentas.py       # tools determinísticas: calcular_media, consultar_calendario
  base_conhecimento.py # "RAG" simplificado por palavra-chave
  agente.py            # orquestra contexto + OpenAI + ferramentas -> RespostaAgente
  resiliencia.py       # retry com backoff exponencial, limitador de taxa, erro 429
  juiz.py              # modelo juiz do DeepEval
scripts/verificar_ambiente.py   # teste de sanidade do ambiente
scripts/provocar_429.py        # demo do vídeo 2.3 (gasta cota!)
tests/
```
