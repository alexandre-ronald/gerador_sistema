from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Organograma
from .forms import OrganogramaForm


# --- Views para Organograma ---

class OrganogramaListView(LoginRequiredMixin, ListView):
    model = Organograma
    template_name = 'cadastro/organograma_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Organogramas"
        return context

class OrganogramaCreateView(LoginRequiredMixin, CreateView):
    model = Organograma
    form_class = OrganogramaForm
    template_name = 'cadastro/organograma_form.html'
    success_url = reverse_lazy('cadastro:organograma_list')

    def form_valid(self, form):
        messages.success(self.request, "Organograma criado com sucesso!")
        return super().form_valid(form)

class OrganogramaUpdateView(LoginRequiredMixin, UpdateView):
    model = Organograma
    form_class = OrganogramaForm
    template_name = 'cadastro/organograma_form.html'
    success_url = reverse_lazy('cadastro:organograma_list')

    def form_valid(self, form):
        messages.success(self.request, "Organograma atualizado!")
        return super().form_valid(form)

class OrganogramaDeleteView(LoginRequiredMixin, DeleteView):
    model = Organograma
    template_name = 'cadastro/organograma_confirm_delete.html'
    success_url = reverse_lazy('cadastro:organograma_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Organograma removido.")
        return super().delete(request, *args, **kwargs)

