import asyncio
import base64
import json
import logging
import os
from asyncio import Queue
from contextlib import asynccontextmanager
from io import BytesIO

import aiohttp
import aiosqlite
from cachetools import TTLCache
from config import (DEFAULT_SYSTEM_PROMPTS, providers_config,
                    update_image_gen_client, update_user_clients)
from key import ADMIN_USER_ID, ALLOWED_USER_IDS

AVAILABLE_MODELS = None
IMAGE_GENERATION_MODELS = None
IMAGE_RECOGNITION_MODELS = None
WHISPER_MODELS = None

DATABASE_FILE = os.environ.get("DATABASE_FILE", "bot_data.db")
DEFAULT_MODEL = "openai-large"
DEFAULT_IMAGE_GEN_MODEL = "flux_poli"
DEFAULT_WHISPER_MODEL = "whisper-large-v3"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_ENHANCE = True
DEFAULT_VOICE = "alloy"

DEFAULT_MODELS = [
    {"model_id": "gemini-1.5-flash", "model_name": "Gemini-1.5-flash", "api": "gemini"},
    {"model_id": "gemini-2.0-flash-exp", "model_name": "Gemini-2.0-flash-exp", "api": "gemini"},
    {"model_id": "gemini-2.0-flash-thinking-exp-01-21", "model_name": "Gemini-2.0-flash-thinking-exp-01-21", "api": "gemini"},
    {"model_id": "gemini-1.5-pro", "model_name": "Gemini-1.5-pro", "api": "gemini"},
    {"model_id": "gemini-exp-1206", "model_name": "Gemini-exp-1206", "api": "gemini"},
    {"model_id": "gpt-4o", "model_name": "Gpt-4o", "api": "g4f"},
    {"model_id": "gpt-4o-mini", "model_name": "Gpt-4o-mini", "api": "g4f"},
    {"model_id": "blackboxai", "model_name": "Blackboxai", "api": "g4f"},
    {"model_id": "blackboxai-pro", "model_name": "Blackboxai-pro", "api": "g4f"},
    {"model_id": "llama-3.3-70b", "model_name": "Llama-3.3-70b","api": "g4f"},
    {"model_id": "llama-3.1-70b", "model_name": "Llama-3.1-70b","api": "g4f"},
    {"model_id": "llama-3.1-405b", "model_name": "Llama-3.1-405b","api": "g4f"},
    {"model_id": "qwen-2-72b", "model_name": "Qwen-2-72b","api": "g4f"},
    {"model_id": "qwq-32b", "model_name": "Qwq-32b","api": "g4f"},
    {"model_id": "qwen-2.5-coder-32b", "model_name": "Qwen-2.5-coder-32b","api": "g4f"},
    {"model_id": "qwen-2.5-72b", "model_name": "Qwen-2.5-72b","api": "g4f"},
    {"model_id": "deepseek-chat", "model_name": "Deepseek-chat","api": "g4f"},
    {"model_id": "deepseek-r1", "model_name": "Deepseek-r1","api": "g4f"},
    {"model_id": "deepseek-v3", "model_name": "Deepseek-v3","api": "g4f"},
    {"model_id": "gemini-1.5-flash", "model_name": "Gemini-1.5-flash", "api": "g4f"},
    {"model_id": "sonar", "model_name": "Sonar-perplexity", "api": "g4f"},
    {"model_id": "sonar-pro", "model_name": "Sonar-pro-perplexity", "api": "g4f"},
    {"model_id": "sonar-reasoning", "model_name": "Sonar-reasoning-perplexity", "api": "g4f"},
    {"model_id": "o3-mini-low", "model_name": "o3-mini-low", "api": "g4f"},
    {"model_id": "openai", "model_name": "GPT-4o-mini","api": "poli"},
    {"model_id": "openai-large", "model_name": "GPT-4o","api": "poli"},
    {"model_id": "searchgpt", "model_name": "SearchGPT","api": "poli"},
    {"model_id": "deepseek", "model_name": "DeepSeek-V3","api": "poli"},
    {"model_id": "deepseek-r1", "model_name": "Deepseek-r1","api": "poli"},
    {"model_id": "google/gemini-2.0-pro-exp-02-05:free", "model_name": "Gemini-2.0-pro-exp-02-05","api": "openrouter"},
    {"model_id": "google/gemini-2.0-flash-thinking-exp:free", "model_name": "Gemini-2.0-flash-thinking-exp","api": "openrouter"},
    {"model_id": "deepseek/deepseek-r1-distill-llama-70b:free", "model_name": "DeepSeek-R1-Distill-70B", "api": "openrouter"},
    {"model_id": "deepseek/deepseek-r1:free", "model_name": "DeepSeek-R1", "api": "openrouter"},
    {"model_id": "deepseek/deepseek-chat:free", "model_name": "DeepSeekV3", "api": "openrouter"},
    {"model_id": "qwen/qwen-2.5-coder-32b-instruct:free", "model_name": "Qwen-2.5-Coder-32B", "api": "openrouter"},
    {"model_id": "qwen/qwen2.5-vl-72b-instruct:free", "model_name": "Qwen-2.5-VL-72B", "api": "openrouter"},
    {"model_id": "qwen/qwen-vl-plus:free", "model_name": "Qwen-VL-Plus", "api": "openrouter"},
    {"model_id": "google/gemini-2.0-flash-exp:free", "model_name": "Gemini-2.0-flash-exp","api": "openrouter"},
    {"model_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", "model_name": "DeepSeek-R1-Distill-32B","api":"ddc"},
    {"model_id": "deepseek-v3", "model_name": "DeepSeek-V3", "api": "ddc"},
    {"model_id": "gpt-4o", "model_name": "GPT-4o", "api": "ddc"}
]
DEFAULT_IMAGE_GEN_MODELS = [
    {"model_id": "flux", "api": "poli"},
    {"model_id": "turbo", "api": "poli"},
]
DEFAULT_IMAGE_RECOGNITION_MODELS = [
    {"model_id": "blackboxai", "api": "g4f"},
    {"model_id": "gpt-4o", "api": "g4f"},
    {"model_id": "o1", "api": "g4f"},
    {"model_id": "o3-mini", "api": "g4f"},
    {"model_id": "gemini-1.5-pro", "api": "g4f"},
    {"model_id": "gemini-1.5-flash", "api": "g4f"},
    {"model_id": "llama-3.1-8b", "api": "g4f"},
    {"model_id": "llama-3.1-70b", "api": "g4f"},
    {"model_id": "llama-3.1-405b", "api": "g4f"},
    {"model_id": "gemini-2.0-flash", "api": "g4f"},
    {"model_id": "deepseek-v3", "api": "g4f"},
    {"model_id": "llama-3.2-90b", "api": "g4f"},
    {"model_id": "minicpm-2.5", "api": "g4f"},
    {"model_id": "gpt-4o-mini", "api": "g4f"},
    {"model_id": "o1-mini", "api": "g4f"}
]
DEFAULT_WHISPER_MODELS = ["whisper-large-v3", "whisper-large-v3-turbo"]
AVAILABLE_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer",
    "coral", "verse", "ballad", "ash", "sage", "amuch", "dan"
]

user_context_cache = TTLCache(maxsize=5000, ttl=600)  # 10 минут

class DatabaseConnectionPool:
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self._pool: Queue[aiosqlite.Connection] = Queue(maxsize=max_connections)
        self._active_connections = 0
        self._lock = asyncio.Lock()

    async def _create_connection(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(DATABASE_FILE)
        await conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA cache_size=-4000;
            PRAGMA temp_store=MEMORY;
            PRAGMA mmap_size=30000000000;
            PRAGMA busy_timeout=5000;
        """)
        return conn

    async def acquire(self) -> aiosqlite.Connection:
        if not self._pool.empty():
            return self._pool.get_nowait()

        async with self._lock:
            if self._active_connections < self.max_connections:
                self._active_connections += 1
                return await self._create_connection()
            
        return await self._pool.get()

    async def release(self, conn: aiosqlite.Connection):
        try:
            self._pool.put_nowait(conn)
        except asyncio.QueueFull:
            await conn.close()
            async with self._lock:
                self._active_connections -= 1

    async def close_all(self):
        async with self._lock:
            while not self._pool.empty():
                conn = self._pool.get_nowait()
                try:
                    await conn.close()
                except Exception as e:
                    logging.error(f"Ошибка закрытия соединения из пула: {e}")
            self._active_connections = 0

db_pool = DatabaseConnectionPool(max_connections=50)

@asynccontextmanager
async def get_db_connection():
    conn = await db_pool.acquire()
    try:
        yield conn
    finally:
        await db_pool.release(conn)

async def optimize_database():
    async with get_db_connection() as db:
        try:
            await db.executescript("""
                PRAGMA optimize;
                ANALYZE;
                REINDEX;
                VACUUM;
            """)
            await db.commit()
            logging.info("Оптимизация базы данных завершена успешно")
        except Exception as e:
            logging.error(f"Ошибка при оптимизации базы данных: {e}")
            await db.rollback()

async def _setup_database(db):
    await db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA cache_size=-2000;
        PRAGMA synchronous=NORMAL;
        PRAGMA temp_store=MEMORY;
        PRAGMA mmap_size=30000000000;
    """)

async def _create_tables(db):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS admin_users (user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS models (
            model_id TEXT, api TEXT, model_name TEXT,
            PRIMARY KEY (model_id, api)
        );
        CREATE TABLE IF NOT EXISTS image_generation_models (
            model_id TEXT, api TEXT, PRIMARY KEY (model_id, api)
        );
        CREATE TABLE IF NOT EXISTS image_recognition_models (
            model_id TEXT, api TEXT, PRIMARY KEY (model_id, api)
        );
        CREATE TABLE IF NOT EXISTS whisper_models (name TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS user_contexts (
            user_id INTEGER PRIMARY KEY, model TEXT, messages TEXT, api_type TEXT,
            g4f_image_base64 TEXT, long_message TEXT, image_generation_model TEXT,
            aspect_ratio TEXT, enhance INTEGER, show_processing_time INTEGER,
            voice TEXT DEFAULT 'alloy', system_role TEXT DEFAULT 'default'
        );
    """)
    async with db.execute("PRAGMA table_info(user_contexts)") as cursor:
        columns = [row[1] for row in await cursor.fetchall()]
    if "system_role" not in columns:
        await db.execute("ALTER TABLE user_contexts ADD COLUMN system_role TEXT DEFAULT 'default'")
    await db.commit()

async def _create_indices(db):
    await db.executescript("""
        CREATE INDEX IF NOT EXISTS idx_user_contexts_user_id ON user_contexts (user_id);
        CREATE INDEX IF NOT EXISTS idx_models_api ON models(api);
        CREATE INDEX IF NOT EXISTS idx_user_contexts_model ON user_contexts(model);
        CREATE INDEX IF NOT EXISTS idx_user_contexts_api_type ON user_contexts(api_type);
        CREATE INDEX IF NOT EXISTS idx_user_contexts_image_generation_model ON user_contexts(image_generation_model);
    """)
    await db.commit()

async def _populate_initial_data(db):
    global ALLOWED_USER_IDS, ADMIN_USER_ID
    global AVAILABLE_MODELS, IMAGE_GENERATION_MODELS, IMAGE_RECOGNITION_MODELS, WHISPER_MODELS

    async with db.execute("SELECT COUNT(*) FROM allowed_users") as cursor:
        if (await cursor.fetchone())[0] == 0:
            await db.executemany("INSERT INTO allowed_users (user_id) VALUES (?)", [(user_id,) for user_id in ALLOWED_USER_IDS])
    
    async with db.execute("SELECT user_id FROM allowed_users") as cursor:
        ALLOWED_USER_IDS = [row[0] for row in await cursor.fetchall()]

    async with db.execute("SELECT COUNT(*) FROM admin_users") as cursor:
        if (await cursor.fetchone())[0] == 0:
            await db.execute("INSERT INTO admin_users (user_id) VALUES (?)", (ADMIN_USER_ID,))

    async with db.execute("SELECT user_id FROM admin_users") as cursor:
        rows = await cursor.fetchall()
        ADMIN_USER_ID = rows[0][0] if rows else None

    async with db.execute("SELECT model_id, model_name, api FROM models") as cursor:
        rows = await cursor.fetchall()
        loaded_models = {f"{row[0]}_{row[2]}": {"model_name": row[1], "api": row[2]} for row in rows}
    if not loaded_models:
        await db.executemany("INSERT INTO models (model_id, model_name, api) VALUES (?, ?, ?)",
                             [(m["model_id"], m["model_name"], m["api"]) for m in DEFAULT_MODELS])
        loaded_models = {f"{m['model_id']}_{m['api']}": {"model_name": m["model_name"], "api": m["api"]} for m in DEFAULT_MODELS}

    async with db.execute("SELECT model_id, api FROM image_generation_models") as cursor:
        loaded_image_gen_models = [{"model_id": row[0], "api": row[1]} for row in await cursor.fetchall()]
    if not loaded_image_gen_models:
        await db.executemany("INSERT INTO image_generation_models (model_id, api) VALUES (?, ?)",
                             [(m["model_id"], m["api"]) for m in DEFAULT_IMAGE_GEN_MODELS])
        loaded_image_gen_models = DEFAULT_IMAGE_GEN_MODELS

    async with db.execute("SELECT model_id, api FROM image_recognition_models") as cursor:
        loaded_image_rec_models = [{"model_id": row[0], "api": row[1]} for row in await cursor.fetchall()]
    if not loaded_image_rec_models:
        await db.executemany("INSERT INTO image_recognition_models (model_id, api) VALUES (?, ?)",
                             [(m["model_id"], m["api"]) for m in DEFAULT_IMAGE_RECOGNITION_MODELS])
        loaded_image_rec_models = DEFAULT_IMAGE_RECOGNITION_MODELS

    async with db.execute("SELECT name FROM whisper_models") as cursor:
        loaded_whisper_models = [row[0] for row in await cursor.fetchall()]
    if not loaded_whisper_models:
        await db.executemany("INSERT INTO whisper_models (name) VALUES (?)",
                             [(name,) for name in DEFAULT_WHISPER_MODELS])
        loaded_whisper_models = DEFAULT_WHISPER_MODELS
    
    await db.commit()

    AVAILABLE_MODELS = loaded_models
    IMAGE_GENERATION_MODELS = loaded_image_gen_models
    IMAGE_RECOGNITION_MODELS = loaded_image_rec_models
    WHISPER_MODELS = loaded_whisper_models

async def initialize_database():
    async with get_db_connection() as db:
        await _setup_database(db)
        await _create_tables(db)
        await _populate_initial_data(db)
        await initialize_models()
        await _create_indices(db)
        await optimize_database()

async def clear_all_user_contexts():
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT user_id, api_type, system_role FROM user_contexts")
        user_data = await cursor.fetchall()
        
        if not user_data:
            return

        update_params = []
        for user_id, api_type, system_role in user_data:
            system_role = system_role or "default"
            system_prompt = DEFAULT_SYSTEM_PROMPTS.get(system_role, DEFAULT_SYSTEM_PROMPTS["default"])
            
            if api_type == "gemini":
                messages = json.dumps([{"role": "system", "parts": [{"text": system_prompt}]}])
            else:
                messages = json.dumps([{"role": "system", "content": system_prompt}])
            
            update_params.append((messages, user_id))
        
        await db.executemany(
            """
            UPDATE user_contexts
            SET messages = ?, long_message = '', g4f_image_base64 = NULL
            WHERE user_id = ?
            """,
            update_params
        )
        await db.commit()
        user_context_cache.clear()

async def reset_user_context(user_id):
    cache_key = f"context_{user_id}"
    
    async with get_db_connection() as db:
        async with db.execute("SELECT api_type, system_role FROM user_contexts WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return

            api_type, system_role = row
            system_role = system_role or "default"
        
        system_prompt = DEFAULT_SYSTEM_PROMPTS.get(system_role, DEFAULT_SYSTEM_PROMPTS["default"])
        if api_type == "gemini":
            messages = json.dumps([{"role": "system", "parts": [{"text": system_prompt}]}])
        else:
            messages = json.dumps([{"role": "system", "content": system_prompt}])
        
        await db.execute(
            """
            UPDATE user_contexts
            SET messages = ?, long_message = '', g4f_image_base64 = NULL
            WHERE user_id = ?
            """,
            (messages, user_id)
        )
        await db.commit()

    if cache_key in user_context_cache:
        del user_context_cache[cache_key]
        
async def _create_default_context(db, user_id):
    async with db.execute("SELECT model_id, api FROM models WHERE model_id = ?", (DEFAULT_MODEL,)) as cursor:
        model_row = await cursor.fetchone()
    model_id = model_row[0] if model_row else DEFAULT_MODEL
    api_type = model_row[1] if model_row else AVAILABLE_MODELS[f"{DEFAULT_MODEL}_poli"]["api"]

    if api_type == "gemini":
        system_message = [{"role": "system", "parts": [{"text": DEFAULT_SYSTEM_PROMPTS["default"]}]}]
    else:
        system_message = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPTS["default"]}]

    context = {
        "model": f"{model_id}_{api_type}", "messages": system_message, "api_type": api_type,
        "g4f_image": None, "long_message": "", "image_generation_model": DEFAULT_IMAGE_GEN_MODEL,
        "aspect_ratio": DEFAULT_ASPECT_RATIO, "enhance": True, "show_processing_time": False,
        "voice": DEFAULT_VOICE, "system_role": "default"
    }
    await save_context(user_id, context)

    if api_type == "g4f":
        model_key = context["model"].split('_')[0]
        update_user_clients(user_id, model_key)
        image_gen_model_id = context["image_generation_model"].split('_')[0]
        await update_image_gen_client(user_id, image_gen_model_id)
        
    return context

async def load_context(user_id):
    cache_key = f"context_{user_id}"
    if cached_context := user_context_cache.get(cache_key):
        return cached_context

    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT model, messages, api_type, g4f_image_base64, long_message, "
            "image_generation_model, aspect_ratio, enhance, show_processing_time, "
            "voice, system_role FROM user_contexts WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

    if row:
        context = {
            "model": f"{row[0]}_{row[2]}", "messages": json.loads(row[1]), "api_type": row[2],
            "g4f_image": BytesIO(base64.b64decode(row[3])) if row[3] else None,
            "long_message": row[4], "image_generation_model": row[5], "aspect_ratio": row[6],
            "enhance": bool(row[7]), "show_processing_time": bool(row[8]),
            "voice": row[9] or DEFAULT_VOICE, "system_role": row[10] or "default"
        }
    else:
        async with get_db_connection() as db:
            context = await _create_default_context(db, user_id)

    user_context_cache[cache_key] = context
    return context

async def save_context(user_id, context):
    cache_key = f"context_{user_id}"
    if cache_key in user_context_cache:
        del user_context_cache[cache_key]
    
    async with get_db_connection() as db:
        async with db.cursor() as cursor:
            try:
                context_to_save = context.copy()
                model_id = context_to_save["model"].split('_')[0]
                
                g4f_image_base64 = None
                if "g4f_image" in context_to_save and context_to_save["g4f_image"]:
                    g4f_image_base64 = base64.b64encode(
                        context_to_save["g4f_image"].getvalue()
                    ).decode("utf-8")
                
                messages_json = json.dumps(context_to_save["messages"], 
                                          ensure_ascii=False, 
                                          separators=(',', ':'))
                await cursor.execute(
                    """
                    INSERT INTO user_contexts (
                        user_id, model, messages, api_type, g4f_image_base64,
                        long_message, image_generation_model, 
                        aspect_ratio, enhance, show_processing_time, 
                        voice, system_role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        model = excluded.model,
                        messages = excluded.messages,
                        api_type = excluded.api_type,
                        g4f_image_base64 = excluded.g4f_image_base64,
                        long_message = excluded.long_message,
                        image_generation_model = excluded.image_generation_model,
                        aspect_ratio = excluded.aspect_ratio,
                        enhance = excluded.enhance,
                        show_processing_time = excluded.show_processing_time,
                        voice = excluded.voice,
                        system_role = excluded.system_role;
                    """,
                    (
                        user_id,
                        model_id, 
                        messages_json,
                        context_to_save["api_type"],
                        g4f_image_base64,
                        context_to_save["long_message"],
                        context_to_save["image_generation_model"],
                        context_to_save["aspect_ratio"],
                        int(context_to_save["enhance"]),
                        int(context_to_save.get("show_processing_time", True)),
                        context_to_save.get("voice", DEFAULT_VOICE),
                        context_to_save.get("system_role", "default")
                    ),
                )
                await db.commit()
                
                user_context_cache[cache_key] = context
                
            except Exception as e:
                await db.rollback()
                logging.error(f"Ошибка сохранения контекста для пользователя {user_id}: {e}")
                raise e

async def _load_data(query, default_data):
    try:
        async with get_db_connection() as db:
            cursor = await db.execute(query)
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Ошибка загрузки данных: {e}")
        return default_data

async def load_models():
    rows = await _load_data("SELECT model_id, model_name, api FROM models", [])
    if not rows:
        return {f"{m['model_id']}_{m['api']}": {"model_name": m["model_name"], "api": m["api"]} for m in DEFAULT_MODELS}
    return {f"{row[0]}_{row[2]}": {"model_name": row[1], "api": row[2]} for row in rows}

async def load_image_generation_models():
    rows = await _load_data("SELECT model_id, api FROM image_generation_models", [])
    return [{"model_id": row[0], "api": row[1]} for row in rows] or DEFAULT_IMAGE_GEN_MODELS

async def load_image_recognition_models():
    rows = await _load_data("SELECT model_id, api FROM image_recognition_models", [])
    return [{"model_id": row[0], "api": row[1]} for row in rows] or DEFAULT_IMAGE_RECOGNITION_MODELS

async def load_whisper_models():
    rows = await _load_data("SELECT name FROM whisper_models", [])
    return [row[0] for row in rows] or DEFAULT_WHISPER_MODELS

async def _save_data(table_name, columns, data):
    async with get_db_connection() as db:
        try:
            await db.execute(f"DELETE FROM {table_name}")
            placeholders = ", ".join("?" * len(columns))
            await db.executemany(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})", data)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logging.error(f"Ошибка сохранения данных в {table_name}: {e}")
            raise

async def save_models(models):
    data = [(key.split("_")[0], value["model_name"], value["api"]) for key, value in models.items()]
    await _save_data("models", ("model_id", "model_name", "api"), data)

async def save_image_generation_models(models):
    data = [(model["model_id"], model["api"]) for model in models]
    await _save_data("image_generation_models", ("model_id", "api"), data)

async def save_image_recognition_models(models):
    data = [(model["model_id"], model["api"]) for model in models]
    await _save_data("image_recognition_models", ("model_id", "api"), data)

async def save_whisper_models(models):
    data = [(model_name,) for model_name in models]
    await _save_data("whisper_models", ("name",), data)

AVAILABLE_MODELS = None
IMAGE_GENERATION_MODELS = None
IMAGE_RECOGNITION_MODELS = None
WHISPER_MODELS = None

async def initialize_models():
    global AVAILABLE_MODELS, IMAGE_GENERATION_MODELS, IMAGE_RECOGNITION_MODELS, WHISPER_MODELS
    AVAILABLE_MODELS = await load_models()
    IMAGE_GENERATION_MODELS = await load_image_generation_models()
    IMAGE_RECOGNITION_MODELS = await load_image_recognition_models()
    WHISPER_MODELS = await load_whisper_models()

async def _update_models_from_source(session: aiohttp.ClientSession, config: dict):
    api_name = config["api_name"]
    url = config["url"]
    headers = config.get("headers", {})
    
    if config.get("requires_token"):
        token = providers_config.get(api_name, {}).get("api_key")
        if not token:
            logging.warning(f"API-ключ для '{api_name}' не найден. Обновление пропущено.")
            return
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Ошибка при получении моделей от {api_name.capitalize()}: HTTP {response.status}")
                return
            models_data = await response.json()

        new_models = []
        new_image_rec_models = []
        
        items = config["items_path"](models_data)
        for item in items:
            if not config["filter"](item):
                continue

            model_id = config["id_path"](item)
            if not model_id:
                continue
            
            model_name = config["name_path"](item)
            new_models.append((model_id, model_name, api_name))

            if config.get("vision_path") and config["vision_path"](item):
                new_image_rec_models.append((model_id, api_name))

        async with get_db_connection() as db:
            await db.execute("DELETE FROM models WHERE api = ?", (api_name,))
            if config.get("vision_path"):
                await db.execute("DELETE FROM image_recognition_models WHERE api = ?", (api_name,))
            
            if new_models:
                await db.executemany("INSERT OR REPLACE INTO models (model_id, model_name, api) VALUES (?, ?, ?)", new_models)
            if new_image_rec_models:
                await db.executemany("INSERT OR REPLACE INTO image_recognition_models (model_id, api) VALUES (?, ?)", new_image_rec_models)
            
            await db.commit()
            logging.info(f"Модели от {api_name.capitalize()} успешно обновлены.")

    except Exception as e:
        logging.error(f"Критическая ошибка при обновлении моделей от {api_name.capitalize()}: {e}", exc_info=True)
        async with get_db_connection() as db:
            await db.rollback()

MODEL_SOURCES_CONFIG = {
    "pollinations": {
        "api_name": "poli", "url": "https://text.pollinations.ai/models",
        "items_path": lambda data: data,
        "filter": lambda item: item.get("tier") in ["seed", "anonymous"],
        "id_path": lambda item: item.get("name"),
        "name_path": lambda item: item.get("description", item.get("name")),
        "vision_path": lambda item: item.get("vision"),
    },
    "openrouter": {
        "api_name": "openrouter", "url": "https://openrouter.ai/api/v1/models",
        "items_path": lambda data: data.get("data", []),
        "filter": lambda item: "free" in item.get("id", ""),
        "id_path": lambda item: item.get("id"),
        "name_path": lambda item: item.get("name"),
        "vision_path": lambda item: "image" in item.get("architecture", {}).get("input_modalities", []),
    },
    "ddc": {
        "api_name": "ddc", "url": "https://api.a4f.co/v1/models",
        "items_path": lambda data: data.get("data", []),
        "filter": lambda item: item.get("type") == "chat/completion",
        "id_path": lambda item: item.get("id"),
        "name_path": lambda item: item.get("id"),
        "vision_path": lambda item: "vision" in item.get("features", []),
    },
    "github": {
        "api_name": "github", "url": "https://models.github.ai/v1/models", "requires_token": True,
        "items_path": lambda data: data.get("data", []),
        "filter": lambda item: True,
        "id_path": lambda item: item.get("id"),
        "name_path": lambda item: item.get("name"),
        "vision_path": lambda item: "image" in item.get("supported_input_modalities", []),
    },
    "electronhub": {
        "api_name": "electronhub", "url": "https://api.electronhub.ai/v1/models",
        "items_path": lambda data: data.get("data", []),
        "filter": lambda item: ":free" in item.get("id", ""),
        "id_path": lambda item: item.get("id"),
        "name_path": lambda item: item.get("name"),
        "vision_path": lambda item: item.get("metadata", {}).get("vision"),
    },
    "airforce": {
        "api_name": "airforce", "url": "https://api.airforce/v1/models",
        "items_path": lambda data: data.get("data", []),
        "filter": lambda item: item.get("supports_chat"),
        "id_path": lambda item: item.get("id"),
        "name_path": lambda item: item.get("id"),
    },
    "mnn": {
        "api_name": "mnn", "url": "https://api.mnnai.ru/v1/models",
        "items_path": lambda data: data.get("data", []),
        "filter": lambda item: item.get("type") == "chat.completions",
        "id_path": lambda item: item.get("id"),
        "name_path": lambda item: item.get("id"),
        "vision_path": lambda item: item.get("vision"),
    },
    "llm7": {
        "api_name": "llm7", "url": "https://api.llm7.io/v1/models",
        "items_path": lambda data: data,
        "filter": lambda item: True,
        "id_path": lambda item: item.get("id"),
        "name_path": lambda item: item.get("id"),
        "vision_path": lambda item: "image" in item.get("modalities", {}).get("input", []),
    },
}

async def update_all_external_models(session: aiohttp.ClientSession):
    logging.info("Начало обновления всех внешних моделей...")
    tasks = [_update_models_from_source(session, config) for config in MODEL_SOURCES_CONFIG.values()]
    await asyncio.gather(*tasks)
    logging.info("Процесс обновления внешних моделей завершен.")


def is_allowed(user_id):
    return user_id in ALLOWED_USER_IDS

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

async def av_models():
    return AVAILABLE_MODELS


async def gen_models():
    return IMAGE_GENERATION_MODELS

async def rec_models():
    try:
        async with get_db_connection() as db:
            models = {}
            async with db.execute("SELECT model_id, api FROM image_recognition_models") as cursor:
                async for row in cursor:
                    model_id = row[0]
                    api = row[1]
                    key = f"{model_id}_{api}"
                    models[key] = {
                        "model_id": model_id,
                        "api": api
                    }
            return models
    except Exception as e:
        logging.info(f"Ошибка загрузки моделей распознавания изображений: {e}")
        return {}


async def def_aspect():
    return DEFAULT_ASPECT_RATIO

async def def_gen_model():
    return DEFAULT_IMAGE_GEN_MODEL

async def whisp_models():
    return WHISPER_MODELS

async def def_enhance():
    return DEFAULT_ENHANCE

async def def_voice():
    return DEFAULT_VOICE

async def av_voices():
    return AVAILABLE_VOICES

async def init_av_models():
    global AVAILABLE_MODELS
    AVAILABLE_MODELS = await load_models()

async def init_rec_models():
    global IMAGE_RECOGNITION_MODELS
    IMAGE_RECOGNITION_MODELS = await load_image_recognition_models()

async def init_gen_models():
    global IMAGE_GENERATION_MODELS
    IMAGE_GENERATION_MODELS = await load_image_generation_models()


async def init_whisp_models():
    global WHISPER_MODELS
    WHISPER_MODELS = await load_whisper_models()

async def initialize_allowed_users():
    global ALLOWED_USER_IDS
    async with get_db_connection() as db:
        async with db.execute("SELECT user_id FROM allowed_users") as cursor:
            rows = await cursor.fetchall()
            ALLOWED_USER_IDS = [row[0] for row in rows]

async def get_all_allowed_users():

    async with get_db_connection() as db:
        async with db.execute("SELECT user_id FROM allowed_users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
        

async def init_all_user_clients():
    try:
        DEFAULT_IMAGE_GEN_MODEL = await def_gen_model()

        async with get_db_connection() as db:
            async with db.execute("SELECT user_id, model, api_type, image_generation_model FROM user_contexts") as cursor:
                rows = await cursor.fetchall()

        # Инициализируем клиентов группами по 10 для предотвращения перегрузки
        batch_size = 10
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            tasks = []
            
            for user_id, model, api_type, image_gen_model in batch:
                if api_type == "g4f":
                    try:
                        model_key = model.split('_')[0]
                        tasks.append(asyncio.create_task(update_user_clients(user_id, model_key)))
                        
                        if image_gen_model:
                            image_gen_model_id = image_gen_model.split('_')[0]
                            tasks.append(asyncio.create_task(update_image_gen_client(user_id, image_gen_model_id)))
                        else:
                            default_image_gen_model_id = DEFAULT_IMAGE_GEN_MODEL.split('_')[0]
                            tasks.append(asyncio.create_task(update_image_gen_client(user_id, default_image_gen_model_id)))
                    except Exception as e:
                        logging.error(f"Ошибка при создании задачи для пользователя {user_id}: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.5)
                
    except Exception as e:
        logging.error(f"Глобальная ошибка в init_all_user_clients: {e}")

async def trim_context(messages, is_admin=False, max_messages=10):
    
    if is_admin:
        return messages
    
    if len(messages) <= max_messages:
        return messages
    
    return [messages[0]] + messages[-(max_messages-1):]
