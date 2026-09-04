import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ReportDesignerUITests(TestCase):
    def setUp(self):
        user_model=get_user_model();self.user=user_model.objects.create_user(username="owner_report",password="test123");self.other=user_model.objects.create_user(username="other_report",password="test123")
        self.sistema=Sistema.objects.create(usuario=self.user,nome="Report App",slug="report-app");modulo=Modulo.objects.create(sistema=self.sistema,nome="core");self.entidade=Entidade.objects.create(modulo=modulo,nome="Contrato")
        Campo.objects.create(entidade=self.entidade,nome="numero",tipo="CharField",max_length=30);Campo.objects.create(entidade=self.entidade,nome="fornecedor",tipo="CharField",max_length=120);Campo.objects.create(entidade=self.entidade,nome="valor",tipo="DecimalField",max_digits=12,decimal_places=2);Campo.objects.create(entidade=self.entidade,nome="vigencia",tipo="DateField")
        self.url=reverse("sistema:report_designer",args=[self.sistema.id]);self.save_url=reverse("sistema:salvar_reports",args=[self.sistema.id]);self.client.force_login(self.user)

    def report(self,report_id="relatorio_1",title="Relatório de contratos"):
        return {"id":report_id,"enabled":True,"title":title,"description":"Acompanhe os contratos cadastrados.","fields":["numero","fornecedor","valor"],"filters":[{"field":"fornecedor","type":"contains"},{"field":"valor","type":"gte"}],"order_by":"-valor"}

    def payload(self):
        return {"reports":{"Contrato":[self.report()]}}

    def test_designer_renders_business_friendly_language(self):
        response=self.client.get(self.url);self.assertEqual(response.status_code,200)
        for text in ["Design · GEN-065","Relatórios","Disponibilizar relatório","Título do relatório","Colunas do relatório","Filtros para o usuário","Ordenação inicial","Como o relatório ficará","Prévia da tabela","Salvar relatórios"]:self.assertContains(response,text)
        self.assertNotContains(response,"alert(")

    def test_multiple_report_controls_are_available(self):
        response=self.client.get(self.url)
        for text in ["Relatórios desta informação","Novo relatório","Uma mesma informação pode ter vários relatórios","newReport","duplicateReport","removeReport","Duplicar","Remover"]:self.assertContains(response,text)

    def test_visual_column_and_filter_organization_controls_are_available(self):
        response=self.client.get(self.url)
        for text in ["Colunas escolhidas","Outras informações disponíveis","moveField","Mover coluna para cima","Mover coluna para baixo","Remover coluna","Adicionar","rp-column-order","rp-filter-grid","Disponível para filtrar","Não será exibido como filtro","A prévia respeita a ordem das colunas que você definiu."]:self.assertContains(response,text)

    def test_filter_types_are_presented_in_friendly_language(self):
        response=self.client.get(self.url)
        for text in ["Como o usuário poderá filtrar?","Contém","É igual a","Começa com","A partir de","Até","Entre dois valores","changeFilterType","filter_options","default_filter_type"]:self.assertContains(response,text)

    def test_save_persists_multiple_reports(self):
        payload={"reports":{"Contrato":[self.report("relatorio_1","Contratos por fornecedor"),self.report("relatorio_2","Contratos por valor")]}}
        response=self.client.post(self.save_url,data=json.dumps(payload),content_type="application/json");self.assertEqual(response.status_code,200)
        saved=VersaoGeracao.objects.get(sistema=self.sistema,numero=0).estrutura_json["reports"]["Contrato"]
        self.assertEqual(len(saved),2);self.assertEqual(saved[0]["id"],"relatorio_1");self.assertEqual(saved[1]["id"],"relatorio_2");self.assertEqual(saved[1]["title"],"Contratos por valor")

    def test_save_preserves_selected_column_order(self):
        payload=self.payload();payload["reports"]["Contrato"][0]["fields"]=["valor","numero","fornecedor"]
        response=self.client.post(self.save_url,data=json.dumps(payload),content_type="application/json");self.assertEqual(response.status_code,200)
        saved=VersaoGeracao.objects.get(sistema=self.sistema,numero=0).estrutura_json["reports"]["Contrato"][0];self.assertEqual(saved["fields"],["valor","numero","fornecedor"])

    def test_save_persists_reports_and_preserves_existing_draft_keys(self):
        VersaoGeracao.objects.create(sistema=self.sistema,numero=0,estrutura_json={"forms":{"Contrato":{}},"workflows":{"Contrato":{}}})
        response=self.client.post(self.save_url,data=json.dumps(self.payload()),content_type="application/json");self.assertEqual(response.status_code,200)
        draft=VersaoGeracao.objects.get(sistema=self.sistema,numero=0);self.assertIn("forms",draft.estrutura_json);self.assertIn("workflows",draft.estrutura_json)
        report=draft.estrutura_json["reports"]["Contrato"][0];self.assertTrue(report["enabled"]);self.assertEqual(report["fields"],["numero","fornecedor","valor"]);self.assertEqual(report["filters"],[{"field":"fornecedor","type":"contains"},{"field":"valor","type":"gte"}]);self.assertEqual(report["order_by"],"-valor")

    def test_legacy_single_report_dict_is_normalized_to_collection(self):
        legacy=self.report();legacy.pop("id")
        response=self.client.post(self.save_url,data=json.dumps({"reports":{"Contrato":legacy}}),content_type="application/json");self.assertEqual(response.status_code,200)
        reports=response.json()["reports"]["Contrato"];self.assertEqual(len(reports),1);self.assertEqual(reports[0]["id"],"relatorio_1")

    def test_legacy_string_filter_is_normalized(self):
        payload=self.payload();payload["reports"]["Contrato"][0]["filters"]=["fornecedor"]
        response=self.client.post(self.save_url,data=json.dumps(payload),content_type="application/json");self.assertEqual(response.status_code,200);self.assertEqual(response.json()["reports"]["Contrato"][0]["filters"],[{"field":"fornecedor","type":"contains"}])

    def test_save_rejects_duplicate_report_id(self):
        payload={"reports":{"Contrato":[self.report("relatorio_1"),self.report("relatorio_1")]}}
        response=self.client.post(self.save_url,data=json.dumps(payload),content_type="application/json");self.assertEqual(response.status_code,400);self.assertIn("repetido",response.json()["mensagem"])

    def test_save_rejects_invalid_filter_type_for_field(self):
        payload=self.payload();payload["reports"]["Contrato"][0]["filters"]=[{"field":"valor","type":"contains"}]
        response=self.client.post(self.save_url,data=json.dumps(payload),content_type="application/json");self.assertEqual(response.status_code,400);self.assertIn("Tipo de filtro não disponível",response.json()["mensagem"])

    def test_save_rejects_unknown_entity(self):
        payload=self.payload();payload["reports"]["Fantasma"]=payload["reports"].pop("Contrato");response=self.client.post(self.save_url,data=json.dumps(payload),content_type="application/json");self.assertEqual(response.status_code,400)

    def test_save_rejects_unknown_field(self):
        payload=self.payload();payload["reports"]["Contrato"][0]["fields"].append("nao_existe");response=self.client.post(self.save_url,data=json.dumps(payload),content_type="application/json");self.assertEqual(response.status_code,400);self.assertIn("nao_existe",response.json()["mensagem"])

    def test_saved_report_is_loaded_back(self):
        self.client.post(self.save_url,data=json.dumps(self.payload()),content_type="application/json");response=self.client.get(self.url);self.assertContains(response,"Relatório de contratos");self.assertContains(response,"Acompanhe os contratos cadastrados.")

    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other);self.assertEqual(self.client.get(self.url).status_code,404);self.assertEqual(self.client.post(self.save_url,data=json.dumps(self.payload()),content_type="application/json").status_code,404)
