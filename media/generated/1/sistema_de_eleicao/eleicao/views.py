from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from .models import Candidato, Cargo
from .forms import CandidatoForm, CargoForm


class CandidatoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Candidato
    template_name = 'eleicao/candidato_list.html'
    context_object_name = 'objetos'
    paginate_by = 10
    permission_required = 'eleicao.view_candidato'
    raise_exception = True

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            search_filter = Q()

            search_filter |= Q(nome_do_candidato__icontains=query)

            queryset = queryset.filter(search_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_registros'] = self.get_queryset().count()
        context['titulo_pagina'] = "Candidato"
        context['search_query'] = self.request.GET.get('q', '').strip()
        return context


class CandidatoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Candidato
    form_class = CandidatoForm
    template_name = 'eleicao/candidato_form.html'
    success_url = reverse_lazy('eleicao:candidato_list')
    permission_required = 'eleicao.add_candidato'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Candidato criado com sucesso!")
        return super().form_valid(form)


class CandidatoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Candidato
    form_class = CandidatoForm
    template_name = 'eleicao/candidato_form.html'
    success_url = reverse_lazy('eleicao:candidato_list')
    permission_required = 'eleicao.change_candidato'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Candidato atualizado!")
        return super().form_valid(form)


class CandidatoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Candidato
    template_name = 'eleicao/candidato_confirm_delete.html'
    success_url = reverse_lazy('eleicao:candidato_list')
    permission_required = 'eleicao.delete_candidato'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Candidato removido.")
        return super().delete(request, *args, **kwargs)


class CargoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Cargo
    template_name = 'eleicao/cargo_list.html'
    context_object_name = 'objetos'
    paginate_by = 10
    permission_required = 'eleicao.view_cargo'
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
        context['titulo_pagina'] = "Cargo"
        context['search_query'] = self.request.GET.get('q', '').strip()
        return context


class CargoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'eleicao/cargo_form.html'
    success_url = reverse_lazy('eleicao:cargo_list')
    permission_required = 'eleicao.add_cargo'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Cargo criado com sucesso!")
        return super().form_valid(form)


class CargoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'eleicao/cargo_form.html'
    success_url = reverse_lazy('eleicao:cargo_list')
    permission_required = 'eleicao.change_cargo'
    raise_exception = True

    def form_valid(self, form):
        messages.success(self.request, "Cargo atualizado!")
        return super().form_valid(form)


class CargoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Cargo
    template_name = 'eleicao/cargo_confirm_delete.html'
    success_url = reverse_lazy('eleicao:cargo_list')
    permission_required = 'eleicao.delete_cargo'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "Cargo removido.")
        return super().delete(request, *args, **kwargs)


