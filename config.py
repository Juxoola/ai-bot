from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
import concurrent
from aiogram import Bot, Dispatcher
import openai
import google.generativeai as genai
from g4f.client import AsyncClient, Client
from g4f.Provider import RetryProvider, Blackbox, DeepInfraChat,PollinationsAI, TeachAnything,PerplexityLabs,HuggingSpace, ImageLabs, DDG, OIVSCode, Glider, BlackboxAPI, CablyAI, Liaobots
from groq import Groq
from key import GROQ_API_KEY, GEMINI_API_KEY, GLHF_API_KEY, BOT_TOKEN
import g4f
import os
import logging


# Путь к базе данных
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

PROVIDER_MODELS = {
    Blackbox: ['gpt-4', 'gemini-1.5-flash', 'llama-3.3-70b', 'mixtral-7b', 'deepseek-chat', 'dbrx-instruct', 'qwq-32b', 'hermes-2-dpo', 'flux', 'deepseek-r1', 'deepseek-v3', 'blackboxai-pro', 'llama-3.1-8b', 'llama-3.1-70b', 'llama-3.1-405b', 'blackboxai'], 
    Glider: ['llama-3.1-70b', 'llama-3.1-8b', 'llama-3.2-3b', 'deepseek-r1'],
    DeepInfraChat: ['llama-3.1-8b', 'llama-3.2-90b', 'llama-3.3-70b', 'deepseek-v3', 'mixtral-small-28b', 'deepseek-r1', 'phi-4', 'wizardlm-2-8x22b', 'qwen-2.5-72b'], 
    HuggingSpace: ['qvq-72b', 'qwen-2-72b', 'command-r', 'command-r-plus', 'command-r7b', 'flux-dev', 'flux-schnell', 'sd-3.5'],
    DDG: ['gpt-4o-mini', 'claude-3-haiku', 'llama-3.1-70b', 'mixtral-8x7b'], 
    PollinationsAI: ['gpt-4o-mini', 'gpt-4', 'gpt-4o', 'qwen-2.5-72b', 'qwen-2.5-coder-32b', 'llama-3.3-70b', 'mistral-nemo', 'deepseek-chat', 'llama-3.1-8b', 'gpt-4o-vision', 'gpt-4o-mini-vision', 'deepseek-r1', 'sdxl-turbo', 'flux'], 
    OIVSCode: ['gpt-4o-mini'],
    ImageLabs: ['sdxl-turbo'], 
    TeachAnything: ['llama-3.1-70b'],
    PerplexityLabs:['sonar', 'sonar-pro', 'sonar-reasoning'],
    BlackboxAPI:['deepseek-v3', 'deepseek-r1', 'deepseek-chat', 'mixtral-small-28b', 'dbrx-instruct', 'qwq-32b', 'hermes-2-dpo'],
    CablyAI:['o3-mini-low', 'gpt-4o-mini', 'deepseek-r1', 'deepseek-v3' ],
    Liaobots:['gpt-4o-mini', 'gpt-4o', 'gpt-4', 'o1-preview', 'o1-mini', 'deepseek-r1', 'deepseek-v3', 'claude-3-opus', 'claude-3.5-sonnet', 'claude-3-sonnet', 'gemini-2.0-flash', 'gemini-2.0-flash-thinking', 'gemini-1.5-flash', 'gemini-1.5-pro']


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

chat_providers = [DDG,Blackbox, BlackboxAPI, CablyAI, Glider, HuggingSpace, PerplexityLabs, TeachAnything, PollinationsAI, OIVSCode, DeepInfraChat, ImageLabs]
image_providers = [Blackbox, PollinationsAI, OIVSCode]
web_search_providers = [Blackbox]

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
    model_name = "llama-3.1-70b"  # Фиксированная модель для улучшения промпта
    enhanced_chat_providers = get_supported_providers(chat_providers, model_name)
    enhanced_image_providers = get_supported_providers(image_providers, model_name)
    enhance_prompt_client = Client(
        provider=RetryProvider(enhanced_chat_providers, shuffle=False),
        image_provider=RetryProvider(enhanced_image_providers, shuffle=False)
    )
    logging.info("Enhance prompt client initialized with model 'llama-3.1-70b'")


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