from django.test import SimpleTestCase

from sistema.advanced_page_layout import collides, first_available_layout, place_component, resize_component


class AdvancedPageLayoutTests(SimpleTestCase):
    def component(self, component_id, x, y, w, h=1):
        return {"id": component_id, "layout": {"x": x, "y": y, "w": w, "h": h}}

    def test_collision_detection(self):
        self.assertTrue(collides({"x": 0, "y": 0, "w": 6, "h": 1}, {"x": 5, "y": 0, "w": 4, "h": 1}))
        self.assertFalse(collides({"x": 0, "y": 0, "w": 6, "h": 1}, {"x": 6, "y": 0, "w": 6, "h": 1}))

    def test_first_available_uses_remaining_columns(self):
        components = [self.component("a", 0, 0, 6)]
        self.assertEqual(first_available_layout(components, w=6), {"x": 6, "y": 0, "w": 6, "h": 1})

    def test_first_available_moves_to_next_row_when_row_is_full(self):
        components = [self.component("a", 0, 0, 6), self.component("b", 6, 0, 6)]
        self.assertEqual(first_available_layout(components, w=8), {"x": 0, "y": 1, "w": 8, "h": 1})

    def test_place_component_does_not_mutate_input(self):
        components = [self.component("a", 0, 0, 12)]
        incoming = self.component("b", 0, 0, 6)
        placed = place_component(components, incoming)
        self.assertEqual(incoming["layout"]["y"], 0)
        self.assertEqual(placed["layout"]["y"], 1)

    def test_resize_moves_component_when_new_width_collides(self):
        components = [self.component("a", 0, 0, 6), self.component("b", 6, 0, 6)]
        resized = resize_component(components, "a", w=8)
        self.assertEqual(resized["layout"], {"x": 0, "y": 1, "w": 8, "h": 1})

    def test_resize_keeps_position_when_space_is_available(self):
        components = [self.component("a", 0, 0, 4), self.component("b", 8, 0, 4)]
        resized = resize_component(components, "a", w=8)
        self.assertEqual(resized["layout"], {"x": 0, "y": 0, "w": 8, "h": 1})
