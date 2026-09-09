"""Only synthetic credentials are used; provider diagnostics never need real keys."""
import io
import json
import sys
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

import article
import chat
import image
import video
import voidscape


SECRET = "SYNTHETIC_PRIVATE_VALUE"


@pytest.mark.parametrize("message", [
    f"request https://user:{SECRET}@example.com/api?key={SECRET}#fragment-{SECRET}",
    f"request https://example.com/api?opaque={SECRET}",
    f"Authorization: Bearer {SECRET}",
    f"Proxy-Authorization: Basic {SECRET}",
    f'{{"Authorization": "Bearer {SECRET}"}}',
    f'{{"api_key": "{SECRET}"}}',
    f"{{'access_token': '{SECRET}'}}",
    f"OPENAI_API_KEY={SECRET}",
    f"api-key = {SECRET}",
    f"refresh_token: {SECRET}",
    f"password={SECRET}",
    f"secret='{SECRET}'",
    f"Bearer {SECRET}",
    f"sk-{SECRET}",
    f"gsk_{SECRET}",
    "hf_SYNTHETICPRIVATEVALUE",
])
def test_recognizable_credential_forms_are_redacted(message):
    result = video.sanitize_error(message)
    assert SECRET not in result
    assert "SYNTHETICPRIVATEVALUE" not in result
    assert result != message


def test_safe_diagnostics_and_environment_names_survive():
    message = "GROQ_API_KEY not set; HTTP 429 rate limit; https://example.com/api"
    assert video.sanitize_error(message) == message


@pytest.mark.parametrize("module", [video, image, article, chat])
@pytest.mark.parametrize("envelope", [False, True])
def test_all_reader_cli_errors_are_sanitized(module, envelope, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError(f"failed token={SECRET}")

    monkeypatch.setattr(module, "run", fail)
    args = ["run", "unused"] + (["--envelope"] if envelope else [])
    assert module.main(args) == 6
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err
    output = json.loads(captured.out)
    assert "[REDACTED_SECRET]" in (output["error"]["message"] if envelope else output["error"])


@pytest.mark.parametrize("as_json", [False, True])
def test_guided_error_output_is_sanitized(capsys, as_json):
    assert voidscape._print_error(RuntimeError(f"api_key={SECRET}"), as_json) == 6
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err
    assert "[REDACTED_SECRET]" in captured.out + captured.err


def test_backend_fallback_sanitizes_before_truncating(tmp_path, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError("prefix " * 15 + f"token={SECRET}")

    monkeypatch.setattr(video, "_transcribe_one", fail)
    with pytest.raises(video.BackendFailures) as caught:
        video._transcribe("unused", {}, None, tmp_path, "groq,openai")
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err + str(caught.value)
    assert "SYNTHETIC" not in captured.err


def test_chunk_gap_and_log_are_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(video, "_split_audio", lambda *args: [("one", 0), ("two", 5)])

    def request(backend, path):
        if path == "two":
            raise RuntimeError(f"Authorization: Bearer {SECRET}")
        return {"text": "source speech"}

    monkeypatch.setattr(video, "_api_request", request)
    transcript = video._api_transcribe("groq", "unused")
    assert "source speech" in transcript
    assert SECRET not in transcript + capsys.readouterr().err


def test_http_rejection_body_is_not_read_or_echoed(monkeypatch):
    class Body(io.BytesIO):
        def read(self, *args):
            pytest.fail("provider rejection body must not be read")

    def reject(*args, **kwargs):
        raise HTTPError("https://example.com", 401, "Unauthorized", {}, Body(SECRET.encode()))

    monkeypatch.setattr(video.os.environ, "get", lambda *args: "synthetic-configured-key")
    monkeypatch.setattr(video, "_build_multipart", lambda *args: (b"", "boundary"))
    monkeypatch.setattr(video, "urlopen", reject)
    with pytest.raises(RuntimeError) as caught:
        video._api_request("groq", "unused")
    assert "HTTP 401" in str(caught.value)
    assert "body omitted" in str(caught.value)
    assert SECRET not in str(caught.value)


def test_transport_reason_cannot_echo_an_opaque_secret(monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise URLError(SECRET)

    monkeypatch.setattr(video.os.environ, "get", lambda *args: "synthetic-configured-key")
    monkeypatch.setattr(video, "_build_multipart", lambda *args: (b"", "boundary"))
    monkeypatch.setattr(video, "urlopen", fail)
    monkeypatch.setattr(video, "_MAX_ATTEMPTS", 1)
    with pytest.raises(RuntimeError) as caught:
        video._api_request("groq", "unused")
    assert "network request failed" in str(caught.value)
    assert SECRET not in str(caught.value) + capsys.readouterr().err


@pytest.mark.parametrize("original", [RuntimeError(f"429 rate limit {SECRET}"), ValueError(SECRET), OSError(SECRET)])
def test_gemini_omits_provider_detail_preserving_classification(monkeypatch, original):
    def client(**kwargs):
        raise original

    monkeypatch.setattr(video.os.environ, "get", lambda *args: "synthetic-configured-key")
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=SimpleNamespace(Client=client)))
    with pytest.raises(video.ProviderFailure) as caught:
        video._gemini("unused.wav")
    assert video._classify_error(caught.value) == video._classify_error(original)
    assert SECRET not in str(caught.value)
    assert caught.value.__suppress_context__ is True
    previous_aggregate = RuntimeError(f"gemini: {type(original).__name__}: {str(original)[:140]}")
    aggregate = video.BackendFailures(str(caught.value), [caught.value])
    assert video._classify_error(aggregate) == video._classify_error(previous_aggregate)


def test_source_transcript_is_not_rewritten_by_error_sanitizer():
    source = f"A quoted example: token={SECRET}"
    assert video._resp_to_text({"text": source}) == source


def test_gemini_response_property_errors_are_also_private(monkeypatch):
    class Response:
        @property
        def text(self):
            raise RuntimeError(SECRET)

    client = SimpleNamespace(files=SimpleNamespace(upload=lambda **kwargs: object()),
                             models=SimpleNamespace(generate_content=lambda **kwargs: Response()))
    monkeypatch.setattr(video.os.environ, "get", lambda *args: "synthetic-configured-key")
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=SimpleNamespace(Client=lambda **kwargs: client)))
    with pytest.raises(video.ProviderFailure) as caught:
        video._gemini("unused.wav")
    assert SECRET not in str(caught.value)
