from django import forms
from .models import Sistema


class SistemaForm(forms.ModelForm):
    class Meta:
        model = Sistema
        fields = ['nome', 'descricao', 'caminho_geracao']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition',
                'placeholder': 'Ex: CRM Empresarial, Loja Virtual 2025'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition',
                'rows': 4,
                'placeholder': 'Breve descrição do propósito do sistema...'
            }),
            'caminho_geracao': forms.TextInput(attrs={
                'class': 'flex-1 rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition',
                'placeholder': 'Ex: /home/user/projetos/gerados/meu_crm'
            }),
        }