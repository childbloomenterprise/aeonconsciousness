class Ahamkara:
    def bind(
        self,
        continuity_id: str,
        provider: str,
        memory_refs: list[str],
        response_id: str | None = None,
    ) -> dict[str, object]:
        return {
            "continuity_owner": continuity_id,
            "response_owner": "AEON cognitive runtime",
            "provider_role": f"{provider} reasoning organ",
            "provider_is_self": False,
            "memory_ownership": {memory_id: "AEON persisted history" for memory_id in memory_refs},
            "external_actions_claimed": False,
            "provider_response_id": response_id,
        }
