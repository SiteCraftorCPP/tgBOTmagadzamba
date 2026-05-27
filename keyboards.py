from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👑 Админка", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗂 Управление разделами", callback_data="admin:cats:0")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def admin_category_menu(cat_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"admin:add_prod:cat:{cat_id}")],
            [InlineKeyboardButton(text="📋 Товары раздела", callback_data=f"admin:list_cat:{cat_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:cats:0")],
        ]
    )


def admin_categories_keyboard(categories: list[dict], page: int, per_page: int = 5) -> InlineKeyboardMarkup:
    buttons = []
    total = len(categories)
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    for c in categories[start_idx:end_idx]:
        buttons.append([InlineKeyboardButton(text=f"📁 {c['name']}", callback_data=f"admin:cat:{c['id']}")])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:cats:{page - 1}"))
    if total > per_page:
        nav_row.append(InlineKeyboardButton(text=f"{page + 1} / {((total - 1) // per_page) + 1}", callback_data="noop"))
    if end_idx < total:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:cats:{page + 1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    buttons.append([InlineKeyboardButton(text="➕ Добавить раздел", callback_data="admin:add_cat")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def categories_keyboard(categories: list[dict], prefix: str, back_data: str = "menu:main") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"📁 {c['name']}", callback_data=f"{prefix}{c['id']}")]
        for c in categories
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_data)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_pagination(category_id: str, current_idx: int, total: int, product_id: str) -> InlineKeyboardMarkup:
    nav_row = []
    if total > 1:
        prev_idx = (current_idx - 1) % total
        next_idx = (current_idx + 1) % total
        nav_row = [
            InlineKeyboardButton(text="⬅️", callback_data=f"catalog:cat:{category_id}:{prev_idx}"),
            InlineKeyboardButton(text=f"{current_idx + 1} / {total}", callback_data="noop"),
            InlineKeyboardButton(text="➡️", callback_data=f"catalog:cat:{category_id}:{next_idx}"),
        ]
    
    buttons = []
    if nav_row:
        buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="🛒 Оформить заказ", callback_data=f"order:start:{product_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 К разделам", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard(back_callback: str | None = None) -> InlineKeyboardMarkup:
    buttons = []
    if back_callback:
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="flow:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_card(product_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data=f"order:start:{product_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )




def _catalog_title(name: str, max_chars: int = 52) -> str:
    n = name.strip() or "—"
    if len(n) <= max_chars:
        return n
    return n[: max_chars - 1] + "…"


def payment_stub(product_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить заказ", callback_data="payment:stub")],
            [InlineKeyboardButton(text="⬅️ Назад к адресу", callback_data="order:back:address")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="flow:cancel")],
            [InlineKeyboardButton(text="💄 К товару", callback_data=f"product:show:{product_id}")],
        ]
    )
