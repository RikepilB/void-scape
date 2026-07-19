import pytest
import video


@pytest.mark.parametrize("raw,expected", [
    ("75", 75.0),
    ("01:15", 75.0),
    ("1:15", 75.0),
    ("00:01:15", 75.0),
    ("1:01:15", 3675.0),
    ("12.5", 12.5),
    ("00:12.5", 12.5),
    (" 01:15 ", 75.0),
])
def test_parse_timestamp_ok(raw, expected):
    assert video._parse_timestamp(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "1:2:3:4", "-5", "1:-2", "1:xx"])
def test_parse_timestamp_rejects(raw):
    with pytest.raises(ValueError):
        video._parse_timestamp(raw)
