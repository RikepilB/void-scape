import json

import video


def test_default_pricing_model_keys_match_pricing_json():
    """DEFAULT_PRICING is the fallback when pricing.json can't be read; it must offer the same
    model choices or --agent-model breaks only on that rarely-exercised path."""
    real = json.loads(video.PRICING_PATH.read_text(encoding="utf-8"))
    assert (set(video.DEFAULT_PRICING["model_per_mtok"]) ==
            set(real["model_per_mtok"]))


def fake_probe_info():
    return {"source": "local", "input": "x.mp4", "sidecar_transcript": None,
            "captions_available": False, "duration_s": 120.0, "width": 640,
            "height": 360, "fps": 30.0, "has_audio": True}


def patched_estimate(monkeypatch, **kw):
    monkeypatch.setattr(video, "probe", lambda inp: fake_probe_info())
    return video.estimate("x.mp4", pr=video.DEFAULT_PRICING, **kw)


def test_cost_math_regression(monkeypatch):
    """Pins GPT-5.6 patch accounting: 512x288 becomes 16x9 patches."""
    o = patched_estimate(monkeypatch)
    assert o["frames"] == 60                       # adaptive_frames(120)
    assert o["per_frame_tokens"] == 144            # ceil(512/32) * ceil(288/32)
    assert o["tokens"]["frames"] == 60 * 144
    assert o["tokens"]["transcript"] == 400        # 2 min * 200
    assert o["tokens"]["output"] == 798            # 600 words * 1.33
    assert o["cost_usd"]["transcription"] == 0.0
    assert o["free"] is True
    assert o["agent_model"] == "gpt-5.6-terra"
    assert o["vision_estimator"] == "openai_patch32"
    assert "API-equivalent" in o["cost_basis"]


def test_custom_legacy_pixel_estimator_is_supported(monkeypatch):
    pricing = {**video.DEFAULT_PRICING, "model_per_mtok": {
        **video.DEFAULT_PRICING["model_per_mtok"],
        "legacy-test": {"input": 1.0, "output": 1.0,
                        "vision_estimator": "legacy_pixels_750"},
    }}
    monkeypatch.setattr(video, "probe", lambda inp: fake_probe_info())
    o = video.estimate("x.mp4", pr=pricing, agent_model="legacy-test")
    assert o["per_frame_tokens"] == 197
    assert o["vision_estimator"] == "legacy_pixels_750"


def test_unknown_agent_model_is_rejected(monkeypatch):
    import pytest

    with pytest.raises(ValueError, match="unknown agent model"):
        patched_estimate(monkeypatch, agent_model="gpt-9")


def test_estimate_notes_dedup_for_visual_tiers(monkeypatch):
    assert "dedup" in patched_estimate(monkeypatch)["note"]
    assert "dedup" in patched_estimate(monkeypatch, tier="visual")["note"]
    assert "note" not in patched_estimate(monkeypatch, tier="audio")

def test_estimate_ignores_cloud_chain_when_sidecar_resolves_for_free(monkeypatch):
    """A sidecar transcript short-circuits _transcribe() before the chain is ever consulted, so
    naming a cloud backend as a fallback preference must not inflate the cost gate."""
    monkeypatch.setattr(video, "probe", lambda inp: {**fake_probe_info(),
                                                     "sidecar_transcript": "clip.srt"})
    o = video.estimate("x.mp4", pr=video.DEFAULT_PRICING, tier="audio", backend="groq")
    assert o["requires_cloud_approval"] is False
    assert o["cost_usd"]["transcription"] == 0.0
    assert o["free"] is True


def test_estimate_prices_most_expensive_backend_in_chain(monkeypatch):
    o = patched_estimate(monkeypatch, tier="audio", backend="captions,openai")
    assert o["cost_usd"]["transcription"] == 0.012
    assert o["free"] is False
    assert o["requires_cloud_approval"] is True


def test_estimate_marks_missing_local_backend_anywhere_in_chain(monkeypatch):
    monkeypatch.setattr(video, "_have_local_backend", lambda backend: False)
    o = patched_estimate(monkeypatch, tier="audio", backend="captions,faster-whisper")
    assert o["needs_install"] is True
    assert o["model_download"]["status"] == "dependency_missing"


def test_cli_omitted_agent_model_falls_through_to_pricing_json_active(monkeypatch, capsys):
    """--agent-model must default to None on the CLI, not a hardcoded literal, or editing
    pricing.json's _active would have no effect for a plain `estimate` invocation."""
    custom_pricing = {**video.DEFAULT_PRICING, "model_per_mtok": {
        **video.DEFAULT_PRICING["model_per_mtok"], "_active": "gpt-5.6-luna",
    }}
    monkeypatch.setattr(video, "probe", lambda inp: fake_probe_info())
    monkeypatch.setattr(video, "load_pricing", lambda: custom_pricing)

    assert video.main(["estimate", "x.mp4"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["agent_model"] == "gpt-5.6-luna"


def test_estimate_surfaces_required_thorough_model_download(monkeypatch):
    monkeypatch.setattr(video, "_have_local_backend", lambda backend: True)
    monkeypatch.setattr(video, "_model_available_locally", lambda model, root=None: False)
    o = patched_estimate(monkeypatch, tier="audio", backend="faster-whisper",
                         transcribe_mode="thorough")
    assert o["transcribe_mode"] == "thorough"
    assert o["needs_model_download"] is True
    assert o["model_download"] == {"status": "required", "model": "medium"}


def test_estimate_reports_cached_when_a_fallback_is_available(monkeypatch):
    """Requested (medium) isn't cached, but the fallback chain (small/base/tiny) has one that
    is -- run() gracefully degrades to it, so estimate() must not demand --allow-model-download."""
    monkeypatch.setattr(video, "_have_local_backend", lambda backend: True)
    monkeypatch.setattr(video, "_model_available_locally",
                        lambda model, root=None: model != "medium")
    o = patched_estimate(monkeypatch, tier="audio", backend="faster-whisper",
                         transcribe_mode="thorough")
    assert o["needs_model_download"] is False
    assert o["model_download"] == {"status": "cached", "model": "medium"}
