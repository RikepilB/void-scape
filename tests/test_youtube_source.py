import pytest

from youtube_source import selection


@pytest.mark.parametrize('url', [
    'https://youtu.be/abcdefghijk?si=tracking',
    'https://www.youtube.com/watch?v=abcdefghijk&utm_source=test',
    'https://m.youtube.com/shorts/abcdefghijk',
    'https://youtube.com/embed/abcdefghijk',
    'https://youtube.com/live/abcdefghijk',
])
def test_video_aliases_share_identity(url):
    assert selection(url) == {'kind': 'video', 'url': 'https://www.youtube.com/watch?v=abcdefghijk',
                              'key': 'youtube:abcdefghijk'}


@pytest.mark.parametrize('url', [
    'http://youtube.com/watch?v=abcdefghijk',
    'https://youtube.com.evil.test/watch?v=abcdefghijk',
    'https://evil.test/youtube.com/watch?v=abcdefghijk',
    'https://user:pass@youtube.com/watch?v=abcdefghijk',
    'https://youtube.com:443/watch?v=abcdefghijk',
    ' https://youtu.be/abcdefghijk',
    'https://youtu.be/abcdefghijk\n',
    'https://youtu.be/abcdefghijk#t=10',
    'https://youtube.com/watch?v=abcdefghijk&t=10',
    'https://youtube.com/watch?v=abcdefghijk&list=PLabcdefghijk',
    'https://youtube.com/watch?v=abcdefghijk&v=lmnopqrstuv',
    'https://youtube.com/watch?v=abcdefghijk&token=private',
    'https://youtube.com/watch?v=abc',
    'https://youtube.com/watch',
    'https://youtube.com/feed/subscriptions',
    'https://youtube.com/playlist?list=WL',
    'https://youtube.com/playlist?list=PLabcdefghijk&index=4',
    'https://youtu.be/abcdefghijk/extra',
    'https://youtube.com/@example/../feed',
    'https://youtube.com/@example%2Ffeed',
    '--exec=unsafe',
])
def test_ambiguous_or_unauthorized_scope_is_rejected(url):
    with pytest.raises(ValueError):
        selection(url)


def test_playlist_identity_is_preserved():
    assert selection('https://youtube.com/playlist?list=PLabcdefghijk&si=tracking') == {
        'kind': 'playlist', 'url': 'https://www.youtube.com/playlist?list=PLabcdefghijk', 'key': None}


@pytest.mark.parametrize('tab', ['videos', 'shorts', 'streams'])
def test_explicit_channel_tab_is_preserved(tab):
    assert selection(f'https://youtube.com/@example/{tab}')['url'].endswith(f'/@example/{tab}')


def test_channel_root_defaults_only_to_videos():
    assert selection('https://youtube.com/@example')['url'] == 'https://www.youtube.com/@example/videos'
    channel = 'UC' + 'a' * 22
    assert selection(f'https://youtube.com/channel/{channel}')['url'].endswith(f'/channel/{channel}/videos')
