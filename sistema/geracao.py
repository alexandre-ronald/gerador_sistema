import os
import zipfile
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.urls import reverse

from .models import Sistema
from .services import GeradorService


def processar_geracao_ajax(request, pk):
    """Gera o projeto usando o GeradorService e compacta os artefatos já gerados.

    O instalacao.bat é materializado pelo próprio GeradorService. Esta função
    deliberadamente não recria nem sobrescreve esse arquivo, evitando que um
    instalador legado seja injetado depois da geração.
    """
    try:
        gerador = GeradorService(pk)
        logs_execucao = gerador.gerar_projeto_completo()

        sistema = get_object_or_404(Sistema, pk=pk)
        diretorio_destino = gerador.diretorio_base

        if not diretorio_destino.is_dir():
            raise RuntimeError(
                f"Diretório de destino '{diretorio_destino}' não foi localizado após a geração."
            )

        instalador = diretorio_destino / "instalacao.bat"
        if not instalador.is_file():
            raise RuntimeError(
                "O GeradorService não materializou instalacao.bat. "
                "A geração foi interrompida para evitar exportar um projeto incompleto."
            )

        logs_execucao.append("📦 Compactando os artefatos gerados...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_zip = f"{slugify(sistema.nome)}_{timestamp}.zip"
        diretorio_zips = os.path.join(settings.MEDIA_ROOT, "downloads_sistemas")
        os.makedirs(diretorio_zips, exist_ok=True)
        caminho_zip_final = os.path.join(diretorio_zips, nome_zip)

        with zipfile.ZipFile(caminho_zip_final, "w", zipfile.ZIP_DEFLATED) as zipf:
            for raiz, dirs, arquivos in os.walk(diretorio_destino):
                dirs[:] = [d for d in dirs if d not in {".venv", "__pycache__"}]
                for arquivo in arquivos:
                    caminho_completo = os.path.join(raiz, arquivo)
                    caminho_relativo = os.path.relpath(caminho_completo, diretorio_destino)
                    zipf.write(caminho_completo, caminho_relativo)

        sistema.arquivo_zip = f"downloads_sistemas/{nome_zip}"
        sistema.save(update_fields=["arquivo_zip"])

        logs_execucao.append(f"Arquivo compactado gerado com sucesso: {nome_zip}")
        logs_execucao.append("Processo de geração e exportação finalizado com sucesso!")

        return JsonResponse({
            "status": "sucesso",
            "logs": logs_execucao,
            "url_zip": reverse("sistema:baixar_zip", kwargs={"pk": sistema.pk}),
        })

    except Exception as exc:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": str(exc),
            },
            status=400,
        )
