import os
import zipfile
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import slugify

from .models import Sistema, VersaoGeracao
from .services import GeradorService
from .structure_service import serialize_system_structure


def _bat_display_name(value):
    import unicodedata
    return unicodedata.normalize("NFKD", str(value or "Sistema")).encode("ascii", "ignore").decode("ascii")


def _bat_env_writer(db_type):
    keys_by_db = {
        "postgresql": ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT"],
        "mysql": ["MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_HOST", "MYSQL_PORT"],
        "sqlserver": ["MSSQL_DATABASE", "MSSQL_USER", "MSSQL_PASSWORD", "MSSQL_HOST", "MSSQL_PORT"],
        "oracle": ["ORACLE_NAME", "ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_HOST", "ORACLE_PORT"],
    }
    keys = keys_by_db.get(db_type, [])
    pairs = ", ".join(f"{key!r}: os.environ.get({key!r}, '')" for key in keys)
    if pairs:
        pairs += ", "
    pairs += "'DJANGO_DEBUG': '1', 'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1', 'DJANGO_SECRET_KEY': os.environ.get('DJANGO_SECRET_KEY') or secrets.token_urlsafe(50)"
    return f'''python -c "import os,json,secrets; from pathlib import Path; v={{ {pairs} }}; Path('.env').write_text(''.join(k+'='+json.dumps(val, ensure_ascii=False)+'\\n' for k,val in v.items()), encoding='utf-8')"
if %errorlevel% neq 0 (
    echo [ERRO] Nao foi possivel criar o arquivo .env.
    pause
    exit /b 1
)
echo [OK] Arquivo .env criado.
echo.
'''


def _bat_database_prompt(db_type):
    defaults = {
        "postgresql": [("POSTGRES_DB", "sistema_db"), ("POSTGRES_USER", "postgres"), ("POSTGRES_PASSWORD", ""), ("POSTGRES_HOST", "localhost"), ("POSTGRES_PORT", "5432")],
        "mysql": [("MYSQL_DATABASE", "sistema_db"), ("MYSQL_USER", "root"), ("MYSQL_PASSWORD", ""), ("MYSQL_HOST", "localhost"), ("MYSQL_PORT", "3306")],
        "sqlserver": [("MSSQL_DATABASE", "sistema_db"), ("MSSQL_USER", "sa"), ("MSSQL_PASSWORD", ""), ("MSSQL_HOST", "localhost"), ("MSSQL_PORT", "1433")],
        "oracle": [("ORACLE_NAME", "sistema_db"), ("ORACLE_USER", "system"), ("ORACLE_PASSWORD", ""), ("ORACLE_HOST", "localhost"), ("ORACLE_PORT", "1521")],
    }
    if db_type not in defaults:
        return "echo [OK] Banco SQLite selecionado.\necho.\n"
    lines = ["echo.", f"echo CONFIGURACAO DO BANCO {db_type.upper()}", "echo."]
    for key, default in defaults[db_type]:
        lines.append(f'set "{key}="')
        lines.append(f'set /p "{key}={key} [{default}]: "')
        if default:
            lines.append(f'if not defined {key} set "{key}={default}"')
    lines.append("")
    lines.append(_bat_env_writer(db_type))
    return "\n".join(lines)


def _installer_content(sistema):
    name = _bat_display_name(sistema.nome)
    return f'''@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title Instalador - {name}

echo ================================================================
echo   Configurando: {name}
echo ================================================================
if not exist "manage.py" (
    echo [ERRO] Execute este instalador na pasta raiz do projeto.
    pause
    exit /b 1
)
if not exist ".venv\\Scripts\\python.exe" python -m venv .venv
if %errorlevel% neq 0 exit /b %errorlevel%
call ".venv\\Scripts\\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha na instalacao das dependencias.
    pause
    exit /b %errorlevel%
)
{_bat_database_prompt(sistema.banco_dados)}
python manage.py check
if %errorlevel% neq 0 (
    echo [ERRO] Falha no Django check.
    pause
    exit /b %errorlevel%
)
python manage.py makemigrations
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERRO] Falha nas migracoes.
    pause
    exit /b %errorlevel%
)
python manage.py createsuperuser
python manage.py runserver
'''


@login_required
def processar_geracao_ajax(request, pk):
    try:
        sistema = get_object_or_404(Sistema, pk=pk, usuario=request.user)
        logs = GeradorService(sistema.pk).gerar_projeto_completo()
        root = sistema.caminho_geracao
        if not root or not os.path.isdir(root):
            raise RuntimeError(f"Diretório de destino '{root}' não foi localizado.")

        with open(os.path.join(root, "instalacao.bat"), "w", encoding="utf-8-sig", newline="") as bat_file:
            bat_file.write(_installer_content(sistema))
        logs.append("Instalador criado: instalacao.bat")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_zip = f"{slugify(sistema.nome)}_{timestamp}.zip"
        pasta_zip = os.path.join(settings.MEDIA_ROOT, "downloads_sistemas")
        os.makedirs(pasta_zip, exist_ok=True)
        zip_path = os.path.join(pasta_zip, nome_zip)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for base, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in {".venv", "__pycache__"}]
                for filename in files:
                    full = os.path.join(base, filename)
                    zipf.write(full, os.path.relpath(full, root))

        sistema.arquivo_zip = f"downloads_sistemas/{nome_zip}"
        sistema.save(update_fields=["arquivo_zip", "atualizado_em"])
        numero = (sistema.versoes.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1
        versao = VersaoGeracao.objects.create(
            sistema=sistema, numero=numero, descricao=f"Geração {timestamp}", estrutura_json=serialize_system_structure(sistema)
        )
        with open(zip_path, "rb") as zip_file:
            versao.arquivo_zip.save(nome_zip, zip_file, save=True)

        logs.extend([f"Versão de geração registrada: v{numero}", f"ZIP gerado: {nome_zip}"])
        return JsonResponse({"status": "sucesso", "logs": logs, "versao": numero, "url_zip": reverse("sistema:baixar_zip", kwargs={"pk": sistema.pk})})
    except Exception as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)


@login_required
def preview_geracao(request, pk):
    sistema = get_object_or_404(Sistema, pk=pk, usuario=request.user)
    versao = sistema.versoes.first()
    if not versao:
        return JsonResponse({"status": "erro", "mensagem": "Nenhuma geração disponível para preview."}, status=404)
    root = sistema.caminho_geracao
    arquivos = []
    if os.path.isdir(root):
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d not in {".venv", "__pycache__"}]
            for name in names:
                arquivos.append(os.path.relpath(os.path.join(base, name), root).replace(os.sep, "/"))
    return JsonResponse({"status": "sucesso", "sistema": sistema.nome, "versao": versao.numero, "criado_em": versao.criado_em.isoformat(), "estrutura": versao.estrutura_json, "arquivos": sorted(arquivos)})
