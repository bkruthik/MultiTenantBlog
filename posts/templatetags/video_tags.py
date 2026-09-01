import re
from django import template

register = template.Library()


@register.filter
def youtube_embed_url(url):
    """
    Transforms any YouTube URL (watch, share, shorts) into an embeddable URL.
    Examples:
      - https://www.youtube.com/watch?v=dQw4w9WgXcQ -> https://www.youtube.com/embed/dQw4w9WgXcQ
      - https://youtu.be/dQw4w9WgXcQ -> https://www.youtube.com/embed/dQw4w9WgXcQ
      - https://www.youtube.com/shorts/dQw4w9WgXcQ -> https://www.youtube.com/embed/dQw4w9WgXcQ
    """
    if not url:
        return ""

    url = url.strip()

    # If already an embed URL
    if "youtube.com/embed/" in url:
        return url

    # Match standard watch link: v=VIDEO_ID
    match = re.search(r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})', url)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/embed/{video_id}"

    return url


@register.filter
def is_direct_video(url):
    """
    Checks if the URL is a direct video file (e.g. mp4, webm, ogg).
    """
    if not url:
        return False
    url_lower = url.lower().split('?')[0]
    return url_lower.endswith(('.mp4', '.webm', '.ogg', '.mov'))
