"""A first-run mistake has to explain itself: where Voidscape looked, and how to fix it."""
import json
import os
import re

import pytest

import article
import image
import video
import voidscape


@pytest.fixture
def no_workspace(monkeypatch, tmp_path):
    """No workspace.json anywhere, which is the state right after `voidscape init`."""
    monkeypatch.setenv("VOIDSCAPE_WORKSPACE_PATH", str(tmp_path / "absent.json"))
    return tmp_path


@pytest.fixture
def inbox_workspace(monkeypatch, tmp_path):
    inbox = tmp_path / "Inbox"
    inbox.mkdir()
    config = tmp_path / "workspace.json"
    config.write_text(json.dumps({"inbox_dir": str(inbox)}), encoding="utf-8")
    monkeypatch.setenv("VOIDSCAPE_WORKSPACE_PATH", str(config))
    return inbox


def test_missing_bare_name_reports_cwd_and_the_command_that_configures_an_inbox(
    no_workspace, monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    message = video.describe_missing_input("hello.mp4")

    assert message.startswith("no such file: hello.mp4")
    assert str(tmp_path) in message
    assert "no Inbox is configured" in message
    assert "voidscape customize --inbox" in message
    assert "full path" in message


def test_missing_bare_name_names_the_configured_inbox(inbox_workspace, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    message = video.describe_missing_input("hello.mp4")

    assert str(inbox_workspace) in message
    assert "no Inbox is configured" not in message


def test_missing_full_path_stays_a_single_line(no_workspace, tmp_path):
    target = tmp_path / "absent.mp4"

    message = video.describe_missing_input(str(target))

    assert message == f"no such file: {target}"


def test_every_reader_raises_the_explaining_message(no_workspace, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match=re.escape("no such file: hello.mp4")):
        video.probe("hello.mp4")
    with pytest.raises(FileNotFoundError, match=re.escape("no such file or folder: shots")):
        image.probe("shots")
    with pytest.raises(FileNotFoundError, match=re.escape("no such file: post.html")):
        article.probe("post.html")

    for reader, argument in ((video, "hello.mp4"), (image, "shots"), (article, "post.html")):
        try:
            reader.probe(argument)
        except FileNotFoundError as exc:
            assert "voidscape customize --inbox" in str(exc)


def test_next_step_hint_keeps_windows_separators_copy_pasteable():
    hint = voidscape._shell_arg(r"C:\Users\a\Fast screenshot context\hello.mp4")

    assert "\\\\" not in hint
    assert hint.startswith('"') if os.name == "nt" else hint.startswith("'")


def test_next_step_hint_leaves_a_plain_path_unquoted():
    assert voidscape._shell_arg("hello.mp4") == "hello.mp4"


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe metacharacter rules")
@pytest.mark.parametrize("metacharacter", list('&|<>^()%!,;= "'))
def test_next_step_hint_never_leaves_a_command_metacharacter_bare(metacharacter):
    """A pasted hint must not let a filename turn into command syntax."""
    hint = voidscape._shell_arg(f"clip{metacharacter}name.mp4")

    assert hint.startswith('"') and hint.endswith('"')
    assert hint.count('"') % 2 == 0


def test_interactive_customize_saves_after_one_confirmation(tmp_path, monkeypatch, capsys):
    config = tmp_path / "workspace.json"
    answers = iter([
        str(tmp_path / "inbox"), str(tmp_path / "library"), "faster-whisper", "small", "45",
        "y",   # save?
        "y",   # create the missing folders?
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(voidscape.sys.stdin, "isatty", lambda: True)

    assert voidscape.main(["customize", "--config", str(config)]) == 0

    assert json.loads(config.read_text(encoding="utf-8"))["inbox_dir"] == str(tmp_path / "inbox")
    assert (tmp_path / "inbox").is_dir()
    assert "Saved local Voidscape preferences" in capsys.readouterr().out


def test_declining_the_confirmation_writes_nothing(tmp_path, monkeypatch, capsys):
    config = tmp_path / "workspace.json"
    answers = iter([
        str(tmp_path / "inbox"), str(tmp_path / "library"), "faster-whisper", "small", "45",
        "",   # decline the save
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(voidscape.sys.stdin, "isatty", lambda: True)

    assert voidscape.main(["customize", "--config", str(config)]) == 0

    assert not config.exists()
    assert not (tmp_path / "inbox").exists()
    assert "No files changed." in capsys.readouterr().out


def test_flag_driven_customize_still_requires_yes(tmp_path, capsys):
    config = tmp_path / "workspace.json"

    assert voidscape.main([
        "customize", "--config", str(config), "--inbox", str(tmp_path / "inbox"),
    ]) == 0

    assert not config.exists()
    assert "Re-run with --yes" in capsys.readouterr().out


def test_doctor_says_what_a_missing_workspace_costs(no_workspace, capsys):
    voidscape.main(["doctor"])

    out = capsys.readouterr().out
    assert "OPTIONAL workspace: not configured" in out
    assert "bare filename will not resolve" in out
    assert "voidscape customize" in out


def test_init_next_steps_do_not_lead_with_a_bare_filename(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("VOIDSCAPE_WORKSPACE_PATH", str(tmp_path / "absent.json"))

    voidscape.main(["init", "--no-skill"])

    out = capsys.readouterr().out
    assert 'voidscape inspect "meeting.mp4"' not in out
    assert "Pass the full path" in out
    assert "bare filename works only" in out
