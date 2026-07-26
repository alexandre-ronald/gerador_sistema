from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Centro De Custos, Custo
from .forms import Centro De CustosForm, CustoForm


# --- Views para Centro De Custos ---

class Centro De CustosListView(LoginRequiredMixin, ListView):
    model = Centro De Custos
    template_name = 'custo/centro de custos_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Centro De Custoss"
        return context

class Centro De CustosCreateView(LoginRequiredMixin, CreateView):
    model = Centro De Custos
    form_class = Centro De CustosForm
    template_name = 'custo/centro de custos_form.html'
    success_url = reverse_lazy('custo:centro de custos_list')

    def form_valid(self, form):
        messages.success(self.request, "Centro De Custos criado com sucesso!")
        return super().form_valid(form)

class Centro De CustosUpdateView(LoginRequiredMixin, UpdateView):
    model = Centro De Custos
    form_class = Centro De CustosForm
    template_name = 'custo/centro de custos_form.html'
    success_url = reverse_lazy('custo:centro de custos_list')

    def form_valid(self, form):
        messages.success(self.request, "Centro De Custos atualizado!")
        return super().form_valid(form)

class Centro De CustosDeleteView(LoginRequiredMixin, DeleteView):
    model = Centro De Custos
    template_name = 'custo/centro de custos_confirm_delete.html'
    success_url = reverse_lazy('custo:centro de custos_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Centro De Custos removido.")
        return super().delete(request, *args, **kwargs)


# --- Views para Custo ---

class CustoListView(LoginRequiredMixin, ListView):
    model = Custo
    template_name = 'custo/custo_list.html'
    context_object_name = 'objetos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Dados para os Cards de Sumário
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Custos"
        return context

class CustoCreateView(LoginRequiredMixin, CreateView):
    model = Custo
    form_class = CustoForm
    template_name = 'custo/custo_form.html'
    success_url = reverse_lazy('custo:custo_list')

    def form_valid(self, form):
        messages.success(self.request, "Custo criado com sucesso!")
        return super().form_valid(form)

class CustoUpdateView(LoginRequiredMixin, UpdateView):
    model = Custo
    form_class = CustoForm
    template_name = 'custo/custo_form.html'
    success_url = reverse_lazy('custo:custo_list')

    def form_valid(self, form):
        messages.success(self.request, "Custo atualizado!")
        return super().form_valid(form)

class CustoDeleteView(LoginRequiredMixin, DeleteView):
    model = Custo
    template_name = 'custo/custo_confirm_delete.html'
    success_url = reverse_lazy('custo:custo_list')

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Custo removido.")
        return super().delete(request, *args, **kwargs)

