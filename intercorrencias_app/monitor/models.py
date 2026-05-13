from django.db import models
from django.conf import settings  # Necessário para o AUTH_USER_MODEL

# --- IMPORTS DE OUTROS APPS ---

from cadastro.models import Area



class Equipamento(models.Model):
    
    
    area = models.ForeignKey(
        'cadastro.Area',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name="Area"
    )
    
    
    
    nome = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Nome"
    )
    
    
    
    
    # --- CAMPOS DE AUDITORIA ---
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    

    class Meta:
        verbose_name = "Equipamento"
        verbose_name_plural = "Equipamentoss"

    def __str__(self):
        return str(self.area)

class Tipo_Intercorrencia(models.Model):
    
    
    nome = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Nome"
    )
    
    
    
    
    # --- CAMPOS DE AUDITORIA ---
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    

    class Meta:
        verbose_name = "Tipo_Intercorrencia"
        verbose_name_plural = "Tipo_Intercorrenciass"

    def __str__(self):
        return str(self.nome)

class Intercorrencia(models.Model):
    
    
    area = models.ForeignKey(
        'cadastro.Area',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name="Area"
    )
    
    
    
    criado_em = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Criado_Em"
    )
    
    
    
    criado_por = models.IntegerField(
        
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Criado_Por"
    )
    
    
    
    data_final = models.DateField(
        
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Data_Final"
    )
    
    
    
    data_inicio = models.DateField(
        
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Data_Inicio"
    )
    
    
    
    descricao = models.CharField(
        max_length=255,
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Descricao"
    )
    
    
    
    dias_impacto = models.IntegerField(
        
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Dias_Impacto"
    )
    
    
    
    equipamento = models.ForeignKey(
        'monitor.Equipamento',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name="Equipamento"
    )
    
    
    
    qtd_exames_impactados = models.IntegerField(
        
        
        null=False,
        blank=False,
        unique=False,
        verbose_name="Qtd_Exames_Impactados"
    )
    
    
    
    tipo = models.ForeignKey(
        'monitor.Tipo_Intercorrencia',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name="Tipo"
    )
    
    
    
    
    # --- CAMPOS DE AUDITORIA ---
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    

    class Meta:
        verbose_name = "Intercorrencia"
        verbose_name_plural = "Intercorrenciass"

    def __str__(self):
        return str(self.area)
