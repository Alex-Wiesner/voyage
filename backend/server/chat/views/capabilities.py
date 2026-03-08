from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.agent_tools import get_tool_schemas


class CapabilitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return available AI capabilities/tools."""
        tools = get_tool_schemas()
        return Response(
            {
                "tools": [
                    {
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                    }
                    for tool in tools
                ]
            }
        )
