from app.services.reverse_image_search_service import _extract_candidates
from app.services.volc_ai_search_client import VolcAiSearchClient


def test_reverse_search_sends_only_image_query():
    client = VolcAiSearchClient(
        base_url="https://aisearch.example",
        api_key="token",
        dataset_id="image-dataset",
        search_path="/api/v1/search",
    )
    captured = {}

    def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"search_results": [{"image_id": "img-1", "score": 0.91}]}

    client._post_json = fake_post
    result = client.search("", image_url="https://cdn.example/query.jpg", user_id="u-1")

    assert captured["path"] == "/api/v1/search"
    assert captured["payload"]["query"] == {
        "text": "",
        "image_url": "https://cdn.example/query.jpg",
    }
    assert result.matches == [{"image_id": "img-1", "score": 0.91}]


def test_reverse_match_parser_ignores_metadata_and_normalizes_scores():
    matches = _extract_candidates(
        [
            {"fields": {"image_id": "img-1", "title": "ignored", "score": 91}},
            {"document": {"_id": "img-2", "identity_code": "ignored"}, "score": 0.72},
            {"id": "img-1", "score": 0.4},
        ]
    )

    assert matches == [("img-1", 0.91), ("img-2", 0.72)]
