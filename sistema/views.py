from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import SistemaForm   # vamos criar esse form agora
from django.db import transaction

from django.http import JsonResponse
from .models import Sistema, Modulo, Entidade, Campo
from django.views.decorators.csrf import csrf_exempt

from .services import GeradorService

import os
import zipfile
from datetime import datetime
from django.utils.text import slugify
from django.core.files import File
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse
from django.contrib.auth.models import User


import json

@login_required
def lista_sistemas(request):
    #sistemas = Sistema.objects.all().order_by('nome')
    sistemas = Sistema.objects.filter(usuario=request.user).order_by('-atualizado_em')
    context = {
        'sistemas': sistemas,
    }
    return render(request, 'sistema/lista.html', context)

def editor(request, pk=None):
    sistema = None
    estrutura = {"sistema": {}, "modulos": []}

    if pk:
        sistema = Sistema.objects.get(pk=pk)

        estrutura = {
            "sistema": {
                "nome": sistema.nome,
                "descricao": sistema.descricao,
                "caminho": sistema.caminho
            },
            "modulos": sistema.get_estrutura_json()  # você deve ter isso
        }

    return render(request, "editor.html", {
        "estrutura_json": json.dumps(estrutura)
    })


@login_required
def criar_sistema(request):
    if request.method == 'POST':
        form = SistemaForm(request.POST)
        if form.is_valid():
            sistema = form.save()
            messages.success(request, f"Sistema '{sistema.nome}' criado com sucesso!")
            return redirect('sistema:lista')
    else:
        form = SistemaForm()

    return render(request, 'sistema/editor.html', {'form': form})


@login_required
def editar_sistema2(request, pk):
    sistema = get_object_or_404(Sistema, pk=pk)

    if request.method == 'POST':
        form = SistemaForm(request.POST, instance=sistema)
        if form.is_valid():
            sistema = form.save()
            messages.success(request, f"Sistema '{sistema.nome}' atualizado com sucesso!")
            return redirect('sistema:lista')
    else:
        form = SistemaForm(instance=sistema)

    return render(request, 'sistema/criar.html', {
        'form': form,
        'sistema': sistema,   # para o título e valores nos inputs
    })


@login_required
def gerar_sistema_processar(request, sistema_id):
    if request.method != "POST":
        return JsonResponse({"status": "erro", "mensagem": "Método inválido"}, status=405)

    try:
        sistema = Sistema.objects.get(id=sistema_id)

        logs = gerar_sistema(sistema)

        return JsonResponse({
            "status": "sucesso",
            "logs": logs
        })

    except Exception as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": str(e)
        }, status=500)


def to_int(value):
    try:
        return int(value)
    except:
        return None


@csrf_exempt
def atualizar_sistema(request, sistema_id):

    if request.method != "PUT":
        return JsonResponse({"erro": "Método não permitido"}, status=405)

    try:
        data = json.loads(request.body)

        with transaction.atomic():

            sistema = Sistema.objects.get(id=sistema_id)

            # ======================
            # SISTEMA
            # ======================
            sistema_data = data.get("sistema", {})

            sistema.nome = sistema_data.get("nome", "")
            sistema.descricao = sistema_data.get("descricao", "")
            sistema.caminho_geracao = sistema_data.get("caminho", "")
            sistema.banco_dados = sistema_data.get("banco_dados", "sqlite3")
            sistema.tipo_menu = sistema_data.get("tipo_menu", "vertical")
            sistema.usar_custom_user = sistema_data.get("usar_custom_user", True)
            sistema.gerar_api_rest = sistema_data.get("gerar_api_rest", False)
            sistema.gerar_docker = sistema_data.get("gerar_docker", False)
            sistema.usar_auditoria = sistema_data.get("usar_auditoria", False)

            sistema.save()

            # ======================
            # LIMPA
            # ======================
            sistema.modulos.all().delete()

            # ======================
            # PASSO 1 — CRIAR ESTRUTURA
            # ======================
            entidades_map = {}

            for mod_data in data.get("modulos") or []:

                modulo = Modulo.objects.create(
                    sistema=sistema,
                    nome=mod_data.get("nome", "Modulo")
                )

                for ent_data in mod_data.get("entidades") or []:

                    entidade = Entidade.objects.create(
                        modulo=modulo,
                        nome=ent_data.get("nome", "Entidade")
                    )

                    # 🔥 guarda no mapa
                    entidades_map[entidade.nome] = entidade

            # ======================
            # PASSO 2 — CRIAR CAMPOS
            # ======================
            for mod_data in data.get("modulos") or []:

                for ent_data in mod_data.get("entidades") or []:

                    entidade = entidades_map.get(ent_data.get("nome"))

                    for campo_data in ent_data.get("campos") or []:

                        campo_kwargs = {
                            "entidade": entidade,
                            "nome": campo_data.get("nome", "campo"),
                            "tipo": campo_data.get("tipo", "CharField"),

                            "max_length": to_int(campo_data.get("max_length")),
                            "max_digits": to_int(campo_data.get("max_digits")),
                            "decimal_places": to_int(campo_data.get("decimal_places")),

                            "null": campo_data.get("null", False),
                            "blank": campo_data.get("blank", False),
                            "unique": campo_data.get("unique", False),

                            "default_value": campo_data.get("default"),
                            "upload_to": campo_data.get("upload_to"),
                            "related_name_str": campo_data.get("related_name"),
                            "on_delete": campo_data.get("on_delete", "models.CASCADE"),
                        }

                        # 🔥 RELACIONAMENTO CORRETO
                        rel_nome = campo_data.get("rel")

                        if rel_nome:
                            entidade_rel = entidades_map.get(rel_nome)

                            if entidade_rel:
                                campo_kwargs["entidade_relacionada"] = entidade_rel
                            else:
                                print(f"⚠️ Rel não encontrado: {rel_nome}")

                        Campo.objects.create(**campo_kwargs)

        return JsonResponse({
            "status": "ok",
            "sistema_id": sistema.id
        })

    except Sistema.DoesNotExist:
        return JsonResponse({"erro": "Sistema não encontrado"}, status=404)

    except Exception as e:
        print("ERRO INTERNO:", str(e))

        return JsonResponse({
            "erro": str(e)
        }, status=500)
def excluir_sistema(request, sistema_id):

    sistema = get_object_or_404(Sistema, id=sistema_id)
    sistema.delete()
    messages.success(request, f"Sistema '{sistema.nome}' excluído com sucesso!")
    return redirect('sistema:lista')

def editar_sistema(request, sistema_id):
    sistema = get_object_or_404(Sistema, id=sistema_id)

    estrutura = {
        "sistema": {
            "nome": sistema.nome,
            "descricao": sistema.descricao,
            "caminho": sistema.caminho_geracao,
            "tipo_menu": sistema.tipo_menu,
            "banco_dados": sistema.banco_dados,
            "usar_custom_user": sistema.usar_custom_user,
            "gerar_api_rest": sistema.gerar_api_rest,
            "gerar_docker": sistema.gerar_docker,
            "usar_auditoria": sistema.usar_auditoria
        },
        "modulos": []
    }

    for mod in sistema.modulos.all():
        mod_data = {
            "nome": mod.nome,
            "entidades": []
        }

        for ent in mod.entidades.all():
            ent_data = {
                "nome": ent.nome,
                "campos": []
            }

            for c in ent.campos.all():
                ent_data["campos"].append({
                    "nome": c.nome,
                    "tipo": c.tipo,
                    "max_length": c.max_length,
                    "max_digits": c.max_digits,
                    "decimal_places": c.decimal_places,

                    # 🔥 CORREÇÃO AQUI
                    "rel": c.entidade_relacionada.nome if c.entidade_relacionada else None,

                    "null": c.null,
                    "blank": c.blank,
                    "unique": c.unique,
                    "default": c.default_value,
                    "upload_to": c.upload_to,
                    "related_name": c.related_name_str,
                    "on_delete": c.on_delete,
                })

            mod_data["entidades"].append(ent_data)

        estrutura["modulos"].append(mod_data)

    return render(request, "sistema/editor.html", {
        "estrutura_json": json.dumps(estrutura),
        "sistema_id": sistema.id
    })

@csrf_exempt
@csrf_exempt
def salvar_modelo(request):
    if request.method == "POST":
        try:
            dados = json.loads(request.body)
            sis_data = dados.get('sistema', {})

            # 1. Sistema
            sistema, created = Sistema.objects.update_or_create(
                nome=sis_data.get('nome'),
                defaults={
                    'descricao': sis_data.get('descricao', ''),
                    'caminho_geracao': sis_data.get('caminho', ''),
                    'banco_dados': sis_data.get('banco_dados', 'sqlite3'),
                    'tipo_menu': sis_data.get('tipo_menu', 'lateral'),
                    'usar_custom_user': sis_data.get('usar_custom_user', True),
                    'gerar_api_rest': sis_data.get('gerar_api_rest', False),
                    'gerar_docker': sis_data.get('gerar_docker', False),
                    'usar_auditoria': sis_data.get('usar_auditoria', False),
                }
            )

            # 🔥 Limpa a estrutura anterior para sobrescrever
            sistema.modulos.all().delete()
            entidades_map = {}

            # =========================
            # 🔵 PASSO 1 — Criar estrutura básica
            # =========================
            for mod_data in dados.get('modulos', []):
                modulo = Modulo.objects.create(
                    sistema=sistema,
                    nome=mod_data.get('nome')
                )

                for ent_data in mod_data.get('entidades', []):
                    entidade = Entidade.objects.create(
                        modulo=modulo,
                        nome=ent_data.get('nome'),
                        nome_plural=ent_data.get('nome_plural') or (ent_data.get('nome') + "s")
                    )
                    entidades_map[entidade.nome] = entidade

            # =========================
            # 🔵 PASSO 2 — Criar campos (com lógica de tipos)
            # =========================
            for mod_data in dados.get('modulos', []):
                for ent_data in mod_data.get('entidades', []):
                    entidade = entidades_map.get(ent_data.get('nome'))

                    for campo_data in ent_data.get('campos', []):
                        tipo_campo = campo_data.get('tipo', 'CharField')
                        
                        # Montagem básica do dicionário
                        campo_kwargs = {
                            "entidade": entidade,
                            "nome": campo_data.get('nome'),
                            "tipo": tipo_campo,
                            "null": campo_data.get('null', False),
                            "blank": campo_data.get('blank', False),
                            "unique": campo_data.get('unique', False),
                            "default_value": campo_data.get('default_value') or campo_data.get('default', ''),
                            "upload_to": campo_data.get('upload_to', ''),
                            "related_name_str": campo_data.get('related_name', ''),
                            "on_delete": campo_data.get('on_delete', 'models.CASCADE'),
                        }

                        # 🛠️ LÓGICA DE MAX_LENGTH
                        # Inteiros e Datas NÃO aceitam max_length no Django
                        tipos_sem_max_length = ['IntegerField', 'FloatField', 'DateField', 'DateTimeField', 'BooleanField', 'TextField']
                        
                        if tipo_campo not in tipos_sem_max_length:
                            campo_kwargs["max_length"] = campo_data.get('max_length') or 255
                        
                        # 🔥 RELACIONAMENTOS (FK)
                        rel_nome = campo_data.get('rel')
                        if rel_nome:
                            entidade_rel = entidades_map.get(rel_nome)
                            if entidade_rel:
                                campo_kwargs["entidade_relacionada"] = entidade_rel

                        # Criar no Banco do Gerador
                        Campo.objects.create(**campo_kwargs)

            return JsonResponse({"status": "sucesso", "sistema_id": sistema.id})

        except Exception as e:
            print("ERRO NA SALVAR_MODELO:", str(e))
            return JsonResponse({"status": "erro", "mensagem": str(e)}, status=400)
        

###########
# Geração #
###########


def gerar_sistema_view(request, pk):
    """Exibe a tela do monitor de log"""
    sistema = get_object_or_404(Sistema, pk=pk)
    # Contagem para o resumo lateral
    total_entidades = Entidade.objects.filter(modulo__sistema=sistema).count()
    
    context = {
        'sistema': sistema,
        'total_entidades': total_entidades,
    }
    return render(request, 'sistema/gerar_sistema.html', context)

import os
import zipfile
from datetime import datetime
from django.utils.text import slugify
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Sistema  # Ajuste para o seu model real de Sistema

def processar_geracao_ajax(request, pk):
    """Executa o motor de geração e retorna os logs em JSON com script e ZIP portátil"""
    try:
        # 1. Instancia o serviço e roda o gerador padrão
        gerador = GeradorService(pk)
        logs_execucao = gerador.gerar_projeto_completo()
        
        # Recupera o objeto do sistema para pegar caminhos e nomes
        # (Se o seu gerador já guarda a instância em gerador.sistema, pode usar direto)
        sistema = get_object_or_404(Sistema, pk=pk)
        diretorio_destino = sistema.caminho_geracao  # Diretório físico gerado

        # Validar se o diretório de geração realmente existe
        if not diretorio_destino or not os.path.exists(diretorio_destino):
            raise Exception(f"Diretório de destino '{diretorio_destino}' não foi localizado pelo compressor.")

        # ====================================================================
        # PASSO 1: Criar o 'instalacao.bat' dentro da raiz do diretório gerado
        # ====================================================================
        logs_execucao.append("Injetando script de automação 'instalacao.bat'...")
        caminho_bat = os.path.join(diretorio_destino, 'instalacao.bat')
        
        conteudo_bat = f"""@echo off
SETLOCAL EnableDelayedExpansion
title Instalador do Sistema - {sistema.nome}

echo ====================================================================
echo   Configurando ambiente local para: {sistema.nome}
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
call .venv\\Scripts\\activate

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
"""
        with open(caminho_bat, 'w', encoding='utf-8') as bat_file:
            bat_file.write(conteudo_bat)


        # ====================================================================
        # PASSO 2: Compactar o diretório inteiro em um arquivo ZIP portátil
        # ====================================================================
        logs_execucao.append("Iniciando compactação portátil em arquivo .ZIP...")
        
        # Gerando nome dinâmico com a Timestamp do momento (AnoMêsDia_HoraMinutoSegundo)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_zip = f"{slugify(sistema.nome)}_{timestamp}.zip"
        
        # Define a pasta de uploads padrão do Django no servidor para guardar os zips
        diretorio_zips = os.path.join(settings.MEDIA_ROOT, 'downloads_sistemas')
        os.makedirs(diretorio_zips, exist_ok=True)
        caminho_zip_final = os.path.join(diretorio_zips, nome_zip)

        # Captura todos os arquivos gerados (incluindo o recém-criado bat)
        with zipfile.ZipFile(caminho_zip_final, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for raiz, dirs, arquivos in os.walk(diretorio_destino):
                for arquivo in arquivos:
                    caminho_completo = os.path.join(raiz, arquivo)
                    # Caminho relativo evita colocar caminhos absolutos do servidor dentro do ZIP
                    caminho_relativo = os.path.relpath(caminho_completo, diretorio_destino)
                    zipf.write(caminho_completo, caminho_relativo)

        # Guardar a referência no banco de dados para o card histórico funcionar
        # Nota: Lembre-se de criar o campo arquivo_zip no model se ainda não criou
        sistema.arquivo_zip = f"downloads_sistemas/{nome_zip}"
        sistema.save()

        logs_execucao.append(f"Arquivo compactado gerado com sucesso: {nome_zip}")
        logs_execucao.append("Processo de exportação finalizado com sucesso!")

        return JsonResponse({
            "status": "sucesso",
            "logs": logs_execucao,
            "url_zip": sistema.arquivo_zip.url
        })

    except Exception as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": str(e)
        }, status=400)

def processar_geracao_ajax2(request, pk):
    """Executa o motor de geração e retorna os logs em JSON"""
    try:
        # Instancia o serviço que criamos anteriormente
        gerador = GeradorService(pk)
        
        # O método gerar_projeto_completo() deve retornar a lista de logs (self.logs)
        logs_execucao = gerador.gerar_projeto_completo()

        return JsonResponse({
            "status": "sucesso",
            "logs": logs_execucao
        })
    except Exception as e:
        # Se algo der errado no Python, o erro vai para o monitor em vermelho
        return JsonResponse({
            "status": "erro",
            "mensagem": str(e)
        }, status=400)

def gerar_sucesso_view(request, pk):
    """Exibe as instruções de terminal pós-geração"""
    sistema = get_object_or_404(Sistema, pk=pk)
    nome_projeto = sistema.nome.lower().replace(" ", "_")
    
    context = {
        'sistema': sistema,
        'nome_projeto': nome_projeto,
        'caminho': sistema.caminho_geracao
    }
    return render(request, 'sistema/gerar_sucesso.html', context)

def gerar_e_zipar_sistema(request, sistema_id):
    sistema = get_object_or_404(Sistema, id=sistema_id, usuario=request.user)
    
    # 1. Definir caminhos (ajuste para a lógica onde seu gerador cria as pastas)
    diretorio_sistema = os.path.join(settings.MEDIA_ROOT, 'gerador_temp', sistema.slug)
    
    # [AQUI: Seu gerador existente cria a estrutura de pastas do Django: manage.py, apps, etc.]
    # ex: criar_estrutura_django(diretorio_sistema, sistema)

    # 2. Criar o arquivo instalacao.bat dentro da raiz do sistema gerado
    caminho_bat = os.path.join(diretorio_sistema, 'instalacao.bat')
    conteudo_bat = gerar_conteudo_bat(sistema.slug)
    with open(caminho_bat, 'w', encoding='utf-8') as bat_file:
        bat_file.write(conteudo_bat)

    # 3. Criar o arquivo ZIP com Timestamp no nome
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_zip = f"{sistema.slug}_{timestamp}.zip"
    caminho_zip_temporario = os.path.join(settings.MEDIA_ROOT, 'gerador_temp', nome_zip)

    with zipfile.ZipFile(caminho_zip_temporario, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for raiz, dirs, arquivos in os.walk(diretorio_sistema):
            for arquivo in arquivos:
                caminho_completo = os.path.join(raiz, arquivo)
                # Guarda no zip mantendo a estrutura relativa de pastas
                caminho_relativo = os.path.relpath(caminho_completo, diretorio_sistema)
                zipf.write(caminho_completo, caminho_relativo)

    # 4. Salvar o ZIP no Model para persistência posterior
    with open(caminho_zip_temporario, 'rb') as f:
        sistema.arquivo_zip.save(nome_zip, File(f), save=True)

    # Limpeza do arquivo temporário local se necessário
    if os.path.exists(caminho_zip_temporario):
        os.remove(caminho_zip_temporario)

    return redirect('meus_sistemas')

def gerar_conteudo_bat(nome_projeto):
    return f"""@echo off
SETLOCAL EnableDelayedExpansion
title Instalador Automatico - {nome_projeto}

echo ====================================================================
echo    Iniciando a instalacao automatica do sistema: {nome_projeto}
echo ====================================================================
echo.

:: 1. Criando o ambiente virtual (.venv)
echo [*] Criando ambiente virtual Python (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar o ambiente virtual. Certifique-se de que o Python esta no PATH.
    pause
    exit /b %errorlevel%
)
echo [OK] Ambiente virtual criado com sucesso.
echo.

:: 2. Ativando a venv e Instalando pacotes
echo [*] Ativando ambiente virtual e instalando pacotes...
call .venv\\Scripts\\activate

:: Garantir atualizacao do pip
python -m pip install --upgrade pip

:: Instala os pacotes padrão do Django e complementos
echo [*] Instalando Django e dependencias...
pip install django django-crispy-forms crispy-bootstrap5 pillow

if %errorlevel% neq 0 (
    echo [ERRO] Falha na instalacao dos pacotes pip.
    pause
    exit /b %errorlevel%
)
echo [OK] Dependencias instaladas com sucesso.
echo.

:: 3. Executando as Migraçoes
echo [*] Preparando banco de dados (Migrate)...
python manage.py makemigrations
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao executar as migracoes do Banco de Dados.
    pause
    exit /b %errorlevel%
)
echo [OK] Banco de dados configurado.
echo.

:: 4. Criação do Superusuário (Interativo)
echo ====================================================================
echo    CRIACAO DO USUARIO ADMINISTRADOR (SUPERUSER)
echo ====================================================================
echo Digite os dados para acessar o painel administrativo posteriormente:
echo.
python manage.py createsuperuser
echo.
echo [OK] Configuracao do Administrador concluida.
echo.

:: 5. Inicialização do Servidor
echo ====================================================================
echo    Instalacao Concluida com Sucesso!
echo    O servidor sera iniciado em: http://127.0.0.1:8000/
echo ====================================================================
echo.
echo Pressione qualquer tecla para rodar o sistema...
pause > nul

python manage.py runserver
"""
@login_required
@login_required
def dashboard_view(request):
    sistemas = Sistema.objects.filter(usuario=request.user).prefetch_related('modulos')
    
    # Contadores consolidados do usuário
    total_modulos = Modulo.objects.filter(sistema__usuario=request.user).count()
    total_entidades = Entidade.objects.filter(modulo__sistema__usuario=request.user).count()
    total_zips = sistemas.exclude(arquivo_zip='').exclude(arquivo_zip__isnull=True).count()

    context = {
        'sistemas': sistemas,
        'total_modulos': total_modulos,
        'total_entidades': total_entidades,
        'total_zips': total_zips,
    }
    
    return render(request, 'sistema/dashboard.html', context)

@login_required
def analytics_view(request):
    return render(request, 'sistema/analytics.html')

@login_required
def users_view(request):
    # Traz a lista de usuários cadastrados no banco do Django
    users_list = User.objects.all().order_by('-date_joined')
    return render(request, 'sistema/users.html', {'users_list': users_list})

@login_required
def search_view(request):
    query = request.GET.get('q', '')
    results = [] 
    return render(request, 'sistema/search.html', {'query': query, 'results': results})

@login_required
def profile_view(request):
    return render(request, 'sistema/profile.html')

@login_required
def settings_view(request):
    return render(request, 'sistema/settings.html')