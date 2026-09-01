from django.test import SimpleTestCase

from sistema.crud_designer import CrudDesignerError, normalize_crud_config


class CrudDesignerContractTests(SimpleTestCase):
    def setUp(self):
        self.metadata = {
            "name": "Pedido",
            "verbose_name_plural": "Pedidos",
            "fields": [
                {"name": "numero", "type": "CharField", "verbose_name": "Número"},
                {"name": "descricao", "type": "TextField", "verbose_name": "Descrição"},
                {"name": "quantidade", "type": "IntegerField", "verbose_name": "Quantidade"},
                {"name": "ativo", "type": "BooleanField", "verbose_name": "Ativo"},
                {"name": "data", "type": "DateField", "verbose_name": "Data"},
                {"name": "status", "type": "CharField", "verbose_name": "Status", "choices": [["A", "Aberto"], ["F", "Fechado"]]},
                {"name": "fornecedor", "type": "ForeignKey", "verbose_name": "Fornecedor"},
                {"name": "tags", "type": "ManyToManyField", "verbose_name": "Tags"},
            ],
        }

    def test_default_contract_is_safe_and_complete(self):
        config = normalize_crud_config("Pedido", self.metadata)
        self.assertEqual(config["title"], "Pedidos")
        self.assertEqual(config["page_size"], 25)
        self.assertEqual(config["default_order"], "")
        self.assertEqual(config["search"]["fields"], ["numero", "descricao", "status"])
        self.assertTrue(config["actions"]["create"])
        tags = next(item for item in config["columns"] if item["field"] == "tags")
        self.assertFalse(tags["visible"])
        self.assertFalse(tags["sortable"])

    def test_custom_columns_keep_explicit_order_and_do_not_add_new_fields(self):
        config = normalize_crud_config(
            "Pedido",
            self.metadata,
            {
                "columns": [
                    {"field": "descricao", "label": "Resumo", "order": 1, "visible": True, "sortable": True},
                    {"field": "numero", "label": "Nº", "order": 0, "visible": True, "sortable": True},
                ]
            },
        )
        self.assertEqual([item["field"] for item in config["columns"]], ["numero", "descricao"])
        self.assertEqual(config["columns"][0]["label"], "Nº")
        self.assertNotIn("quantidade", [item["field"] for item in config["columns"]])

    def test_removed_fields_are_ignored_when_not_strict(self):
        config = normalize_crud_config(
            "Pedido",
            self.metadata,
            {"columns": [{"field": "campo_removido", "order": 0}, {"field": "numero", "order": 1}]},
        )
        self.assertEqual([item["field"] for item in config["columns"]], ["numero"])

    def test_direct_update_rejects_unknown_field_in_strict_mode(self):
        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config("Pedido", self.metadata, {"columns": [{"field": "inexistente"}]}, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_column_field")

    def test_rejects_duplicate_columns(self):
        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config(
                "Pedido",
                self.metadata,
                {"columns": [{"field": "numero"}, {"field": "numero"}]},
            )
        self.assertEqual(ctx.exception.code, "duplicate_column")

    def test_search_only_accepts_textual_fields(self):
        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config("Pedido", self.metadata, {"search": {"enabled": True, "fields": ["quantidade"]}})
        self.assertEqual(ctx.exception.code, "incompatible_search_field")

    def test_filter_types_are_validated_by_field_type(self):
        config = normalize_crud_config(
            "Pedido",
            self.metadata,
            {
                "filters": [
                    {"field": "status", "type": "select", "order": 0},
                    {"field": "ativo", "type": "boolean", "order": 1},
                    {"field": "data", "type": "date", "order": 2},
                    {"field": "fornecedor", "type": "relation", "order": 3},
                ]
            },
        )
        self.assertEqual([item["type"] for item in config["filters"]], ["select", "boolean", "date", "relation"])

        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config("Pedido", self.metadata, {"filters": [{"field": "ativo", "type": "text"}]})
        self.assertEqual(ctx.exception.code, "incompatible_filter")

    def test_page_size_uses_allowlist(self):
        self.assertEqual(normalize_crud_config("Pedido", self.metadata, {"page_size": 50})["page_size"], 50)
        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config("Pedido", self.metadata, {"page_size": 37})
        self.assertEqual(ctx.exception.code, "invalid_page_size")

    def test_default_order_requires_sortable_configured_column(self):
        config = normalize_crud_config(
            "Pedido",
            self.metadata,
            {"columns": [{"field": "numero", "sortable": True}], "default_order": "-numero"},
        )
        self.assertEqual(config["default_order"], "-numero")

        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config(
                "Pedido",
                self.metadata,
                {"columns": [{"field": "numero", "sortable": False}], "default_order": "numero"},
            )
        self.assertEqual(ctx.exception.code, "invalid_default_order")

    def test_rejects_unsafe_lookup_paths(self):
        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config("Pedido", self.metadata, {"columns": [{"field": "fornecedor__nome"}]}, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_column_field")

    def test_actions_must_be_boolean(self):
        config = normalize_crud_config("Pedido", self.metadata, {"actions": {"delete": False, "view": False}})
        self.assertFalse(config["actions"]["delete"])
        self.assertFalse(config["actions"]["view"])
        self.assertTrue(config["actions"]["edit"])

        with self.assertRaises(CrudDesignerError) as ctx:
            normalize_crud_config("Pedido", self.metadata, {"actions": {"edit": "sim"}})
        self.assertEqual(ctx.exception.code, "invalid_action")
