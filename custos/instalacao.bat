@echo off
SETLOCAL EnableDelayedExpansion
title Instalador do Sistema

echo ====================================================================
echo   Configurando ambiente local para o sistema gerado
echo ====================================================================
echo.

:: 1. Criar ambiente isolado
echo [*] Criando ambiente virtual Python (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar ambiente virtual. Verifique se o Python esta no PATH.
    pause & exit /b %errorlevel%
)

:: 2. Ativar venv e instalar as dependencias declaradas pelo gerador
echo [*] Ativando ambiente virtual...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar o ambiente virtual.
    pause & exit /b %errorlevel%
)

echo [*] Atualizando o gerenciador de pacotes (pip)...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao atualizar o pip.
    pause & exit /b %errorlevel%
)

if not exist requirements.txt (
    echo [ERRO] requirements.txt nao encontrado.
    pause & exit /b 1
)

echo [*] Instalando dependencias do projeto...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar as dependencias do projeto.
    pause & exit /b %errorlevel%
)

:: 3. Rodar as migracoes do banco gerado
echo [*] Configurando banco de dados inicial (Migrate)...
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao gerar as migrations.
    pause & exit /b %errorlevel%
)
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar as tabelas no Banco de Dados.
    pause & exit /b %errorlevel%
)

:: 4. Prompt para criar o admin do usuario final
echo.
echo ====================================================================
echo   CRIE O SEU USUARIO ADMINISTRADOR DE ACESSO
echo ====================================================================
python manage.py createsuperuser

echo.
echo ====================================================================
echo   Tudo pronto! Seu sistema foi configurado localmente.
echo   O servidor sera iniciado em: http://127.0.0.1:8000/
echo ====================================================================
echo.
pause
python manage.py runserver
