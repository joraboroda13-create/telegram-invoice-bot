from aiogram import Bot, Dispatcher, executor, types
import aiohttp
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = "8281321191:AAER63wKekcIJtMbPLgMBTgLlo3br6f1cFw"
GOOGLE_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwrc5XIW3TslJJcXlFhsOIrmZDyn3veEdf8U7vJzHpR0_c39PQG6u2-egO1f864wLckyg/exec"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_data = {}


# --- Кнопки ---
def yes_no_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Да"), types.KeyboardButton("Нет"))
    return kb


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_data[message.from_user.id] = {
        "items": [],
        "state": "itemName"
    }
    await message.answer("Название товара:")


@dp.message_handler(lambda msg: True)
async def handle(message: types.Message):
    uid = message.from_user.id
    data = user_data.setdefault(uid, {"items": [], "state": "itemName"})
    state = data["state"]

    # 1. Название товара
    if state == "itemName":
        data["current_item"] = {"itemName": message.text}
        data["state"] = "qty"
        return await message.answer("Кол-во:")

    # 2. Количество
    if state == "qty":
        data["current_item"]["qty"] = message.text
        data["state"] = "price"
        return await message.answer("Цена за ед.:")

    # 3. Цена
    if state == "price":
        data["current_item"]["price"] = message.text
        data["current_item"]["comment"] = "-"  # авто

        # сохраняем товар
        data["items"].append(data["current_item"].copy())
        data["current_item"] = {}

        data["state"] = "addMore"
        return await message.answer(
            "Добавить ещё товар?",
            reply_markup=yes_no_keyboard()
        )

    # 4. Добавить ещё? (кнопки)
    if state == "addMore":
        txt = message.text.lower().strip()

        if txt == "да":
            data["state"] = "itemName"
            return await message.answer("Название товара:", reply_markup=types.ReplyKeyboardRemove())

        if txt == "нет":
            data["seller"] = message.from_user.full_name
            await message.answer("Отправляем данные...", reply_markup=types.ReplyKeyboardRemove())

            logging.info("Отправляем данные в Google: %s", data)

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        GOOGLE_WEBHOOK_URL,
                        json=data,
                        headers={"Content-Type": "application/json"}
                    ) as resp:
                        text = await resp.text()
                        logging.info("STATUS: %s", resp.status)
                        logging.info("TEXT: %s", text)
                except Exception as e:
                    logging.error("Ошибка при отправке: %s", e)

            await message.answer("Готово! Данные отправлены.")
            user_data.pop(uid, None)
            return

        # Если нажал что-то другое
        return await message.answer("Пожалуйста, нажмите кнопку: Да или Нет.")


if __name__ == "__main__":
    executor.start_polling(dp)

