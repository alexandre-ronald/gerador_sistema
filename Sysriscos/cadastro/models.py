from django.db import models
from django.conf import settings  # Necessário para o AUTH_USER_MODEL

# --- IMPORTS DE OUTROS APPS ---



class Organograma(models.Model):
    
    
    descrição = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Descrição"
    )
    
    
    
    sigla = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Sigla"
    )
    
    
    
    

    class Meta:
        verbose_name = "Organograma"
        verbose_name_plural = "Organogramass"

    def __str__(self):
        return str(self.descrição)
