from django.db import models

# --- IMPORTS DE OUTROS APPS ---

from cadastros.models import Cargos, Organograma



class Eleitor(models.Model):
    
    
    
    nome = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Nome"
    )
    
    
    
    
    unidade = models.ForeignKey(
        Organograma, 
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        verbose_name="Unidade"
    )
    
    

    def __str__(self):
        return str(self.nome)

class Candidato(models.Model):
    
    
    
    cargo = models.ForeignKey(
        Cargos, 
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        verbose_name="Cargo"
    )
    
    
    
    
    nome = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        verbose_name="Nome"
    )
    
    

    def __str__(self):
        return str(self.cargo)
