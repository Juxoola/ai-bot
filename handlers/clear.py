from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import Form, dp, DEFAULT_SYSTEM_PROMPTS
from database import load_context, save_context, is_allowed, def_gen_model, def_rec_model, def_aspect, def_enhance, def_voice
from handlers.check import check_in_progress, set_in_progress, clear_in_progress
from handlers.rate_limit import check_rate_limit

otvet = "У вас нет доступа к этому боту.\nВам [сюда](https://nahnah.ru/)"

@dp.message(F.text == "🗑️ Очистить")
@dp.message(F.text == "Очистить")
@dp.message(F.text == "/clear")
async def cmd_clear_context(message: types.Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.reply(otvet, parse_mode=ParseMode.MARKDOWN)
        return

    if not await check_rate_limit(message, "clear"):
        return
        
    can_proceed = await check_in_progress(message, state)
    if not can_proceed:
        return

    try:
        await set_in_progress(state)
        
        user_id = message.from_user.id
        user_context = await load_context(user_id)
        api_type = user_context["api_type"]
        
        system_role = user_context.get("system_role", "default")
        system_prompt = DEFAULT_SYSTEM_PROMPTS.get(system_role, DEFAULT_SYSTEM_PROMPTS["default"])
        
        new_context = {
            "model": user_context["model"],
            "api_type": api_type,
            "g4f_image": None,
            "g4f_image_base64": None,
            "long_message": "",
            "image_generation_model": user_context.get("image_generation_model", await def_gen_model()),
            "image_recognition_model": user_context.get("image_recognition_model", await def_rec_model()),
            "aspect_ratio": user_context.get("aspect_ratio", await def_aspect()),
            "enhance": user_context.get("enhance", await def_enhance()),
            "show_processing_time": user_context.get("show_processing_time", True),
            "voice": user_context.get("voice", await def_voice()),
            "system_role": system_role,
            "messages": []
        }
        
        if api_type == "gemini":
            new_context["messages"] = [{"role": "system", "parts": [{"text": system_prompt}]}]
        else:
            new_context["messages"] = [{"role": "system", "content": system_prompt}]

        await save_context(user_id, new_context)
        await message.reply("✅ Контекст очищен.")
        
        await clear_in_progress(state)
    except Exception as e:
        await clear_in_progress(state)
        await message.reply(f"🔔 Произошла ошибка при очистке контекста: {e}")