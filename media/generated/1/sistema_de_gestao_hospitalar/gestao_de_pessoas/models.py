from django.db import models
from django.conf import settings




class FuncionRio(models.Model):


    cpf = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    data_de_admissao = models.DateField(
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    nome_completo = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")


    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionário"

    def __str__(self):
        return str(self.cpf)

class Organograma(models.Model):


    descricao = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    sigla = models.CharField(
        max_length=15,
        null=False,
        blank=False,
        unique=False,
        verbose_name=""
    )



    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")


    class Meta:
        verbose_name = "Organograma"
        verbose_name_plural = "Organograma"

    def __str__(self):
        return str(self.descricao)

