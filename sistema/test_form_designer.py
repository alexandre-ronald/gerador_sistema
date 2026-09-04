from django.test import SimpleTestCase

from .form_designer import (
    FormDesignerError,
    compatible_widgets,
    infer_widget,
    normalize_form_config,
)


class FormDesignerContractTests(SimpleTestCase):
    def metadata(self):
        return {
            "name": "Pedido",
            "fields": [
                {"name": "descricao", "type": "TextField", "label": "Descrição", "editable": True},
                {"name": "valor", "type": "DecimalField", "label": "Valor", "editable": True},
                {"name": "data_pedido", "type": "DateField", "label": "Data", "editable": True},
                {"name": "ativo", "type": "BooleanField", "label": "Ativo", "editable": True},
                {"name": "fornecedor", "type": "ForeignKey", "label": "Fornecedor", "editable": True},
                {"name": "criado_em", "type": "DateTimeField", "label": "Criado em", "editable": False},
            ],
        }

    def test_legacy_config_builds_safe_defaults(self):
        form = normalize_form_config("Pedido", self.metadata())
        self.assertEqual(form["title"], "Cadastro de Pedido")
        self.assertEqual([item["name"] for item in form["fields"]], [
            "descricao", "valor", "data_pedido", "ativo", "fornecedor", "criado_em"
        ])
        self.assertEqual(form["fields"][0]["widget"], "textarea")
        self.assertTrue(form["fields"][-1]["readonly"])
        self.assertFalse(form["fields"][-1]["visible"])

    def test_widget_inference_and_compatibility(self):
        self.assertEqual(infer_widget("DecimalField"), "number")
        self.assertEqual(infer_widget("DateField"), "date")
        self.assertEqual(infer_widget("ForeignKey"), "select")
        self.assertIn("textarea", compatible_widgets("TextField"))
        self.assertNotIn("checkbox", compatible_widgets("DecimalField"))

    def test_custom_sections_order_and_field_appearance(self):
        form = normalize_form_config("Pedido", self.metadata(), {
            "title": "Novo pedido",
            "sections": [{"id": "principal", "title": "Principal", "order": 0}],
            "fields": [{
                "name": "descricao", "order": 4, "section": "principal", "visible": True,
                "readonly": False, "width": 6, "label": "Objeto", "placeholder": "Informe",
                "help_text": "Resumo do pedido", "widget": "textarea"
            }],
        })
        field = next(item for item in form["fields"] if item["name"] == "descricao")
        self.assertEqual(form["title"], "Novo pedido")
        self.assertEqual(field["section"], "principal")
        self.assertEqual(field["width"], 6)
        self.assertEqual(field["label"], "Objeto")
        self.assertEqual(field["placeholder"], "Informe")

    def test_width_two_is_supported(self):
        form = normalize_form_config("Pedido", self.metadata(), {
            "fields": [{"name": "valor", "width": 2}]
        })
        field = next(item for item in form["fields"] if item["name"] == "valor")
        self.assertEqual(field["width"], 2)

    def test_new_metadata_field_is_added_without_destroying_customization(self):
        metadata = self.metadata()
        config = {"fields": [{"name": "descricao", "label": "Objeto", "width": 6}]}
        metadata["fields"].append({"name": "observacao", "type": "TextField", "label": "Observação"})
        form = normalize_form_config("Pedido", metadata, config)
        names = [item["name"] for item in form["fields"]]
        self.assertIn("observacao", names)
        self.assertEqual(next(item for item in form["fields"] if item["name"] == "descricao")["label"], "Objeto")

    def test_removed_field_is_ignored_in_non_strict_normalization(self):
        form = normalize_form_config("Pedido", self.metadata(), {
            "fields": [{"name": "campo_removido", "width": 12}]
        })
        self.assertNotIn("campo_removido", [item["name"] for item in form["fields"]])

    def test_direct_update_rejects_unknown_field(self):
        with self.assertRaises(FormDesignerError) as ctx:
            normalize_form_config("Pedido", self.metadata(), {
                "fields": [{"name": "campo_removido", "width": 12}]
            }, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_field")

    def test_duplicate_or_unknown_sections_are_rejected(self):
        with self.assertRaises(FormDesignerError) as duplicate:
            normalize_form_config("Pedido", self.metadata(), {
                "sections": [{"id": "principal"}, {"id": "principal"}]
            })
        self.assertEqual(duplicate.exception.code, "duplicate_section")

        with self.assertRaises(FormDesignerError) as unknown:
            normalize_form_config("Pedido", self.metadata(), {
                "fields": [{"name": "descricao", "section": "inexistente"}]
            })
        self.assertEqual(unknown.exception.code, "unknown_section")

    def test_width_widget_and_boolean_validation(self):
        cases = [
            ({"name": "descricao", "width": 5}, "invalid_width"),
            ({"name": "valor", "widget": "checkbox"}, "incompatible_widget"),
            ({"name": "descricao", "visible": "true"}, "invalid_visible"),
            ({"name": "descricao", "readonly": 1}, "invalid_readonly"),
        ]
        for field_config, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(FormDesignerError) as ctx:
                    normalize_form_config("Pedido", self.metadata(), {"fields": [field_config]})
                self.assertEqual(ctx.exception.code, code)

    def test_unsafe_entity_and_field_names_are_rejected(self):
        with self.assertRaises(FormDesignerError):
            normalize_form_config("Pedido__secret", self.metadata())
        with self.assertRaises(FormDesignerError):
            normalize_form_config("Pedido", self.metadata(), {
                "fields": [{"name": "fornecedor__nome"}]
            }, strict=True)

    def test_error_is_structured(self):
        try:
            normalize_form_config("Pedido", self.metadata(), {"fields": [{"name": "valor", "width": 7}]})
        except FormDesignerError as exc:
            self.assertEqual(exc.as_dict()["code"], "invalid_width")
            self.assertEqual(exc.as_dict()["field"], "valor")
        else:
            self.fail("FormDesignerError esperado")
