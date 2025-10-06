from config import bot,Form, openai_clients
from aiogram.fsm.context import FSMContext
from database import load_context,save_context
from aiogram import types
import asyncio
import logging
import aiofiles.tempfile
import aiofiles.os
import os


async def handle_files_or_urls(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        if message.document:
            processing_msg = await message.reply("🔔 Начинается обработка файла...")

            file_id = message.document.file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path
            file_data = await bot.download_file(file_path)

            async with aiofiles.tempfile.NamedTemporaryFile(
                "wb", delete=False, suffix=f"_{message.document.file_name}"
            ) as tmp_file:
                await tmp_file.write(file_data.read())
                temp_file_path = tmp_file.name

            file_content = await process_local_file(temp_file_path)

            if file_content == "Unsupported file type":
                await processing_msg.edit_text(
                    "🚨 Неподдерживаемый тип файла. Поддерживаемые форматы:\n"
                    "- Документы: PDF, DOCX, DOC, XLSX, XLS\n"
                    "- Текстовые файлы: TXT, CSV, MD\n"
                    "- Код: PY, JS, PHP, HTML, XML, JSON, YAML, SQL и другие"
                )
                return
            elif file_content == "Error processing file":
                await processing_msg.edit_text(
                    "🚨 Произошла ошибка при обработке файла. Пожалуйста, попробуйте еще раз."
                )
                return

            user_context = await load_context(user_id)
            model_key = user_context["model"]  
            model_id, api_type = model_key.split('_')
            allowed_apis = list(openai_clients.keys()) + ["g4f"]

            if api_type == "gemini":
                last_message = user_context["messages"][-1] if user_context["messages"] else None
                if last_message and last_message["role"] == "user" and any("data" in part for part in last_message["parts"]):
                    user_context["messages"][-1]["parts"].append({"text": file_content})
                else:
                    user_context["messages"].append({"role": "user", "parts": [{"text": file_content}]})
            elif api_type in  allowed_apis:
                user_context["messages"].append({"role": "user", "content": file_content})

            await save_context(user_id, user_context)

            await processing_msg.edit_text("🔔 Файл успешно обработан и добавлен в контекст.")
            await state.set_state(Form.waiting_for_message)

    except Exception as e:
        logging.error(f"Ошибка при обработке файла: {e}")
        if 'processing_msg' in locals():
            await processing_msg.edit_text(f"🚨 Произошла ошибка при обработке файла: {e}")
        else:
            await message.reply(f"🚨 Произошла ошибка при обработке файла: {e}")
        await state.set_state(Form.waiting_for_message)
    finally:
        if "temp_file_path" in locals() and os.path.exists(temp_file_path):
            await aiofiles.os.remove(temp_file_path)

async def process_local_file(file_path):
    import fitz 
    import os
    import logging
    
    file_content = ""
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # PDF файлы
        if file_ext == ".pdf":
            doc = await asyncio.to_thread(fitz.open, file_path)
            for page in doc:
                file_content += await asyncio.to_thread(page.get_text)
            doc.close()
        
        # Microsoft Word (.docx) документы
        elif file_ext == ".docx":
            from docx import Document
            doc = await asyncio.to_thread(Document, file_path)
            for para in doc.paragraphs:
                file_content += para.text + "\n"
            # Также получаем текст из таблиц
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        row_text.append(cell.text)
                    file_content += " | ".join(row_text) + "\n"
        
        # Старые Microsoft Word (.doc) документы
        elif file_ext == ".doc":
            try:
                # Используем antiword как основной способ
                import subprocess
                result = await asyncio.to_thread(subprocess.run, ['antiword', file_path], capture_output=True, text=True)
                if result.returncode == 0:
                    file_content = result.stdout
                else:
                    raise Exception(f"antiword завершился с ошибкой: {result.stderr}")
            except Exception as e2:
                logging.warning(f"Не удалось обработать .doc с помощью antiword: {e2}")
                try:
                    # Пробуем через libreoffice как запасной вариант
                    import os
                    tmp_txt = f"{file_path}.txt"
                    result = await asyncio.to_thread(subprocess.run, ['libreoffice', '--headless', '--convert-to', 'txt', file_path,
                                             '--outdir', os.path.dirname(file_path)],
                                            capture_output=True, text=True)
                    
                    # Определяем имя выходного файла
                    base_name = os.path.basename(file_path)
                    file_name_without_ext = os.path.splitext(base_name)[0]
                    converted_txt = os.path.join(os.path.dirname(file_path), f"{file_name_without_ext}.txt")
                    
                    if await aiofiles.os.path.exists(converted_txt):
                        async with aiofiles.open(converted_txt, 'r', encoding='utf-8', errors='ignore') as f:
                            file_content = await f.read()
                        await aiofiles.os.remove(converted_txt)
                    else:
                        raise Exception("Конвертация не удалась")
                except Exception as e3:
                    logging.error(f"Все методы обработки .doc не удались: {e3}")
                    return "Error processing .doc file: All methods failed"
        
        # Microsoft Excel (.xlsx) таблицы
        elif file_ext == ".xlsx":
            import openpyxl
            wb = await asyncio.to_thread(openpyxl.load_workbook, file_path, data_only=True)
            for sheet in wb.worksheets:
                file_content += f"Лист: {sheet.title}\n"
                for row in sheet.iter_rows(values_only=True):
                    file_content += " | ".join([str(cell) if cell is not None else "" for cell in row]) + "\n"
                file_content += "\n"
        
        # Старые Microsoft Excel (.xls) таблицы
        elif file_ext == ".xls":
            try:
                import xlrd
                wb = await asyncio.to_thread(xlrd.open_workbook, file_path)
                for sheet_index in range(wb.nsheets):
                    sheet = wb.sheet_by_index(sheet_index)
                    file_content += f"Лист: {sheet.name}\n"
                    for row_index in range(sheet.nrows):
                        row_values = sheet.row_values(row_index)
                        file_content += " | ".join([str(cell) if cell else "" for cell in row_values]) + "\n"
                    file_content += "\n"
            except Exception as e:
                logging.error(f"Ошибка при обработке .xls файла: {e}")
                try:
                    # Резервный метод через libreoffice
                    tmp_csv = f"{file_path}.csv"
                    result = await asyncio.to_thread(subprocess.run, ['libreoffice', '--headless', '--convert-to', 'csv', file_path,
                                             '--outdir', os.path.dirname(file_path)],
                                            capture_output=True, text=True)
                    if await aiofiles.os.path.exists(tmp_csv):
                        async with aiofiles.open(tmp_csv, 'r', encoding='utf-8', errors='ignore') as f:
                            file_content = await f.read()
                        await aiofiles.os.remove(tmp_csv)
                    else:
                        raise Exception("Конвертация не удалась")
                except Exception as e2:
                    logging.error(f"Все методы обработки .xls не удались: {e2}")
                    return "Error processing .xls file: All methods failed"
        
        # Стандартные текстовые файлы
        elif file_ext in (
            ".txt", ".xml", ".json", ".js", ".har", ".sh", ".py",
            ".php", ".css", ".yaml", ".sql", ".log", ".csv", ".twig", ".md",
            ".c", ".cpp", ".h", ".java", ".rb", ".pl", ".rs", ".go", ".ts", ".jsx", ".tsx",
            ".conf", ".ini", ".toml", ".lua", ".bat", ".ps1", ".yml"
        ):
            async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                file_content += await f.read()
        else:
            return "Unsupported file type"
            
        return file_content
    except Exception as e:
        logging.error(f"Ошибка при обработке файла {file_path}: {e}")
        return f"Error processing file: {str(e)}"