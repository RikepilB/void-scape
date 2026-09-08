"""preview and read must agree on which backends can actually run.

A backend the read path would refuse must never be priced as runnable. That is the cost gate
lying in the dangerous direction: an agent checks the gate, is told free and installed, and the
run then fails.
"""
import pytest

import video


def test_known_backends_are_exactly_what_the_read_path_dispatches():
    """`_transcribe_one` branches on these names; the set must not drift from them."""
    assert video.KNOWN_BACKENDS == frozenset({
        "captions", "faster-whisper", "local", "trx", "gemini",
        "groq", "openai", "openai-mini", "openrouter",
    })
    # Every API backend is dispatchable, so every API backend must be known.
    assert set(video.BACKEND_API) <= video.KNOWN_BACKENDS
    assert video.CLOUD_BACKENDS <= video.KNOWN_BACKENDS


@pytest.mark.parametrize("backend", sorted({
    "captions", "faster-whisper", "local", "trx", "gemini",
    "groq", "openai", "openai-mini", "openrouter",
}))
def test_every_known_backend_validates(backend):
    assert video.validate_backend_chain(backend) == [backend]


def test_an_empty_backend_short_circuits_rather_than_raising():
    """An empty string means "no backend requested" and is handled by the caller, not here."""
    assert video.validate_backend_chain("") == []


@pytest.mark.parametrize("backend", ["whisper-cpp", "fastr-whisper", "whisper", "  "])
def test_an_unknown_backend_is_refused_and_names_the_alternatives(backend):
    with pytest.raises(ValueError) as excinfo:
        video.validate_backend_chain(backend)
    message = str(excinfo.value)
    assert backend.strip() in message
    assert "faster-whisper" in message          # names a real option
    assert "references/backends.md" in message  # points at the setup doc


def test_a_chain_is_validated_per_element():
    assert video.validate_backend_chain("openrouter,groq") == ["openrouter", "groq"]
    with pytest.raises(ValueError, match="whisper-cpp"):
        video.validate_backend_chain("faster-whisper,whisper-cpp")


def test_an_unknown_backend_is_never_reported_available():
    """The old default returned True for anything unrecognised, which is what made the gate lie."""
    assert video._have_local_backend("whisper-cpp") is False
    assert video._have_local_backend("fastr-whisper") is False
    # A known cloud backend needs no local install, so it stays available.
    assert video._have_local_backend("groq") is True
