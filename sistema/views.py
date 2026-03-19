from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import SistemaForm   # vamos criar esse form agora
from django.db import transaction

from django.http import JsonResponse
from .models import Sistema, Modulo, Entidade, Campo
from django.views.decorators.csrf import csrf_exempt

from .services import GeradorService


import json

@login_required
def lista_sistemas(request):
    sistemas = Sistema.objects.all().order_by('nome')
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
            sistema.usar_custom_user = sistema_data.get("usar_custom_user", True)
            sistema.gerar_api_rest = sistema_data.get("gerar_api_rest", False)
            sistema.gerar_docker = sistema_data.get("gerar_docker", False)

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
    
def editar_sistema(request, sistema_id):
    sistema = get_object_or_404(Sistema, id=sistema_id)

    estrutura = {
        "sistema": {
            "nome": sistema.nome,
            "descricao": sistema.descricao,
            "caminho": sistema.caminho_geracao,
            "banco_dados": sistema.banco_dados,
            "usar_custom_user": sistema.usar_custom_user,
            "gerar_api_rest": sistema.gerar_api_rest,
            "gerar_docker": sistema.gerar_docker,
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
def salvar_modelo(request):
    if request.method == "POST":
        print('salvar sistema')

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
                    'usar_custom_user': sis_data.get('usar_custom_user', True),
                    'gerar_api_rest': sis_data.get('gerar_api_rest', False),
                    'gerar_docker': sis_data.get('gerar_docker', False),
                }
            )

            # 🔥 limpa tudo
            sistema.modulos.all().delete()

            entidades_map = {}

            # =========================
            # 🔵 PASSO 1 — criar estrutura
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
                        nome_plural=ent_data.get('nome') + "s"
                    )

                    # 🔥 salva no mapa
                    entidades_map[entidade.nome] = entidade

            # =========================
            # 🔵 PASSO 2 — criar campos (AGORA COM FK)
            # =========================
            for mod_data in dados.get('modulos', []):

                for ent_data in mod_data.get('entidades', []):

                    entidade = entidades_map.get(ent_data.get('nome'))

                    for campo_data in ent_data.get('campos', []):

                        campo_kwargs = {
                            "entidade": entidade,
                            "nome": campo_data.get('nome'),
                            "tipo": campo_data.get('tipo', 'CharField'),
                            "max_length": campo_data.get('max_length') or 255,
                            "null": campo_data.get('null', False),
                            "blank": campo_data.get('blank', False),
                            "unique": campo_data.get('unique', False),
                            "default_value": campo_data.get('default'),
                            "upload_to": campo_data.get('upload_to'),
                            "related_name_str": campo_data.get('related_name'),
                            "on_delete": campo_data.get('on_delete', 'models.CASCADE'),
                        }

                        # 🔥 RELACIONAMENTO
                        rel_nome = campo_data.get('rel')

                        if rel_nome:
                            entidade_rel = entidades_map.get(rel_nome)

                            if entidade_rel:
                                campo_kwargs["entidade_relacionada"] = entidade_rel
                            else:
                                print(f"⚠️ Rel não encontrado: {rel_nome}")

                        Campo.objects.create(**campo_kwargs)

            return JsonResponse({
                "status": "sucesso",
                "sistema_id": sistema.id
            })

        except Exception as e:
            print("ERRO:", str(e))
            return JsonResponse({
                "status": "erro",
                "mensagem": str(e)
            }, status=400)
        

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

def processar_geracao_ajax(request, pk):
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