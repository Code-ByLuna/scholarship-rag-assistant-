"""Deployment regression checks: isolation, proxy/CORS, integrity and cache layout."""

import hashlib
import shutil
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.db import OperationalError
from django.test import Client, override_settings

from scripts.provision_rag_assets import (
    ROOT,
    download_model,
    load_manifest,
    validate_index,
    validate_model_files,
)


def test_liveness_has_no_database_or_generation_dependency(monkeypatch):
    connection = Mock()
    connection.cursor.side_effect = OperationalError("synthetic unavailable database")
    monkeypatch.setattr("api.health.connection", connection)
    monkeypatch.setattr(
        "core.llm.grounded_generation", Mock(side_effect=AssertionError("Unexpected Gemini call"))
    )
    response = Client().get("/api/health/live")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    connection.cursor.assert_not_called()
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_readiness_checks_index_and_local_model_without_gemini(monkeypatch):
    version = load_manifest()["index_version"]
    monkeypatch.setattr(
        "core.rag.retrieval.index_status", lambda: {"ready": True, "version": version}
    )
    monkeypatch.setattr(
        "core.rag.retrieval.load_store",
        lambda version: SimpleNamespace(vectors=SimpleNamespace(shape=(139, 384))),
    )
    model = Mock()
    model.get_sentence_embedding_dimension.return_value = 384
    loader = Mock(return_value=model)
    monkeypatch.setattr("core.rag.embeddings.get_model", loader)
    monkeypatch.setattr(
        "core.llm.grounded_generation", Mock(side_effect=AssertionError("Unexpected Gemini call"))
    )
    response = Client().get("/api/health/ready")
    assert response.status_code == 200
    assert all(response.json()["checks"].values())
    assert response.json()["errors"] == []
    assert loader.call_args.kwargs.get("allow_download", False) is False


@pytest.mark.django_db
def test_readiness_failed_dependencies_are_sanitized(monkeypatch):
    connection = Mock()
    connection.cursor.side_effect = OperationalError("synthetic private connection details")
    monkeypatch.setattr("api.health.connection", connection)
    monkeypatch.setattr("core.rag.retrieval.index_status", lambda: {"ready": True, "version": "v"})
    monkeypatch.setattr(
        "core.rag.retrieval.load_store",
        Mock(side_effect=ValueError("synthetic file integrity details")),
    )
    monkeypatch.setattr(
        "core.rag.embeddings.get_model", Mock(side_effect=OSError("synthetic cache details"))
    )
    response = Client().get("/api/health/ready")
    assert response.status_code == 503
    assert set(response.json()["errors"]) == {
        "DATABASE_UNAVAILABLE",
        "VECTOR_UNAVAILABLE",
        "EMBEDDING_UNAVAILABLE",
    }
    assert "synthetic" not in response.content.decode()


def test_https_proxy_and_vercel_session_header_preflight():
    origin = "https://frontend-test.example"
    with override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        CORS_ALLOWED_ORIGINS=[origin],
    ):
        client = Client()
        secure = client.get("/api/health/live", HTTP_X_FORWARDED_PROTO="https")
        assert secure.status_code == 200 and "Location" not in secure
        assert client.get("/api/health/live").status_code == 301
        preflight = client.options(
            "/api/agent/query",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-session-token,x-request-id",
        )
        assert preflight.status_code == 200
        assert preflight["Access-Control-Allow-Origin"] == origin
        assert all(
            header in preflight["Access-Control-Allow-Headers"]
            for header in ("x-session-token", "x-request-id")
        )
        denied = client.options(
            "/api/agent/query",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_ORIGIN="https://untrusted-test.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert "Access-Control-Allow-Origin" not in denied


def test_collected_static_files_can_be_served_without_frontend_nginx(tmp_path, settings):
    path = tmp_path / "admin/css/base.css"
    path.parent.mkdir(parents=True)
    path.write_text("body { color: black; }")
    middleware = list(settings.MIDDLEWARE)
    middleware.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
    with override_settings(
        MIDDLEWARE=middleware,
        STATIC_ROOT=tmp_path,
        DEBUG=False,
        WHITENOISE_AUTOREFRESH=False,
        WHITENOISE_USE_FINDERS=False,
        SECURE_SSL_REDIRECT=False,
    ):
        response = Client().get("/static/admin/css/base.css")
        assert response.status_code == 200
        assert b"color: black" in b"".join(response.streaming_content)


def test_packaged_index_is_valid_and_tampering_is_rejected(tmp_path):
    manifest = load_manifest()
    for name in manifest["index_files"]:
        destination = tmp_path / "var/index" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "var/index" / name, destination)
    (tmp_path / "data").mkdir()
    shutil.copyfile(
        ROOT / "data/scholarship_dataset_ready.json",
        tmp_path / "data/scholarship_dataset_ready.json",
    )
    validate_index(manifest, tmp_path)
    vectors = tmp_path / "var/index" / manifest["index_version"] / "vectors.faiss"
    vectors.write_bytes(vectors.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_index(manifest, tmp_path)


def test_model_validation_accepts_linux_blob_layout_and_rejects_escape(tmp_path):
    cache = tmp_path / "model"
    snapshot = cache / "snapshots" / ("a" * 40)
    snapshot.mkdir(parents=True)
    blob = cache / "blobs/weights"
    blob.parent.mkdir()
    blob.write_bytes(b"synthetic weights")
    try:
        (snapshot / "model.safetensors").symlink_to(blob)
    except OSError:
        # Windows without symlink privilege still verifies the copied-file path;
        # on Linux the same test exercises the actual HF cache symlink layout.
        shutil.copyfile(blob, snapshot / "model.safetensors")
    manifest = {"model_files": {"model.safetensors": hashlib.sha256(blob.read_bytes()).hexdigest()}}
    validate_model_files(manifest, snapshot)
    malicious = deepcopy(manifest)
    malicious["model_files"] = {"../../../outside": "0" * 64}
    with pytest.raises(ValueError, match="Unsafe"):
        validate_model_files(malicious, snapshot)


def test_model_download_uses_pinned_revision_and_updates_offline_reference(tmp_path, monkeypatch):
    revision = "a" * 40
    snapshot = tmp_path / "snapshots" / revision
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_bytes(b"{}")
    manifest = {
        "embedding_model": "public/test",
        "embedding_revision": revision,
        "model_files": {"config.json": hashlib.sha256(b"{}").hexdigest()},
    }
    downloader = Mock(return_value=str(snapshot))
    monkeypatch.setattr("huggingface_hub.snapshot_download", downloader)
    monkeypatch.setattr("scripts.provision_rag_assets.model_cache", lambda manifest: tmp_path)
    download_model(manifest)
    assert downloader.call_args.kwargs["revision"] == revision
    assert downloader.call_args.kwargs["allow_patterns"] == ["config.json"]
    assert (tmp_path / "refs/main").read_text() == revision


@pytest.mark.django_db
def test_readiness_detects_missing_files_even_with_a_cached_store(tmp_path, monkeypatch):
    version = "a" * 32
    bundle = tmp_path / version
    bundle.mkdir()
    for name in ("vectors.faiss", "chunks.json", "metadata.json"):
        (bundle / name).write_bytes(b"test file")
    monkeypatch.setattr("core.rag.retrieval.index_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "core.rag.retrieval.index_status", lambda: {"ready": True, "version": version}
    )
    loader = Mock(return_value=SimpleNamespace(vectors=SimpleNamespace(shape=(139, 384))))
    monkeypatch.setattr("core.rag.retrieval.load_store", loader)
    model = Mock()
    model.get_sentence_embedding_dimension.return_value = 384
    monkeypatch.setattr("core.rag.embeddings.get_model", lambda *args: model)
    assert Client().get("/api/health/ready").status_code == 200
    (bundle / "vectors.faiss").unlink()
    response = Client().get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["vector_index"] is False
    assert "VECTOR_UNAVAILABLE" in response.json()["errors"]
    assert loader.call_count == 1
