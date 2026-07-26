@echo off
SETLOCAL EnableDelayedExpansion
title Instalador do Sistema - Sistema de Custos Hospitalares

echo ====================================================================
echo   Configurando ambiente local para: Sistema de Custos Hospitalares
echo ====================================================================
echo.

:: 1. Criar ambiente isolado
echo [*] Criando ambiente virtual Python (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar ambiente virtual. Verifique se o Python esta no PATH.
    pause & exit /b %errorlevel%
)

:: 2. Ativar venv e instalar dependencias
echo [*] Ativando ambiente virtual...
 Salvador:
call .venv\Scripts\activate

echo [*] Atualizando o gerenciador de pacotes (pip)...
python -m pip install --upgrade pip

echo [*] Instalando dependencias do framework...
pip install django django-crispy-forms crispy-bootstrap5 pillow
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias do Django.
    pause & exit /b %errorlevel%
)

:: 3. Rodar as migrações do banco gerado
echo [*] Configurando banco de dados inicial (Migrate)...
python manage.py makemigrations
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar as tabelas no Banco de Dados.
    pause & exit /b %errorlevel%
)

:: 4. Prompt para criar o admin do usuário final
echo.
echo ====================================================================
echo   CRIE O SEU USUARIO ADMINISTRADOR DE ACESSO
echo ====================================================================
python manage.py createsuperuser
echo.

:: 5. Iniciar a aplicação
echo ====================================================================
echo   Tudo pronto! Seu sistema foi configurado localmente.
echo   O servidor sera iniciado em: http://127.0.0.1:8000/
echo ====================================================================
echo.
pause
python manage.py runserver
