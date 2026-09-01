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
        self.assertIn("Form Designer", source)
        self.assertIn("System Builder · GEN-050", source)
        self.assertIn('id="entity"', source)
        self.assertIn('id="form-title"', source)
        self.assertIn('id="canvas"', source)
        self.assertIn('id="properties"', source)

    def test_exposes_grid_and_field_properties(self):
        source = self.source()
        self.assertIn("const widths=[3,4,6,8,12]", source)
        self.assertIn('data-p="label"', source)
        self.assertIn('data-p="placeholder"', source)
        self.assertIn('data-p="help_text"', source)
        self.assertIn('data-p="width"', source)
        self.assertIn('data-p="widget"', source)
        self.assertIn('data-p="visible"', source)
        self.assertIn('data-p="readonly"', source)

    def test_supports_sections(self):
        source = self.source()
        self.assertIn('id="add-section"', source)
        self.assertIn("sectionId()", source)
        self.assertIn("data-section-title", source)
        self.assertIn("data-section-description", source)
        self.assertIn("data-remove-section", source)

    def test_supports_field_ordering_and_drag_drop(self):
        source = self.source()
        self.assertIn('draggable="${previewMode?', source)
        self.assertIn("dragstart", source)
        self.assertIn("dragover", source)
        self.assertIn("drop", source)
        self.assertIn('data-move="-1"', source)
        self.assertIn('data-move="1"', source)

    def test_preview_is_local_only(self):
        source = self.source()
        self.assertIn("Preview Mode", source)
        self.assertIn("previewMode=true", source)
        self.assertIn("previewMode=false", source)
        self.assertNotIn('preview_mode', source)

    def test_save_uses_forms_contract(self):
        source = self.source()
        self.assertIn("JSON.stringify({forms})", source)
        self.assertIn("forms=data.forms", source)
        self.assertIn("/sistemas/1/form-designer/salvar/", source)
