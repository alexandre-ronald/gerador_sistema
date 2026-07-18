from django.db import models
from django.conf import settings  # Necessário para o AUTH_USER_MODEL

# --- IMPORTS DE OUTROS APPS ---

from cadastros.models import Cargos, Organograma



class Eleitor(models.Model):
    
    
    nome = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Nome"
    )
    
    
    
    unidade = models.ForeignKey(
        'cadastros.Organograma',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name="Unidade"
    )
    
    
    
    

    class Meta:
        verbose_name = "Eleitor"
        verbose_name_plural = "Eleitorss"

    def __str__(self):
        return str(self.nome)

class Candidato(models.Model):
    
    
    cargo = models.ForeignKey(
        'cadastros.Cargos',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name="Cargo"
    )
    
    
    
    nome = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Nome"
    )
    
    
    
    

    class Meta:
        verbose_name = "Candidato"
        verbose_name_plural = "Candidatoss"

    def __str__(self):
        return str(self.cargo)
