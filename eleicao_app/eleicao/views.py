from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Eleitor, Candidato
from .forms import EleitorForm, CandidatoForm


# --- Views para Eleitor ---

class EleitorListView(LoginRequiredMixin, ListView):
    model = Eleitor
    template_name = 'eleicao/eleitor_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Eleitors"
        return context

class EleitorCreateView(LoginRequiredMixin, CreateView):
    model = Eleitor
    form_class = EleitorForm
    template_name = 'eleicao/eleitor_form.html'
    success_url = reverse_lazy('eleicao:eleitor_list')

    def form_valid(self, form):
        messages.success(self.request, "Eleitor criado com sucesso!")
        return super().form_valid(form)

class EleitorUpdateView(LoginRequiredMixin, UpdateView):
    model = Eleitor
    form_class = EleitorForm
    template_name = 'eleicao/eleitor_form.html'
    success_url = reverse_lazy('eleicao:eleitor_list')

    def form_valid(self, form):
        messages.success(self.request, "Eleitor atualizado!")
        return super().form_valid(form)

class EleitorDeleteView(LoginRequiredMixin, DeleteView):
    model = Eleitor
    template_name = 'eleicao/eleitor_confirm_delete.html'
    success_url = reverse_lazy('eleicao:eleitor_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Eleitor removido.")
        return super().delete(request, *args, **kwargs)


# --- Views para Candidato ---

class CandidatoListView(LoginRequiredMixin, ListView):
    model = Candidato
    template_name = 'eleicao/candidato_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Candidatos"
        return context

class CandidatoCreateView(LoginRequiredMixin, CreateView):
    model = Candidato
    form_class = CandidatoForm
    template_name = 'eleicao/candidato_form.html'
    success_url = reverse_lazy('eleicao:candidato_list')

    def form_valid(self, form):
        messages.success(self.request, "Candidato criado com sucesso!")
        return super().form_valid(form)

class CandidatoUpdateView(LoginRequiredMixin, UpdateView):
    model = Candidato
    form_class = CandidatoForm
    template_name = 'eleicao/candidato_form.html'
    success_url = reverse_lazy('eleicao:candidato_list')

    def form_valid(self, form):
        messages.success(self.request, "Candidato atualizado!")
        return super().form_valid(form)

class CandidatoDeleteView(LoginRequiredMixin, DeleteView):
    model = Candidato
    template_name = 'eleicao/candidato_confirm_delete.html'
    success_url = reverse_lazy('eleicao:candidato_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Candidato removido.")
        return super().delete(request, *args, **kwargs)

