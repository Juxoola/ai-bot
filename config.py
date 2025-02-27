from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
import concurrent
from aiogram import Bot, Dispatcher
import g4f.providers
import openai
import google.generativeai as genai
from g4f.client import AsyncClient, Client
from g4f.Provider import RetryProvider
from groq import Groq
from key import GROQ_API_KEY, GEMINI_API_KEY, GLHF_API_KEY, BOT_TOKEN
import g4f
import os
import logging
import json
import importlib

DATABASE_FILE = os.environ.get("DATABASE_FILE", "bot_data.db")

bot = Bot(token=BOT_TOKEN)
# States
class Form(StatesGroup):
    waiting_for_message = State()
    waiting_for_settings_selection = State()
    waiting_for_image_recognition_model = State()
    waiting_for_model_selection = State()
    waiting_for_new_model_name = State()
    waiting_for_new_model_id = State()
    waiting_for_new_model_api = State()
    waiting_for_delete_model_name = State()
    waiting_for_confirmation = State()
    waiting_for_image = State()
    waiting_for_enhance = State()
    waiting_for_image_and_prompt = State()
    waiting_for_image_prompt = State() 
    waiting_for_custom_image_prompt = State() 
    waiting_for_pdf = State()  
    waiting_for_image_generation_prompt = State()  
    waiting_for_image_generation_model = State() 
    waiting_for_aspect_ratio = State()
    waiting_for_add_image_gen_model_name = State() 
    waiting_for_delete_image_gen_model_name = State()  
    waiting_for_confirmation_image_gen_model_delete = State()  
    waiting_for_add_image_rec_model_name = State()  
    waiting_for_delete_image_rec_model_name = State()  
    waiting_for_confirmation_image_rec_model_delete = State()  
    waiting_for_image_recognition = State()  
    waiting_for_image_recognition_model_selection = State()  
    waiting_for_image_recognition_prompt = State() 
    waiting_for_custom_image_recognition_prompt = State()  
    waiting_for_audio = State()  
    waiting_for_whisper_model_selection = State()  
    waiting_for_search_query = State() 
    waiting_for_long_message = State() 
    waiting_for_web_search_message = State()
    web_search_enabled = State()
    waiting_for_add_user_id = State()
    waiting_for_remove_user_id = State()
    waiting_for_files_or_urls = State() 
    waiting_for_bucket_id = State()
    waiting_for_web_file_query = State() 
    waiting_for_message_to_all = State()
    waiting_for_user_id_to_send = State()
    waiting_for_message_to_user = State()   
    waiting_for_image_and_prompt_openai = State()
    waiting_for_custom_image_prompt_openai = State()

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Initialize OpenAI client
openai_client = openai.AsyncOpenAI(
    api_key=GLHF_API_KEY,
    base_url="https://text.pollinations.ai/openai"
)

genai.configure(api_key=GEMINI_API_KEY)

groq_client = Groq(api_key=GROQ_API_KEY)

# Функция для динамического импорта провайдера по его имени
def get_provider(provider_name: str):
    module = importlib.import_module("g4f.Provider")
    return getattr(module, provider_name)

# Читаем списки провайдеров из переменных окружения (имена через запятую)
raw_chat_providers = os.environ.get(
    "CHAT_PROVIDERS",
    "DDG,Blackbox,CablyAI,Glider,HuggingSpace,PerplexityLabs,TeachAnything,PollinationsAI,OIVSCode,DeepInfraChat,ImageLabs"
)
chat_providers = [get_provider(p.strip()) for p in raw_chat_providers.split(",") if p.strip()]

raw_image_providers = os.environ.get(
    "IMAGE_PROVIDERS",
    "Blackbox,DeepInfraChat,PollinationsAI,OIVSCode"
)
image_providers = [get_provider(p.strip()) for p in raw_image_providers.split(",") if p.strip()]

raw_web_search_providers = os.environ.get(
    "WEB_SEARCH_PROVIDERS",
    "Blackbox"
)
web_search_providers = [get_provider(p.strip()) for p in raw_web_search_providers.split(",") if p.strip()]

# Конфигурация моделей для каждого провайдера (ожидается JSON-строка)
raw_provider_models = os.environ.get("PROVIDER_MODELS")
if raw_provider_models:
    try:
        provider_models_config = json.loads(raw_provider_models)
        PROVIDER_MODELS = {}
        for key, value in provider_models_config.items():
            if isinstance(value, str):
                models = [m.strip() for m in value.split(",") if m.strip()]
            elif isinstance(value, list):
                models = value
            else:
                models = []
            provider_class = get_provider(key)
            PROVIDER_MODELS[provider_class] = models
    except Exception as e:
        logging.error("Error parsing PROVIDER_MODELS env variable: %s", e)
        PROVIDER_MODELS = {}
else:
    PROVIDER_MODELS = {
        get_provider("Blackbox"): ['gpt-4o', 'gemini-1.5-flash', 'llama-3.3-70b', 'mixtral-7b', 'deepseek-chat', 'dbrx-instruct', 'qwq-32b', 'hermes-2-dpo', 'flux', 'deepseek-r1', 'deepseek-v3', 'blackboxai-pro', 'llama-3.1-8b', 'llama-3.1-70b', 'llama-3.1-405b', 'blackboxai', 'gemini-2.0-flash', 'o3-mini'],
        get_provider("Glider"): ['llama-3.1-70b', 'llama-3.1-8b', 'llama-3.2-3b', 'deepseek-r1'],
        get_provider("DeepInfraChat"): ['llama-3.1-8b', 'llama-3.2-90b', 'llama-3.3-70b', 'deepseek-v3', 'mixtral-small-28b', 'deepseek-r1', 'phi-4', 'wizardlm-2-8x22b', 'qwen-2.5-72b', 'llama-3.2-90b', 'minicpm-2.5'],
        get_provider("HuggingSpace"): ['qvq-72b', 'qwen-2-72b', 'command-r', 'command-r-plus', 'command-r7b', 'flux-dev', 'flux-schnell', 'sd-3.5'],
        get_provider("DDG"): ['gpt-4o-mini', 'claude-3-haiku', 'llama-3.3-70b', 'mixtral-small-24b', 'o3-mini'],
        get_provider("PollinationsAI"): ['gpt-4o-mini', 'gpt-4', 'gpt-4o', 'qwen-2.5-72b', 'qwen-2.5-coder-32b', 'llama-3.3-70b', 'mistral-nemo', 'deepseek-chat', 'llama-3.1-8b', 'gpt-4o-vision', 'gpt-4o-mini-vision', 'deepseek-r1', 'gemini-2.0-flash', 'gemini-2.0-flash-thinking', 'sdxl-turbo', 'flux'],
        get_provider("OIVSCode"): ['gpt-4o-mini'],
        get_provider("ImageLabs"): ['sdxl-turbo'],
        get_provider("TeachAnything"): ['llama-3.1-70b'],
        get_provider("PerplexityLabs"): ['sonar', 'sonar-pro', 'sonar-reasoning', 'sonar-reasoning-pro', 'r1-1776'],
        get_provider("CablyAI"): ['o3-mini-low', 'gpt-4o-mini', 'deepseek-r1', 'deepseek-v3'],
        get_provider("Liaobots"): ['gpt-4o-mini', 'gpt-4o', 'gpt-4', 'o1-preview', 'o1-mini', 'deepseek-r1', 'deepseek-v3', 'claude-3-opus', 'claude-3.5-sonnet', 'claude-3-sonnet', 'gemini-2.0-flash', 'gemini-2.0-flash-thinking', 'gemini-1.5-flash', 'gemini-1.5-pro']
    }

def get_supported_providers(provider_classes, model_name=None):

    supported_providers = []
    for provider_class in provider_classes:
        custom_models = PROVIDER_MODELS.get(provider_class)

        if custom_models is not None: 
            if not model_name or not custom_models or model_name in custom_models:
                supported_providers.append(provider_class)
            
        else:

            supported_providers.append(provider_class) 
            if model_name: 
                print(f"Provider {provider_class.__name__} is not in PROVIDER_MODELS, assuming it supports all models (or as defined by empty list [] in PROVIDER_MODELS).")

    return supported_providers

g4f_client_providers = get_supported_providers(chat_providers)
g4f_image_client_providers = get_supported_providers(image_providers) 
g4f_web_search_client_providers = get_supported_providers(web_search_providers)


g4f_client = Client(provider=RetryProvider(g4f_client_providers, shuffle=False), image_provider=RetryProvider(g4f_image_client_providers, shuffle=False))

g4f_image_client = Client(provider=RetryProvider(g4f_image_client_providers, shuffle=False), image_provider=RetryProvider(g4f_image_client_providers, shuffle=False))  # Change to 

g4f_web_search_client = Client(provider=RetryProvider(g4f_web_search_client_providers, shuffle=False)) 


def update_g4f_clients(model_name=None):

    global g4f_client, g4f_image_client, g4f_web_search_client

    updated_chat_providers = get_supported_providers(chat_providers, model_name)
    updated_image_providers = get_supported_providers(image_providers, model_name)
    updated_web_search_providers = get_supported_providers(web_search_providers, model_name)

    g4f_client = Client(
        provider=RetryProvider(updated_chat_providers, shuffle=False),
        image_provider=RetryProvider(updated_image_providers, shuffle=False)
    )

    g4f_image_client = Client(
        provider=RetryProvider(updated_image_providers, shuffle=False),
        image_provider=RetryProvider(updated_image_providers, shuffle=False)
    )

    g4f_web_search_client = Client(
        provider=RetryProvider(updated_web_search_providers, shuffle=False)
    )


user_clients = {} 

def get_user_clients(user_id, model_name=None):
   
    from g4f.Provider import RetryProvider
    from g4f.client import Client
    
    updated_chat_providers = get_supported_providers(chat_providers, model_name)
    updated_image_providers = get_supported_providers(image_providers, model_name)
    updated_web_search_providers = get_supported_providers(web_search_providers, model_name)
    updated_image_gen_providers = get_supported_providers(chat_providers, model_name)

    
    clients = {
        "g4f_client": Client(
            provider=RetryProvider(updated_chat_providers, shuffle=False),
            image_provider=RetryProvider(updated_image_providers, shuffle=False)
        ),
        "g4f_image_client": Client(
            provider=RetryProvider(updated_image_providers, shuffle=False),
            image_provider=RetryProvider(updated_image_providers, shuffle=False)
        ),
        "g4f_web_search_client": Client(
            provider=RetryProvider(updated_web_search_providers, shuffle=False)
        ),
        "g4f_image_gen_client": Client(
            provider=RetryProvider(updated_image_gen_providers, shuffle=False),
            image_provider=RetryProvider(updated_image_gen_providers, shuffle=False)
        )
    }
    return clients

def update_user_clients(user_id, model_name=None):

    global user_clients
    user_clients[user_id] = get_user_clients(user_id, model_name)

    import logging
    logging.info(f"Clients updated for user {user_id} with model '{model_name}'")
    return user_clients[user_id]

def get_client(user_id, client_type="g4f_client", model_name=None):
   
    if user_id not in user_clients:
        update_user_clients(user_id, model_name)
    return user_clients.get(user_id).get(client_type)


enhance_prompt_client = None

async def init_enhance_prompt_client():
    
    global enhance_prompt_client
    model_name = "llama-3.3-70b"  # Фиксированная модель для улучшения промпта
    enhanced_chat_providers = get_supported_providers(chat_providers, model_name)
    enhanced_image_providers = get_supported_providers(image_providers, model_name)
    enhance_prompt_client = Client(
        provider=RetryProvider(enhanced_chat_providers, shuffle=False),
        image_provider=RetryProvider(enhanced_image_providers, shuffle=False)
    )
    logging.info("Enhance prompt client initialized with model {model_name}")


def update_image_gen_client(user_id, image_gen_model):

    global user_clients
    from g4f.client import Client
    from g4f.Provider import RetryProvider

    updated_image_gen_providers = get_supported_providers(chat_providers, image_gen_model)
    new_client = Client(
        provider=RetryProvider(updated_image_gen_providers, shuffle=False),
        image_provider=RetryProvider(updated_image_gen_providers, shuffle=False)
    )
    if user_id not in user_clients:
        user_clients[user_id] = get_user_clients(user_id, image_gen_model)
    else:
        user_clients[user_id]["g4f_image_gen_client"] = new_client
    import logging
    logging.info(f"User {user_id}: Image generation client updated with model '{image_gen_model}'")
    return new_client