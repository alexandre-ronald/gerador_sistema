from django.db import models
from django.conf import settings  # Necessário para o AUTH_USER_MODEL

# --- IMPORTS DE OUTROS APPS ---



class CentroDeCustos(models.Model):
    
    
    codigo = models.CharField(
        max_length=200,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Codigo"
    )
    
    
    
    nome = models.CharField(
        max_length=200,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Nome"
    )
    
    
    
    

    class Meta:
        verbose_name = "Centro De Custos"
        verbose_name_plural = "Centro De Custoss"

    def __str__(self):
        return str(self.codigo)

class Custo(models.Model):
    
    
    centro_custo = models.ForeignKey(
        'custo.CentroDeCustos',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name="Centro_Custo"
    )
    
    
    
    data = models.DateField(
        
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Data"
    )
    
    
    
    descricao = models.CharField(
        max_length=200,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Descricao"
    )
    
    
    
    valor = models.DecimalField(
        
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Valor"
    )
    
    
    
    

    class Meta:
        verbose_name = "Custo"
        verbose_name_plural = "Custos"

    def __str__(self):
        return str(self.centro_custo)
