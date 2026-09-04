from django.template.loader import render_to_string
from django.test import SimpleTestCase


class FormDesignerUITests(SimpleTestCase):
    def source(self):
        return render_to_string("sistema/form_designer.html", {
            "sistema": type("SistemaStub", (), {"id": 1})(),
            "entities": [],
            "forms_json": "{}",
            "entity_metadata_json": "{}",
        })

    def test_exposes_form_designer_shell(self):
        source = self.source()
        self.assertIn("Form Designer 2.0", source)
        self.assertIn("Design · GEN-062", source)
        self.assertIn("Voltar ao Workspace", source)
        self.assertIn('id="entity"', source)
        self.assertIn('id="form-title"', source)
        self.assertIn('id="canvas"', source)
        self.assertIn('id="properties"', source)

    def test_exposes_grid_and_field_properties(self):
        source = self.source()
        self.assertIn("const widths=[2,3,4,6,8,12]", source)
        self.assertIn("const widthLabels={2:'1/6',3:'1/4',4:'1/3',6:'1/2',8:'2/3',12:'Linha'}", source)
        self.assertIn('data-p="label"', source)
        self.assertIn('data-p="placeholder"', source)
        self.assertIn('data-p="help_text"', source)
        self.assertIn('data-width="${w}"', source)
        self.assertIn('data-p="widget"', source)
        self.assertIn('data-p="visible"', source)
        self.assertIn('data-p="readonly"', source)
        self.assertIn("Nome exibido", source)
        self.assertIn("Texto de exemplo", source)
        self.assertIn("Tipo de entrada", source)
        self.assertIn("Mostrar no formulário", source)

    def test_supports_friendly_widget_labels(self):
        source = self.source()
        self.assertIn("text:'Texto'", source)
        self.assertIn("textarea:'Texto longo'", source)
        self.assertIn("number:'Número'", source)
        self.assertIn("date:'Data'", source)
        self.assertIn("datetime:'Data e hora'", source)
        self.assertIn("checkbox:'Sim / Não'", source)
        self.assertIn("select:'Lista de opções'", source)

    def test_supports_sections(self):
        source = self.source()
        self.assertIn('id="add-section"', source)
        self.assertIn("Adicionar seção", source)
        self.assertIn("sectionId()", source)
        self.assertIn("data-section-title", source)
        self.assertIn("data-section-description", source)
        self.assertIn("data-remove-section", source)
        self.assertIn("Seções do formulário", source)
        self.assertIn('id="section-count"', source)
        self.assertIn("Nenhuma seção criada", source)

    def test_supports_section_ordering(self):
        source = self.source()
        self.assertIn("orderedSections()", source)
        self.assertIn("normalizeSectionOrder()", source)
        self.assertIn('data-move-section="-1"', source)
        self.assertIn('data-move-section="1"', source)
        self.assertIn("Mover seção para cima", source)
        self.assertIn("Mover seção para baixo", source)

    def test_exposes_section_field_counts_and_empty_state(self):
        source = self.source()
        self.assertIn("fieldsInSection", source)
        self.assertIn("Nenhum campo nesta seção", source)
        self.assertIn("Campos que ainda não foram associados a uma seção", source)

    def test_supports_field_ordering_and_drag_drop(self):
        source = self.source()
        self.assertIn('draggable="true"', source)
        self.assertIn("dragstart", source)
        self.assertIn("dragover", source)
        self.assertIn("drop", source)
        self.assertIn('data-move="-1"', source)
        self.assertIn('data-move="1"', source)

    def test_preview_is_local_only(self):
        source = self.source()
        self.assertIn("Visualização do formulário", source)
        self.assertIn("previewMode=true", source)
        self.assertIn("previewMode=false", source)
        self.assertNotIn('preview_mode', source)

    def test_preview_matches_generated_form_structure(self):
        source = self.source()
        self.assertIn("renderPreviewCanvas", source)
        self.assertIn("fd-preview-page-heading", source)
        self.assertIn("fd-preview-card", source)
        self.assertIn("col-12 col-md-${f.width}", source)
        self.assertIn("form-check form-switch fd-preview-boolean", source)
        self.assertIn("Preencha os dados abaixo para cadastrar o registro.", source)
        self.assertIn("Salvar registro", source)
        self.assertIn("Nenhum campo visível configurado para esta entidade.", source)

    def test_save_uses_forms_contract(self):
        source = self.source()
        self.assertIn("JSON.stringify({forms})", source)
        self.assertIn("forms=data.forms", source)
        self.assertIn("/sistemas/1/form-designer/salvar/", source)
