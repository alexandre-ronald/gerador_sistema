from django import forms


class FuncionRioForm(forms.ModelForm):
    class Meta:
        model = FuncionRio
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = '--- Selecione uma opção ---'

class OrganogramaForm(forms.ModelForm):
    class Meta:
        model = Organograma
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = '--- Selecione uma opção ---'

