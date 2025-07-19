from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot, Dispatcher
import openai
import anthropic
from google import genai
from g4f.client import Client
from g4f.Provider import RetryProvider
from groq import Groq
from key import GROQ_API_KEY, GEMINI_API_KEY, BOT_TOKEN
import os
import logging
import json
import importlib


# Monkey patch для PerplexityLabs - установка working = True
try:
    from g4f.Provider import PerplexityLabs
    PerplexityLabs.working = True
    logging.info("Monkey patch применен: PerplexityLabs.working = True")
except ImportError:
    logging.error("Не удалось импортировать PerplexityLabs для применения monkey patch")

DATABASE_FILE = os.environ.get("DATABASE_FILE", "bot_data.db")

DEFAULT_SYSTEM_PROMPTS = {
    "default": "###INSTRUCTIONS### ВСЕГДА ОТВЕЧАЙТЕ ПОЛЬЗОВАТЕЛЮ НА ОСНОВНОМ ЯЗЫКЕ ЕГО СООБЩЕНИЯ. ПРЕДОСТАВЛЯТЬ ПОЛЕЗНУЮ И ТОЧНУЮ ИНФОРМАЦИЮ. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN.",
    "assistant": "###INSTRUCTIONS### Вы — полезный, уважительный и правдивый ассистент. Отвечайте как можно точнее и информативнее, используя предоставленный контекст. Если вам не хватает информации, признайте это, не придумывайте факты. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN.",
    "professor": "###INSTRUCTIONS### Вы — профессор с глубокими знаниями в различных областях науки. Отвечайте подробно, используя научную терминологию, приводите факты и исследования. Ваша цель — дать образовательный ответ высокого качества. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN.",
    "friend": "###INSTRUCTIONS### Ты мой друг, общайся со мной в дружеской, неформальной манере. Используй разговорный стиль, будь эмпатичным и поддерживающим. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN.",
    "psychologist": "###INSTRUCTIONS### Вы — опытный психолог. Слушайте внимательно, проявляйте эмпатию, задавайте уточняющие вопросы. Давайте поддерживающие, но профессиональные ответы с элементами психологического анализа. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN.",
    "developer": "###INSTRUCTIONS### Вы — опытный программист. Отвечайте технически точно, приводите фрагменты кода, объясняйте сложные концепции простым языком. Если возможно, давайте несколько решений проблемы. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN.",
    "poet": "###INSTRUCTIONS### Ты — поэт с изысканным стилем. Отвечай красивым, образным языком, используй метафоры, рифмы и другие поэтические приемы. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN.",
    "zumer": "###INSTRUCTIONS### ты зумер, отвечай на вопросы в стиле зумера используй смайлики и сленг. ВСЕГДА ФОРМАТИРУЙТЕ ОТВЕТЫ С ИСПОЛЬЗОВАНИЕМ MARKDOWN."
}

timeout_config_str = os.environ.get("TIMEOUT_CONFIG", '{}')
try:
    TIMEOUT_CONFIG = json.loads(timeout_config_str)
    logging.info(f"Загружена конфигурация таймаутов: {TIMEOUT_CONFIG}")
except json.JSONDecodeError:
    logging.error(f"Ошибка при парсинге TIMEOUT_CONFIG: {timeout_config_str}")
    TIMEOUT_CONFIG = {"apis": [], "models": {}}

def should_bypass_timeout(model_id, api_type):

    api_models = TIMEOUT_CONFIG.get("models", {}).get(api_type, [])
    if model_id in api_models:
        return True
    
    return False

bot = Bot(token=BOT_TOKEN)
# States
class Form(StatesGroup):
    waiting_for_message = State()
    waiting_for_settings_selection = State()
    waiting_for_image_recognition_model = State()
    waiting_for_api_selection = State()
    waiting_for_model_selection = State()
    waiting_for_new_model_name = State()
    waiting_for_new_model_id = State()
    waiting_for_new_model_api = State()
    waiting_for_delete_model_name = State()
    waiting_for_delete_model_api_selection = State()
    waiting_for_delete_model_by_api = State()
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
    waiting_for_voice_selection = State()
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
    waiting_for_image_and_prompt_anthropic = State()
    waiting_for_custom_image_prompt_anthropic = State()
    waiting_for_new_image_rec_model_id = State()
    waiting_for_new_image_rec_model_api = State()
    waiting_for_image_edit_instructions = State()
    waiting_for_new_image_gen_model_id = State()
    waiting_for_new_image_gen_model_api = State()
    waiting_for_role_selection = State()
    playing_tictactoe = State()
    playing_guess_number = State()
    in_progress = State() 

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


providers_json = os.environ.get("OPENAI_PROVIDERS", "")
providers_json = providers_json.strip("'")
try:
    providers_config = json.loads(providers_json)
except json.JSONDecodeError as e:
    logging.error("Ошибка при разборе OPENAI_PROVIDERS: %s", e)
    providers_config = {}


openai_clients = {}
for provider, cfg in providers_config.items():
    api_key = cfg.get("api_key")
    base_url = cfg.get("base_url")
    if not api_key or not base_url:
        logging.warning(f"Для провайдера {provider} не задан 'api_key' или 'base_url'. Пропускаем.")
        continue
    
    openai_clients[provider] = openai.OpenAI(
        api_key=api_key, 
        base_url=base_url, 
        max_retries=0
    )

anthropic_clients = {}
anthropic_providers_json = os.environ.get("ANTHROPIC_PROVIDERS", "")
anthropic_providers_json = anthropic_providers_json.strip("'")
try:
    anthropic_providers_config = json.loads(anthropic_providers_json)
except json.JSONDecodeError as e:
    logging.error("Ошибка при разборе ANTHROPIC_PROVIDERS: %s", e)
    anthropic_providers_config = {}

for provider, cfg in anthropic_providers_config.items():
    api_key = cfg.get("api_key")
    base_url = cfg.get("base_url", "https://api.anthropic.com")
    if not api_key:
        logging.warning(f"Для провайдера Anthropic {provider} не задан 'api_key'. Пропускаем.")
        continue
    
    anthropic_clients[provider] = anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url
    )

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


groq_client = Groq(api_key=GROQ_API_KEY)

def get_provider(provider_name: str):
    module = importlib.import_module("g4f.Provider")
    return getattr(module, provider_name)

raw_chat_providers = os.environ.get(
    "CHAT_PROVIDERS",
    ""
)
chat_providers = [get_provider(p.strip()) for p in raw_chat_providers.split(",") if p.strip()]

raw_image_providers = os.environ.get(
    "IMAGE_PROVIDERS",
    ""
)
image_providers = [get_provider(p.strip()) for p in raw_image_providers.split(",") if p.strip()]



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
    PROVIDER_MODELS = {}

raw_provider_image_recognition_models = os.environ.get("PROVIDER_IMAGE_RECOGNITION_MODELS")
if raw_provider_image_recognition_models:
    try:
        provider_image_recognition_config = json.loads(raw_provider_image_recognition_models)
        PROVIDER_IMAGE_RECOGNITION_MODELS = {}
        for key, value in provider_image_recognition_config.items():
            if isinstance(value, str):
                models = [m.strip() for m in value.split(",") if m.strip()]
            elif isinstance(value, list):
                models = value
            else:
                models = []
            provider_class = get_provider(key)
            PROVIDER_IMAGE_RECOGNITION_MODELS[provider_class] = models
    except Exception as e:
        logging.error("Error parsing PROVIDER_IMAGE_RECOGNITION_MODELS env variable: %s", e)
        PROVIDER_IMAGE_RECOGNITION_MODELS = {}
else:
    PROVIDER_IMAGE_RECOGNITION_MODELS = {}

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


g4f_client = Client(provider=RetryProvider(g4f_client_providers, shuffle=False), image_provider=RetryProvider(g4f_image_client_providers, shuffle=False))

g4f_image_client = Client(provider=RetryProvider(g4f_image_client_providers, shuffle=False), image_provider=RetryProvider(g4f_image_client_providers, shuffle=False))


def update_g4f_clients(model_name=None):

    global g4f_client, g4f_image_client

    updated_chat_providers = get_supported_providers(chat_providers, model_name)
    updated_image_providers = get_supported_providers(image_providers, model_name)

    g4f_client = Client(
        provider=RetryProvider(updated_chat_providers, shuffle=False),
        image_provider=RetryProvider(updated_image_providers, shuffle=False)
    )

    g4f_image_client = Client(
        provider=RetryProvider(updated_image_providers, shuffle=False),
        image_provider=RetryProvider(updated_image_providers, shuffle=False)
    )


user_clients = {} 

def get_user_clients(user_id, model_name=None):
    from g4f.Provider import RetryProvider
    from g4f.client import Client
    
    updated_chat_providers = get_supported_providers(chat_providers, model_name)
    updated_image_providers = get_supported_providers(image_providers, model_name)
    updated_image_gen_providers = get_supported_providers(chat_providers, model_name)
    
    updated_image_recognition_providers = get_image_recognition_providers(model_name)
    if not updated_image_recognition_providers:
        updated_image_recognition_providers = updated_image_providers
    
    clients = {
        "g4f_client": Client(
            provider=RetryProvider(updated_chat_providers, shuffle=False),
            image_provider=RetryProvider(updated_image_providers, shuffle=False)
        ),
        "g4f_image_client": Client(
            provider=RetryProvider(updated_image_providers, shuffle=False),
            image_provider=RetryProvider(updated_image_providers, shuffle=False)
        ),
        "g4f_image_gen_client": Client(
            provider=RetryProvider(updated_image_gen_providers, shuffle=False),
            image_provider=RetryProvider(updated_image_gen_providers, shuffle=False)
        ),
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
model_name_e = "gpt-4o"  

async def init_enhance_prompt_client():
    
    global enhance_prompt_client
    enhanced_chat_providers = get_supported_providers(chat_providers, model_name_e)
    logging.info(f"Providers {enhanced_chat_providers}")
    enhanced_image_providers = get_supported_providers(image_providers, model_name_e)
    enhance_prompt_client = Client(
        provider=RetryProvider(enhanced_chat_providers, shuffle=False),
        image_provider=RetryProvider(enhanced_image_providers, shuffle=False)
    )
    logging.info(f"Enhance prompt client initialized with model {model_name_e}")


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

def get_openai_client(api_type: str):

    client = openai_clients.get(api_type)
    if not client:
        available = ", ".join(openai_clients.keys())
        raise ValueError(f"Неподдерживаемый тип OpenAI провайдера: {api_type}. Доступные: {available}")
    return client

def get_anthropic_client(api_type: str):
    client = anthropic_clients.get(api_type)
    if not client:
        available = ", ".join(anthropic_clients.keys())
        raise ValueError(f"Неподдерживаемый тип Anthropic провайдера: {api_type}. Доступные: {available}")
    return client

def get_image_recognition_providers(model_name=None):
    supported_providers = []
    
    for provider_class, models in PROVIDER_IMAGE_RECOGNITION_MODELS.items():
        if not model_name or model_name in models:
            supported_providers.append(provider_class)
            
    return supported_providers

async def update_image_client_for_recognition(user_id, image_rec_model):

    global user_clients
    from g4f.client import Client
    from g4f.Provider import RetryProvider

    image_rec_providers = get_image_recognition_providers(image_rec_model)
    

    if not image_rec_providers:
        logging.warning(f"Для модели '{image_rec_model}' нет провайдеров с поддержкой распознавания изображений")
        image_rec_providers = get_supported_providers(image_providers, image_rec_model)
        logging.info(f"Используем общие провайдеры изображений: {[p.__name__ for p in image_rec_providers]}")
    
    if len(image_rec_providers) > 0:
        logging.info(f"Используем провайдеров для распознавания изображений модели {image_rec_model}: {[p.__name__ for p in image_rec_providers]}")
    else:
        logging.error(f"Не найдено ни одного провайдера для модели {image_rec_model}!")
        image_rec_providers = image_providers
        logging.info(f"Используем все доступные провайдеры изображений: {[p.__name__ for p in image_rec_providers]}")
    
    new_client = Client(
        provider=RetryProvider(image_rec_providers, shuffle=False),
        image_provider=RetryProvider(image_rec_providers, shuffle=False)
    )
    
    if user_id not in user_clients:
        user_clients[user_id] = get_user_clients(user_id, image_rec_model)
    else:
        user_clients[user_id]["g4f_image_client"] = new_client
    
    return new_client