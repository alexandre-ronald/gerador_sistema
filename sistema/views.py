import json
import os

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SistemaForm
from .models import Entidade, Modulo, Sistema
from .services import GeradorService
from .structure_service import save_system_structure, serialize_system_structure

User = get_user_model()


class RegistroUsuarioForm(forms.ModelForm):
    nome_completo = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={"class": "form-control bg-body", "placeholder": "Seu nome completo"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control bg-body", "placeholder": "seu@email.com"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control bg-body", "placeholder": "••••••••"}), label="Senha")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control bg-body", "placeholder": "••••••••"}), label="Confirme a Senha")

    class Meta:
        model = User
        fields = ["email", "password"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado no sistema.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("confirm_password") and cleaned["password"] != cleaned["confirm_password"]:
            self.add_error("confirm_password", "As senhas não coincidem.")
        return cleaned


@login_required
def registrar_usuario_view(request):
    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                nome = form.cleaned_data["nome_completo"].strip().split(" ", 1)
                user = User.objects.create_user(
                    username=form.cleaned_data["email"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password"],
                    first_name=nome[0],
                    last_name=nome[1] if len(nome) > 1 else "",
                )
            login(request, user)
            messages.success(request, f"Seja bem-vindo(a), {user.first_name}!")
            return redirect("sistema:dashboard")
    else:
        form = RegistroUsuarioForm()
    return render(request, "registration/registro.html", {"form": form})


@login_required
def lista_sistemas(request):
    sistemas = Sistema.objects.filter(usuario=request.user).order_by("-atualizado_em")
    return render(request, "sistema/lista.html", {"sistemas": sistemas})


@login_required
def criar_sistema(request):
    """Open the canonical editor; persistence happens only through salvar_modelo."""
    return render(request, "sistema/editor.html", {
        "estrutura_json": json.dumps({"sistema": {}, "modulos": []}, ensure_ascii=False),
        "sistema_id": None,
    })


@login_required
def editar_sistema(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    estrutura = serialize_system_structure(sistema)
    return render(request, "sistema/editor.html", {
        "estrutura_json": json.dumps(estrutura, ensure_ascii=False),
        "sistema_id": sistema.id,
    })


@login_required
@require_http_methods(["POST"])
def salvar_modelo(request):
    try:
        payload = json.loads(request.body or "{}")
        sistema_id = payload.get("sistema_id")
        sistema = save_system_structure(user=request.user, payload=payload, sistema_id=sistema_id)
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id})
    except Exception as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)


@login_required
@require_http_methods(["PUT", "POST"])
def atualizar_sistema(request, sistema_id):
    """Compatibility endpoint; delegates to the same canonical persistence service."""
    try:
        payload = json.loads(request.body or "{}")
        sistema = save_system_structure(user=request.user, payload=payload, sistema_id=sistema_id)
        return JsonResponse({"status": "sucesso", "sistema_id": sistema.id})
    except Exception as exc:
        return JsonResponse({"status": "erro", "mensagem": str(exc)}, status=400)


@login_required
@require_http_methods(["POST"])
def excluir_sistema(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)
    nome = sistema.nome
    sistema.delete()
    messages.success(request, f"Sistema '{nome}' excluído com sucesso!")
    return redirect("sistema:lista")


@login_required
def gerar_sistema_view(request, pk):
    sistema = get_object_or_404(Sistema, pk=pk, usuario=request.user)
    total_entidades = Entidade.objects.filter(modulo__sistema=sistema).count()
    return render(request, "sistema/gerar_sistema.html", {"sistema": sistema, "total_entidades": total_entidades})


@login_required
def processar_geracao_ajax(request, pk):
    """Compatibility wrapper around the canonical installer/generation endpoint."""
    from .installer_views import processar_geracao_ajax as canonical_process
    return canonical_process(request, pk)


@login_required
def gerar_sucesso_view(request, pk):
    sistema = get_object_or_404(Sistema, pk=pk, usuario=request.user)
    nome_projeto = GeradorService._python_identifier(sistema.nome, "projeto")
    return render(request, "sistema/gerar_sucesso.html", {
        "sistema": sistema,
        "nome_projeto": nome_projeto,
        "caminho": sistema.caminho_geracao,
    })


@login_required
def dashboard_view(request):
    sistemas = Sistema.objects.filter(usuario=request.user).prefetch_related("modulos")
    context = {
        "sistemas": sistemas,
        "total_modulos": Modulo.objects.filter(sistema__usuario=request.user).count(),
        "total_entidades": Entidade.objects.filter(modulo__sistema__usuario=request.user).count(),
        "total_zips": sistemas.exclude(arquivo_zip="").exclude(arquivo_zip__isnull=True).count(),
    }
    return render(request, "sistema/dashboard.html", context)


@login_required
def analytics_view(request):
    return render(request, "sistema/analytics.html")


@login_required
def users_view(request):
    return render(request, "sistema/users.html", {"users_list": User.objects.all().order_by("-date_joined")})


@login_required
def search_view(request):
    return render(request, "sistema/search.html", {"query": request.GET.get("q", ""), "results": []})


@login_required
def profile_view(request):
    return render(request, "sistema/profile.html")


@login_required
def settings_view(request):
    return render(request, "sistema/settings.html")


@login_required
def baixar_zip_sistema(request, pk):
    sistema = get_object_or_404(Sistema, pk=pk, usuario=request.user)
    if not sistema.arquivo_zip or not os.path.exists(sistema.arquivo_zip.path):
        raise Http404("O arquivo ZIP deste sistema não foi encontrado.")
    return FileResponse(open(sistema.arquivo_zip.path, "rb"), as_attachment=True, filename=os.path.basename(sistema.arquivo_zip.name))
