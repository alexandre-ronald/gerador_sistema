from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify
import keyword
import re

User = get_user_model()


class Sistema(models.Model):
    BD_CHOICES = [
        ("sqlite3", "SQLite"),
        ("postgresql", "PostgreSQL"),
        ("mysql", "MySQL"),
        ("sqlserver", "SQL Server"),
        ("oracle", "Oracle"),
    ]

    MENU_CHOICES = [
        ("lateral", "Menu Lateral (Sidebar)"),
        ("superior", "Menu Superior (Navbar)"),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Sistema")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    caminho_geracao = models.CharField(
        max_length=255, blank=True, verbose_name="Pasta onde gerar o projeto"
    )
    banco_dados = models.CharField(
        max_length=50, choices=BD_CHOICES, default="sqlite3", verbose_name="Banco de dados"
    )
    tipo_menu = models.CharField(
        max_length=20, choices=MENU_CHOICES, default="lateral", verbose_name="Estilo do Menu"
    )
    usar_custom_user = models.BooleanField(default=True, verbose_name="Gerar Custom User Model?")
    gerar_api_rest = models.BooleanField(default=False, verbose_name="Configurar Django Rest Framework?")
    gerar_docker = models.BooleanField(default=False, verbose_name="Gerar Dockerfile e docker-compose?")
    usar_auditoria = models.BooleanField(default=False, verbose_name="Usar Auditoria?")
    slug = models.SlugField(max_length=100)
    arquivo_zip = models.FileField(upload_to="sistemas_zip/", null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Sistema"
        verbose_name_plural = "Sistemas"


class Modulo(models.Model):
    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, related_name="modulos")
    nome = models.CharField(max_length=100, verbose_name="Nome do Módulo (App)")
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f"{self.sistema.nome} → {self.nome}"

    @property
    def app_name(self):
        value = slugify(str(self.nome or ""), allow_unicode=False).replace("-", "_")
        value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
        value = re.sub(r"_+", "_", value).strip("_") or "app"
        if value[0].isdigit():
            value = f"_{value}"
        if keyword.iskeyword(value):
            value = f"{value}_"
        return value

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"
        unique_together = ("sistema", "nome")


class Entidade(models.Model):
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name="entidades")
    nome = models.CharField(max_length=100, verbose_name="Nome da Entidade (Model)")
    nome_plural = models.CharField(max_length=100, blank=True, verbose_name="Nome no Plural (Verbose Name Plural)")
    descricao = models.TextField(blank=True)
    gerar_admin = models.BooleanField(default=True, verbose_name="Registrar no admin.py?")
    gerar_crud_views = models.BooleanField(default=False, verbose_name="Gerar Views e Templates de CRUD?")
    gerar_endpoints_api = models.BooleanField(default=False, verbose_name="Gerar ViewSets e Serializers (API)?")

    def __str__(self):
        return f"{self.modulo.nome} → {self.nome}"

    @property
    def classe_nome(self):
        words = re.findall(r"[A-Za-z0-9]+", str(self.nome or ""))
        name = "".join(word[:1].upper() + word[1:] for word in words) or "Modelo"
        return f"Modelo{name}" if name[0].isdigit() else name

    @property
    def codigo_nome(self):
        value = slugify(str(self.nome or ""), allow_unicode=False).replace("-", "_")
        value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
        value = re.sub(r"_+", "_", value).strip("_") or "entidade"
        if value[0].isdigit():
            value = f"_{value}"
        if keyword.iskeyword(value):
            value = f"{value}_"
        return value

    class Meta:
        verbose_name = "Entidade"
        verbose_name_plural = "Entidades"
        unique_together = ("modulo", "nome")


class Campo(models.Model):
    TIPO_CAMPO_CHOICES = [
        ("CharField", "CharField"), ("TextField", "TextField"), ("IntegerField", "IntegerField"),
        ("FloatField", "FloatField"), ("DecimalField", "DecimalField"), ("BooleanField", "BooleanField"),
        ("DateField", "DateField"), ("DateTimeField", "DateTimeField"), ("TimeField", "TimeField"),
        ("EmailField", "EmailField"), ("URLField", "URLField"), ("FileField", "FileField"),
        ("ImageField", "ImageField"), ("ForeignKey", "ForeignKey"),
        ("ManyToManyField", "ManyToManyField"), ("OneToOneField", "OneToOneField"),
    ]

    ON_DELETE_CHOICES = [
        ("models.CASCADE", "CASCADE"), ("models.PROTECT", "PROTECT"),
        ("models.SET_NULL", "SET_NULL"), ("models.RESTRICT", "RESTRICT"),
    ]

    entidade = models.ForeignKey(Entidade, on_delete=models.CASCADE, related_name="campos")
    nome = models.CharField(max_length=100, verbose_name="Nome do Campo")
    tipo = models.CharField(max_length=20, choices=TIPO_CAMPO_CHOICES, verbose_name="Tipo do Campo")
    null = models.BooleanField(default=False)
    blank = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    default_value = models.CharField(max_length=255, blank=True, help_text="Valor padrão (ex: 'Ativo', True, 0)")
    max_length = models.PositiveIntegerField(null=True, blank=True, verbose_name="Max Length")
    max_digits = models.PositiveIntegerField(null=True, blank=True, verbose_name="Dígitos Totais (Decimal)")
    decimal_places = models.PositiveIntegerField(null=True, blank=True, verbose_name="Casas Decimais (Decimal)")
    upload_to = models.CharField(max_length=255, blank=True, verbose_name="Pasta de Upload (File/Image)")
    entidade_relacionada = models.ForeignKey(Entidade, on_delete=models.SET_NULL, null=True, blank=True, related_name="campos_relacionados", verbose_name="Entidade Relacionada")
    on_delete = models.CharField(max_length=50, choices=ON_DELETE_CHOICES, default="models.CASCADE", blank=True)
    related_name_str = models.CharField(max_length=100, blank=True, verbose_name="Related Name")
    verbose_name = models.CharField(max_length=100, blank=True)
    help_text = models.TextField(blank=True)

    @property
    def eh_relacional(self):
        return self.tipo in {"ForeignKey", "OneToOneField", "ManyToManyField"}

    @property
    def codigo_nome(self):
        value = slugify(str(self.nome or ""), allow_unicode=False).replace("-", "_")
        value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
        value = re.sub(r"_+", "_", value).strip("_") or "campo"
        if value[0].isdigit():
            value = f"_{value}"
        if keyword.iskeyword(value):
            value = f"{value}_"
        return value

    def __str__(self):
        return f"{self.entidade.nome}.{self.nome} ({self.tipo})"

    class Meta:
        verbose_name = "Campo"
        verbose_name_plural = "Campos"
        ordering = ["entidade", "nome"]
