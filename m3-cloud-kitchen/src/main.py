"""Baseline entry point for loading and printing cloud kitchen seed data."""

from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
import webbrowser

from seed_data import inventory, orders, recipes, restock, status

# Restock rule configuration for Task 8.
# Base par level target (grams) for each ingredient.
PAR_LEVEL_GRAMS = 10000
# Threshold at or below which an ingredient is considered "running low".
LOW_STOCK_THRESHOLD_GRAMS = 1000
# Number of days from the simulation date for an ingredient to be flagged
# as "expiring soon".
EXPIRING_SOON_WINDOW_DAYS = 5

# Common status and restock reason strings used throughout the simulation.
STATUS_REMARK_DELIVERED = "Delivered"
STATUS_REASON_NO_RECIPE_PREFIX = "No matching recipe for item(s): "
STATUS_REASON_MISSING_INGREDIENTS_PREFIX = "Missing or insufficient ingredients: "
RESTOCK_REASON_ORDER_SHORTAGE = "Missing or insufficient for order fulfillment"
RESTOCK_REASON_EXPIRING_SOON = "Expiring soon"
RESTOCK_REASON_OUT_OF_STOCK = "Out of stock"
RESTOCK_REASON_RUNNING_LOW = "Running low on stock"


def load_recipes():
    """Return the seeded recipe records for use in the application."""
    # Assumption to verify: importing these module-level lists directly is acceptable
    # for Task 1, and we do not yet need defensive copying or a database/file loader.
    return recipes


def print_recipes(recipe_data):
    """Print every recipe and its ingredient requirements to the console."""
    print("\n=== Recipes ===")
    for recipe in recipe_data:
        print(f"Recipe ID: {recipe['recipe_id']}")
        print(f"Name: {recipe['name']}")
        print("Ingredients:")
        for ingredient in recipe["ingredients"]:
            print(f"  - {ingredient['name']}: {ingredient['qty_grams']} grams")
        print()


def load_inventory():
    """Return the seeded inventory records for the simulation."""
    # Assumption to verify: inventory quantities are intentionally stored in grams
    # for every ingredient, including items like buns that might later use unit counts.
    return inventory


def print_inventory(inventory_data):
    """Print every inventory item with quantity and expiry information."""
    print("\n=== Inventory ===")
    for item in inventory_data:
        print(f"Ingredient: {item['ingredient']}")
        print(f"Quantity: {item['qty_grams']} grams")
        print(f"Expiry Date: {item['expiry_date']}")
        print()


def load_orders():
    """Return the seeded customer order records."""
    # Assumption to verify: order item names are expected to match recipe names exactly.
    return orders


def print_orders(order_data):
    """Print every order, including its brand and requested items."""
    print("\n=== Orders ===")
    for order in order_data:
        print(f"Order ID: {order['order_id']}")
        print(f"Brand: {order['brand']}")
        print("Items:")
        for item in order["items"]:
            print(f"  - {item['item']}: {item['qty']}")
        print()


def load_restock():
    """Return the seeded restock recommendations."""
    # Incomplete / follow-up: the seed table is still available for baseline loading
    # tests, but the live restock output is now recalculated from final inventory.
    return restock


def print_restock(restock_data):
    """Print every restock item with quantity needed and reason."""
    print("\n=== Restock ===")
    for item in restock_data:
        print(f"Item: {item['item']}")
        print(f"Quantity Needed: {item['qty_needed_grams']} grams")
        print(f"Reason: {item['reason']}")
        print()


def load_status():
    """Return the seeded delivery status records."""
    # Uncertain: it is not yet clear whether status should remain independent seed
    # data or later be derived from order fulfillment results in the simulation.
    return status


def print_status(status_data):
    """Print every order status with delivery result and remark."""
    print("\n=== Status ===")
    for entry in status_data:
        print(f"Order ID: {entry['order_id']}")
        print(f"Delivered: {entry['delivered']}")
        print(f"Remark: {entry['remark']}")
        print()


def find_recipe_by_name(recipe_data, item_name, strict=False):
    """Return the recipe that matches an order item name.

    Parameters
    ----------
    recipe_data : list[dict]
        The full recipes table loaded from seed_data.
    item_name : str
        The menu item name from an order line.
    strict : bool, optional
        When False (default), the function returns the matching recipe or None
        if not found. When True, the function raises a clear error if no recipe
        exists for the given item name.

    Returns
    -------
    dict | None
        The matching recipe record if found; otherwise None when strict is False.
    """
    # Step 0: validate and normalize the incoming item name so callers get an
    # immediate error for bad inputs, and so lookups are case-insensitive and
    # tolerant of leading/trailing whitespace.
    if not isinstance(item_name, str) or not item_name.strip():
        raise ValueError("item_name must be a non-empty string.")
    normalized_item_name = item_name.strip().lower()

    # Step 1: iterate over recipes and compare normalized names so that
    # " Margherita Pizza ", "margherita pizza", etc. all resolve to the
    # same underlying recipe.
    for recipe in recipe_data:
        if recipe["name"].strip().lower() == normalized_item_name:
            return recipe

    # Step 2: if no recipe is found, either return None (non-strict mode) so the
    # caller can handle a missing recipe gracefully, or raise a LookupError in
    # strict mode with a helpful message that lists valid recipe names.
    if strict:
        valid_names = sorted(r["name"] for r in recipe_data)
        raise LookupError(
            f"No recipe found for '{item_name}'. Valid items: {', '.join(valid_names)}"
        )

    return None


def calculate_ingredient_requirements(recipe, quantity):
    """Return the total grams required for each ingredient in an order item."""
    requirements = []

    # Step 2: multiply each recipe ingredient quantity by the ordered item count
    # so we know the total grams needed to prepare that order item.
    for ingredient in recipe["ingredients"]:
        requirements.append(
            {
                "name": ingredient["name"],
                "required_qty_grams": ingredient["qty_grams"] * quantity,
            }
        )

    return requirements


def check_inventory_availability(inventory_data, requirements, reference_date=None):
    """Summarize whether inventory can satisfy a set of ingredient requirements.

    Parameters
    ----------
    inventory_data : list[dict]
        The current inventory table (ingredient, qty_grams, expiry_date).
    requirements : list[dict]
        Per-ingredient demand records with keys ``name`` and ``required_qty_grams``.
    reference_date : datetime.date | None
        The simulation date used to evaluate expiry. If None, defaults to
        ``date.today()``.

    Returns
    -------
    dict
        A summary dictionary with two keys:
        - ``all_available`` (bool): True only if every requirement is fully met.
        - ``details`` (list[dict]): one entry per ingredient with:
          ``ingredient``, ``required_qty_grams``, ``available_qty_grams``,
          and ``is_available``.
    """
    # Step 0: choose a reference date so expiry checks are deterministic. When
    # no explicit simulation date is provided, we fall back to today's date.
    if reference_date is None:
        reference_date = date.today()

    inventory_lookup = {item["ingredient"]: item for item in inventory_data}
    availability_results = []
    all_available = True

    # Step 3: compare each required ingredient against the inventory table to see
    # whether it exists, is not expired, and whether the available grams are
    # sufficient.
    for requirement in requirements:
        inventory_item = inventory_lookup.get(requirement["name"])

        if inventory_item is not None:
            # Parse the stored expiry date string and determine whether the
            # ingredient should be considered expired for this simulation run.
            expiry_date = datetime.strptime(inventory_item["expiry_date"], "%Y-%m-%d").date()
            is_expired = expiry_date < reference_date
            available_qty = inventory_item["qty_grams"]
        else:
            is_expired = False
            available_qty = 0

        # An ingredient is available only if it exists in inventory, is not
        # expired, and has at least the required grams.
        is_available = (
            inventory_item is not None
            and not is_expired
            and available_qty >= requirement["required_qty_grams"]
        )

        availability_results.append(
            {
                "ingredient": requirement["name"],
                "required_qty_grams": requirement["required_qty_grams"],
                "available_qty_grams": available_qty,
                "is_available": is_available,
            }
        )

        if not is_available:
            all_available = False

    return {"all_available": all_available, "details": availability_results}


def combine_requirements(requirement_groups):
    """Merge repeated ingredient requirements into a single total per ingredient."""
    combined_requirements = {}

    # Step 2: combine ingredient demand across all items in the same order so
    # fulfillment is checked against the total grams needed for the entire order.
    # Step 2: combine ingredient demand across all items in the same order so
    # fulfillment is checked against the total grams needed for the entire order.
    for requirements in requirement_groups:
        for requirement in requirements:
            ingredient_name = requirement["name"]
            combined_requirements.setdefault(ingredient_name, 0)
            combined_requirements[ingredient_name] += requirement["required_qty_grams"]
    return [
        {"name": ingredient_name, "required_qty_grams": required_qty}
        for ingredient_name, required_qty in combined_requirements.items()
    ]


def deduct_inventory(inventory_data, requirements):
    """Subtract the used ingredient grams from inventory after a successful order."""
    inventory_lookup = {item["ingredient"]: item for item in inventory_data}

    # Step 4: deduct only after the full order passes the availability check so
    # we do not partially consume stock for orders that cannot be delivered.
    # Assumption to verify: partial stock should not be deducted for failed orders;
    # inventory changes only when the entire order is considered deliverable.
    for requirement in requirements:
        inventory_lookup[requirement["name"]]["qty_grams"] -= requirement["required_qty_grams"]


def apply_final_inventory_snapshot(inventory_data, final_inventory_data):
    """Copy the final cumulative inventory quantities back into the main table."""
    final_inventory_lookup = {
        item["ingredient"]: item["qty_grams"] for item in final_inventory_data
    }

    # Step 6: update the final inventory table only after all orders have been
    # processed so the printed inventory reflects the true remaining stock.
    for item in inventory_data:
        if item["ingredient"] in final_inventory_lookup:
            item["qty_grams"] = final_inventory_lookup[item["ingredient"]]


def update_status_entry(status_data, order_id, delivered, remark):
    """Update or create a status-table entry for a processed order."""
    for entry in status_data:
        if entry["order_id"] == order_id:
            entry["delivered"] = delivered
            entry["remark"] = remark
            return

    # Incomplete / follow-up: if later tasks formalize a stricter schema, we may
    # want to prevent new status rows and require every order to exist up front.
    status_data.append({"order_id": order_id, "delivered": delivered, "remark": remark})


def calculate_restock_needs(inventory_data, reference_date=None):
    """Build restock recommendations from final inventory using rule-based logic.

    Restock rules (Task 8 baseline):
    - **Expiring soon**: ingredients with expiry dates within
      ``EXPIRING_SOON_WINDOW_DAYS`` of ``reference_date`` are restocked to
      ``PAR_LEVEL_GRAMS`` and take priority over stock-level checks.
    - **Out of stock**: ingredients at exactly 0 grams are restocked to
      ``PAR_LEVEL_GRAMS``.
    - **Running low**: ingredients with quantity at or below
      ``LOW_STOCK_THRESHOLD_GRAMS`` but above 0 are topped up to
      ``PAR_LEVEL_GRAMS``.

    The current implementation attaches a single primary reason per ingredient.
    Later Task 8 steps may extend this to support multiple reasons.

    Parameters
    ----------
    inventory_data : list[dict]
        Final inventory records after all orders have been processed.
    reference_date : datetime.date | None
        Simulation date used to evaluate "expiring soon". Defaults to today
        when not provided.
    """
    if reference_date is None:
        # Assumption to verify: when no simulation date is passed in, the code uses
        # Python's date.today() from the local runtime environment as "today."
        # Please verify this matches the intended simulation date basis.
        reference_date = date.today()

    restock_recommendations = []

    for item in inventory_data:
        expiry_date = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
        days_until_expiry = (expiry_date - reference_date).days

        # Track all applicable reasons so we can preserve multiple restock
        # drivers when they occur (e.g., low stock and expiring soon).
        reasons: list[str] = []
        qty_needed_grams = 0

        # Rule 1: expired or expiring soon (within the configured window)
        # This includes ingredients that are already past their expiry date
        # as well as those that will expire in the next
        # ``EXPIRING_SOON_WINDOW_DAYS`` days.
        if days_until_expiry <= EXPIRING_SOON_WINDOW_DAYS:
            reasons.append(RESTOCK_REASON_EXPIRING_SOON)
            # Top up to full par level based on expiry risk alone.
            qty_needed_grams = max(qty_needed_grams, PAR_LEVEL_GRAMS)

        # Rule 2: out of stock
        if item["qty_grams"] == 0:
            reasons.append(RESTOCK_REASON_OUT_OF_STOCK)
            qty_needed_grams = max(qty_needed_grams, PAR_LEVEL_GRAMS)

        # Rule 3: running low (but not empty)
        if 0 < item["qty_grams"] <= LOW_STOCK_THRESHOLD_GRAMS:
            reasons.append(RESTOCK_REASON_RUNNING_LOW)
            qty_needed_grams = max(qty_needed_grams, PAR_LEVEL_GRAMS - item["qty_grams"])

        if reasons:
            # For backward compatibility with earlier tasks/tests, keep a
            # single "reason" string while also allowing multiple reasons to
            # be represented when needed.
            primary_reason = reasons[0] if len(reasons) == 1 else "; ".join(reasons)

            restock_recommendations.append(
                {
                    "item": item["ingredient"],
                    "qty_needed_grams": qty_needed_grams,
                    "reason": primary_reason,
                }
            )

    return restock_recommendations


def refresh_restock_table(restock_data, inventory_data, reference_date=None):
    """Replace the live restock table with recommendations from final inventory."""
    # Step 7: rebuild the restock table after all orders have been processed so it
    # reflects the final inventory state instead of intermediate order failures.
    # Incomplete / follow-up: this replaces the whole restock table each run, so it
    # does not preserve historical/manual restock notes outside the current simulation.
    restock_data.clear()
    restock_data.extend(calculate_restock_needs(inventory_data, reference_date))


def process_single_order(
    order,
    recipe_data,
    inventory_data,
    status_data,
    restock_data,
    reference_date=None,
):
    """Process a single order and return a detailed result structure.

    This helper defines the interface and return shape for Task 6. It now
    implements both the success path and the failure path so callers can see
    whether the order was fulfilled, why, and which ingredients were missing.

    Parameters
    ----------
    order : dict
        A single order record from the orders table.
    recipe_data : list[dict]
        The full recipes table, used for recipe lookup.
    inventory_data : list[dict]
        The current working inventory that will be read and updated.
    status_data : list[dict]
        The status table that will be updated with delivery results.
    restock_data : list[dict]
        The restock list that will be extended with missing ingredients.
    reference_date : datetime.date | None
        Optional simulation date forwarded to availability checks.

    Returns
    -------
    dict
        A result dictionary mirroring the structure used by ``process_orders``.
    """
    # Start with a skeleton result so callers can inspect what happened.
    order_result = {
        "order_id": order["order_id"],
        "brand": order["brand"],
        "items": [],
        "order_requirements": [],
        "inventory_check": None,
        "fulfilled": False,
        "reason": "",
    }

    requirement_groups = []
    missing_recipe_items = []

    # Step 1: look up a recipe for each ordered item and record per-item
    # ingredient requirements. If any recipe is missing, we defer full failure
    # handling to a later Task 6 step and surface a clear error for now.
    for item in order["items"]:
        recipe = find_recipe_by_name(recipe_data, item["item"])

        if recipe is None:
            missing_recipe_items.append(item["item"])
            order_result["items"].append(
                {
                    "item": item["item"],
                    "qty": item["qty"],
                    "recipe_found": False,
                    "requirements": [],
                }
            )
            continue

        requirements = calculate_ingredient_requirements(recipe, item["qty"])
        requirement_groups.append(requirements)
        order_result["items"].append(
            {
                "item": item["item"],
                "qty": item["qty"],
                "recipe_found": True,
                "requirements": requirements,
            }
        )

    # If any recipe was missing, we treat this as a failure for the order and
    # record a human-readable reason. We do not attempt substitutions.
    order_requirements = []
    if missing_recipe_items:
        reason_parts = [
            STATUS_REASON_NO_RECIPE_PREFIX + ", ".join(missing_recipe_items)
        ]
        order_result["fulfilled"] = False
        order_result["reason"] = " | ".join(reason_parts)
        update_status_entry(status_data, order["order_id"], False, order_result["reason"])
        return order_result

    # Step 2: combine per-item ingredient requirements into a single
    # order-level demand table so inventory is checked against totals.
    order_requirements = combine_requirements(requirement_groups)
    order_result["order_requirements"] = order_requirements

    # Step 3: check whether inventory can satisfy the combined requirements,
    # including expiry rules via reference_date.
    inventory_check = check_inventory_availability(
        inventory_data, order_requirements, reference_date=reference_date
    )
    order_result["inventory_check"] = inventory_check

    # Identify any ingredients that are missing, expired, or insufficient.
    missing_ingredients = [
        detail for detail in inventory_check["details"] if not detail["is_available"]
    ]

    if not inventory_check["all_available"]:
        # Failure path: build a clear reason message listing missing ingredients
        # and add those ingredients to the restock recommendations.
        missing_names = ", ".join(detail["ingredient"] for detail in missing_ingredients)
        order_result["fulfilled"] = False
        order_result["reason"] = (
            STATUS_REASON_MISSING_INGREDIENTS_PREFIX + missing_names
        )
        update_status_entry(status_data, order["order_id"], False, order_result["reason"])

        for detail in missing_ingredients:
            restock_data.append(
                {
                    "item": detail["ingredient"],
                    # Simple rule: request enough to reach 10,000 grams from
                    # whatever is currently available.
                    "qty_needed_grams": PAR_LEVEL_GRAMS - detail["available_qty_grams"],
                    "reason": RESTOCK_REASON_ORDER_SHORTAGE,
                }
            )

        return order_result

    # Step 4 (success path): deduct the used grams from the working inventory,
    # mark the order as delivered, and update the status table.
    deduct_inventory(inventory_data, order_requirements)
    order_result["fulfilled"] = True
    order_result["reason"] = STATUS_REMARK_DELIVERED
    update_status_entry(status_data, order["order_id"], True, STATUS_REMARK_DELIVERED)

    return order_result


def process_orders(
    recipe_data,
    inventory_data,
    order_data,
    status_data,
    restock_data,
    reference_date=None,
):
    """Process all orders in sequence using the single-order helper.

    This function delegates the core fulfillment logic to ``process_single_order``
    and enforces **cumulative** inventory usage:
    - A shared ``working_inventory`` copy is passed into each order.
    - Successful orders deduct from ``working_inventory`` only.
    - Later orders see whatever quantity remains after earlier deductions.
    - After all orders, ``inventory_data`` is updated once from the final
      working snapshot and restock recommendations are rebuilt.
    """
    processed_orders = []
    # Step 0: use a working inventory snapshot during processing so each order is
    # checked against stock remaining after previous successful orders, while the
    # final inventory table is only updated once the full order list is complete.
    working_inventory = deepcopy(inventory_data)

    for order in order_data:
        # Step 1: delegate per-order work to process_single_order, passing in the
        # shared working inventory, status table, and restock list.
        order_result = process_single_order(
            order,
            recipe_data,
            working_inventory,
            status_data,
            restock_data,
            reference_date=reference_date,
        )
        processed_orders.append(order_result)

    # Step 2: after all orders are processed, copy the cumulative working
    # inventory quantities back into the main inventory table.
    apply_final_inventory_snapshot(inventory_data, working_inventory)

    # Step 3: rebuild the restock table based on the final inventory state.
    refresh_restock_table(restock_data, inventory_data, reference_date)

    return processed_orders


def print_order_processing_results(processed_orders):
    """Print recipe lookup, ingredient demand, inventory checks, and fulfillment."""
    print("\n=== Order Processing ===")
    for order in processed_orders:
        print(f"Order ID: {order['order_id']}")
        print(f"Brand: {order['brand']}")

        for item in order["items"]:
            print(f"Item: {item['item']}")
            print(f"Quantity Ordered: {item['qty']}")
            print(f"Recipe Found: {item['recipe_found']}")

            if not item["recipe_found"]:
                print("Inventory Check: Skipped because the recipe was not found.")
                print()
                continue

            print("Required Ingredients:")
            for requirement in item["requirements"]:
                print(
                    f"  - {requirement['name']}: "
                    f"{requirement['required_qty_grams']} grams required"
                )

            print()

        print("Combined Order Requirements:")
        for requirement in order["order_requirements"]:
            print(f"  - {requirement['name']}: {requirement['required_qty_grams']} grams required")

        print(f"All Ingredients Available: {order['inventory_check']['all_available']}")
        print("Inventory Details:")
        for detail in order["inventory_check"]["details"]:
            print(
                f"  - {detail['ingredient']}: "
                f"required={detail['required_qty_grams']} grams, "
                f"available={detail['available_qty_grams']} grams, "
                f"enough={detail['is_available']}"
            )

        print(f"Fulfilled: {order['fulfilled']}")
        print(f"Reason: {order['reason']}")
        print()


def _group_orders_by_reason(processed_orders):
    """Return a list of {reason, count} entries for failed orders.

    This small helper keeps the grouping logic out of ``build_business_summary``
    so that function can read more like a high-level recipe.
    """
    reason_counts = {}
    for order in processed_orders:
        if order.get("fulfilled"):
            continue
        reason = order.get("reason") or "Unspecified"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return [
        {"reason": reason, "count": count}
        for reason, count in reason_counts.items()
    ]


def _summarize_brands(processed_orders):
    """Return a list of per-brand delivery stats.

    Each entry has the form {brand, delivered, not_delivered}.
    """
    brand_stats = {}
    for order in processed_orders:
        brand = order.get("brand") or "Unknown"
        stats = brand_stats.setdefault(
            brand, {"brand": brand, "delivered": 0, "not_delivered": 0}
        )
        if order.get("fulfilled"):
            stats["delivered"] += 1
        else:
            stats["not_delivered"] += 1

    return list(brand_stats.values())


def build_business_summary(processed_orders, inventory_data, restock_data, status_data):
    """Construct a manager-facing summary of the simulation results.

    This function defines the **shape** of the business summary for Task 9.
    Later steps (Task 9.2 and beyond) will implement the actual aggregation logic.

    Parameters
    ----------
    processed_orders : list[dict]
        The detailed per-order results returned from ``process_orders``.
    inventory_data : list[dict]
        The final inventory table after all orders have been processed.
    restock_data : list[dict]
        The final restock recommendations produced from ``calculate_restock_needs``.
    status_data : list[dict]
        The final status table indicating which orders were delivered and why.

    Returns
    -------
    dict
        A nested dictionary with three top-level sections:

        - ``"orders"``: high-level delivery performance metrics.
          Expected keys include::

              {
                  "total_orders": int,
                  "delivered_orders": int,
                  "not_delivered_orders": int,
                  "delivery_rate_pct": float,
                  "by_reason": [
                      {"reason": str, "count": int},
                  ],
                  "by_brand": [
                      {
                          "brand": str,
                          "delivered": int,
                          "not_delivered": int,
                      },
                  ],
              }

        - ``"inventory"``: key indicators about remaining stock and risk.
          Expected keys include::

              {
                  "total_ingredients": int,
                  "ingredients_below_par": [str],
                  "ingredients_expiring_soon": [str],
              }

        - ``"restock"``: a concise view of restock recommendations.
          Expected keys include::

              {
                  "total_restock_items": int,
                  "total_restock_qty_grams": int,
                  "items": [
                      {
                          "item": str,
                          "qty_needed_grams": int,
                          "reason": str,
                      },
                  ],
              }

    Notes
    -----
    - This interface is intentionally conservative: callers can rely on the
      presence of the keys described above, while future refinements may add
      more fields without breaking existing code.
    - The implementation initially raises ``NotImplementedError`` so that the
      structure is testable before the aggregation logic is written.
    """
    # Summary computation for Task 9.2: aggregate orders, inventory, and restock.
    # The steps are kept simple and readable so each section is easy to test.

    # 1) Build the orders section with high-level delivery metrics.
    total_orders = len(processed_orders)
    delivered_orders = sum(1 for order in processed_orders if order.get("fulfilled"))
    not_delivered_orders = total_orders - delivered_orders

    if total_orders > 0:
        delivery_rate_pct = (delivered_orders / total_orders) * 100.0
    else:
        delivery_rate_pct = 0.0

    # Group non-delivered orders by their failure reason.
    by_reason = _group_orders_by_reason(processed_orders)

    # Group results by brand to show performance per partner brand.
    by_brand = _summarize_brands(processed_orders)

    orders_section = {
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "not_delivered_orders": not_delivered_orders,
        "delivery_rate_pct": delivery_rate_pct,
        "by_reason": by_reason,
        "by_brand": by_brand,
    }

    # 2) Build the inventory section using the final inventory snapshot.
    total_ingredients = len(inventory_data)

    # Ingredients below par are any items with quantity strictly less than the
    # configured PAR_LEVEL_GRAMS threshold.
    ingredients_below_par = [
        item["ingredient"]
        for item in inventory_data
        if item.get("qty_grams", 0) < PAR_LEVEL_GRAMS
    ]

    # Ingredients expiring soon are inferred from restock entries whose reason
    # includes the "Expiring soon" flag.
    expiring_items = set()
    for entry in restock_data:
        reason = entry.get("reason", "")
        if "Expiring soon" in reason:
            expiring_items.add(entry.get("item"))

    ingredients_expiring_soon = sorted(name for name in expiring_items if name)

    inventory_section = {
        "total_ingredients": total_ingredients,
        "ingredients_below_par": ingredients_below_par,
        "ingredients_expiring_soon": ingredients_expiring_soon,
    }

    # 3) Build the restock section by rolling up quantities and listing items.
    total_restock_items = len(restock_data)
    total_restock_qty_grams = sum(
        entry.get("qty_needed_grams", 0) for entry in restock_data
    )

    # Create shallow copies of restock entries so callers can safely mutate the
    # summary without affecting the original restock table.
    restock_items = [
        {
            "item": entry.get("item"),
            "qty_needed_grams": entry.get("qty_needed_grams", 0),
            "reason": entry.get("reason", ""),
        }
        for entry in restock_data
    ]

    restock_section = {
        "total_restock_items": total_restock_items,
        "total_restock_qty_grams": total_restock_qty_grams,
        "items": restock_items,
    }

    # 4) Combine all sections into the final business summary structure.
    return {
        "orders": orders_section,
        "inventory": inventory_section,
        "restock": restock_section,
    }


def build_business_summary_html(summary):
    """Return an HTML representation of the business summary.

    This function is intended for end-user reporting. It takes the structured
    summary produced by ``build_business_summary`` and renders it into a
    simple, aesthetically formatted HTML string.
    """
    # Read the three main sections from the summary, falling back to empty
    # dictionaries so the renderer is resilient to missing keys.
    orders = summary.get("orders", {})
    inventory = summary.get("inventory", {})
    restock = summary.get("restock", {})

    # ``parts`` accumulates each HTML fragment and is joined once at the end.
    parts: list[str] = []

    # Basic document skeleton and inline CSS for layout and readability.
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang='en'>")
    parts.append("<head>")
    parts.append("  <meta charset='UTF-8'>")
    parts.append("  <title>Cloud Kitchen Business Summary</title>")
    parts.append(
        "  <style>"
        "body { font-family: Arial, sans-serif; margin: 20px; }"
        "h1, h2 { color: #333333; }"
        "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }"
        "th, td { border: 1px solid #dddddd; padding: 8px; text-align: left; }"
        "th { background-color: #f2f2f2; }"
        "tr:nth-child(even) { background-color: #fafafa; }"
        "</style>"
    )
    parts.append("</head>")
    parts.append("<body>")

    # High-level orders and delivery metrics (totals and delivery rate).
    parts.append("  <h1>Cloud Kitchen Business Summary</h1>")
    parts.append("  <h2>Orders and Delivery</h2>")
    parts.append("  <p>")
    parts.append(
        f"Total Orders: <strong>{orders.get('total_orders', 0)}</strong><br>"
        f"Delivered: <strong>{orders.get('delivered_orders', 0)}</strong><br>"
        f"Not Delivered: <strong>{orders.get('not_delivered_orders', 0)}</strong><br>"
        f"Delivery Rate: <strong>{orders.get('delivery_rate_pct', 0.0):.1f}%</strong>"
    )
    parts.append("  </p>")

    # Breakdown table of failure reasons for non-delivered orders.
    by_reason = orders.get("by_reason", [])
    if by_reason:
        parts.append("  <h3>Top Failure Reasons</h3>")
        parts.append("  <table>")
        parts.append("    <tr><th>Reason</th><th>Count</th></tr>")
        for entry in by_reason:
            parts.append(
                "    <tr>"
                f"<td>{entry.get('reason', '')}</td>"
                f"<td>{entry.get('count', 0)}</td>"
                "</tr>"
            )
        parts.append("  </table>")

    # Per-brand table highlighting delivery performance by partner brand.
    by_brand = orders.get("by_brand", [])
    if by_brand:
        parts.append("  <h3>Performance by Brand</h3>")
        parts.append("  <table>")
        parts.append("    <tr><th>Brand</th><th>Delivered</th><th>Not Delivered</th></tr>")
        for entry in by_brand:
            parts.append(
                "    <tr>"
                f"<td>{entry.get('brand', '')}</td>"
                f"<td>{entry.get('delivered', 0)}</td>"
                f"<td>{entry.get('not_delivered', 0)}</td>"
                "</tr>"
            )
        parts.append("  </table>")

    # Inventory snapshot headline: how many ingredients are being tracked.
    parts.append("  <h2>Inventory Snapshot</h2>")
    parts.append(
        f"  <p>Total Ingredients Tracked: "
        f"<strong>{inventory.get('total_ingredients', 0)}</strong></p>"
    )

    # Unordered list of ingredients that sit below the configured par level.
    below_par = inventory.get("ingredients_below_par", [])
    if below_par:
        parts.append("  <h3>Ingredients Below Par Level</h3>")
        parts.append("  <ul>")
        for name in below_par:
            parts.append(f"    <li>{name}</li>")
        parts.append("  </ul>")

    # Unordered list of ingredients that are expired or expiring soon.
    expiring = inventory.get("ingredients_expiring_soon", [])
    if expiring:
        parts.append("  <h3>Ingredients Expiring Soon</h3>")
        parts.append("  <ul>")
        for name in expiring:
            parts.append(f"    <li>{name}</li>")
        parts.append("  </ul>")

    # Aggregate restock metrics plus a detailed table per ingredient.
    parts.append("  <h2>Restock Overview</h2>")
    parts.append(
        f"  <p>Total Restock Items: "
        f"<strong>{restock.get('total_restock_items', 0)}</strong><br>"
        f"Total Restock Quantity: "
        f"<strong>{restock.get('total_restock_qty_grams', 0)} grams</strong>" \
        "</p>"
    )

    restock_items = restock.get("items", [])
    if restock_items:
        parts.append("  <table>")
        parts.append("    <tr><th>Item</th><th>Quantity Needed (grams)</th><th>Reason</th></tr>")
        for entry in restock_items:
            parts.append(
                "    <tr>"
                f"<td>{entry.get('item', '')}</td>"
                f"<td>{entry.get('qty_needed_grams', 0)}</td>"
                f"<td>{entry.get('reason', '')}</td>"
                "</tr>"
            )
        parts.append("  </table>")

    # Close out the HTML document and return a single string for callers to write
    # to disk or serve over HTTP.
    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts)


def print_business_summary(summary):
    """Pretty-print the business summary in a manager-friendly format.

    This function focuses on **presentation only**. It expects a summary
    dictionary produced by ``build_business_summary`` and prints a concise,
    human-readable report.
    """
    # Print a high-level section for orders and delivery performance.
    orders = summary.get("orders", {})
    print("\n=== Business Summary ===")
    print("\n-- Orders and Delivery --")
    print(f"Total Orders: {orders.get('total_orders', 0)}")
    print(f"Delivered: {orders.get('delivered_orders', 0)}")
    print(f"Not Delivered: {orders.get('not_delivered_orders', 0)}")
    print(
        f"Delivery Rate: {orders.get('delivery_rate_pct', 0.0):.1f}%"
    )

    # Show a compact breakdown of why orders failed.
    by_reason = orders.get("by_reason", [])
    if by_reason:
        print("\nTop Failure Reasons:")
        for entry in by_reason:
            print(f"  - {entry.get('reason')}: {entry.get('count', 0)} order(s)")

    # Show performance per partner brand.
    by_brand = orders.get("by_brand", [])
    if by_brand:
        print("\nPerformance by Brand:")
        for entry in by_brand:
            print(
                f"  - {entry.get('brand')}: "
                f"delivered={entry.get('delivered', 0)}, "
                f"not_delivered={entry.get('not_delivered', 0)}"
            )

    # Print key inventory signals: how many ingredients, which are weak or risky.
    inventory = summary.get("inventory", {})
    print("\n-- Inventory Snapshot --")
    print(f"Total Ingredients Tracked: {inventory.get('total_ingredients', 0)}")

    below_par = inventory.get("ingredients_below_par", [])
    if below_par:
        print("Ingredients Below Par Level:")
        for name in below_par:
            print(f"  - {name}")
    else:
        print("All ingredients are at or above par level.")

    expiring = inventory.get("ingredients_expiring_soon", [])
    if expiring:
        print("Ingredients Expiring Soon:")
        for name in expiring:
            print(f"  - {name}")

    # Summarize restock recommendations at the end.
    restock = summary.get("restock", {})
    print("\n-- Restock Overview --")
    print(f"Total Restock Items: {restock.get('total_restock_items', 0)}")
    print(
        "Total Restock Quantity: "
        f"{restock.get('total_restock_qty_grams', 0)} grams"
    )

    items = restock.get("items", [])
    if items:
        print("\nRestock Items:")
        for entry in items:
            print(
                f"  - {entry.get('item')}: "
                f"{entry.get('qty_needed_grams', 0)} grams "
                f"({entry.get('reason', 'No reason specified')})"
            )


def main(html: bool = True):
    """Load seed tables, run the simulation, and optionally open an HTML summary.

    Parameters
    ----------
    html : bool, optional
        When True, generate the business summary HTML and open it in the
        default web browser after printing the console summary.
    """
    # Assumption to verify: we process working copies of mutable tables so the seed
    # definitions stay unchanged across runs and tests.
    # Incomplete / follow-up: this script still prints results directly to the console
    # and does not yet persist updated inventory, restock, or status tables anywhere.

    # 1) Load all seed tables needed for the simulation.
    recipe_data = load_recipes()
    inventory_data = deepcopy(load_inventory())
    order_data = load_orders()
    # Step 8: start with an empty live restock table because recommendations are
    # now generated from final inventory after all orders have been processed.
    restock_data = []
    status_data = deepcopy(load_status())

    # 2) Process all orders and update inventory, restock, and status tables.
    processed_orders = process_orders(
        recipe_data,
        inventory_data,
        order_data,
        status_data,
        restock_data,
    )

    # 3) Compute a manager-facing business summary from the final tables.
    summary = build_business_summary(
        processed_orders,
        inventory_data,
        restock_data,
        status_data,
    )

    # 4) Print detailed technical output followed by the high-level summary.
    print_recipes(recipe_data)
    print_orders(order_data)
    print_order_processing_results(processed_orders)
    print_inventory(inventory_data)
    print_restock(restock_data)
    print_status(status_data)
    print_business_summary(summary)

    # 5) Optionally generate and open the HTML business summary in a browser.
    if html:
        html_content = build_business_summary_html(summary)
        output_path = Path("business_summary.html")
        output_path.write_text(html_content, encoding="utf-8")
        webbrowser.open(output_path.resolve().as_uri())


def test():
    print(load_recipes())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the cloud kitchen simulation and optional HTML summary.",
    )
    parser.add_argument(
        "--no-html",
        action="store_false",
        dest="html",
        default=True,
        help="Do not open the business summary in a web browser.",
    )
    args = parser.parse_args()

    main(html=args.html)