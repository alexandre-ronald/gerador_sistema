from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Equipamento, Tipo_Intercorrencia, Intercorrencia
from .forms import EquipamentoForm, Tipo_IntercorrenciaForm, IntercorrenciaForm


# --- Views para Equipamento ---

class EquipamentoListView(LoginRequiredMixin, ListView):
    model = Equipamento
    template_name = 'monitor/equipamento_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Equipamentos"
        return context

class EquipamentoCreateView(LoginRequiredMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'monitor/equipamento_form.html'
    success_url = reverse_lazy('monitor:equipamento_list')

    def form_valid(self, form):
        messages.success(self.request, "Equipamento criado com sucesso!")
        return super().form_valid(form)

class EquipamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'monitor/equipamento_form.html'
    success_url = reverse_lazy('monitor:equipamento_list')

    def form_valid(self, form):
        messages.success(self.request, "Equipamento atualizado!")
        return super().form_valid(form)

class EquipamentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Equipamento
    template_name = 'monitor/equipamento_confirm_delete.html'
    success_url = reverse_lazy('monitor:equipamento_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Equipamento removido.")
        return super().delete(request, *args, **kwargs)


# --- Views para Tipo_Intercorrencia ---

class Tipo_IntercorrenciaListView(LoginRequiredMixin, ListView):
    model = Tipo_Intercorrencia
    template_name = 'monitor/tipo_intercorrencia_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Tipo_Intercorrencias"
        return context

class Tipo_IntercorrenciaCreateView(LoginRequiredMixin, CreateView):
    model = Tipo_Intercorrencia
    form_class = Tipo_IntercorrenciaForm
    template_name = 'monitor/tipo_intercorrencia_form.html'
    success_url = reverse_lazy('monitor:tipo_intercorrencia_list')

    def form_valid(self, form):
        messages.success(self.request, "Tipo_Intercorrencia criado com sucesso!")
        return super().form_valid(form)

class Tipo_IntercorrenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Tipo_Intercorrencia
    form_class = Tipo_IntercorrenciaForm
    template_name = 'monitor/tipo_intercorrencia_form.html'
    success_url = reverse_lazy('monitor:tipo_intercorrencia_list')

    def form_valid(self, form):
        messages.success(self.request, "Tipo_Intercorrencia atualizado!")
        return super().form_valid(form)

class Tipo_IntercorrenciaDeleteView(LoginRequiredMixin, DeleteView):
    model = Tipo_Intercorrencia
    template_name = 'monitor/tipo_intercorrencia_confirm_delete.html'
    success_url = reverse_lazy('monitor:tipo_intercorrencia_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Tipo_Intercorrencia removido.")
        return super().delete(request, *args, **kwargs)


# --- Views para Intercorrencia ---

class IntercorrenciaListView(LoginRequiredMixin, ListView):
    model = Intercorrencia
    template_name = 'monitor/intercorrencia_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Intercorrencias"
        return context

class IntercorrenciaCreateView(LoginRequiredMixin, CreateView):
    model = Intercorrencia
    form_class = IntercorrenciaForm
    template_name = 'monitor/intercorrencia_form.html'
    success_url = reverse_lazy('monitor:intercorrencia_list')

    def form_valid(self, form):
        messages.success(self.request, "Intercorrencia criado com sucesso!")
        return super().form_valid(form)

class IntercorrenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Intercorrencia
    form_class = IntercorrenciaForm
    template_name = 'monitor/intercorrencia_form.html'
    success_url = reverse_lazy('monitor:intercorrencia_list')

    def form_valid(self, form):
        messages.success(self.request, "Intercorrencia atualizado!")
        return super().form_valid(form)

class IntercorrenciaDeleteView(LoginRequiredMixin, DeleteView):
    model = Intercorrencia
    template_name = 'monitor/intercorrencia_confirm_delete.html'
    success_url = reverse_lazy('monitor:intercorrencia_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Intercorrencia removido.")
        return super().delete(request, *args, **kwargs)

