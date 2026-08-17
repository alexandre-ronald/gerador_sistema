from __future__ import annotations

import os
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.utils.text import slugify

from .models import Sistema
from .services import GeradorService


def _installation_bat(system_name: str) -> str:
    """Return a Windows installer script encoded as UTF-8 with an explicit code page."""
    return f"""@echo off
chcp 65001 >nul
SETLOCAL EnableDelayedExpansion
title Instalador do Sistema - {system_name}

echo ====================================================================
echo   Configurando ambiente local para: {system_name}
echo ====================================================================
echo.

:: 1. Criar ambiente isolado
echo [*] Criando ambiente virtual Python (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar ambiente virtual. Verifique se o Python esta no PATH.
    pause
    exit /b %errorlevel%
)

:: 2. Ativar venv e instalar dependencias
echo [*] Ativando ambiente virtual...
call .venv\\Scripts\\activate.bat
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar o ambiente virtual.
    pause
    exit /b %errorlevel%
)

echo [*] Atualizando o gerenciador de pacotes (pip)...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao atualizar o pip.
    pause
    exit /b %errorlevel%
)

echo [*] Instalando dependencias do framework...
pip install django django-crispy-forms crispy-bootstrap5 pillow
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias do Django.
    pause
    exit /b %errorlevel%
)

:: 3. Rodar as migracoes do banco gerado
echo [*] Configurando banco de dados inicial (Migrate)...
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao gerar as migracoes do projeto.
    pause
    exit /b %errorlevel%
)
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar as tabelas no Banco de Dados.
    pause
    exit /b %errorlevel%
)

:: 4. Prompt para criar o admin do usuario final
echo.
echo ====================================================================
echo   CRIE O SEU USUARIO ADMINISTRADOR DE ACESSO
echo ====================================================================
python manage.py createsuperuser
if %errorlevel% neq 0 (
    echo [AVISO] Criacao do superusuario cancelada ou nao concluida.
)
echo.

:: 5. Iniciar a aplicacao
echo ====================================================================
echo   Tudo pronto! Seu sistema foi configurado localmente.
echo   O servidor sera iniciado em: http://127.0.0.1:8000/
echo ====================================================================
echo.
pause
python manage.py runserver
"""


def processar_geracao_ajax(request, pk):
    """Generate, package and register a complete project export."""
    try:
        gerador = GeradorService(pk)
        logs_execucao = gerador.gerar_projeto_completo()
        sistema = Sistema.objects.get(pk=pk)
        diretorio_destino = sistema.caminho_geracao

        if not diretorio_destino or not os.path.isdir(diretorio_destino):
            raise RuntimeError(
                f"Diretorio de destino '{diretorio_destino}' nao foi localizado pelo compressor."
            )

        logs_execucao.append("Injetando script de automacao 'instalacao.bat'...")
        caminho_bat = Path(diretorio_destino) / "instalacao.bat"
        caminho_bat.write_text(
            _installation_bat(sistema.nome),
            encoding="utf-8-sig",
            newline="\r\n",
        )

        logs_execucao.append("Iniciando compactacao portatil em arquivo .ZIP...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_zip = f"{slugify(sistema.nome)}_{timestamp}.zip"
        diretorio_zips = Path(settings.MEDIA_ROOT) / "downloads_sistemas"
        diretorio_zips.mkdir(parents=True, exist_ok=True)
        caminho_zip_final = diretorio_zips / nome_zip

        with zipfile.ZipFile(caminho_zip_final, "w", zipfile.ZIP_DEFLATED) as zipf:
            for raiz, _dirs, arquivos in os.walk(diretorio_destino):
                for arquivo in arquivos:
                    caminho_completo = Path(raiz) / arquivo
                    caminho_relativo = caminho_completo.relative_to(diretorio_destino)
                    zipf.write(caminho_completo, caminho_relativo.as_posix())

        sistema.arquivo_zip = f"downloads_sistemas/{nome_zip}"
        sistema.save(update_fields=["arquivo_zip", "atualizado_em"])

        logs_execucao.append(f"Arquivo compactado gerado com sucesso: {nome_zip}")
        logs_execucao.append("Processo de exportacao finalizado com sucesso!")

        return JsonResponse(
            {
                "status": "sucesso",
                "logs": logs_execucao,
                "url_zip": reverse("sistema:baixar_zip", kwargs={"pk": sistema.pk}),
            }
        )
    except Exception as exc:
        return JsonResponse(
            {"status": "erro", "mensagem": str(exc)},
            status=400,
        )
