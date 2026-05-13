from django.db import models
from django.conf import settings  # Necessário para o AUTH_USER_MODEL

# --- IMPORTS DE OUTROS APPS ---



class Area(models.Model):
    
    
    nome = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Nome"
    )
    
    
    
    sigla = models.CharField(
        max_length=30,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Sigla"
    )
    
    
    
    
    # --- CAMPOS DE AUDITORIA ---
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    

    class Meta:
        verbose_name = "Area"
        verbose_name_plural = "Areass"

    def __str__(self):
        return str(self.nome)
