import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from adventures.models import Collection, CollectionItineraryItem
from chat.agent_tools import add_to_itinerary, get_trip_details
from chat.views import ChatViewSet


User = get_user_model()


class ChatAgentToolSharedTripAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="chat-owner",
            email="chat-owner@example.com",
            password="password123",
        )
        self.shared_user = User.objects.create_user(
            username="chat-shared",
            email="chat-shared@example.com",
            password="password123",
        )
        self.non_member = User.objects.create_user(
            username="chat-non-member",
            email="chat-non-member@example.com",
            password="password123",
        )
        self.collection = Collection.objects.create(
            user=self.owner,
            name="Shared Trip",
        )
        self.collection.shared_with.add(self.shared_user)

    def test_get_trip_details_allows_owner_access(self):
        result = get_trip_details(self.owner, collection_id=str(self.collection.id))

        self.assertIn("trip", result)
        self.assertEqual(result["trip"]["id"], str(self.collection.id))
        self.assertEqual(result["trip"]["name"], self.collection.name)

    def test_get_trip_details_allows_shared_user_access(self):
        result = get_trip_details(
            self.shared_user, collection_id=str(self.collection.id)
        )

        self.assertIn("trip", result)
        self.assertEqual(result["trip"]["id"], str(self.collection.id))

    def test_get_trip_details_owner_also_in_shared_with_avoids_duplicates(self):
        self.collection.shared_with.add(self.owner)

        result = get_trip_details(self.owner, collection_id=str(self.collection.id))

        self.assertIn("trip", result)
        self.assertEqual(result["trip"]["id"], str(self.collection.id))

    @patch("adventures.models.background_geocode_and_assign")
    def test_add_to_itinerary_allows_shared_user_access(self, _mock_background_geocode):
        result = add_to_itinerary(
            self.shared_user,
            collection_id=str(self.collection.id),
            name="Eiffel Tower",
            latitude=48.85837,
            longitude=2.294481,
        )

        self.assertTrue(result.get("success"))
        self.assertEqual(result["location"]["name"], "Eiffel Tower")
        self.assertTrue(
            CollectionItineraryItem.objects.filter(
                id=result["itinerary_item"]["id"],
                collection=self.collection,
            ).exists()
        )

    @patch("adventures.models.background_geocode_and_assign")
    def test_add_to_itinerary_owner_also_in_shared_with_avoids_duplicates(
        self,
        _mock_background_geocode,
    ):
        self.collection.shared_with.add(self.owner)

        result = add_to_itinerary(
            self.owner,
            collection_id=str(self.collection.id),
            name="Louvre Museum",
            latitude=48.860611,
            longitude=2.337644,
        )

        self.assertTrue(result.get("success"))
        self.assertEqual(result["location"]["name"], "Louvre Museum")

    @patch("adventures.models.background_geocode_and_assign")
    def test_non_member_access_remains_denied(self, _mock_background_geocode):
        trip_result = get_trip_details(
            self.non_member,
            collection_id=str(self.collection.id),
        )
        itinerary_result = add_to_itinerary(
            self.non_member,
            collection_id=str(self.collection.id),
            name="Should Fail",
            latitude=48.85837,
            longitude=2.294481,
        )

        self.assertEqual(
            trip_result,
            {
                "error": "collection_id is required and must reference a trip you can access"
            },
        )
        self.assertEqual(itinerary_result, {"error": "Trip not found"})


class ChatViewSetToolValidationBoundaryTests(TestCase):
    def test_dates_is_required_matches_required_param_short_circuit(self):
        self.assertTrue(
            ChatViewSet._is_required_param_tool_error({"error": "dates is required"})
        )

    def test_dates_non_empty_list_error_does_not_match_required_param_short_circuit(
        self,
    ):
        self.assertFalse(
            ChatViewSet._is_required_param_tool_error(
                {"error": "dates must be a non-empty list"}
            )
        )

    def test_collection_access_error_does_not_short_circuit_required_param_regex(self):
        error_text = (
            "collection_id is required and must reference a trip you can access"
        )

        self.assertFalse(
            ChatViewSet._is_required_param_tool_error({"error": error_text})
        )
        self.assertFalse(
            ChatViewSet._is_required_param_tool_error_message_content(
                json.dumps({"error": error_text})
            )
        )
