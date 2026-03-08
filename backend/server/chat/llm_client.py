import json
import logging

import litellm

from integrations.models import UserAPIKey

logger = logging.getLogger(__name__)

CHAT_PROVIDER_CONFIG = {
    "openai": {
        "label": "OpenAI",
        "needs_api_key": True,
        "default_model": "gpt-4o",
        "api_base": None,
    },
    "anthropic": {
        "label": "Anthropic",
        "needs_api_key": True,
        "default_model": "anthropic/claude-sonnet-4-20250514",
        "api_base": None,
    },
    "gemini": {
        "label": "Google Gemini",
        "needs_api_key": True,
        "default_model": "gemini/gemini-2.0-flash",
        "api_base": None,
    },
    "ollama": {
        "label": "Ollama",
        "needs_api_key": True,
        "default_model": "ollama/llama3.1",
        "api_base": None,
    },
    "groq": {
        "label": "Groq",
        "needs_api_key": True,
        "default_model": "groq/llama-3.3-70b-versatile",
        "api_base": None,
    },
    "mistral": {
        "label": "Mistral",
        "needs_api_key": True,
        "default_model": "mistral/mistral-large-latest",
        "api_base": None,
    },
    "github_models": {
        "label": "GitHub Models",
        "needs_api_key": True,
        "default_model": "github/gpt-4o",
        "api_base": None,
    },
    "openrouter": {
        "label": "OpenRouter",
        "needs_api_key": True,
        "default_model": "openrouter/auto",
        "api_base": None,
    },
    "opencode_zen": {
        "label": "OpenCode Zen",
        "needs_api_key": True,
        "default_model": "openai/gpt-4o-mini",
        "api_base": "https://opencode.ai/zen/v1",
    },
}


def _safe_get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize_provider_id(provider_id):
    value = str(provider_id or "").strip()
    lowered = value.lower()
    if lowered.startswith("llmproviders."):
        return lowered.split(".", 1)[1]
    return lowered


def _default_provider_label(provider_id):
    return provider_id.replace("_", " ").title()


def is_chat_provider_available(provider_id):
    normalized_provider = _normalize_provider_id(provider_id)
    return normalized_provider in CHAT_PROVIDER_CONFIG


def get_provider_catalog():
    seen = set()
    catalog = []

    for provider_id in getattr(litellm, "provider_list", []):
        normalized_provider = _normalize_provider_id(provider_id)
        if not normalized_provider or normalized_provider in seen:
            continue

        seen.add(normalized_provider)
        provider_config = CHAT_PROVIDER_CONFIG.get(normalized_provider)
        if provider_config:
            catalog.append(
                {
                    "id": normalized_provider,
                    "label": provider_config["label"],
                    "available_for_chat": True,
                    "needs_api_key": provider_config["needs_api_key"],
                    "default_model": provider_config["default_model"],
                    "api_base": provider_config["api_base"],
                }
            )
            continue

        catalog.append(
            {
                "id": normalized_provider,
                "label": _default_provider_label(normalized_provider),
                "available_for_chat": False,
                "needs_api_key": None,
                "default_model": None,
                "api_base": None,
            }
        )

    # Include app-supported OpenAI-compatible aliases that are not part of
    # LiteLLM's native provider list (for example OpenCode Zen).
    for provider_id, provider_config in CHAT_PROVIDER_CONFIG.items():
        normalized_provider = _normalize_provider_id(provider_id)
        if not normalized_provider or normalized_provider in seen:
            continue

        seen.add(normalized_provider)
        catalog.append(
            {
                "id": normalized_provider,
                "label": provider_config["label"],
                "available_for_chat": True,
                "needs_api_key": provider_config["needs_api_key"],
                "default_model": provider_config["default_model"],
                "api_base": provider_config["api_base"],
            }
        )

    return catalog


def get_llm_api_key(user, provider):
    """Get the user's API key for the given provider."""
    normalized_provider = _normalize_provider_id(provider)
    try:
        key_obj = UserAPIKey.objects.get(user=user, provider=normalized_provider)
        return key_obj.get_api_key()
    except UserAPIKey.DoesNotExist:
        return None


def get_system_prompt(user, collection=None):
    """Build the system prompt with user context."""
    from integrations.models import UserRecommendationPreferenceProfile

    base_prompt = """You are a helpful travel planning assistant for the Voyage travel app. You help users discover places, plan trips, and organize their itineraries.

Your capabilities:
- Search for interesting places (restaurants, tourist attractions, hotels) near any location
- View and manage the user's trip collections and itineraries
- Add new locations to trip itineraries
- Check weather/temperature data for travel dates

When suggesting places:
- Be specific with names, addresses, and why a place is worth visiting
- Consider the user's travel dates and weather conditions
- Group suggestions logically (by area, by type, by day)

When modifying itineraries:
- Always confirm with the user before adding items
- Suggest logical ordering based on geography
- Consider travel time between locations

Be conversational, helpful, and enthusiastic about travel. Keep responses concise but informative."""

    try:
        profile = UserRecommendationPreferenceProfile.objects.get(user=user)
        prefs = []
        if profile.cuisines:
            prefs.append(f"Cuisine preferences: {profile.cuisines}")
        if profile.interests:
            prefs.append(f"Interests: {profile.interests}")
        if profile.trip_style:
            prefs.append(f"Travel style: {profile.trip_style}")
        if profile.notes:
            prefs.append(f"Additional notes: {profile.notes}")
        if prefs:
            base_prompt += "\n\nUser preferences:\n" + "\n".join(prefs)
    except UserRecommendationPreferenceProfile.DoesNotExist:
        pass

    return base_prompt


async def stream_chat_completion(user, messages, provider, tools=None):
    """Stream a chat completion using LiteLLM.

    Yields SSE-formatted strings.
    """
    normalized_provider = _normalize_provider_id(provider)
    provider_config = CHAT_PROVIDER_CONFIG.get(normalized_provider)
    if not provider_config:
        payload = {
            "error": f"Provider is not available for chat: {normalized_provider}."
        }
        yield f"data: {json.dumps(payload)}\n\n"
        return

    api_key = get_llm_api_key(user, normalized_provider)
    if provider_config["needs_api_key"] and not api_key:
        payload = {
            "error": f"No API key found for provider: {normalized_provider}. Please add one in Settings."
        }
        yield f"data: {json.dumps(payload)}\n\n"
        return

    completion_kwargs = {
        "model": provider_config["default_model"],
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto" if tools else None,
        "stream": True,
        "api_key": api_key,
    }
    if provider_config["api_base"]:
        completion_kwargs["api_base"] = provider_config["api_base"]

    try:
        response = await litellm.acompletion(**completion_kwargs)

        async for chunk in response:
            choices = _safe_get(chunk, "choices", []) or []
            if not choices:
                continue

            delta = _safe_get(choices[0], "delta")
            if not delta:
                continue

            chunk_data = {}
            content = _safe_get(delta, "content")
            if content:
                chunk_data["content"] = content

            tool_calls = _safe_get(delta, "tool_calls") or []
            if tool_calls:
                serialized = []
                for tool_call in tool_calls:
                    function = _safe_get(tool_call, "function")
                    serialized.append(
                        {
                            "id": _safe_get(tool_call, "id"),
                            "type": _safe_get(tool_call, "type"),
                            "function": {
                                "name": _safe_get(function, "name", "") or "",
                                "arguments": _safe_get(function, "arguments", "") or "",
                            },
                        }
                    )
                chunk_data["tool_calls"] = serialized

            if chunk_data:
                yield f"data: {json.dumps(chunk_data)}\n\n"

        yield "data: [DONE]\n\n"
    except Exception:
        logger.exception("LLM streaming error")
        yield f"data: {json.dumps({'error': 'An error occurred while processing your request. Please try again.'})}\n\n"
