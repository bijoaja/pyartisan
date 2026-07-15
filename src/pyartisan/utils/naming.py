def name_parts(name: str) -> tuple[str, str]:
    """Return (name_lower, name_title) from any user input.

    Examples:
        'blog'      -> ('blog', 'Blog')
        'blog_post' -> ('blog_post', 'BlogPost')
        'blog-post' -> ('blog_post', 'BlogPost')
    """
    name_lower = name.lower().replace("-", "_")
    name_title = "".join(w.capitalize() for w in name_lower.split("_"))
    return name_lower, name_title
