"""
Demo Mode — HuggingFace Inference API (gratuito)
Fallback quando o utilizador nao tem DeepSeek API Key.
"""
import os
import requests

HF_API_URL = "https://api-inference.huggingface.co/models/"
HF_TOKEN = os.getenv("HF_TOKEN", "")


def call_hf(model_id: str, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
    """Chama HuggingFace Inference API (gratuito)."""
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(model=model_id, token=HF_TOKEN or None)
        response = client.text_generation(
            prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )
        return response if response else "[Demo: resposta vazia]"
    except Exception as e:
        try:
            headers = {}
            if HF_TOKEN:
                headers["Authorization"] = f"Bearer {HF_TOKEN}"
            resp = requests.post(
                f"{HF_API_URL}{model_id}",
                headers=headers,
                json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature, "return_full_text": False}},
                timeout=90,
            )
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0].get("generated_text", "")
            if isinstance(data, dict):
                return data.get("generated_text", "")
            return str(data)[:1000]
        except Exception as e2:
            return f"[Demo: indisponivel. Adiciona DeepSeek API Key em Definicoes para qualidade maxima. Erro: {str(e2)[:80]}]"


DEMO_MODELS = {
    "chat": "mistralai/Mistral-7B-Instruct-v0.3",
    "compose": "mistralai/Mistral-7B-Instruct-v0.3",
    "lyrics": "mistralai/Mistral-7B-Instruct-v0.3",
    "analysis": "microsoft/phi-4",
}


def is_demo_mode(user_deepseek_key: str = "") -> bool:
    """Verifica se esta em modo demo."""
    if user_deepseek_key and user_deepseek_key.startswith("sk-"):
        return False
    return True


def get_llm_client(user_deepseek_key: str = "", use_demo: bool = None):
    """
    Retorna o cliente LLM apropriado.
    Se o utilizador tem DeepSeek key → usa DeepSeek.
    Se nao → usa HuggingFace (demo gratuito).
    """
    if use_demo is None:
        use_demo = is_demo_mode(user_deepseek_key)

    if not use_demo:
        from openai import OpenAI
        return OpenAI(api_key=user_deepseek_key, base_url="https://api.deepseek.com/v1"), "deepseek-chat"

    # Demo mode — HuggingFace
    return None, "demo"
