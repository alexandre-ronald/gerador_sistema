from django.db import models
from django.conf import settings  # Necessário para o AUTH_USER_MODEL

# --- IMPORTS DE OUTROS APPS ---



class Unidade(models.Model):
    
    
    nome = models.CharField(
        max_length=500,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Nome"
    )
    
    
    
    sigla = models.CharField(
        max_length=200,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Sigla"
    )
    
    
    
    

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"

    def __str__(self):
        return str(self.nome)
