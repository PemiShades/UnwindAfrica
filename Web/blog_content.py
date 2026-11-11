"""HTML allowlist shared by the CMS editor and public journal renderer."""
from urllib.parse import urlsplit

import bleach


ALLOWED_TAGS = {
    "p", "br", "hr", "h2", "h3", "h4", "blockquote", "ul", "ol", "li",
    "strong", "b", "em", "i", "u", "a", "img", "sub", "sup", "iframe",
}
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "iframe": ["src", "title", "width", "height", "allow", "allowfullscreen", "loading"],
}


def _allowed_attribute(tag, name, value):
    if tag == "iframe" and name == "src":
        parsed = urlsplit(value)
        return parsed.scheme == "https" and parsed.hostname in {
            "www.youtube.com", "youtube.com", "www.youtube-nocookie.com",
            "youtube-nocookie.com", "player.vimeo.com",
        } and parsed.path.startswith("/embed/")
    return name in ALLOWED_ATTRIBUTES.get(tag, ())


def clean_blog_html(value):
    return bleach.clean(
        value or "",
        tags=ALLOWED_TAGS,
        attributes=_allowed_attribute,
        protocols={"http", "https", "mailto"},
        strip=True,
    )
