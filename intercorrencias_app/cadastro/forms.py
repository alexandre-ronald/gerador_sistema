from django import forms
from django.apps import apps # Importação vital para evitar o erro de loading


class AreaForm(forms.ModelForm):
    class Meta:
        # Buscamos o modelo dinamicamente para garantir que ele já foi carregado
        model = apps.get_model('cadastro', 'Area')
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Injeta classes do Bootstrap e melhora a exibição de ForeignKeys
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
            
            # Se for um campo de relacionamento, adiciona uma label amigável
            if isinstance(field, forms.models.ModelChoiceField):
                field.empty_label = "--- Selecione uma opção ---"
