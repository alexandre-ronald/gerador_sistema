import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao

class WorkflowDesignerUITests(TestCase):
    def setUp(self):
        U=get_user_model();self.user=U.objects.create_user(username='owner_workflow',password='test123');self.other=U.objects.create_user(username='other_workflow',password='test123')
        self.sistema=Sistema.objects.create(usuario=self.user,nome='Workflow App',slug='workflow-app');self.modulo=Modulo.objects.create(sistema=self.sistema,nome='core');self.entidade=Entidade.objects.create(modulo=self.modulo,nome='Pedido')
        Campo.objects.create(entidade=self.entidade,nome='status',tipo='CharField',max_length=30);Campo.objects.create(entidade=self.entidade,nome='descricao',tipo='TextField');Campo.objects.create(entidade=self.entidade,nome='valor',tipo='DecimalField',max_digits=10,decimal_places=2)
        self.url=reverse('sistema:workflow_designer',args=[self.sistema.id]);self.save_url=reverse('sistema:salvar_workflows',args=[self.sistema.id]);self.client.force_login(self.user)
    def payload(self):
        return {'workflows':{'Pedido':{'enabled':True,'state_field':'status','initial_state':'rascunho','states':[{'id':'rascunho','label':'Rascunho','final':False,'order':0},{'id':'aprovado','label':'Aprovado','final':True,'order':1}],'transitions':[{'id':'aprovar','label':'Aprovar','from':['rascunho'],'to':'aprovado','enabled':True,'confirm':True,'confirm_message':'Confirmar aprovação?','order':0}]}}}
    def test_designer_renders_friendly_workflow_language(self):
        r=self.client.get(self.url);self.assertEqual(r.status_code,200)
        for text in ['Fluxo do processo','Design · GEN-064','Informações do sistema','Usar fluxo de etapas','Onde guardar a etapa atual','Etapa inicial','Etapas','Mudanças de etapa','Adicionar etapa','Adicionar mudança','Nome da etapa','Nome da ação','Vai para','Pode acontecer quando estiver em','Pedir confirmação','Pergunta de confirmação']:self.assertContains(r,text)
        self.assertNotContains(r,'alert(')
    def test_visual_stage_editor_exposes_order_initial_and_final_controls(self):
        r=self.client.get(self.url)
        for text in ['wf-state-number','wf-state-head','wf-state-actions','moveState','setInitialState','Mover para cima','Mover para baixo','Definir como inicial','Começa aqui','Organize a sequência, escolha onde começa e marque quais etapas encerram o processo.']:self.assertContains(r,text)
    def test_visual_transition_editor_exposes_route_order_and_status(self):
        r=self.client.get(self.url)
        for text in ['wf-transition-number','wf-transition-head','wf-transition-actions','wf-route','moveTransition','stateLabel','originLabel','Sai de','Pede confirmação','Mover mudança para cima','Mover mudança para baixo','Organize as ações e visualize claramente de onde o registro sai e para onde ele vai.']:self.assertContains(r,text)
    def test_process_view_explains_generated_workflow(self):
        r=self.client.get(self.url)
        for text in ['Visão do processo','Fluxo gerado','flowHtml','workflowFlow','wf-flow-step','wf-flow-transition','É assim que o fluxo será disponibilizado para quem usar o sistema gerado.','Este fluxo está ativo no sistema gerado.','Este fluxo está inativo e não controlará as etapas no sistema gerado.']:self.assertContains(r,text)
    def test_designer_keeps_internal_workflow_contract(self):
        r=self.client.get(self.url)
        for text in ['state_field','initial_state','transitions','estado_','transicao_','status']:self.assertContains(r,text)
    def test_workspace_lists_workflow_link(self):
        r=self.client.get(reverse('sistema:workspace',args=[self.sistema.id]));self.assertEqual(r.status_code,200);self.assertContains(r,'Workflow Designer');self.assertContains(r,self.url)
    def test_save_persists_workflow_and_preserves_other_draft_keys(self):
        VersaoGeracao.objects.create(sistema=self.sistema,numero=0,estrutura_json={'forms':{'Pedido':{'sections':[]}},'cruds':{'Pedido':{'title':'Pedidos'}},'business_rules':{'Pedido':{'rules':[]}}})
        r=self.client.post(self.save_url,data=json.dumps(self.payload()),content_type='application/json');self.assertEqual(r.status_code,200);self.assertEqual(r.json()['status'],'sucesso');d=VersaoGeracao.objects.get(sistema=self.sistema,numero=0)
        for k in ['forms','cruds','business_rules']:self.assertIn(k,d.estrutura_json)
        w=d.estrutura_json['workflows']['Pedido'];self.assertEqual(w['state_field'],'status');self.assertEqual(w['transitions'][0]['id'],'aprovar')
    def test_saved_workflow_is_loaded_back_into_designer(self):
        self.client.post(self.save_url,data=json.dumps(self.payload()),content_type='application/json');r=self.client.get(self.url)
        for text in ['rascunho','aprovar','Confirmar aprovação?']:self.assertContains(r,text)
    def test_save_rejects_unknown_entity(self):
        p=self.payload();p['workflows']['Fantasma']=p['workflows'].pop('Pedido');r=self.client.post(self.save_url,data=json.dumps(p),content_type='application/json');self.assertEqual(r.status_code,400);self.assertEqual(r.json()['erro']['code'],'unknown_workflow_entity')
    def test_save_rejects_incompatible_state_field(self):
        p=self.payload();p['workflows']['Pedido']['state_field']='valor';r=self.client.post(self.save_url,data=json.dumps(p),content_type='application/json');self.assertEqual(r.status_code,400);self.assertEqual(r.json()['erro']['code'],'incompatible_state_field')
    def test_save_infers_status_as_state_field_when_missing(self):
        p=self.payload();p['workflows']['Pedido']['state_field']='';r=self.client.post(self.save_url,data=json.dumps(p),content_type='application/json')
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['workflows']['Pedido']['state_field'],'status')
        d=VersaoGeracao.objects.get(sistema=self.sistema,numero=0);self.assertEqual(d.estrutura_json['workflows']['Pedido']['state_field'],'status')
    def test_save_explains_missing_initial_state_in_business_language(self):
        p=self.payload();p['workflows']['Pedido']['initial_state']='';r=self.client.post(self.save_url,data=json.dumps(p),content_type='application/json')
        self.assertEqual(r.status_code,400);self.assertEqual(r.json()['erro']['code'],'missing_initial_state');self.assertIn('Defina a etapa inicial',r.json()['mensagem'])
    def test_save_rejects_transition_from_final_state(self):
        p=self.payload();p['workflows']['Pedido']['transitions'][0]['from']=['aprovado'];p['workflows']['Pedido']['transitions'][0]['to']='rascunho';r=self.client.post(self.save_url,data=json.dumps(p),content_type='application/json');self.assertEqual(r.status_code,400);self.assertEqual(r.json()['erro']['code'],'final_state_has_outgoing_transition')
    def test_save_requires_workflows_object(self):
        r=self.client.post(self.save_url,data=json.dumps({'workflows':[]}),content_type='application/json');self.assertEqual(r.status_code,400);self.assertEqual(r.json()['erro']['code'],'invalid_workflows_config')
    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other);self.assertEqual(self.client.get(self.url).status_code,404);self.assertEqual(self.client.post(self.save_url,data=json.dumps(self.payload()),content_type='application/json').status_code,404)
