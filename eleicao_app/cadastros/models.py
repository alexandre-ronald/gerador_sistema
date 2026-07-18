from django.db import models
from django.conf import settings  # Necessário para o AUTH_USER_MODEL

# --- IMPORTS DE OUTROS APPS ---



class Organograma(models.Model):
    
    
    descricao = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Descricao"
    )
    
    
    
    sigla = models.CharField(
        max_length=20,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Sigla"
    )
    
    
    
    

    class Meta:
        verbose_name = "Organograma"
        verbose_name_plural = "Organogramass"

    def __str__(self):
        return str(self.descricao)

class Cargos(models.Model):
    
    
    cargo = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Cargo"
    )
    
    
    
    

    class Meta:
        verbose_name = "Cargos"
        verbose_name_plural = "Cargosss"

    def __str__(self):
        return str(self.cargo)
