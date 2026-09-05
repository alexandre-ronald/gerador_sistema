from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Sistema


class InterfaceDesignerForm(forms.ModelForm):
    class Meta:
        model = Sistema
        fields = [
            "tipo_menu",
            "interface_modo",
            "interface_densidade",
            "interface_nome",
            "interface_cor_primaria",
            "interface_cor_destaque",
            "interface_breadcrumb",
            "interface_busca",
            "interface_notificacoes",
            "interface_menu_usuario",
        ]
        widgets = {
            "tipo_menu": forms.RadioSelect(),
            "interface_modo": forms.RadioSelect(),
            "interface_densidade": forms.RadioSelect(),
            "interface_nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Sistema de Contratos"}),
            "interface_cor_primaria": forms.TextInput(attrs={"class": "form-control form-control-color", "type": "color"}),
            "interface_cor_destaque": forms.TextInput(attrs={"class": "form-control form-control-color", "type": "color"}),
            "interface_breadcrumb": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "interface_busca": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "interface_notificacoes": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "interface_menu_usuario": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


@login_required
def interface_designer(request, sistema_id):
    sistema = get_object_or_404(Sistema, pk=sistema_id, usuario=request.user)

    if request.method == "POST":
        form = InterfaceDesignerForm(request.POST, instance=sistema)
        if form.is_valid():
            form.save()
            messages.success(request, "Interface atualizada com sucesso.")
            return redirect("sistema:interface_designer", sistema_id=sistema.pk)
    else:
        form = InterfaceDesignerForm(instance=sistema)

    return render(request, "sistema/interface_designer.html", {
        "sistema": sistema,
        "form": form,
    })
