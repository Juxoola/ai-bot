from key import ALLOWED_USER_IDS, ADMIN_USER_ID
import json
import base64
from io import BytesIO
import aiosqlite
import asyncio
from collections import deque
from contextlib import asynccontextmanager
import os
from config import openai_clients
import time
from cachetools import TTLCache, LRUCache
import logging

AVAILABLE_MODELS = None
IMAGE_GENERATION_MODELS = None
IMAGE_RECOGNITION_MODELS = None
WHISPER_MODELS = None


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

DATABASE_FILE = os.environ.get("DATABASE_FILE", "bot_data.db")

DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_IMAGE_GEN_MODEL = "flux_poli"
DEFAULT_IMAGE_RECOGNITION_MODEL = "gemini-2.0-flash"
DEFAULT_WHISPER_MODEL = "whisper-large-v3"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_ENHANCE = True

user_context_cache = TTLCache(maxsize=2000, ttl=300)  # 5 минут

class DatabaseConnectionPool:
    def __init__(self, max_connections=20):
        self.max_connections = max_connections
        self.pool = deque(maxlen=max_connections)
        self.lock = asyncio.Lock()
        self.in_use = set()
        self.connection_timeouts = {}
        self.connection_stats = {"total_created": 0, "current_active": 0, "max_concurrent": 0}

    async def acquire(self):
        async with self.lock:
            current_time = time.time()
            for conn in list(self.in_use):
                if current_time - self.connection_timeouts.get(conn, 0) > 30:
                    try:
                        self.in_use.remove(conn)
                        self.connection_stats["current_active"] -= 1
                        await conn.close()
                    except Exception:
                        pass
            
            while True:
                if self.pool:
                    conn = self.pool.popleft()
                    self.in_use.add(conn)
                    self.connection_stats["current_active"] += 1
                    self.connection_stats["max_concurrent"] = max(
                        self.connection_stats["max_concurrent"], 
                        self.connection_stats["current_active"]
                    )
                    self.connection_timeouts[conn] = time.time()
                    return conn
                
                if len(self.in_use) < self.max_connections:
                    conn = await aiosqlite.connect(DATABASE_FILE)
                    await conn.execute("PRAGMA journal_mode=WAL")
                    await conn.execute("PRAGMA synchronous=NORMAL")
                    await conn.execute("PRAGMA cache_size=-4000")
                    await conn.execute("PRAGMA temp_store=MEMORY")
                    await conn.execute("PRAGMA mmap_size=30000000000")
                    await conn.execute("PRAGMA busy_timeout=5000")
                    self.in_use.add(conn)
                    self.connection_stats["total_created"] += 1
                    self.connection_stats["current_active"] += 1
                    self.connection_stats["max_concurrent"] = max(
                        self.connection_stats["max_concurrent"], 
                        self.connection_stats["current_active"]
                    )
                    self.connection_timeouts[conn] = time.time()
                    return conn
                
                await asyncio.sleep(0.1)

    async def release(self, conn):
        async with self.lock:
            if conn in self.in_use:
                self.in_use.remove(conn)
                self.connection_stats["current_active"] -= 1
                self.pool.append(conn)
            
    async def get_stats(self):
        async with self.lock:
            return self.connection_stats.copy()

    async def close_all(self):
        async with self.lock:
            while self.pool:
                conn = self.pool.popleft()
                try:
                    await conn.close()
                except Exception as e:
                    logging.error(f"Error closing connection from pool: {e}")
            
            for conn in list(self.in_use):
                try:
                    await conn.close()
                except Exception as e:
                    logging.error(f"Error closing in-use connection: {e}")
                
            self.in_use.clear()
            self.connection_timeouts.clear()
            self.connection_stats["current_active"] = 0

db_pool = DatabaseConnectionPool(max_connections=20)

#семафор для ограничения одновременного доступа к базе данных
db_semaphore = asyncio.Semaphore(20)

@asynccontextmanager
async def get_db_connection():
    async with db_semaphore:
        conn = await db_pool.acquire()
        try:
            yield conn
        finally:
            await db_pool.release(conn)

async def optimize_database():

    async with get_db_connection() as db:
        try:
            await db.execute("PRAGMA optimize")
            await db.execute("ANALYZE")
            await db.execute("REINDEX")
            await db.execute("VACUUM")
            await db.commit()
            print("Database optimization completed successfully")
        except Exception as e:
            print(f"Error during database optimization: {e}")
            await db.rollback()

async def initialize_database():
    global ALLOWED_USER_IDS
    global ADMIN_USER_ID
    global AVAILABLE_MODELS, IMAGE_GENERATION_MODELS, IMAGE_RECOGNITION_MODELS, WHISPER_MODELS

    async with get_db_connection() as db:
        await db.execute("PRAGMA journal_mode=WAL")
        
        await db.execute("PRAGMA cache_size=-2000")  # 2MB cache
        
        await db.execute("PRAGMA synchronous=NORMAL")
        
        await db.execute("PRAGMA temp_store=MEMORY")
        
        await db.execute("PRAGMA mmap_size=30000000000") 
        
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS allowed_users (
                user_id INTEGER PRIMARY KEY
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                user_id INTEGER PRIMARY KEY
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT,
                api TEXT,
                model_name TEXT,
                PRIMARY KEY (model_id, api)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS image_generation_models (
                model_id TEXT,
                api TEXT,
                PRIMARY KEY (model_id, api)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS image_recognition_models (
                model_id TEXT,
                api TEXT,
                PRIMARY KEY (model_id, api)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS whisper_models (
                name TEXT PRIMARY KEY
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_contexts (
                user_id INTEGER PRIMARY KEY,
                model TEXT,
                messages TEXT,
                api_type TEXT,
                g4f_image_base64 TEXT,
                long_message TEXT,
                web_search_enabled INTEGER,
                image_generation_model TEXT,
                aspect_ratio TEXT,
                enhance INTEGER,
                show_processing_time INTEGER
            )
            """
        )
        async with db.execute("PRAGMA table_info(user_contexts)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]


        await db.commit()

        async with db.execute("SELECT COUNT(*) FROM allowed_users") as cursor:
            row = await cursor.fetchone()
            allowed_users_count = row[0]

        if allowed_users_count == 0:
            await db.executemany("INSERT INTO allowed_users (user_id) VALUES (?)", [(user_id,) for user_id in ALLOWED_USER_IDS])
            await db.commit()

        async with db.execute("SELECT user_id FROM allowed_users") as cursor:
            rows = await cursor.fetchall()
            ALLOWED_USER_IDS = [row[0] for row in rows]

        async with db.execute("SELECT COUNT(*) FROM admin_users") as cursor:
            row = await cursor.fetchone()
            admin_users_count = row[0]

        if admin_users_count == 0:
            await db.execute("INSERT INTO admin_users (user_id) VALUES (?)", (ADMIN_USER_ID,))
            await db.commit()

        async with db.execute("SELECT user_id FROM admin_users") as cursor:
            rows = await cursor.fetchall()
            ADMIN_USER_ID = rows[0][0] if rows else None

        async with db.execute("SELECT model_id, model_name, api FROM models") as cursor:
            rows = await cursor.fetchall()
            loaded_models = {f"{row[0]}_{row[2]}": {"model_name": row[1], "api": row[2]} for row in rows}

        if not loaded_models:
            await db.executemany(
                "INSERT INTO models (model_id, model_name, api) VALUES (?, ?, ?)",
                [(model["model_id"], model["model_name"], model["api"]) for model in DEFAULT_MODELS]
            )
            await db.commit()
            loaded_models = {
                f"{model['model_id']}_{model['api']}": {
                    "model_name": model["model_name"], 
                    "api": model["api"]
                } for model in DEFAULT_MODELS
            }

        async with db.execute("SELECT model_id, api FROM image_generation_models") as cursor:
            rows = await cursor.fetchall()
            loaded_image_gen_models = [{"model_id": row[0], "api": row[1]} for row in rows]

        if not loaded_image_gen_models:
            await db.executemany(
                "INSERT INTO image_generation_models (model_id, api) VALUES (?, ?)",
                [(model["model_id"], model["api"]) for model in DEFAULT_IMAGE_GEN_MODELS]
            )
            await db.commit()
            loaded_image_gen_models = DEFAULT_IMAGE_GEN_MODELS

        async with db.execute("SELECT model_id, api FROM image_recognition_models") as cursor:
            rows = await cursor.fetchall()
            loaded_image_rec_models = [{"model_id": row[0], "api": row[1]} for row in rows]

        if not loaded_image_rec_models:
            await db.executemany(
                "INSERT INTO image_recognition_models (model_id, api) VALUES (?, ?)",
                [(model["model_id"], model["api"]) for model in DEFAULT_IMAGE_RECOGNITION_MODELS]
            )
            await db.commit()
            loaded_image_rec_models = DEFAULT_IMAGE_RECOGNITION_MODELS

        async with db.execute("SELECT name FROM whisper_models") as cursor:
            rows = await cursor.fetchall()
            loaded_whisper_models = [row[0] for row in rows]

        if not loaded_whisper_models:
            await db.executemany("INSERT INTO whisper_models (name) VALUES (?)",
                                 [(model_name,) for model_name in DEFAULT_WHISPER_MODELS])
            await db.commit()
            loaded_whisper_models = DEFAULT_WHISPER_MODELS

        AVAILABLE_MODELS = loaded_models
        IMAGE_GENERATION_MODELS = loaded_image_gen_models
        IMAGE_RECOGNITION_MODELS = loaded_image_rec_models
        WHISPER_MODELS = loaded_whisper_models

        await initialize_models()
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_user_id ON user_contexts (user_id)")

        await db.execute("CREATE INDEX IF NOT EXISTS idx_models_api ON models(api)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_model ON user_contexts(model)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_api_type ON user_contexts(api_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_image_generation_model ON user_contexts(image_generation_model)")

        await optimize_database()

async def clear_all_user_contexts():
    """
    Очищает поля messages, long_message и g4f_image_base64 в таблице user_contexts при запуске бота.
    """
    async with get_db_connection() as db:
        await db.execute(
            """
            UPDATE user_contexts
            SET messages = CASE
                WHEN api_type = 'gemini' THEN '[]'
                ELSE '[{"role": "system", "content": "###INSTRUCTIONS### ALWAYS ANSWER TO THE USER IN THE MAIN LANGUAGE OF THEIR MESSAGE."}]'
            END,
            long_message = '',
            g4f_image_base64 = NULL
            """
        )
        await db.commit()
        
async def load_context(user_id):
    cache_key = f"context_{user_id}"
    if cache_key in user_context_cache:
        return user_context_cache[cache_key]
    
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT model, messages, api_type, g4f_image_base64, long_message, web_search_enabled, image_generation_model, aspect_ratio, enhance, show_processing_time FROM user_contexts WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                context = {
                    "model": f"{row[0]}_{row[2]}",
                    "messages": json.loads(row[1]),
                    "api_type": row[2],
                    "g4f_image": BytesIO(base64.b64decode(row[3])) if row[3] else None,
                    "long_message": row[4],
                    "web_search_enabled": bool(row[5]),
                    "image_generation_model": row[6],
                    "aspect_ratio": row[7],
                    "enhance": bool(row[8]),
                    "show_processing_time": bool(row[9])

                }
                user_context_cache[cache_key] = context
                return context
            else:
                allowed_apis = list(openai_clients.keys()) + ["g4f"]
                async with db.execute("SELECT model_id, api FROM models WHERE model_id = ?", (DEFAULT_MODEL,)) as cursor:
                    model_row = await cursor.fetchone()
                    model_id = model_row[0] if model_row else DEFAULT_MODEL
                    api_type = model_row[1] if model_row else AVAILABLE_MODELS[f"{DEFAULT_MODEL}_g4f"]["api"]

                context = {
                    "model": f"{model_id}_{api_type}", 
                    "messages": [{"role": "system", "content": "###INSTRUCTIONS### ALWAYS ANSWER TO THE USER IN THE MAIN LANGUAGE OF THEIR MESSAGE."}] if api_type in allowed_apis else [],
                    "api_type": api_type,
                    "g4f_image": None,
                    "long_message": "",
                    "web_search_enabled": False,
                    "image_generation_model": DEFAULT_IMAGE_GEN_MODEL,
                    "aspect_ratio": DEFAULT_ASPECT_RATIO,
                    "enhance": True,
                    "show_processing_time": False 

                }
                await save_context(user_id, context)
                
                if api_type == "g4f":
                    from config import update_user_clients, update_image_gen_client
                    model_key = context["model"].split('_')[0]
                    update_user_clients(user_id, model_key)
                    
                    image_gen_model_id = context["image_generation_model"].split('_')[0]
                    update_image_gen_client(user_id, image_gen_model_id)
                    
                user_context_cache[cache_key] = context
                return context

async def save_context(user_id, context):
    cache_key = f"context_{user_id}"
    if cache_key in user_context_cache:
        del user_context_cache[cache_key]
    
    async with get_db_connection() as db:
        async with db.cursor() as cursor:
            await cursor.execute("BEGIN IMMEDIATE")
            try:
                context_to_save = context.copy()
                model_id = context_to_save["model"].split('_')[0]
                
                if "g4f_image" in context_to_save:
                    if context_to_save["g4f_image"]:
                        context_to_save["g4f_image_base64"] = base64.b64encode(
                            context_to_save["g4f_image"].getvalue()
                        ).decode("utf-8")
                    else:
                        context_to_save["g4f_image_base64"] = None
                    
                    del context_to_save["g4f_image"]

                if "image_generation_model" in context_to_save:
                    if isinstance(context_to_save["image_generation_model"], dict):
                        img_model_id = context_to_save["image_generation_model"]["model_id"]
                        img_api = context_to_save["image_generation_model"]["api"]
                        context_to_save["image_generation_model"] = f"{img_model_id}_{img_api}"

                messages_json = json.dumps(context_to_save["messages"], 
                                          ensure_ascii=False, 
                                          separators=(',', ':')) 

                await cursor.execute(
                    """
                    REPLACE INTO user_contexts (
                        user_id, model, messages, api_type, g4f_image_base64,
                        long_message, web_search_enabled, image_generation_model, 
                        aspect_ratio, enhance, show_processing_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        model_id, 
                        messages_json,
                        context_to_save["api_type"],
                        context_to_save["g4f_image_base64"],
                        context_to_save["long_message"],
                        int(context_to_save["web_search_enabled"]),
                        context_to_save["image_generation_model"],
                        context_to_save["aspect_ratio"],
                        int(context_to_save["enhance"]),
                        int(context_to_save.get("show_processing_time", True))
                    ),
                )
                await db.commit()
                
                updated_context = context.copy()
                if "g4f_image" in updated_context and updated_context["g4f_image"]:
                    updated_context["g4f_image"] = BytesIO(
                        base64.b64decode(context_to_save["g4f_image_base64"])
                    )
                user_context_cache[cache_key] = updated_context
                
            except Exception as e:
                await db.rollback()
                logging.error(f"Error saving context for user {user_id}: {e}")
                raise e

async def load_models():
    try:
        async with get_db_connection() as db:
            models = {}
            async with db.execute("SELECT model_id, model_name, api FROM models") as cursor:
                async for row in cursor:
                    unique_key = f"{row[0]}_{row[2]}"
                    models[unique_key] = {"model_name": row[1], "api": row[2]}
            return models
    except Exception as e:
        print(f"Error loading models: {e}")
        return {
            f"{model['model_id']}_{model['api']}": {
                "model_name": model["model_name"], 
                "api": model["api"]
            } for model in DEFAULT_MODELS
        }


async def load_image_generation_models():
    try:
        async with get_db_connection() as db:
            models = []
            async with db.execute("SELECT model_id, api FROM image_generation_models") as cursor:
                async for row in cursor:
                    models.append({"model_id": row[0], "api": row[1]})
            return models
    except Exception as e:
        print(f"Error loading image generation models: {e}")
        return DEFAULT_IMAGE_GEN_MODELS

async def load_image_recognition_models():
    try:
        async with get_db_connection() as db:
            models = []
            async with db.execute("SELECT model_id, api FROM image_recognition_models") as cursor:
                async for row in cursor:
                    models.append({"model_id": row[0], "api": row[1]})
            return models
    except Exception as e:
        print(f"Error loading image recognition models: {e}")
        return DEFAULT_IMAGE_RECOGNITION_MODELS

async def load_whisper_models():
    try:
        async with get_db_connection() as db:
            models = []
            async with db.execute("SELECT name FROM whisper_models") as cursor:
                async for row in cursor:
                    models.append(row[0])
            return models
    except Exception as e:
        print(f"Error loading whisper models: {e}")
        return DEFAULT_WHISPER_MODELS

async def save_models(models):
    async with get_db_connection() as db:
        async with db.cursor() as cursor:
            await cursor.execute("BEGIN")
            try:
                await cursor.execute("DELETE FROM models")
                insert_data = [
                    (key.split("_")[0], data["model_name"], data["api"])
                    for key, data in models.items()
                ]
                await cursor.executemany(
                    "INSERT INTO models (model_id, model_name, api) VALUES (?, ?, ?)",
                    insert_data
                )
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"Error saving models: {e}")

async def save_image_generation_models(models):
    async with get_db_connection() as db:
        async with db.cursor() as cursor:
            await cursor.execute("BEGIN")
            try:
                await cursor.execute("DELETE FROM image_generation_models")
                insert_data = [
                    (model["model_id"], model["api"])
                    for model in models
                ]
                await cursor.executemany(
                    "INSERT INTO image_generation_models (model_id, api) VALUES (?, ?)",
                    insert_data
                )
                await db.commit()
            except Exception as e:
                await db.rollback()
                raise e

async def save_image_recognition_models(models):
    async with get_db_connection() as db:
        async with db.cursor() as cursor:
            await cursor.execute("BEGIN")
            try:
                await cursor.execute("DELETE FROM image_recognition_models")
                await cursor.executemany(
                    "INSERT INTO image_recognition_models (model_id, api) VALUES (?, ?)",
                    [(model["model_id"], model["api"]) for model in models],
                )
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"Error saving image recognition models: {e}")

async def save_whisper_models(models):
    async with get_db_connection() as db:
        async with db.cursor() as cursor:
            await cursor.execute("BEGIN")
            try:
                await cursor.execute("DELETE FROM whisper_models")
                await cursor.executemany(
                    "INSERT INTO whisper_models (name) VALUES (?)",
                    [(model_name,) for model_name in models],
                )
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"Error saving whisper models: {e}")

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
        print(f"Error loading image recognition models: {e}")
        return {}

async def def_rec_model():
    return {"model_id": DEFAULT_IMAGE_RECOGNITION_MODEL, "api": "g4f"}

async def def_aspect():
    return DEFAULT_ASPECT_RATIO

async def def_gen_model():
    return DEFAULT_IMAGE_GEN_MODEL

async def whisp_models():
    return WHISPER_MODELS

async def def_enhance():
    return DEFAULT_ENHANCE

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
        from config import update_user_clients, update_image_gen_client
        from database import def_gen_model
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
                        tasks.append(asyncio.to_thread(update_user_clients, user_id, model_key))
                        
                        if image_gen_model:
                            image_gen_model_id = image_gen_model.split('_')[0]
                            tasks.append(asyncio.to_thread(update_image_gen_client, user_id, image_gen_model_id))
                        else:
                            default_image_gen_model_id = DEFAULT_IMAGE_GEN_MODEL.split('_')[0]
                            tasks.append(asyncio.to_thread(update_image_gen_client, user_id, default_image_gen_model_id))
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

