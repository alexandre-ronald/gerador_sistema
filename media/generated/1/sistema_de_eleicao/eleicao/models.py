from django.db import models
from django.conf import settings




class Candidato(models.Model):


    cargo = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        
        verbose_name=""
    )



    nome_do_candidato = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")


    class Meta:
        verbose_name = "Candidato"
        verbose_name_plural = "Candidatos"

    def __str__(self):
        return str(self.cargo)

class Cargo(models.Model):


    descricao = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    sigla = models.CharField(
        max_length=10,
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")


    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"

    def __str__(self):
        return str(self.descricao)

