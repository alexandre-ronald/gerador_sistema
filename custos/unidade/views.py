from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Unidade
from .forms import UnidadeForm


# --- Views para Unidade ---

class UnidadeListView(LoginRequiredMixin, ListView):
    model = Unidade
    template_name = 'unidade/unidade_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Unidades"
        return context

class UnidadeCreateView(LoginRequiredMixin, CreateView):
    model = Unidade
    form_class = UnidadeForm
    template_name = 'unidade/unidade_form.html'
    success_url = reverse_lazy('unidade:unidade_list')

    def form_valid(self, form):
        messages.success(self.request, "Unidade criado com sucesso!")
        return super().form_valid(form)

class UnidadeUpdateView(LoginRequiredMixin, UpdateView):
    model = Unidade
    form_class = UnidadeForm
    template_name = 'unidade/unidade_form.html'
    success_url = reverse_lazy('unidade:unidade_list')

    def form_valid(self, form):
        messages.success(self.request, "Unidade atualizado!")
        return super().form_valid(form)

class UnidadeDeleteView(LoginRequiredMixin, DeleteView):
    model = Unidade
    template_name = 'unidade/unidade_confirm_delete.html'
    success_url = reverse_lazy('unidade:unidade_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Unidade removido.")
        return super().delete(request, *args, **kwargs)

