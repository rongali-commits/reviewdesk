from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_and_public_pages(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["product"] == "ReviewDesk"
    assert client.get("/").status_code == 200
    assert client.get("/admin").status_code == 200
    assert client.get("/wall").status_code == 200


def test_complete_feedback_workflow(
    client: TestClient, admin_headers: dict[str, str], contact_payload: dict[str, object]
) -> None:
    created = client.post("/api/admin/contacts", headers=admin_headers, json=contact_payload)
    assert created.status_code == 201
    contact = created.json()["contact"]
    assert created.json()["review_url"].endswith(contact["token"])

    context = client.get(f"/api/review/{contact['token']}")
    assert context.status_code == 200
    assert context.json()["name"] == "Taylor Morgan"

    feedback = client.post(
        f"/api/review/{contact['token']}/feedback",
        json={
            "rating": 4,
            "comment": "Helpful service and clear communication.",
            "display_name": "Taylor Morgan",
            "testimonial_consent": True,
            "website": "",
        },
    )
    assert feedback.status_code == 201
    assert feedback.json()["public_review_url"] == "/demo/public"

    duplicate = client.post(
        f"/api/review/{contact['token']}/feedback",
        json={
            "rating": 5,
            "comment": "Submitting twice should not be allowed.",
            "display_name": "Taylor Morgan",
            "testimonial_consent": True,
            "website": "",
        },
    )
    assert duplicate.status_code == 409

    overview = client.get("/api/admin/overview", headers=admin_headers).json()
    assert overview["metrics"]["responded"] == 1
    assert overview["metrics"]["average_rating"] == 4.0


def test_requests_stop_after_feedback(
    client: TestClient, admin_headers: dict[str, str], contact_payload: dict[str, object]
) -> None:
    contact = client.post(
        "/api/admin/contacts", headers=admin_headers, json=contact_payload
    ).json()["contact"]
    result = client.post(
        f"/api/review/{contact['token']}/feedback",
        json={
            "rating": 3,
            "comment": "The wait was longer than expected.",
            "display_name": "Taylor Morgan",
            "testimonial_consent": False,
            "website": "",
        },
    )
    assert result.status_code == 201
    processed = client.post("/api/admin/process", headers=admin_headers).json()
    assert processed["processed"] == 0


def test_testimonial_requires_consent(
    client: TestClient, admin_headers: dict[str, str], contact_payload: dict[str, object]
) -> None:
    contact = client.post(
        "/api/admin/contacts", headers=admin_headers, json=contact_payload
    ).json()["contact"]
    client.post(
        f"/api/review/{contact['token']}/feedback",
        json={
            "rating": 2,
            "comment": "Private feedback only.",
            "display_name": "Taylor Morgan",
            "testimonial_consent": False,
            "website": "",
        },
    )
    item = client.get("/api/admin/feedback", headers=admin_headers).json()["items"][0]
    featured = client.put(
        f"/api/admin/feedback/{item['id']}",
        headers=admin_headers,
        json={"featured": True},
    ).json()["feedback"]
    assert featured["featured"] is False
    assert client.get("/api/testimonials").json()["items"] == []


def test_webhook_authentication_and_creation(
    client: TestClient, webhook_headers: dict[str, str], contact_payload: dict[str, object]
) -> None:
    assert client.post(
        "/api/webhooks/customers",
        json={"event": "job.completed", "customer": contact_payload},
    ).status_code == 401
    response = client.post(
        "/api/webhooks/customers",
        headers=webhook_headers,
        json={"event": "job.completed", "customer": contact_payload},
    )
    assert response.status_code == 201


def test_admin_is_private(client: TestClient) -> None:
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get(
        "/api/admin/overview", headers={"X-Admin-Token": "reviewdesk-demo-view"}
    ).status_code == 401


def test_demo_submission_is_not_persisted(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/demo-feedback",
        json={
            "rating": 5,
            "comment": "A polished and clear demo.",
            "display_name": "Demo Visitor",
            "testimonial_consent": True,
            "website": "",
        },
    )
    assert response.status_code == 201
    assert response.json()["demo"] is True
    overview = client.get("/api/admin/overview", headers=admin_headers).json()
    assert overview["metrics"]["contacts"] == 0


def test_honeypot_rejects_automated_submission(client: TestClient) -> None:
    response = client.post(
        "/api/demo-feedback",
        json={
            "rating": 5,
            "comment": "Bot submission",
            "display_name": "Fake User",
            "testimonial_consent": True,
            "website": "https://spam.example",
        },
    )
    assert response.status_code == 422
