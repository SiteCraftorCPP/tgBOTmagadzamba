import asyncio
from html import escape
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from config import Config, load_config
from keyboards import admin_categories_keyboard, admin_category_menu, admin_menu, cancel_keyboard, categories_keyboard, main_menu, payment_stub, product_card, product_pagination
from storage import add_category, add_product, ensure_storage, get_category, get_product, list_categories, list_products, save_order


router = Router()
config: Config

_TELEGRAM_TEXT_SOFT_LIMIT = 3800


class AddCategory(StatesGroup):
    name = State()


class AddProduct(StatesGroup):
    category_id = State()
    photo = State()
    name = State()
    price = State()
    description = State()


class OrderProduct(StatesGroup):
    name = State()
    phone = State()
    address = State()


def is_admin(user_id: int | None) -> bool:
    return user_id in config.admin_ids


def product_link(product_id: str) -> str:
    return f"https://t.me/{config.bot_username}?start={product_id}"


def product_caption(product: dict[str, Any], include_link: bool = False) -> str:
    name = str(product["name"])
    raw_desc = str(product["description"])
    max_desc = 520 if include_link else 900
    if len(raw_desc) > max_desc:
        desc = raw_desc[: max_desc - 1] + "…"
    else:
        desc = raw_desc
    text = (
        f"💄 <b>{escape(name)}</b>\n\n"
        f"{escape(desc)}\n\n"
        f"💰 Цена: <b>{escape(str(product['price']))}</b>"
    )
    if include_link:
        text += f"\n\n🔗 Ссылка: {product_link(product['id'])}"
    return text


def admin_list_chunks(products: list[dict[str, Any]]) -> list[str]:
    cats = {c["id"]: c["name"] for c in list_categories()}
    header = "📋 <b>Товары</b>\n\n"
    chunks: list[str] = []
    current = header
    for product in products:
        raw_name = str(product["name"]).strip()
        if len(raw_name) > 160:
            raw_name = raw_name[:159] + "…"
        raw_price = str(product["price"]).strip()
        pid = str(product["id"]).strip()
        cat_name = cats.get(product.get("category_id"), "Без раздела")
        block = (
            f"📁 <b>{escape(cat_name)}</b>\n"
            f"💄 <b>{escape(raw_name)}</b> - {escape(raw_price)}\n"
            f"ID: <code>{escape(pid)}</code>\n"
            f"🔗 {product_link(pid)}\n\n"
        )
        if len(block) > _TELEGRAM_TEXT_SOFT_LIMIT:
            if len(current) > len(header):
                chunks.append(current.rstrip())
                current = header
            chunks.append(block[: _TELEGRAM_TEXT_SOFT_LIMIT - 10] + "…\n")
            continue
        if len(current) + len(block) > _TELEGRAM_TEXT_SOFT_LIMIT:
            chunks.append(current.rstrip())
            current = block
        else:
            current += block
    if current.strip() and current != header:
        chunks.append(current.rstrip())
    return chunks if chunks else [header + "— пусто —"]


async def show_product(message: Message, product: dict[str, Any]) -> None:
    try:
        await message.answer_photo(
            photo=product["photo"],
            caption=product_caption(product),
            reply_markup=product_card(product["id"]),
        )
    except TelegramBadRequest:
        await message.answer(
            product_caption(product),
            reply_markup=product_card(product["id"]),
        )


async def show_main_menu(message: Message, user_id: int | None) -> None:
    await message.answer(
        "🌸 Добро пожаловать в магазин косметики!\n"
        "Выберите действие через кнопки ниже.",
        reply_markup=main_menu(is_admin(user_id)),
    )


async def show_admin_menu(message: Message) -> None:
    await message.answer(
        "👑 <b>Админка</b>\nВыберите действие:",
        reply_markup=admin_menu(),
    )


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    product_id_raw = command.args
    product_id = product_id_raw.strip() if product_id_raw else None

    if product_id:
        product = get_product(product_id)
        if not product:
            await message.answer(
                "😔 Товар не найден. Проверьте ссылку или откройте каталог.",
                reply_markup=main_menu(is_admin(message.from_user.id if message.from_user else None)),
            )
            return
        await show_product(message, product)
        return

    await show_main_menu(message, message.from_user.id if message.from_user else None)


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ У вас нет доступа к админке.")
        return
    await show_admin_menu(message)


@router.message(Command("addproduct"))
async def add_product_command(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ Команда доступна только администратору.")
        return
    cats = list_categories()
    if not cats:
        await message.answer("Сначала создайте хотя бы один раздел через админку (/admin).")
        return
    await state.clear()
    await message.answer("🗂 Выберите раздел для добавления товара:", reply_markup=categories_keyboard(cats, "admin:add_prod:cat:", "admin:menu"))


@router.callback_query(F.data == "menu:main")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await show_main_menu(callback.message, callback.from_user.id)


@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await show_admin_menu(callback.message)


@router.callback_query(F.data == "admin:add_cat")
async def admin_add_cat(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(AddCategory.name)
    await callback.message.answer("📁 Введите название нового раздела:", reply_markup=cancel_keyboard("admin:cats:0"))
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.message(AddCategory.name, F.text)
async def add_cat_name(message: Message, state: FSMContext) -> None:
    add_category(message.text.strip())
    await state.clear()
    cats = list_categories()
    await message.answer("✅ Раздел добавлен!\n\n🗂 <b>Управление разделами</b>\nВыберите раздел или добавьте новый:", reply_markup=admin_categories_keyboard(cats, 0))


@router.message(AddCategory.name, ~F.text)
async def add_cat_name_invalid(message: Message) -> None:
    await message.answer("📁 Отправьте название раздела текстом.", reply_markup=cancel_keyboard("admin:cats:0"))


@router.callback_query(F.data.startswith("admin:cats"))
async def admin_cats_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    cats = list_categories()
    await state.clear()
    
    parts = callback.data.split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    
    text = "🗂 <b>Управление разделами</b>\nВыберите раздел или добавьте новый:"
    markup = admin_categories_keyboard(cats, page)
    
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=markup)
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("admin:cat:"))
async def admin_cat_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    cat_id = callback.data.split(":")[-1]
    cat = get_category(cat_id)
    if not cat:
        await callback.answer("Раздел не найден", show_alert=True)
        return
    await state.clear()
    text = f"📁 Раздел: <b>{escape(cat['name'])}</b>\nВыберите действие:"
    markup = admin_category_menu(cat_id)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=markup)
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("admin:add_prod:cat:"))
async def admin_add_prod_cat(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    cat_id = callback.data.split(":")[-1]
    await state.update_data(category_id=cat_id)
    await state.set_state(AddProduct.photo)
    await callback.message.answer("📸 Отправьте фото товара.", reply_markup=cancel_keyboard(f"admin:cat:{cat_id}"))
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("admin:list_cat:"))
async def admin_list_cat_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    cat_id = callback.data.split(":")[-1]
    products = [p for p in list_products() if p.get("category_id") == cat_id]
    if not products:
        await callback.answer("В этом разделе пока нет товаров.", show_alert=True)
        return

    await callback.answer()
    chunks = admin_list_chunks(products)
    for i, chunk in enumerate(chunks):
        markup = admin_category_menu(cat_id) if i == len(chunks) - 1 else None
        await callback.message.answer(chunk, reply_markup=markup)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass




@router.message(AddProduct.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await state.clear()
        return

    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(AddProduct.name)
    await message.answer(
        "💄 Введите название товара.",
        reply_markup=cancel_keyboard("add:back:photo"),
    )


@router.message(AddProduct.photo)
async def add_product_photo_invalid(message: Message) -> None:
    await message.answer(
        "📸 Нужно отправить именно фото товара.",
        reply_markup=cancel_keyboard("admin:menu"),
    )


@router.message(AddProduct.name, ~F.text)
async def add_product_name_need_text(message: Message) -> None:
    await message.answer("💄 Отправьте название текстом.", reply_markup=cancel_keyboard("add:back:photo"))


@router.message(AddProduct.price, ~F.text)
async def add_product_price_need_text(message: Message) -> None:
    await message.answer("💰 Отправьте цену текстом.", reply_markup=cancel_keyboard("add:back:name"))


@router.message(AddProduct.description, ~F.text)
async def add_product_description_need_text(message: Message) -> None:
    await message.answer(
        "📝 Отправьте описание текстом.", reply_markup=cancel_keyboard("add:back:price")
    )


@router.message(AddProduct.name, F.text)
async def add_product_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProduct.price)
    await message.answer(
        "💰 Введите цену товара.",
        reply_markup=cancel_keyboard("add:back:name"),
    )


@router.message(AddProduct.price, F.text)
async def add_product_price(message: Message, state: FSMContext) -> None:
    await state.update_data(price=message.text.strip())
    await state.set_state(AddProduct.description)
    await message.answer(
        "📝 Введите описание товара.",
        reply_markup=cancel_keyboard("add:back:price"),
    )


@router.message(AddProduct.description, F.text)
async def add_product_description(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if not {"category_id", "name", "price", "photo"}.issubset(data.keys()):
        await state.clear()
        await message.answer("⚠️ Сессия сбросилась. Начните снова с /addproduct.")
        return
    cat_id = data["category_id"]
    product = add_product(
        category_id=cat_id,
        name=data["name"],
        price=data["price"],
        description=message.text.strip(),
        photo=data["photo"],
    )
    await state.clear()
    await message.answer("✅ Товар сохранен!")
    try:
        await message.answer_photo(
            photo=product["photo"],
            caption=product_caption(product, include_link=False),
            reply_markup=admin_category_menu(cat_id),
        )
    except TelegramBadRequest:
        await message.answer(
            product_caption(product, include_link=False),
            reply_markup=admin_category_menu(cat_id),
        )


@router.callback_query(F.data.startswith("add:back:"))
async def add_product_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    step = callback.data.rsplit(":", 1)[-1] if callback.data else ""
    await callback.answer()
    if not callback.message:
        return

    if step == "photo":
        await state.set_state(AddProduct.photo)
        await callback.message.answer(
            "📸 Отправьте фото товара заново.",
            reply_markup=cancel_keyboard(f"admin:cat:{data.get('category_id', '')}"),
        )
    elif step == "name":
        await state.set_state(AddProduct.name)
        await callback.message.answer(
            "💄 Введите название товара заново.",
            reply_markup=cancel_keyboard("add:back:photo"),
        )
    elif step == "price":
        await state.set_state(AddProduct.price)
        await callback.message.answer(
            "💰 Введите цену товара заново.",
            reply_markup=cancel_keyboard("add:back:name"),
        )


@router.callback_query(F.data == "catalog")
async def catalog_callback(callback: CallbackQuery) -> None:
    cats = list_categories()
    await callback.answer()
    if not callback.message:
        return

    if not cats:
        await callback.message.answer(
            "🌷 Каталог пока пуст. Загляните позже!",
            reply_markup=main_menu(is_admin(callback.from_user.id)),
        )
        return

    await callback.message.answer("🛍 <b>Каталог</b>\nВыберите раздел:", reply_markup=categories_keyboard(cats, "catalog:cat:", "menu:main"))
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("catalog:cat:"))
async def catalog_cat_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    cat_id = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0
    
    products = [p for p in list_products() if p.get("category_id") == cat_id]
    if not products:
        await callback.answer("В этом разделе пока нет товаров.", show_alert=True)
        return
        
    page = page % len(products)
    product = products[page]
    markup = product_pagination(cat_id, page, len(products), product["id"])
    
    try:
        if callback.message and callback.message.photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=product["photo"], caption=product_caption(product)),
                reply_markup=markup
            )
        elif callback.message:
            await callback.message.answer_photo(
                photo=product["photo"],
                caption=product_caption(product),
                reply_markup=markup
            )
            await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("product:show:"))
async def product_show_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    product_id = callback.data.rsplit(":", 1)[-1] if callback.data else ""
    product = get_product(product_id)
    await callback.answer()
    if not callback.message:
        return

    if not product:
        await callback.message.answer("😔 Товар не найден.", reply_markup=main_menu(is_admin(callback.from_user.id)))
        return

    await show_product(callback.message, product)


@router.callback_query(F.data.startswith("order:start:"))
async def order_start_callback(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = callback.data.rsplit(":", 1)[-1] if callback.data else ""
    product = get_product(product_id)
    await callback.answer()
    if not callback.message:
        return

    if not product:
        await callback.message.answer("😔 Товар не найден.")
        return

    await state.clear()
    await state.update_data(product_id=product_id)
    await state.set_state(OrderProduct.name)
    await callback.message.answer(
        f"🛒 Оформляем заказ на <b>{escape(product['name'])}</b>.\n\n"
        "👤 Введите ваше имя.",
        reply_markup=cancel_keyboard(f"product:show:{product_id}"),
    )


@router.message(OrderProduct.name, ~F.text)
async def order_need_name_text(message: Message, state: FSMContext) -> None:
    d = await state.get_data()
    pid = d.get("product_id") or ""
    back = f"product:show:{pid}" if pid else "menu:main"
    await message.answer(
        "👤 Введите имя обычным текстом.", reply_markup=cancel_keyboard(back)
    )


@router.message(OrderProduct.name, F.text)
async def order_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(OrderProduct.phone)
    await message.answer(
        "📱 Введите номер телефона.",
        reply_markup=cancel_keyboard("order:back:name"),
    )


@router.message(OrderProduct.phone, ~F.text)
async def order_need_phone_text(message: Message) -> None:
    await message.answer(
        "📱 Введите телефон текстом.", reply_markup=cancel_keyboard("order:back:name")
    )


@router.message(OrderProduct.phone, F.text)
async def order_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.text.strip())
    await state.set_state(OrderProduct.address)
    await message.answer(
        "🚚 Введите адрес доставки.",
        reply_markup=cancel_keyboard("order:back:phone"),
    )


@router.message(OrderProduct.address, ~F.text)
async def order_need_address_text(message: Message) -> None:
    await message.answer(
        "🚚 Введите адрес текстом.", reply_markup=cancel_keyboard("order:back:phone")
    )


@router.message(OrderProduct.address, F.text)
async def order_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    data = await state.get_data()
    pid = data.get("product_id")
    if not pid:
        await state.clear()
        await message.answer(
            "😔 Контекст заказа утерян. Откройте товар заново.",
            reply_markup=main_menu(is_admin(message.from_user.id if message.from_user else None)),
        )
        return
    product = get_product(str(pid))

    if not product:
        await state.clear()
        await message.answer("😔 Товар не найден. Оформление остановлено.")
        return

    order = save_order(
        {
            "status": "payment_stub",
            "product_id": product["id"],
            "product_name": product["name"],
            "price": product["price"],
            "name": data["name"],
            "phone": data["phone"],
            "address": data["address"],
            "telegram_id": message.from_user.id if message.from_user else None,
            "telegram_username": message.from_user.username if message.from_user else None,
        }
    )

    # Отправка уведомления в канал
    username_text = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    order_text = (
        "🚨 <b>НОВЫЙ ЗАКАЗ</b>\n\n"
        f"🛍 <b>Товар:</b> {escape(product['name'])}\n"
        f"💰 <b>Цена:</b> {escape(str(product['price']))}\n\n"
        f"👤 <b>Покупатель:</b> {escape(data['name'])}\n"
        f"📱 <b>Телефон:</b> {escape(data['phone'])}\n"
        f"🚚 <b>Адрес:</b> {escape(data['address'])}\n"
        f"💬 <b>Telegram:</b> {username_text}"
    )
    try:
        await message.bot.send_message(chat_id=config.channel_id, text=order_text)
    except Exception as e:
        print(f"Не удалось отправить заказ в канал: {e}")

    await state.update_data(order_id=order["id"])
    await message.answer(
        "💳 <b>Оплата</b>\n\n"
        f"💄 Товар: <b>{escape(product['name'])}</b>\n"
        f"💰 Цена: <b>{escape(str(product['price']))}</b>",
        reply_markup=payment_stub(product["id"]),
    )


@router.callback_query(F.data.startswith("order:back:"))
async def order_back_callback(callback: CallbackQuery, state: FSMContext) -> None:
    step = callback.data.rsplit(":", 1)[-1] if callback.data else ""
    data = await state.get_data()
    product_id = data.get("product_id")
    await callback.answer()
    if not callback.message:
        return

    if step == "name":
        await state.set_state(OrderProduct.name)
        await callback.message.answer(
            "👤 Введите имя заново.",
            reply_markup=cancel_keyboard(f"product:show:{product_id}" if product_id else "menu:main"),
        )
    elif step == "phone":
        await state.set_state(OrderProduct.phone)
        await callback.message.answer(
            "📱 Введите телефон заново.",
            reply_markup=cancel_keyboard("order:back:name"),
        )
    elif step == "address":
        await state.set_state(OrderProduct.address)
        await callback.message.answer(
            "🚚 Введите адрес доставки заново.",
            reply_markup=cancel_keyboard("order:back:phone"),
        )


@router.callback_query(F.data == "payment:stub")
async def payment_stub_callback(callback: CallbackQuery) -> None:
    await callback.answer(
        "💳 Сервис оплаты временно недоступен. Заказ уже передан менеджеру!",
        show_alert=True,
    )


@router.callback_query(F.data == "flow:cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "❌ Действие отменено.",
            reply_markup=main_menu(is_admin(callback.from_user.id)),
        )


@router.message()
async def fallback(message: Message, _state: FSMContext) -> None:
    await message.answer(
        "🌸 Используйте кнопки ниже или откройте товар по ссылке из канала.",
        reply_markup=main_menu(is_admin(message.from_user.id if message.from_user else None)),
    )


async def main() -> None:
    global config
    config = load_config()
    ensure_storage()

    kwargs: dict[str, Any] = {
        "token": config.bot_token,
        "default": DefaultBotProperties(parse_mode=ParseMode.HTML),
    }
    if config.proxy_url:
        kwargs["session"] = AiohttpSession(proxy=config.proxy_url)
        print("Proxy enabled")
    else:
        print("Direct connection")

    bot = Bot(**kwargs)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        me = await bot.get_me()
    except Exception as exc:
        print(f"Connection failed: {exc}")
        await bot.session.close()
        raise SystemExit(1) from exc

    print(f"Bot started: @{me.username}")

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
