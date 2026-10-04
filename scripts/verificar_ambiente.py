"""Teste de sanidade do ambiente — rode ANTES de qualquer aula.

Uso:
    python scripts/verificar_ambiente.py            # checagem completa (faz 1 chamada à API)
    python scripts/verificar_ambiente.py --sem-api  # não gasta cota

Sai com código 0 se tudo estiver OK e 1 se algo falhou (útil no CI).
"""
import importlib.metadata as md
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

falhas = 0


def checar(descricao: str, ok: bool, dica: str = "") -> None:
    global falhas
    print(f"  {'✅' if ok else '❌'} {descricao}")
    if not ok:
        falhas += 1
        if dica:
            print(f"     ↳ {dica}")


print("\n1) Ferramentas")
checar(f"Python {sys.version.split()[0]} (>= 3.10)", sys.version_info >= (3, 10),
       "Instale o Python 3.10 ou mais novo em python.org")
git = shutil.which("git")
versao_git = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip() if git else ""
checar(versao_git or "Git instalado", bool(git), "Instale o Git em git-scm.com")
NO_CI = os.getenv("CI") == "true"  # o GitHub Actions define CI=true automaticamente
if NO_CI:
    print("  ⏭️  Ambiente virtual (dispensado no CI: a máquina já é descartável)")
else:
    checar("Ambiente virtual ativo", sys.prefix != sys.base_prefix,
           "No PyCharm: selecione o interpretador .venv na barra de status. "
           "No terminal: source .venv/bin/activate  (Windows: .venv\\Scripts\\activate)")

print("\n2) Dependências")
for pacote in ["openai", "deepeval", "python-dotenv", "pytest"]:
    try:
        checar(f"{pacote} {md.version(pacote)}", True)
    except md.PackageNotFoundError:
        checar(pacote, False, "Rode: pip install -r requirements.txt")

print("\n3) Credenciais")
if NO_CI:
    print("  ⏭️  Arquivo .env (no CI a chave vem dos Secrets do GitHub)")
else:
    checar("Arquivo .env existe", (RAIZ / ".env").exists(), "Rode: cp .env.example .env")
try:
    from agente.config import ConfiguracaoInvalidaError, carregar_configuracao
    cfg = carregar_configuracao()
    checar(f"OPENAI_API_KEY configurada (termina em ...{cfg.openai_api_key[-4:]})", True)
except ConfiguracaoInvalidaError as erro:
    cfg = None
    checar("OPENAI_API_KEY configurada", False, str(erro))
except ImportError as erro:
    cfg = None
    checar("Pacote do agente importável", False, str(erro))

print("\n4) Conexão com a API")
if "--sem-api" in sys.argv:
    print("  ⏭️  pulado (--sem-api)")
elif cfg is None:
    print("  ⏭️  pulado (sem chave)")
else:
    try:
        from openai import OpenAI
        cliente = OpenAI(api_key=cfg.openai_api_key)
        r = cliente.chat.completions.create(
            model=cfg.modelo_agente,
            messages=[{"role": "user", "content": "Responda apenas: OK"}],
        )
        texto = r.choices[0].message.content.strip()
        checar(f"{cfg.modelo_agente} respondeu: {texto!r}", True)
    except Exception as erro:  # noqa: BLE001 — queremos mostrar qualquer erro ao aluno
        codigo = getattr(erro, "status_code", getattr(erro, "code", "?"))
        dicas = {400: "Nome do modelo inválido? Confira MODELO_AGENTE no .env",
                 401: "Chave inválida — gere outra em platform.openai.com/api-keys",
                 403: "Chave sem permissão / organização sem acesso ao modelo",
                 429: "Limite de requisições/cota atingido — espere um pouco (veremos isso no Módulo 2)"}
        checar(f"Chamada à API (erro {codigo})", False, dicas.get(codigo, str(erro)[:200]))

print(f"\n{'🎉 Ambiente pronto!' if falhas == 0 else f'⚠️  {falhas} problema(s) encontrado(s).'}\n")
sys.exit(1 if falhas else 0)
