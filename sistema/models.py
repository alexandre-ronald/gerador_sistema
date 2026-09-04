from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify
import keyword
import re

User = get_user_model()


class Sistema(models.Model):
    BD_CHOICES = [("sqlite3", "SQLite"), ("postgresql", "PostgreSQL"), ("mysql", "MySQL"), ("sqlserver", "SQL Server"), ("oracle", "Oracle")]
    MENU_CHOICES = [("lateral", "Menu Lateral (Sidebar)"), ("superior", "Menu Superior (Navbar)")]
    TIPO_CADASTRO = "cadastro"
    TIPO_WORKFLOW = "workflow"
    TIPO_GESTAO = "gestao"
    TIPO_VAZIO = "vazio"
    TIPO_SISTEMA_CHOICES = [
        (TIPO_CADASTRO, "Cadastro e Controle"),
        (TIPO_WORKFLOW, "Solicitações e Workflow"),
        (TIPO_GESTAO, "Gestão e Acompanhamento"),
        (TIPO_VAZIO, "Começar vazio"),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Sistema")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    tipo_sistema = models.CharField(max_length=20, choices=TIPO_SISTEMA_CHOICES, default=TIPO_VAZIO, verbose_name="Tipo inicial")
    caminho_geracao = models.CharField(max_length=255, blank=True, verbose_name="Pasta onde gerar o projeto")
    banco_dados = models.CharField(max_length=50, choices=BD_CHOICES, default="sqlite3", verbose_name="Banco de dados")
    tipo_menu = models.CharField(max_length=20, choices=MENU_CHOICES, default="lateral", verbose_name="Estilo do Menu")
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


class VersaoGeracao(models.Model):
    STATUS_DRAFT = "DRAFT"
    STATUS_VALIDATING = "VALIDATING"
    STATUS_VALIDATED = "VALIDATED"
    STATUS_RELEASED = "RELEASED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Rascunho"),
        (STATUS_VALIDATING, "Em validação"),
        (STATUS_VALIDATED, "Validada"),
        (STATUS_RELEASED, "Publicada"),
    ]

    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, related_name="versoes")
    numero = models.PositiveIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)
    descricao = models.CharField(max_length=255, blank=True)
    estrutura_json = models.JSONField(default=dict)
    arquivo_zip = models.FileField(upload_to="sistemas_versoes/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    changelog = models.TextField(blank=True)
    validado_em = models.DateTimeField(null=True, blank=True)
    publicado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Versão de Geração"
        verbose_name_plural = "Versões de Geração"
        ordering = ["-numero"]
        constraints = [models.UniqueConstraint(fields=["sistema", "numero"], name="uniq_versao_sistema_numero")]

    @property
    def is_draft(self):
        return self.numero == 0 or self.status == self.STATUS_DRAFT

    @property
    def can_release(self):
        return self.numero > 0 and self.status == self.STATUS_VALIDATED

    def __str__(self):
        return f"{self.sistema.nome} v{self.numero}"


class Ambiente(models.Model):
    TIPO_DEVELOPMENT = "DEVELOPMENT"
    TIPO_TEST = "TEST"
    TIPO_STAGING = "STAGING"
    TIPO_PRODUCTION = "PRODUCTION"
    TIPO_CHOICES = [
        (TIPO_DEVELOPMENT, "Development"),
        (TIPO_TEST, "Test"),
        (TIPO_STAGING, "Staging"),
        (TIPO_PRODUCTION, "Production"),
    ]

    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, related_name="ambientes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nome = models.CharField(max_length=100)
    url_base = models.URLField(blank=True)
    ativo = models.BooleanField(default=True)
    release_atual = models.ForeignKey(
        VersaoGeracao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ambientes_atuais",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ambiente"
        verbose_name_plural = "Ambientes"
        ordering = ["sistema", "tipo"]
        constraints = [
            models.UniqueConstraint(fields=["sistema", "tipo"], name="uniq_ambiente_sistema_tipo")
        ]

    def __str__(self):
        return f"{self.sistema.nome} · {self.get_tipo_display()}"


class PromocaoAmbiente(models.Model):
    ambiente = models.ForeignKey(Ambiente, on_delete=models.CASCADE, related_name="promocoes")
    versao = models.ForeignKey(VersaoGeracao, on_delete=models.PROTECT, related_name="promocoes_ambiente")
    promovido_em = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Promoção de Ambiente"
        verbose_name_plural = "Promoções de Ambiente"
        ordering = ["-promovido_em", "-id"]

    def __str__(self):
        return f"{self.ambiente} → v{self.versao.numero}"


class Modulo(models.Model):
    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, related_name="modulos")
    nome = models.CharField(max_length=100, verbose_name="Nome do Módulo (App)")
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f"{self.sistema.nome} → {self.nome}"

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
    gerar_crud_views = models.BooleanField(default=True, verbose_name="Gerar Views e Templates de CRUD?")
    gerar_endpoints_api = models.BooleanField(default=False, verbose_name="Gerar ViewSets e Serializers (API)?")

    def __str__(self):
        return f"{self.modulo.nome} → {self.nome}"

    class Meta:
        verbose_name = "Entidade"
        verbose_name_plural = "Entidades"
        unique_together = ("modulo", "nome")


class Campo(models.Model):
    TIPO_CAMPO_CHOICES = [(x, x) for x in ["CharField", "TextField", "IntegerField", "FloatField", "DecimalField", "BooleanField", "DateField", "DateTimeField", "TimeField", "EmailField", "URLField", "FileField", "ImageField", "ForeignKey", "ManyToManyField", "OneToOneField"]]
    ON_DELETE_CHOICES = [("models.CASCADE", "CASCADE"), ("models.PROTECT", "PROTECT"), ("models.SET_NULL", "SET_NULL"), ("models.RESTRICT", "RESTRICT")]

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

    @codigo_nome.setter
    def codigo_nome(self, value):
        pass

    def __str__(self):
        return f"{self.entidade.nome}.{self.nome} ({self.tipo})"

    class Meta:
        verbose_name = "Campo"
        verbose_name_plural = "Campos"
        ordering = ["entidade", "nome"]


from .runtime_models import RuntimeCheck, RuntimeSnapshot
from .deployment_models import DeploymentPlan
from .observability_models import ObservabilityEvent
