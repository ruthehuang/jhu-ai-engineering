# Project Specification – Cloud Kitchen Inventory Simulation

## 1. Project Purpose
Build a Python simulation for a cloud kitchen that:
- Processes customer orders against recipe-linked inventory.
- Updates delivery status.
- Deducts ingredient quantities cumulatively.
- Tracks expiry risk.
- Produces restock recommendations and a business-friendly summary.

## 2. Project Setup
m3-cloud-kitchen/
├── ref/                    # Reference materials
│   ├── AI-Assisted Cloud Kitchen Inventory Simulation.pdf
│   ├── AI_USAGE_LOG.md
│   └── PROJECT_SPEC.md
└── src/                    # Main project code
    ├── main.py             # Primary script for order fulfillment simulation
    ├── seed_data.py        # Data
    ├── test_main.py        # Unit tests for main.py
    └── business_summary.html  # Example generated HTML report

## 3. Data Structures (from `seed_data.py`)
- **Recipes**  
  - List of recipe records.  
  - Features: `recipe_id`, `name`, `ingredients` (list of `{name, qty_grams}`).

- **Inventory**  
  - List of inventory records.  
  - Features: `ingredient`, `qty_grams`, `expiry_date` (`YYYY-MM-DD`).

- **Orders**  
  - List of customer orders.  
  - Features: `order_id`, `brand`, `items` (list of `{item, qty}`).

- **Restock**  
  - List of restock recommendations.  
  - Features: `item`, `qty_needed_grams`, `reason`.

- **Status**  
  - List of delivery status entries.  
  - Features: `order_id`, `delivered` (bool), `remark`.

## 4. Business Rules (High Level)

### Order Processing
- For each order:
  1. For each item, look up the corresponding recipe by name.
  2. Multiply ingredient quantities by the ordered quantity.
  3. Aggregate ingredient demand across items in the same order.
  4. Check aggregated demand against **current** inventory (after prior orders).

### Inventory Availability
- Order can be fulfilled only if:
  - Every required ingredient exists in inventory.
  - Each has `available_qty ≥ required_qty`.
  - Ingredient is not expired / unusable (based on `expiry_date` and simulation date).

### Fulfillment Logic
- **If order can be fulfilled**:
  - Mark status: `delivered=True`, `remark="Delivered"`.
  - Deduct ingredient quantities from inventory **cumulatively**.
- **If order cannot be fulfilled**:
  - Mark status: `delivered=False`, `remark="Failed"`.
  - Record a clear reason (missing ingredients, insufficient quantity, expiry).
  - Add missing/insufficient/expired ingredients to restock recommendations.

- Base assumption: **all-or-nothing** fulfillment (no partial delivery).

### Cumulative Inventory
- Inventory is a single shared pool:
  - Order N uses inventory remaining after orders `1..N-1`.
  - No reset between orders within one simulation run.

### Restock & Expiry Rules (Defaults)
- Par level: **10,000 g**.
- Low / running-low threshold: **≤ 1,000 g**.
- Expiring-soon window: **within 5 days** of the simulation date.
- Restock output includes:
  - Ingredient name.
  - Current quantity.
  - Reason(s) (low, out-of-stock, expiring soon).
  - Quantity needed to reach par level.
  - Any relevant expiry information.
- If multiple reasons apply, preserve all (do not silently overwrite).

### Business-Friendly Summary
At the end of the simulation, produce a summary including:
- Number of orders delivered / not delivered.
- Reasons for non-delivery.
- Final inventory levels.
- Restock recommendations.
- Ingredients that are low, out of stock, expired, or expiring soon.

## 5. Architecture & Components

- **`main.py`**
  - Entry point for running the simulation.
  - Loads seed data from `seed_data.py`.
  - Orchestrates:
    - Data loading and printing.
    - Recipe lookup.
    - Ingredient requirement calculation.
    - Inventory availability checks.
    - Fulfillment and inventory deduction.
    - Restock logic and expiry handling.
    - Final business summary output.

- **`seed_data.py`**
  - Defines in-memory seed tables: `recipes`, `inventory`, `orders`, `restock`, `status`.

- **`test_main.py`**
  - Unit tests for major functions in `main.py`:
    - Data loading.
    - Recipe lookup.
    - Inventory availability.
    - Fulfillment logic.
    - Cumulative order processing.
    - Restock and expiry rules.
    - Final summary (at least smoke tests / key invariants).

- **`PROJECT_SPEC.md`**
  - Specification file to add context for AI.

- **`AI_USAGE_LOG.md`**
  - Log of major AI interactions: prompt, response summary, what was accepted/changed/rejected, and issues found.

## 6. Implementation Plan

**Task 1 – Project Setup**
- Create/organize: `main.py`, `seed_data.py`, `test_main.py`, `PROJECT_SPEC.md`, `AI_USAGE_LOG.md`.
- Run import test: confirm `main.py` can access data from `seed_data.py`.
- Document project organization and how to run code/tests.

**Task 2 – PROJECT_SPEC.md**
- Initialize this spec with:
  - Purpose, data structures, business rules, plan, testing strategy, assumptions.

**Task 3 – Load & Inspect Seed Data**
- Implement `load_recipes`, `load_inventory`, `load_orders`, `load_restock`, `load_status`.
- Implement corresponding `print_...` functions for console inspection.
- Add tests checking:
  - Data structures exist and have expected types.
  - Non-empty / basic field checks.
- Concrete tasks for AI:
    - T3.1 – Inspect seed data: Open  seed_data.py  and summarize the exact structure of  recipes ,  inventory ,  orders ,  restock ,  status .
    - T3.2 – Implement loader for one table: Add  load_recipes()  in  main.py  (with docstring + comments), then repeat pattern for  inventory ,  orders ,  restock ,  status .
    - T3.3 – Implement printer for one table: Add  print_recipes()  (nicely formatted), then parallel functions for the other four tables.
    - T3.4 – Wire into  main(): Call all loaders and printers in order.
    - T3.5 – Tests: In  test_main.py , add tests that each loader returns the expected type and key fields.

**Task 4 – Recipe Lookup**
- Implement `find_recipe_by_name(order_item_name)` (or similar).
- Handle missing recipes gracefully (e.g., flagged but not crashing).
- Add tests for:
  - Valid item.
  - Invalid item.
  - Multiple-quantity item.
- Concrete tasks for AI:
    - T4.1 – Clarify interfaces: Decide signatures: e.g.,  find_recipe_by_name(recipes, item_name, *, strict=False)  and a separate quantity-scaling helper.
    - T4.2 – Implement recipe lookup with error handling: Implement lookup that 
        - Validates  item_name  (non‑empty string).
        - Returns the matching recipe dict when found.
        - Returns  None  by default when not found.
        - Optionally raises a clear error (with suggestions/valid names) when  strict=True .
    - T4.3 – Quantity scaling helper: Function to compute ingredient requirements for a given quantity.
    - T4.4 – Unit tests: Tests for valid item, missing item, invalid input, and strict vs non‑strict modes.

**Task 5 – Inventory Availability Check**
- Implement `check_inventory_availability(inventory, requirements)`:
  - Returns whether all ingredients are available and details for each ingredient.
- Include expiry logic if applicable.
- Tests:
  - All available.
  - Missing ingredient.
  - Insufficient quantity.
  - Expired/invalid ingredient.
- Concrete tasks for AI:
    - T5.1 – Define interface and output shape: Decide signature, e.g.  check_inventory_availability(inventory, requirements, reference_date=None)  and exact return structure (e.g.  {all_available: bool, details: [...]} ).
    - T5.2 – Implement basic availability check (no expiry yet): For each required ingredient, find matching inventory row, compute available vs required, and flag  is_available .
    - T5.3 – Add expiry handling:  Incorporate  expiry_date  and  reference_date  (defaulting to  date.today() ), and mark expired items as unavailable with a clear reason.
    - T5.4 – Unit tests: Tests for: all available, missing ingredient, insufficient quantity, and expired ingredient.

**Task 6 – Fulfillment Logic**
- Implement `process_single_order(...)` or part of `process_orders`:
  - Delivered vs. not delivered.
  - Deduct inventory only for delivered orders.
  - Add missing/insufficient/expired ingredients to restock list.
- Tests:
  - Successful delivery.
  - Failed delivery.
  - Correct deduction.
  - No deduction when failing.
- Concrete tasks for AI:
    - T6.1 – Design fulfillment interface: Decide signature: e.g.,  process_single_order(order, recipes, inventory, status, restock, reference_date=None)  and return shape (fulfilled, reason, details).
    - T6.2 – Implement success path: Use recipe lookup + requirements +  check_inventory_availability . When all available: mark as delivered, deduct inventory, return success result.
    - T6.3 – Implement failure path: When missing/insufficient/expired: mark as not delivered, capture reason, add items to restock list.
    - T6.4 – Wire into multi-order processor: Call single‑order function for each order, using cumulative inventory.
    - T6.5 – Unit tests: Tests for successful delivery, failed delivery, correct deduction, and no deduction on failure.

**Task 7 – Cumulative Order Processing**
- Implement `process_orders(...)`:
  - Iterate through all orders using updated inventory.
- Tests:
  - Two orders sharing the same ingredient.
  - One order fails due to prior consumption.
  - Final inventory matches expected values.
- Concrete tasks for AI:
    - T7.1 – Verify cumulative behavior design: Confirm that  process_orders  uses a shared working inventory and only snapshots back at the end. Decide how to assert “cumulative” in tests (before/after quantities).
    - T7.2 – Simple two‑order success case: Write/adjust a test where two orders share an ingredient and both succeed. Assert combined deduction equals the sum of both orders’ usage.
    - T7.3 – Failure due to prior consumption: Test where Order 1 succeeds, Order 2 fails because remaining stock is insufficient. Assert: first fulfilled, second not, status + restock reflect this.
    - T7.4 – Final inventory verification: Test that after several orders, final  inventory_data  matches expected quantities (no reset between orders).

**Task 8 – Restock & Expiry Rules**
- Implement `calculate_restock_needs(inventory, reference_date)`:
  - Handles low stock, out-of-stock, expiring soon, multiple reasons.
- Tests for each rule and combination.
- Concrete tasks for AI:
    - T8.1 – Clarify restock rules + shape: Confirm thresholds (≤1000g, par 10,000g, expiring within 5 days). Decide exact output fields (item, current qty, qty_needed_grams, reason(s)).
    - T8.2 – Implement basic stock rules:  In  calculate_restock_needs : handle out-of-stock and low-stock (no expiry yet).
    - T8.3 – Add expiry rules + multiple reasons:  Integrate  reference_date , mark “Expiring soon”, and allow multiple reasons per ingredient.
    - T8.4 – Unit tests:  Tests for: zero stock, low stock, above threshold, expiring soon, and multiple-reason cases.

**Task 9 – Final Business Summary**
- Implement `generate_summary(...)` or printing function:
  - Delivered vs. not delivered counts.
  - Reasons for non-delivery.
  - Final inventory snapshot.
  - Restock recommendations and expiry issues.
- Ensure summary is understandable to non-technical users.
- Concrete tasks for AI:
    - T9.1 – Define summary structure: Specify what the manager-facing summary should include (counts, totals, key reasons, restock snapshot) and document it in a docstring.
    - T9.2 – Implement summary computation: Add a pure function that consumes orders, status, inventory, restock and returns a structured summary dict.
    - T9.3 – Implement summary formatting/printing: Add a function to pretty-print the summary for humans (clear sections, simple text).
    - T9.4 – Wire summary into  main(): Call summary computation and printer at the end of the simulation.
    - T9.5 – Add tests for summary: Create focused unit tests asserting structure and key fields (e.g., delivered counts, restock items).

**Task 10 – Refactor & Review**
- Identify duplicate logic, poor names, magic numbers, etc.
- Introduce constants for thresholds (par level, low-stock threshold, expiry window).
- Document at least two refactors in `PROJECT_SPEC.md`.
- Concrete tasks for AI:
    - T10.1 – Identify improvement candidates: Skim  main.py  and  test_main.py , list 3–5 specific refactor targets (duplication, long functions, magic values).
    - T10.2 – Extract shared constants & helpers: Centralize any remaining magic numbers/strings and tiny repeated snippets into simple helpers/constants.
    - T10.3 – Refactor  main.py  hot spots: Apply small, behavior‑preserving refactors to 1–2 functions (e.g., split complex logic, clarify names).
    - T10.4 – Refactor  test_main.py  for clarity: Deduplicate setup data and improve test naming/grouping without changing coverage.
    - T10.5 – Document refactor in PROJECT_SPEC.md: Add a short “Refactoring & Rationale” section describing at least two improvements.

### Refactoring & Rationale
- Introduced status and restock reason constants in `main.py` (e.g., `STATUS_REMARK_DELIVERED`, `RESTOCK_REASON_OUT_OF_STOCK`). This removes scattered string literals and makes it easier to keep user-facing messages consistent.
- Extracted brand/reason grouping helpers in `build_business_summary` (`_group_orders_by_reason`, `_summarize_brands`). This shortens the main summary function and makes the grouping logic easier to test in isolation.
- Added `make_inventory_item` and `make_order` helpers in `test_main.py` to centralize test data construction. This reduced duplication and made individual tests more readable.
 
**Task 11 – Reflection on AI-Assisted Coding**
- Write 400–600 word reflection (separate write-up, referenced here).

**Option D**
- Generate a polished business report in Markdown, CSV, or HTML format.

## 7. Testing Strategy

- Use `pytest` (or `unittest`) via `test_main.py`.
- For each major function:
  - Normal case.
  - Edge case.
  - Failure case.
- Maintain tests aligned with Tasks 3–9:
  - Data loading and schemas.
  - Recipe lookup behavior.
  - Inventory availability logic.
  - Fulfillment and cumulative processing.
  - Restock/expiry rules.
  - Final summary (e.g., correct counts).

## 8. Constraints & Assumptions

- Single-process, in-memory simulation (no database or external IO).
- Seed data is trusted source of truth; not modified on disk.
- Simulation date:
  - Default: `date.today()` unless specified as a parameter.
- All quantities measured in grams.
- Fulfillment baseline: all-or-nothing (no partial deliveries).

## 9. Known Issues / Open Questions

- Clarify whether simulation date should always be `today` or configurable.
- Consider performance only after correctness (dataset expected to be small).
- Should we accomodate for different quantity units instead of grams (e.g., oz, counts, gallons)?
- To what extent should approximate text matching be implemented for ingredient searches? This isn't a big problem now but will be when the ingredient list gets larger and more complex.