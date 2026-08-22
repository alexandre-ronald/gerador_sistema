from django import forms


class CandidatoForm(forms.ModelForm):
    class Meta:
        model = Candidato
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = '--- Selecione uma opção ---'

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = '--- Selecione uma opção ---'

