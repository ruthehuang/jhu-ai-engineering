"""Unit tests for the baseline seed-data loading functions."""

from copy import deepcopy
from datetime import date
import unittest

from main import (
    calculate_ingredient_requirements,
    calculate_restock_needs,
    check_inventory_availability,
    find_recipe_by_name,
    load_inventory,
    load_orders,
    load_recipes,
    load_restock,
    load_status,
    process_orders,
    build_business_summary,
    print_business_summary,
    build_business_summary_html,
)


def make_inventory_item(ingredient, qty_grams, expiry_date="2026-12-31"):
    """Helper to build simple inventory records for tests."""
    return {"ingredient": ingredient, "qty_grams": qty_grams, "expiry_date": expiry_date}


def make_order(order_id, brand, items):
    """Helper to build simple order records for tests."""
    return {"order_id": order_id, "brand": brand, "items": items}


class TestLoadFunctions(unittest.TestCase):
    """Verify the Task 1 data-loading helpers return the expected seed tables."""

    def test_loads_all_five_tables_successfully(self):
        """Each load function should return a non-empty list from seed_data."""
        # Assumption to verify: Task 1 considers a successful import equivalent to
        # each loader returning the seeded module-level list without raising errors.
        self.assertIsInstance(load_recipes(), list)
        self.assertIsInstance(load_inventory(), list)
        self.assertIsInstance(load_orders(), list)
        self.assertIsInstance(load_restock(), list)
        self.assertIsInstance(load_status(), list)

        self.assertGreater(len(load_recipes()), 0)
        self.assertGreater(len(load_inventory()), 0)
        self.assertGreater(len(load_orders()), 0)
        self.assertGreater(len(load_restock()), 0)
        self.assertGreater(len(load_status()), 0)

    def test_record_counts_match_seed_data(self):
        """Each load function should return the expected number of seed records."""
        self.assertEqual(len(load_recipes()), 5)
        self.assertEqual(len(load_inventory()), 14)
        self.assertEqual(len(load_orders()), 5)
        self.assertEqual(len(load_restock()), 5)
        self.assertEqual(len(load_status()), 5)

    def test_recipe_key_field_types(self):
        """Recipe records should expose valid identifiers and ingredient details."""
        recipe = load_recipes()[0]
        ingredient = recipe["ingredients"][0]

        # Basic type checks
        self.assertIsInstance(recipe["recipe_id"], int)
        self.assertIsInstance(recipe["name"], str)
        self.assertIsInstance(recipe["ingredients"], list)
        self.assertIsInstance(ingredient["name"], str)
        self.assertIsInstance(ingredient["qty_grams"], (int, float))

        # Simple content validation
        self.assertGreater(recipe["recipe_id"], 0)
        self.assertGreater(len(recipe["name"].strip()), 0)
        self.assertGreater(len(recipe["ingredients"]), 0)
        self.assertGreater(len(ingredient["name"].strip()), 0)
        self.assertGreater(ingredient["qty_grams"], 0)

    def test_inventory_key_field_types(self):
        """Inventory records should provide valid quantity and expiry field types."""
        item = load_inventory()[0]

        # Basic type checks
        self.assertIsInstance(item["ingredient"], str)
        self.assertIsInstance(item["qty_grams"], (int, float))
        self.assertIsInstance(item["expiry_date"], str)

        # Simple content validation
        self.assertGreater(len(item["ingredient"].strip()), 0)
        self.assertGreater(item["qty_grams"], 0)
        # Very light expiry sanity check: non-empty and looks like YYYY-MM-DD
        self.assertGreater(len(item["expiry_date"].strip()), 0)
        self.assertEqual(len(item["expiry_date"]), 10)
        self.assertIn("-", item["expiry_date"])

    def test_order_key_field_types(self):
        """Order records should expose valid identifiers, brands, and quantities."""
        order = load_orders()[0]
        item = order["items"][0]

        # Basic type checks
        self.assertIsInstance(order["order_id"], int)
        self.assertIsInstance(order["brand"], str)
        self.assertIsInstance(order["items"], list)
        self.assertIsInstance(item["item"], str)
        self.assertIsInstance(item["qty"], int)

        # Simple content validation
        self.assertGreater(order["order_id"], 0)
        self.assertGreater(len(order["brand"].strip()), 0)
        self.assertGreater(len(order["items"]), 0)
        self.assertGreater(len(item["item"].strip()), 0)
        self.assertGreater(item["qty"], 0)

    def test_restock_key_field_types(self):
        """Restock records should provide an item name, numeric quantity, and reason."""
        item = load_restock()[0]

        # Basic type checks
        self.assertIsInstance(item["item"], str)
        self.assertIsInstance(item["qty_needed_grams"], (int, float))
        self.assertIsInstance(item["reason"], str)

        # Simple content validation
        self.assertGreater(len(item["item"].strip()), 0)
        self.assertGreater(item["qty_needed_grams"], 0)
        self.assertGreater(len(item["reason"].strip()), 0)

    def test_status_key_field_types(self):
        """Status records should provide order linkage and delivery state types."""
        item = load_status()[0]

        # Basic type checks
        self.assertIsInstance(item["order_id"], int)
        self.assertIsInstance(item["delivered"], bool)
        self.assertIsInstance(item["remark"], str)

        # Simple content validation
        self.assertGreater(item["order_id"], 0)
        self.assertGreater(len(item["remark"].strip()), 0)
        # Incomplete / follow-up: if the project later formalizes a status enum or
        # richer state machine, these tests should be expanded beyond simple types.


class TestOrderRecipeLookup(unittest.TestCase):
    """Verify order items can be matched to recipes and scaled correctly."""

    def test_find_recipe_by_name_returns_matching_recipe(self):
        """A valid order item should return its matching recipe record."""
        recipe = find_recipe_by_name(load_recipes(), "Chicken Burger")

        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["recipe_id"], 2)
        self.assertEqual(recipe["name"], "Chicken Burger")

    def test_find_recipe_by_name_handles_missing_recipe_gracefully(self):
        """A missing order item should return None instead of raising an error."""
        recipe = find_recipe_by_name(load_recipes(), "Paneer Wrap")

        self.assertIsNone(recipe)

    def test_find_recipe_by_name_is_case_insensitive_and_trims_whitespace(self):
        """Lookup should tolerate case differences and surrounding whitespace."""
        recipe = find_recipe_by_name(load_recipes(), "  margherita pizza  ")

        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Margherita Pizza")

    def test_find_recipe_by_name_raises_for_invalid_item_name_type(self):
        """Non-string or empty item names should raise a clear ValueError."""
        with self.assertRaises(ValueError):
            find_recipe_by_name(load_recipes(), "")
        with self.assertRaises(ValueError):
            find_recipe_by_name(load_recipes(), None)  # type: ignore[arg-type]

    def test_find_recipe_by_name_strict_mode_raises_lookup_error(self):
        """Strict mode should raise LookupError when a recipe is not found."""
        with self.assertRaises(LookupError):
            find_recipe_by_name(load_recipes(), "Paneer Wrap", strict=True)

    def test_calculate_ingredient_requirements_scales_for_quantity_two(self):
        """Ingredient requirements should double when the order quantity is two."""
        recipe = find_recipe_by_name(load_recipes(), "Margherita Pizza")
        requirements = calculate_ingredient_requirements(recipe, 2)

        expected_requirements = [
            {"name": "Flour", "required_qty_grams": 600},
            {"name": "Tomato Sauce", "required_qty_grams": 200},
            {"name": "Mozzarella Cheese", "required_qty_grams": 300},
        ]

        self.assertEqual(requirements, expected_requirements)


class TestOrderFulfillment(unittest.TestCase):
    """Verify fulfillment updates status, restock, and inventory correctly."""

    def test_process_orders_marks_delivered_when_ingredients_are_available(self):
        """An order with sufficient stock should be marked as delivered."""
        recipe_data = deepcopy(load_recipes())
        inventory_data = deepcopy(load_inventory())
        status_data = deepcopy(load_status())
        restock_data = deepcopy(load_restock())
        order_data = [
            {
                "order_id": 101,
                "brand": "Test Kitchen",
                "items": [{"item": "Chicken Burger", "qty": 1}],
            }
        ]

        processed_orders = process_orders(
            recipe_data, inventory_data, order_data, status_data, restock_data
        )

        self.assertTrue(processed_orders[0]["fulfilled"])
        self.assertEqual(processed_orders[0]["reason"], "Delivered")
        self.assertEqual(status_data[-1]["order_id"], 101)
        self.assertTrue(status_data[-1]["delivered"])
        self.assertEqual(status_data[-1]["remark"], "Delivered")

    def test_process_orders_marks_not_delivered_and_adds_missing_item_to_restock(self):
        """An order with a missing ingredient should fail and log the shortage."""
        recipe_data = [
            {
                "recipe_id": 1,
                "name": "Test Wrap",
                "ingredients": [
                    {"name": "Chicken Breast", "qty_grams": 200},
                    {"name": "Bun", "qty_grams": 100},
                ],
            }
        ]
        inventory_data = [
            make_inventory_item("Chicken Breast", 500),
            make_inventory_item("Bun", 0),
        ]
        order_data = [
            make_order(202, "Test Kitchen", [{"item": "Test Wrap", "qty": 1}])
        ]
        status_data = []
        restock_data = []

        processed_orders = process_orders(
            recipe_data,
            inventory_data,
            order_data,
            status_data,
            restock_data,
            reference_date=date(2026, 6, 3),
        )

        self.assertFalse(processed_orders[0]["fulfilled"])
        self.assertIn("Missing or insufficient ingredients: Bun", processed_orders[0]["reason"])
        self.assertEqual(status_data[0]["order_id"], 202)
        self.assertFalse(status_data[0]["delivered"])
        self.assertIn("Bun", status_data[0]["remark"])
        bun_restock = next(item for item in restock_data if item["item"] == "Bun")
        self.assertEqual(bun_restock["qty_needed_grams"], 10000)
        self.assertEqual(bun_restock["reason"], "Out of stock")

    def test_process_orders_deducts_inventory_after_successful_delivery(self):
        """A delivered order should reduce inventory by the required grams."""
        recipe_data = deepcopy(load_recipes())
        inventory_data = deepcopy(load_inventory())
        status_data = []
        restock_data = []
        order_data = [
            {
                "order_id": 303,
                "brand": "Test Kitchen",
                "items": [{"item": "Margherita Pizza", "qty": 2}],
            }
        ]

        original_flour_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Flour"
        )
        original_sauce_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Tomato Sauce"
        )
        original_cheese_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Mozzarella Cheese"
        )

        process_orders(
            recipe_data,
            inventory_data,
            order_data,
            status_data,
            restock_data,
            reference_date=date(2026, 5, 1),  # before Flour's expiry so order can succeed
        )

        updated_flour_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Flour"
        )
        updated_sauce_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Tomato Sauce"
        )
        updated_cheese_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Mozzarella Cheese"
        )

        self.assertEqual(updated_flour_qty, original_flour_qty - 600)
        self.assertEqual(updated_sauce_qty, original_sauce_qty - 200)
        self.assertEqual(updated_cheese_qty, original_cheese_qty - 300)

    def test_failed_delivery_does_not_deduct_inventory(self):
        """A failed order should leave inventory quantities unchanged."""
        recipe_data = [
            {
                "recipe_id": 1,
                "name": "Test Dish",
                "ingredients": [
                    {"name": "Flour", "qty_grams": 600},
                ],
            }
        ]
        inventory_data = [
            make_inventory_item("Flour", 500),
        ]
        status_data = []
        restock_data = []
        order_data = [
            {
                "order_id": 404,
                "brand": "Test Kitchen",
                "items": [{"item": "Test Dish", "qty": 1}],
            }
        ]

        original_flour_qty = inventory_data[0]["qty_grams"]

        processed_orders = process_orders(
            recipe_data,
            inventory_data,
            order_data,
            status_data,
            restock_data,
            reference_date=date(2026, 6, 3),
        )

        updated_flour_qty = inventory_data[0]["qty_grams"]

        self.assertFalse(processed_orders[0]["fulfilled"])
        self.assertEqual(updated_flour_qty, original_flour_qty)


class TestCumulativeInventoryDeduction(unittest.TestCase):
    """Verify inventory is consumed cumulatively across sequential orders."""

    def test_two_orders_consuming_same_ingredient_use_combined_deduction(self):
        """Two delivered orders should deduct the combined shared ingredient total."""
        recipe_data = deepcopy(load_recipes())
        inventory_data = deepcopy(load_inventory())
        status_data = []
        restock_data = []
        order_data = [
            {"order_id": 401, "brand": "Test Kitchen", "items": [{"item": "Margherita Pizza", "qty": 1}]},
            {"order_id": 402, "brand": "Test Kitchen", "items": [{"item": "Chocolate Cake", "qty": 1}]},
        ]

        original_flour_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Flour"
        )

        processed_orders = process_orders(
            recipe_data,
            inventory_data,
            order_data,
            status_data,
            restock_data,
            # Use a simulation date before any ingredient expiry so both orders
            # can succeed and we can focus purely on cumulative deduction.
            reference_date=date(2025, 12, 31),
        )

        updated_flour_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Flour"
        )

        self.assertTrue(processed_orders[0]["fulfilled"])
        self.assertTrue(processed_orders[1]["fulfilled"])
        self.assertEqual(updated_flour_qty, original_flour_qty - 550)

    def test_later_order_fails_after_prior_order_consumes_remaining_stock(self):
        """A later order should fail if an earlier order uses the remaining shared stock."""
        recipe_data = [
            {
                "recipe_id": 1,
                "name": "First Dish",
                "ingredients": [{"name": "Cheese", "qty_grams": 600}],
            },
            {
                "recipe_id": 2,
                "name": "Second Dish",
                "ingredients": [{"name": "Cheese", "qty_grams": 500}],
            },
        ]
        inventory_data = [
            make_inventory_item("Cheese", 1000),
        ]
        order_data = [
            {"order_id": 501, "brand": "Test Kitchen", "items": [{"item": "First Dish", "qty": 1}]},
            {"order_id": 502, "brand": "Test Kitchen", "items": [{"item": "Second Dish", "qty": 1}]},
        ]
        status_data = []
        restock_data = []

        processed_orders = process_orders(
            recipe_data,
            inventory_data,
            order_data,
            status_data,
            restock_data,
            reference_date=date(2026, 6, 3),
        )

        self.assertTrue(processed_orders[0]["fulfilled"])
        self.assertFalse(processed_orders[1]["fulfilled"])
        self.assertIn("Cheese", processed_orders[1]["reason"])
        self.assertEqual(status_data[1]["order_id"], 502)
        self.assertFalse(status_data[1]["delivered"])
        self.assertEqual(restock_data[0]["item"], "Cheese")
        self.assertEqual(restock_data[0]["qty_needed_grams"], 9600)
        self.assertEqual(restock_data[0]["reason"], "Running low on stock")

    def test_final_inventory_matches_expected_remaining_quantities(self):
        """Final inventory should reflect all successful cumulative deductions."""
        recipe_data = deepcopy(load_recipes())
        inventory_data = deepcopy(load_inventory())
        status_data = []
        restock_data = []
        order_data = [
            {"order_id": 601, "brand": "Test Kitchen", "items": [{"item": "Margherita Pizza", "qty": 2}]},
            {"order_id": 602, "brand": "Test Kitchen", "items": [{"item": "Chocolate Cake", "qty": 1}]},
        ]
 
        process_orders(
            recipe_data,
            inventory_data,
            order_data,
            status_data,
            restock_data,
            # Use a simulation date before any ingredient expiry so this test
            # focuses purely on cumulative deductions.
            reference_date=date(2025, 12, 31),
        )

        flour_qty = next(item["qty_grams"] for item in inventory_data if item["ingredient"] == "Flour")
        sauce_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Tomato Sauce"
        )
        cheese_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Mozzarella Cheese"
        )
        chocolate_qty = next(
            item["qty_grams"] for item in inventory_data if item["ingredient"] == "Chocolate"
        )
        sugar_qty = next(item["qty_grams"] for item in inventory_data if item["ingredient"] == "Sugar")

        self.assertEqual(flour_qty, 9150)
        self.assertEqual(sauce_qty, 9800)
        self.assertEqual(cheese_qty, 9700)
        self.assertEqual(chocolate_qty, 9850)
        self.assertEqual(sugar_qty, 9900)


class TestInventoryAvailabilityCheck(unittest.TestCase):
    """Verify inventory availability checks for normal and edge cases."""

    def test_all_ingredients_available(self):
        """All requirements met should set all_available=True and flags per item."""
        inventory_data = [
            make_inventory_item("Flour", 1000),
        ]
        requirements = [{"name": "Flour", "required_qty_grams": 500}]

        result = check_inventory_availability(inventory_data, requirements, reference_date=date(2026, 6, 3))

        self.assertTrue(result["all_available"])
        self.assertTrue(result["details"][0]["is_available"])

    def test_missing_ingredient_marks_unavailable(self):
        """Missing ingredients should report zero available and not available."""
        inventory_data = []
        requirements = [{"name": "Flour", "required_qty_grams": 500}]

        result = check_inventory_availability(inventory_data, requirements, reference_date=date(2026, 6, 3))

        self.assertFalse(result["all_available"])
        self.assertEqual(result["details"][0]["available_qty_grams"], 0)
        self.assertFalse(result["details"][0]["is_available"])

    def test_insufficient_quantity_marks_unavailable(self):
        """Not enough grams in stock should mark the ingredient as unavailable."""
        inventory_data = [
            make_inventory_item("Flour", 400),
        ]
        requirements = [{"name": "Flour", "required_qty_grams": 500}]

        result = check_inventory_availability(inventory_data, requirements, reference_date=date(2026, 6, 3))

        self.assertFalse(result["all_available"])
        self.assertFalse(result["details"][0]["is_available"])

    def test_expired_ingredient_is_treated_as_unavailable(self):
        """Ingredients expired before the reference date should not be used."""
        inventory_data = [
            make_inventory_item("Flour", 1000, expiry_date="2026-06-01"),
        ]
        requirements = [{"name": "Flour", "required_qty_grams": 500}]

        result = check_inventory_availability(inventory_data, requirements, reference_date=date(2026, 6, 3))

        self.assertFalse(result["all_available"])
        self.assertFalse(result["details"][0]["is_available"])


class TestRestockRules(unittest.TestCase):
    """Verify the Task 5 rule-based restock calculations."""

    def test_expiring_soon_sets_full_restock_quantity(self):
        """Ingredients expiring within 5 days should be marked as expiring soon."""
        inventory_data = [
            make_inventory_item("Cream", 7000, expiry_date="2026-06-06"),
        ]

        restock_data = calculate_restock_needs(inventory_data, reference_date=date(2026, 6, 3))

        self.assertEqual(
            restock_data,
            [{"item": "Cream", "qty_needed_grams": 10000, "reason": "Expiring soon"}],
        )

    def test_multiple_restock_reasons_are_combined(self):
        """Ingredients can carry multiple restock reasons in a combined string."""
        inventory_data = [
            make_inventory_item("Lettuce", 500, expiry_date="2026-06-06"),
        ]

        restock_data = calculate_restock_needs(inventory_data, reference_date=date(2026, 6, 3))

        self.assertEqual(len(restock_data), 1)
        entry = restock_data[0]
        self.assertEqual(entry["item"], "Lettuce")
        self.assertIn("Expiring soon", entry["reason"])
        self.assertIn("Running low on stock", entry["reason"])
        # Quantity should be at least enough to reach par level
        self.assertGreaterEqual(entry["qty_needed_grams"], 9500)

    def test_out_of_stock_sets_full_restock_quantity(self):
        """Zero final stock should be marked as out of stock with 10,000 grams needed."""
        inventory_data = [
            make_inventory_item("Bun", 0),
        ]

        restock_data = calculate_restock_needs(inventory_data, reference_date=date(2026, 6, 3))

        self.assertEqual(
            restock_data,
            [{"item": "Bun", "qty_needed_grams": 10000, "reason": "Out of stock"}],
        )

    def test_running_low_calculates_amount_needed_to_reach_ten_thousand(self):
        """Low stock should request only the amount needed to reach 10,000 grams."""
        inventory_data = [
            make_inventory_item("Chicken Breast", 500),
        ]

        restock_data = calculate_restock_needs(inventory_data, reference_date=date(2026, 6, 3))

        self.assertEqual(
            restock_data,
            [
                {
                    "item": "Chicken Breast",
                    "qty_needed_grams": 9500,
                    "reason": "Running low on stock",
                }
            ],
        )

    def test_adequate_stock_without_expiry_issue_is_not_flagged(self):
        """Adequate stock with no near-expiry condition should not appear in restock."""
        inventory_data = [
            make_inventory_item("Tomato Sauce", 7000),
        ]

        restock_data = calculate_restock_needs(inventory_data, reference_date=date(2026, 6, 3))

        self.assertEqual(restock_data, [])


class TestBusinessSummary(unittest.TestCase):
    """Verify the business summary structure and key metrics."""

    def test_build_business_summary_counts_and_sections(self):
        """Summary should compute counts and rollups from small sample data."""
        # Small sample with one delivered and one failed order to exercise
        # order counts, reasons, and brand breakdown.
        processed_orders = [
            {
                "order_id": 1,
                "brand": "Brand A",
                "fulfilled": True,
                "reason": "Delivered",
            },
            {
                "order_id": 2,
                "brand": "Brand A",
                "fulfilled": False,
                "reason": "Missing or insufficient ingredients: Flour",
            },
        ]

        # Two ingredients: one comfortably above par, one below par.
        inventory_data = [
            make_inventory_item("Flour", 8000),
            make_inventory_item("Salt", 12000),
        ]

        # Restock entries that exercise both expiring-soon and generic reasons.
        restock_data = [
            {"item": "Eggs", "qty_needed_grams": 5000, "reason": "Expiring soon"},
            {
                "item": "Flour",
                "qty_needed_grams": 2000,
                "reason": "Running low on stock",
            },
        ]

        # Status data is not used directly by build_business_summary today, but we
        # pass a simple structure for completeness and future-proofing.
        status_data = [
            {"order_id": 1, "delivered": True, "remark": "Delivered"},
            {
                "order_id": 2,
                "delivered": False,
                "remark": "Missing or insufficient ingredients: Flour",
            },
        ]

        summary = build_business_summary(
            processed_orders,
            inventory_data,
            restock_data,
            status_data,
        )

        # Orders section checks
        orders = summary["orders"]
        self.assertEqual(orders["total_orders"], 2)
        self.assertEqual(orders["delivered_orders"], 1)
        self.assertEqual(orders["not_delivered_orders"], 1)
        self.assertAlmostEqual(orders["delivery_rate_pct"], 50.0)

        # There should be at least one failure reason entry mentioning Flour.
        reason_strings = {entry["reason"] for entry in orders["by_reason"]}
        self.assertTrue(any("Flour" in reason for reason in reason_strings))

        # Brand breakdown should show a single brand with one delivered and one not.
        self.assertEqual(len(orders["by_brand"]), 1)
        brand_entry = orders["by_brand"][0]
        self.assertEqual(brand_entry["brand"], "Brand A")
        self.assertEqual(brand_entry["delivered"], 1)
        self.assertEqual(brand_entry["not_delivered"], 1)

        # Inventory section checks
        inventory = summary["inventory"]
        self.assertEqual(inventory["total_ingredients"], 2)
        self.assertIn("Flour", inventory["ingredients_below_par"])
        self.assertIn("Eggs", inventory["ingredients_expiring_soon"])

        # Restock section checks
        restock_summary = summary["restock"]
        self.assertEqual(restock_summary["total_restock_items"], 2)
        self.assertEqual(restock_summary["total_restock_qty_grams"], 7000)
        item_names = {entry["item"] for entry in restock_summary["items"]}
        self.assertSetEqual(item_names, {"Eggs", "Flour"})

    def test_build_business_summary_handles_empty_inputs(self):
        """Summary should handle empty tables without raising errors."""
        summary = build_business_summary([], [], [], [])

        # Orders section should report zeros and empty breakdowns.
        orders = summary["orders"]
        self.assertEqual(orders["total_orders"], 0)
        self.assertEqual(orders["delivered_orders"], 0)
        self.assertEqual(orders["not_delivered_orders"], 0)
        self.assertEqual(orders["delivery_rate_pct"], 0.0)
        self.assertEqual(orders["by_reason"], [])
        self.assertEqual(orders["by_brand"], [])

        # Inventory and restock sections should also be empty but well-formed.
        inventory = summary["inventory"]
        self.assertEqual(inventory["total_ingredients"], 0)
        self.assertEqual(inventory["ingredients_below_par"], [])
        self.assertEqual(inventory["ingredients_expiring_soon"], [])

        restock = summary["restock"]
        self.assertEqual(restock["total_restock_items"], 0)
        self.assertEqual(restock["total_restock_qty_grams"], 0)
        self.assertEqual(restock["items"], [])

    def test_build_business_summary_html_contains_key_sections(self):
        """HTML summary should include core headings and key metrics."""
        summary = build_business_summary([], [], [], [])
        html = build_business_summary_html(summary)

        self.assertIn("<html", html)
        self.assertIn("Cloud Kitchen Business Summary", html)
        self.assertIn("Orders and Delivery", html)
        self.assertIn("Inventory Snapshot", html)
        self.assertIn("Restock Overview", html)


if __name__ == "__main__":
    unittest.main()
