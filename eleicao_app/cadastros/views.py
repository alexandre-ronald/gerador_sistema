from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Organograma, Cargos
from .forms import OrganogramaForm, CargosForm


# --- Views para Organograma ---

class OrganogramaListView(LoginRequiredMixin, ListView):
    model = Organograma
    template_name = 'cadastros/organograma_list.html'
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
    template_name = 'cadastros/organograma_form.html'
    success_url = reverse_lazy('cadastros:organograma_list')

    def form_valid(self, form):
        messages.success(self.request, "Organograma criado com sucesso!")
        return super().form_valid(form)

class OrganogramaUpdateView(LoginRequiredMixin, UpdateView):
    model = Organograma
    form_class = OrganogramaForm
    template_name = 'cadastros/organograma_form.html'
    success_url = reverse_lazy('cadastros:organograma_list')

    def form_valid(self, form):
        messages.success(self.request, "Organograma atualizado!")
        return super().form_valid(form)

class OrganogramaDeleteView(LoginRequiredMixin, DeleteView):
    model = Organograma
    template_name = 'cadastros/organograma_confirm_delete.html'
    success_url = reverse_lazy('cadastros:organograma_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Organograma removido.")
        return super().delete(request, *args, **kwargs)


# --- Views para Cargos ---

class CargosListView(LoginRequiredMixin, ListView):
    model = Cargos
    template_name = 'cadastros/cargos_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Cargoss"
        return context

class CargosCreateView(LoginRequiredMixin, CreateView):
    model = Cargos
    form_class = CargosForm
    template_name = 'cadastros/cargos_form.html'
    success_url = reverse_lazy('cadastros:cargos_list')

    def form_valid(self, form):
        messages.success(self.request, "Cargos criado com sucesso!")
        return super().form_valid(form)

class CargosUpdateView(LoginRequiredMixin, UpdateView):
    model = Cargos
    form_class = CargosForm
    template_name = 'cadastros/cargos_form.html'
    success_url = reverse_lazy('cadastros:cargos_list')

    def form_valid(self, form):
        messages.success(self.request, "Cargos atualizado!")
        return super().form_valid(form)

class CargosDeleteView(LoginRequiredMixin, DeleteView):
    model = Cargos
    template_name = 'cadastros/cargos_confirm_delete.html'
    success_url = reverse_lazy('cadastros:cargos_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Cargos removido.")
        return super().delete(request, *args, **kwargs)

