from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Area
from .forms import AreaForm


# --- Views para Area ---

class AreaListView(LoginRequiredMixin, ListView):
    model = Area
    template_name = 'cadastro/area_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Areas"
        return context

class AreaCreateView(LoginRequiredMixin, CreateView):
    model = Area
    form_class = AreaForm
    template_name = 'cadastro/area_form.html'
    success_url = reverse_lazy('cadastro:area_list')

    def form_valid(self, form):
        messages.success(self.request, "Area criado com sucesso!")
        return super().form_valid(form)

class AreaUpdateView(LoginRequiredMixin, UpdateView):
    model = Area
    form_class = AreaForm
    template_name = 'cadastro/area_form.html'
    success_url = reverse_lazy('cadastro:area_list')

    def form_valid(self, form):
        messages.success(self.request, "Area atualizado!")
        return super().form_valid(form)

class AreaDeleteView(LoginRequiredMixin, DeleteView):
    model = Area
    template_name = 'cadastro/area_confirm_delete.html'
    success_url = reverse_lazy('cadastro:area_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Area removido.")
        return super().delete(request, *args, **kwargs)

