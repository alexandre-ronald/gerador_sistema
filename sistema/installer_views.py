import os
import zipfile
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import slugify

from .models import Sistema, VersaoGeracao
from .services import GeradorService


def _bat_env_writer(db_type):
    if db_type == "postgresql":
        keys = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT"]
    elif db_type == "mysql":
        keys = ["MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_HOST", "MYSQL_PORT"]
    elif db_type == "sqlserver":
        keys = ["MSSQL_DATABASE", "MSSQL_USER", "MSSQL_PASSWORD", "MSSQL_HOST", "MSSQL_PORT"]
    elif db_type == "oracle":
        keys = ["ORACLE_NAME", "ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_HOST", "ORACLE_PORT"]
    else:
        keys = []
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
echo [OK] Arquivo .env criado com as configuracoes do ambiente e do banco.
echo.
'''


def _bat_database_prompt(db_type):
    if db_type == "postgresql":
        return '''echo.
echo ====================================================================
echo   CONFIGURACAO DO BANCO POSTGRESQL
echo ====================================================================
echo.
set /p POSTGRES_DB=Nome do banco [sistema_db]: 
if "!POSTGRES_DB!"=="" set "POSTGRES_DB=sistema_db"
set /p POSTGRES_USER=Usuario [postgres]: 
if "!POSTGRES_USER!"=="" set "POSTGRES_USER=postgres"
set /p POSTGRES_PASSWORD=Senha: 
set /p POSTGRES_HOST=Host [localhost]: 
if "!POSTGRES_HOST!"=="" set "POSTGRES_HOST=localhost"
set /p POSTGRES_PORT=Porta [5432]: 
if "!POSTGRES_PORT!"=="" set "POSTGRES_PORT=5432"

''' + _bat_env_writer(db_type)
    if db_type == "mysql":
        return '''echo.
echo ====================================================================
echo   CONFIGURACAO DO BANCO MYSQL
echo ====================================================================
echo.
set /p MYSQL_DATABASE=Nome do banco [sistema_db]: 
if "!MYSQL_DATABASE!"=="" set "MYSQL_DATABASE=sistema_db"
set /p MYSQL_USER=Usuario [root]: 
if "!MYSQL_USER!"=="" set "MYSQL_USER=root"
set /p MYSQL_PASSWORD=Senha: 
set /p MYSQL_HOST=Host [localhost]: 
if "!MYSQL_HOST!"=="" set "MYSQL_HOST=localhost"
set /p MYSQL_PORT=Porta [3306]: 
if "!MYSQL_PORT!"=="" set "MYSQL_PORT=3306"

''' + _bat_env_writer(db_type)
    if db_type == "sqlserver":
        return '''echo.
echo ====================================================================
echo   CONFIGURACAO DO SQL SERVER
echo ====================================================================
echo.
set /p MSSQL_DATABASE=Nome do banco [sistema_db]: 
if "!MSSQL_DATABASE!"=="" set "MSSQL_DATABASE=sistema_db"
set /p MSSQL_USER=Usuario [sa]: 
if "!MSSQL_USER!"=="" set "MSSQL_USER=sa"
set /p MSSQL_PASSWORD=Senha: 
set /p MSSQL_HOST=Host [localhost]: 
if "!MSSQL_HOST!"=="" set "MSSQL_HOST=localhost"
set /p MSSQL_PORT=Porta [1433]: 
if "!MSSQL_PORT!"=="" set "MSSQL_PORT=1433"

''' + _bat_env_writer(db_type)
    if db_type == "oracle":
        return '''echo.
echo ====================================================================
echo   CONFIGURACAO DO ORACLE
echo ====================================================================
echo.
set /p ORACLE_NAME=Service/Database [sistema_db]: 
if "!ORACLE_NAME!"=="" set "ORACLE_NAME=sistema_db"
set /p ORACLE_USER=Usuario [system]: 
if "!ORACLE_USER!"=="" set "ORACLE_USER=system"
set /p ORACLE_PASSWORD=Senha: 
set /p ORACLE_HOST=Host [localhost]: 
if "!ORACLE_HOST!"=="" set "ORACLE_HOST=localhost"
set /p ORACLE_PORT=Porta [1521]: 
if "!ORACLE_PORT!"=="" set "ORACLE_PORT=1521"

''' + _bat_env_writer(db_type)
    return _bat_env_writer(db_type) + '''echo [OK] Banco SQLite selecionado. Nenhuma configuracao externa de banco e necessaria.
echo.
'''


def _installer_content(sistema):
    db_prompt = _bat_database_prompt(sistema.banco_dados)
    return f'''@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Instalador - {sistema.nome}

echo ====================================================================
echo   Configurando ambiente local para: {sistema.nome}
echo ====================================================================
echo.

if not exist "manage.py" (
    echo [ERRO] Execute este instalador na pasta raiz do projeto.
    pause
    exit /b 1
)

echo [1/6] Criando ambiente virtual Python (.venv)...
if not exist ".venv\\Scripts\\python.exe" python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar o ambiente virtual. Verifique se o Python esta no PATH.
    pause
    exit /b %errorlevel%
)
call ".venv\\Scripts\\activate.bat"
echo [OK] Ambiente virtual pronto.
echo.

echo [2/6] Atualizando pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao atualizar o pip.
    pause
    exit /b %errorlevel%
)

echo [3/6] Instalando dependencias do projeto...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar as dependencias de requirements.txt.
    pause
    exit /b %errorlevel%
)
echo [OK] Dependencias instaladas.
echo.

:: Configurar banco e gerar .env
{db_prompt}

echo [4/6] Validando configuracao Django...
python manage.py check
if %errorlevel% neq 0 (
    echo [ERRO] O Django encontrou problemas na configuracao.
    echo        Verifique o arquivo .env e as dependencias instaladas.
    pause
    exit /b %errorlevel%
)
echo [OK] Configuracao Django validada.
echo.

echo [5/6] Criando e aplicando migracoes...
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao gerar as migracoes.
    pause
    exit /b %errorlevel%
)
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar as tabelas no banco de dados.
    echo        Confirme se o servidor do banco esta ativo e se os dados do .env estao corretos.
    pause
    exit /b %errorlevel%
)
echo [OK] Banco de dados configurado.
echo.

echo [6/6] Criando usuario administrador...
python manage.py createsuperuser
if %errorlevel% neq 0 echo [AVISO] O superusuario nao foi criado.

echo.
echo ====================================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo   Sistema: {sistema.nome}
echo   Banco: {sistema.get_banco_dados_display()}
echo   URL: http://127.0.0.1:8000/
echo ====================================================================
echo.
pause
python manage.py runserver
'''


def _estrutura_snapshot(sistema):
    return {
        "sistema": {
            "nome": sistema.nome,
            "descricao": sistema.descricao,
            "banco_dados": sistema.banco_dados,
            "tipo_menu": sistema.tipo_menu,
            "gerar_api_rest": sistema.gerar_api_rest,
            "gerar_docker": sistema.gerar_docker,
            "usar_custom_user": sistema.usar_custom_user,
            "usar_auditoria": sistema.usar_auditoria,
        },
        "modulos": [
            {
                "nome": modulo.nome,
                "descricao": modulo.descricao,
                "entidades": [
                    {
                        "nome": entidade.nome,
                        "nome_plural": entidade.nome_plural,
                        "campos": [
                            {
                                "nome": campo.nome,
                                "tipo": campo.tipo,
                                "null": campo.null,
                                "blank": campo.blank,
                                "unique": campo.unique,
                                "default": campo.default_value,
                                "rel": campo.entidade_relacionada.nome if campo.entidade_relacionada else None,
                            }
                            for campo in entidade.campos.all()
                        ],
                    }
                    for entidade in modulo.entidades.all()
                ],
            }
            for modulo in sistema.modulos.all()
        ],
    }


def processar_geracao_ajax(request, pk):
    """Gera o projeto, cria instalador, registra a versão e exporta o ZIP."""
    try:
        gerador = GeradorService(pk)
        logs_execucao = gerador.gerar_projeto_completo()
        sistema = get_object_or_404(Sistema, pk=pk)
        diretorio_destino = sistema.caminho_geracao
        if not diretorio_destino or not os.path.isdir(diretorio_destino):
            raise RuntimeError(f"Diretorio de destino '{diretorio_destino}' nao foi localizado.")

        logs_execucao.append("Injetando instalador UTF-8 com configuracao do banco...")
        caminho_bat = os.path.join(diretorio_destino, "instalacao.bat")
        with open(caminho_bat, "w", encoding="utf-8", newline="") as bat_file:
            bat_file.write(_installer_content(sistema))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_zip = f"{slugify(sistema.nome)}_{timestamp}.zip"
        diretorio_zips = os.path.join(settings.MEDIA_ROOT, "downloads_sistemas")
        os.makedirs(diretorio_zips, exist_ok=True)
        caminho_zip_final = os.path.join(diretorio_zips, nome_zip)

        logs_execucao.append("Iniciando compactacao portatil em arquivo .ZIP...")
        with zipfile.ZipFile(caminho_zip_final, "w", zipfile.ZIP_DEFLATED) as zipf:
            for raiz, dirs, arquivos in os.walk(diretorio_destino):
                dirs[:] = [d for d in dirs if d not in {".venv", "__pycache__"}]
                for arquivo in arquivos:
                    caminho_completo = os.path.join(raiz, arquivo)
                    caminho_relativo = os.path.relpath(caminho_completo, diretorio_destino)
                    zipf.write(caminho_completo, caminho_relativo)

        sistema.arquivo_zip = f"downloads_sistemas/{nome_zip}"
        sistema.save(update_fields=["arquivo_zip", "atualizado_em"])

        numero = (VersaoGeracao.objects.filter(sistema=sistema).order_by("-numero").values_list("numero", flat=True).first() or 0) + 1
        versao = VersaoGeracao.objects.create(
            sistema=sistema,
            numero=numero,
            descricao=f"Geração {timestamp}",
            estrutura_json=_estrutura_snapshot(sistema),
        )
        with open(caminho_zip_final, "rb") as zip_file:
            versao.arquivo_zip.save(nome_zip, zip_file, save=True)

        logs_execucao.append(f"Versao de geracao registrada: v{numero}")
        logs_execucao.append(f"Arquivo compactado gerado com sucesso: {nome_zip}")
        logs_execucao.append("Processo de exportacao finalizado com sucesso!")

        return JsonResponse({
            "status": "sucesso",
            "logs": logs_execucao,
            "versao": numero,
            "url_zip": reverse("sistema:baixar_zip", kwargs={"pk": sistema.pk}),
        })
    except Exception as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)


def preview_geracao(request, pk):
    """Retorna o preview estrutural da última geração sem executar o projeto."""
    sistema = get_object_or_404(Sistema, pk=pk)
    versao = sistema.versoes.first()
    if not versao:
        return JsonResponse({"status": "erro", "mensagem": "Nenhuma geração disponível para preview."}, status=404)

    root = sistema.caminho_geracao
    arquivos = []
    if os.path.isdir(root):
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d not in {".venv", "__pycache__"}]
            for name in names:
                rel = os.path.relpath(os.path.join(base, name), root).replace(os.sep, "/")
                arquivos.append(rel)
    arquivos.sort()

    return JsonResponse({
        "status": "sucesso",
        "sistema": sistema.nome,
        "versao": versao.numero,
        "criado_em": versao.criado_em.isoformat(),
        "estrutura": versao.estrutura_json,
        "arquivos": arquivos,
    })
