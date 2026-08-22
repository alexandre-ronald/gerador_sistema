from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from .models import FuncionRio, Organograma
from .forms import FuncionRioForm, OrganogramaForm


class FuncionRioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = FuncionRio
    template_name = 'gestao_de_pessoas/funcionario_list.html'
    context_object_name = 'objetos'
    paginate_by = 10
    permission_required = 'gestao_de_pessoas.view_funcionario'
    raise_exception = True

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            search_filter = Q()

            search_filter |= Q(cpf__icontains=query)

            search_filter |= Q(nome_completo__icontains=query)

            queryset = queryset.filter(search_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Funcionário"
        context['search_query'] = self.request.GET.get('q', '').strip()
        return context


class FuncionRioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = FuncionRio
    form_class = FuncionRioForm
    template_name = 'gestao_de_pessoas/funcionario_form.html'
    success_url = reverse_lazy('gestao_de_pessoas:funcionario_list')
    permission_required = 'gestao_de_pessoas.add_funcionario'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Funcionário criado com sucesso!")
        return super().form_valid(form)


class FuncionRioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = FuncionRio
    form_class = FuncionRioForm
    template_name = 'gestao_de_pessoas/funcionario_form.html'
    success_url = reverse_lazy('gestao_de_pessoas:funcionario_list')
    permission_required = 'gestao_de_pessoas.change_funcionario'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Funcionário atualizado!")
        return super().form_valid(form)


class FuncionRioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = FuncionRio
    template_name = 'gestao_de_pessoas/funcionario_confirm_delete.html'
    success_url = reverse_lazy('gestao_de_pessoas:funcionario_list')
    permission_required = 'gestao_de_pessoas.delete_funcionario'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Funcionário removido.")
        return super().delete(request, *args, **kwargs)


class OrganogramaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Organograma
    template_name = 'gestao_de_pessoas/organograma_list.html'
    context_object_name = 'objetos'
    paginate_by = 10
    permission_required = 'gestao_de_pessoas.view_organograma'
    raise_exception = True

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            search_filter = Q()

            search_filter |= Q(descricao__icontains=query)

            search_filter |= Q(sigla__icontains=query)

            queryset = queryset.filter(search_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Organograma"
        context['search_query'] = self.request.GET.get('q', '').strip()
        return context


class OrganogramaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Organograma
    form_class = OrganogramaForm
    template_name = 'gestao_de_pessoas/organograma_form.html'
    success_url = reverse_lazy('gestao_de_pessoas:organograma_list')
    permission_required = 'gestao_de_pessoas.add_organograma'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Organograma criado com sucesso!")
        return super().form_valid(form)


class OrganogramaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Organograma
    form_class = OrganogramaForm
    template_name = 'gestao_de_pessoas/organograma_form.html'
    success_url = reverse_lazy('gestao_de_pessoas:organograma_list')
    permission_required = 'gestao_de_pessoas.change_organograma'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Organograma atualizado!")
        return super().form_valid(form)


class OrganogramaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Organograma
    template_name = 'gestao_de_pessoas/organograma_confirm_delete.html'
    success_url = reverse_lazy('gestao_de_pessoas:organograma_list')
    permission_required = 'gestao_de_pessoas.delete_organograma'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Organograma removido.")
        return super().delete(request, *args, **kwargs)


