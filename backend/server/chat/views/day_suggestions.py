import json
import re

import litellm
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.models import Collection
from chat.agent_tools import search_places
from chat.llm_client import (
    get_llm_api_key,
    get_system_prompt,
    is_chat_provider_available,
)


class DaySuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        collection_id = request.data.get("collection_id")
        date = request.data.get("date")
        category = request.data.get("category")
        filters = request.data.get("filters", {}) or {}
        location_context = request.data.get("location_context", "")

        if not all([collection_id, date, category]):
            return Response(
                {"error": "collection_id, date, and category are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_categories = ["restaurant", "activity", "event", "lodging"]
        if category not in valid_categories:
            return Response(
                {"error": f"category must be one of: {', '.join(valid_categories)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        collection = get_object_or_404(Collection, id=collection_id)
        if (
            collection.user != request.user
            and not collection.shared_with.filter(id=request.user.id).exists()
        ):
            return Response(
                {"error": "You don't have access to this collection"},
                status=status.HTTP_403_FORBIDDEN,
            )

        location = location_context or self._get_collection_location(collection)
        system_prompt = get_system_prompt(request.user, collection)
        provider = "openai"

        if not is_chat_provider_available(provider):
            return Response(
                {
                    "error": "AI suggestions are not available. Please configure an API key."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            places_context = self._get_places_context(request.user, category, location)
            prompt = self._build_prompt(
                category=category,
                filters=filters,
                location=location,
                date=date,
                collection=collection,
                places_context=places_context,
            )

            suggestions = self._get_suggestions_from_llm(
                system_prompt=system_prompt,
                user_prompt=prompt,
                user=request.user,
                provider=provider,
            )
            return Response({"suggestions": suggestions}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Failed to generate suggestions. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_collection_location(self, collection):
        for loc in collection.locations.select_related("city", "country").all():
            if loc.city:
                city_name = getattr(loc.city, "name", str(loc.city))
                country_name = getattr(loc.country, "name", "") if loc.country else ""
                return ", ".join([x for x in [city_name, country_name] if x])
            if loc.location:
                return loc.location
            if loc.name:
                return loc.name
        return "Unknown location"

    def _build_prompt(
        self,
        category,
        filters,
        location,
        date,
        collection,
        places_context="",
    ):
        category_prompts = {
            "restaurant": f"Find restaurant recommendations for {location}",
            "activity": f"Find activity recommendations for {location}",
            "event": f"Find event recommendations for {location} around {date}",
            "lodging": f"Find lodging recommendations for {location}",
        }

        prompt = category_prompts.get(
            category, f"Find {category} recommendations for {location}"
        )

        if filters:
            filter_parts = []
            if filters.get("cuisine_type"):
                filter_parts.append(f"cuisine type: {filters['cuisine_type']}")
            if filters.get("price_range"):
                filter_parts.append(f"price range: {filters['price_range']}")
            if filters.get("dietary"):
                filter_parts.append(f"dietary restrictions: {filters['dietary']}")
            if filters.get("activity_type"):
                filter_parts.append(f"type: {filters['activity_type']}")
            if filters.get("duration"):
                filter_parts.append(f"duration: {filters['duration']}")
            if filters.get("event_type"):
                filter_parts.append(f"event type: {filters['event_type']}")
            if filters.get("lodging_type"):
                filter_parts.append(f"lodging type: {filters['lodging_type']}")
            amenities = filters.get("amenities")
            if isinstance(amenities, list) and amenities:
                filter_parts.append(
                    f"amenities: {', '.join(str(x) for x in amenities)}"
                )

            if filter_parts:
                prompt += f" with these preferences: {', '.join(filter_parts)}"

        prompt += f". The trip date is {date}."

        if collection.start_date or collection.end_date:
            prompt += (
                " Collection trip window: "
                f"{collection.start_date or 'unknown'} to {collection.end_date or 'unknown'}."
            )

        if places_context:
            prompt += f" Nearby place context: {places_context}."

        prompt += (
            " Return 3-5 specific suggestions as a JSON array."
            " Each suggestion should have: name, description, why_fits, category, location, rating, price_level."
            " Return ONLY valid JSON, no markdown, no surrounding text."
        )
        return prompt

    def _get_places_context(self, user, category, location):
        tool_category_map = {
            "restaurant": "food",
            "activity": "tourism",
            "event": "tourism",
            "lodging": "lodging",
        }
        result = search_places(
            user,
            location=location,
            category=tool_category_map.get(category, "tourism"),
            radius=8,
        )
        if result.get("error"):
            return ""

        entries = []
        for place in result.get("results", [])[:5]:
            name = place.get("name")
            address = place.get("address") or ""
            if name:
                entries.append(f"{name} ({address})" if address else name)
        return "; ".join(entries)

    def _get_suggestions_from_llm(self, system_prompt, user_prompt, user, provider):
        api_key = get_llm_api_key(user, provider)
        if not api_key:
            raise ValueError("No API key available")

        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=api_key,
            temperature=0.7,
            max_tokens=1000,
        )

        content = (response.choices[0].message.content or "").strip()
        try:
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            parsed = (
                json.loads(json_match.group())
                if json_match
                else json.loads(content or "[]")
            )
            suggestions = parsed if isinstance(parsed, list) else [parsed]
            return suggestions[:5]
        except json.JSONDecodeError:
            return []
