from django.db import models

# --- IMPORTS DE OUTROS APPS ---



class Organograma(models.Model):
    
    
    
    descricao = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Descricao"
    )
    
    
    
    
    sigla = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        verbose_name="Sigla"
    )
    
    

    def __str__(self):
        return str(self.descricao)

class Cargos(models.Model):
    
    
    
    cargo = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Cargo"
    )
    
    

    def __str__(self):
        return str(self.cargo)
