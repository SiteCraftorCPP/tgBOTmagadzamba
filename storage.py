import json
import secrets
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CATEGORIES_FILE = DATA_DIR / "categories.json"
PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"

_CATEGORY_KEYS_STRICT = frozenset({"id", "name"})
_PRODUCT_KEYS_STRICT = frozenset({"id", "category_id", "name", "price", "description", "photo"})


def _sanitize_category(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, dict) or not _CATEGORY_KEYS_STRICT.issubset(record.keys()):
        return None
    return {"id": str(record["id"]).strip(), "name": str(record["name"]).strip()}


def list_categories() -> list[dict[str, Any]]:
    rows = _read_json_list(CATEGORIES_FILE)
    return [x for row in rows if (x := _sanitize_category(row)) is not None]


def add_category(name: str) -> dict[str, Any]:
    cats = list_categories()
    cat_id = secrets.token_urlsafe(4).replace("-", "").replace("_", "")[:6]
    cat = {"id": cat_id, "name": name}
    cats.append(cat)
    _write_json(CATEGORIES_FILE, cats)
    return cat


def get_category(cat_id: str) -> dict[str, Any] | None:
    for c in list_categories():
        if c["id"] == cat_id:
            return c
    return None


def _sanitize_product(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    if not _PRODUCT_KEYS_STRICT.issubset(record.keys()):
        return None
    pid = str(record.get("id", "")).strip()
    photo = str(record.get("photo", "")).strip()
    if not pid or not photo:
        return None
    return {
        "id": pid,
        "category_id": str(record.get("category_id", "")).strip(),
        "name": record["name"],
        "price": record["price"],
        "description": record["description"],
        "photo": photo,
    }


def ensure_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for path in (CATEGORIES_FILE, PRODUCTS_FILE, ORDERS_FILE):
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def _read_json_list(path: Path) -> list[Any]:
    ensure_storage()
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []
    return data


def _write_json(path: Path, data: list[dict[str, Any]]) -> None:
    ensure_storage()
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def list_products() -> list[dict[str, Any]]:
    rows = _read_json_list(PRODUCTS_FILE)
    return [x for row in rows if (x := _sanitize_product(row)) is not None]


def get_product(product_id: str) -> dict[str, Any] | None:
    for product in list_products():
        if product.get("id") == product_id:
            return product
    return None


def add_product(category_id: str, name: str, price: str, description: str, photo: str) -> dict[str, Any]:
    products = list_products()
    product_id = _generate_product_id(products)
    product = {
        "id": product_id,
        "category_id": category_id,
        "name": name,
        "price": price,
        "description": description,
        "photo": photo,
    }
    products.append(product)
    _write_json(PRODUCTS_FILE, products)
    return product


def save_order(order: dict[str, Any]) -> dict[str, Any]:
    raw = _read_json_list(ORDERS_FILE)
    orders = [row for row in raw if isinstance(row, dict)]
    order = {"id": _generate_order_id(orders), **order}
    orders.append(order)
    _write_json(ORDERS_FILE, orders)
    return order


def _generate_product_id(products: list[dict[str, Any]]) -> str:
    existing_ids = {str(product.get("id")) for product in products}
    while True:
        product_id = secrets.token_urlsafe(5).replace("-", "").replace("_", "")[:8]
        if product_id and product_id not in existing_ids:
            return product_id


def _generate_order_id(orders: list[dict[str, Any]]) -> str:
    existing_ids = {str(order.get("id")) for order in orders}
    while True:
        order_id = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10]
        if order_id and order_id not in existing_ids:
            return order_id
