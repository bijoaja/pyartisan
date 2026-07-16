def name_parts(name: str) -> tuple[str, str, str, str]:
    """Return (name_lower, name_title, name_snake, name_plural) from any user input.

    Examples:
        'blog'      -> ('blog', 'Blog', 'blog', 'blogs')
        'blog_post' -> ('blog_post', 'BlogPost', 'blog_post', 'blog_posts')
        'blog-post' -> ('blog_post', 'BlogPost', 'blog_post', 'blog_posts')
        'category'  -> ('category', 'Category', 'category', 'categories')
    """
    name_lower = name.lower().replace("-", "_")
    name_snake = name_lower
    name_title = "".join(w.capitalize() for w in name_lower.split("_"))

    if name_lower.endswith("y") and not name_lower.endswith(("ay", "ey", "oy", "uy")):
        name_plural = name_lower[:-1] + "ies"
    elif name_lower.endswith("s"):
        name_plural = name_lower
    else:
        name_plural = name_lower + "s"

    return name_lower, name_title, name_snake, name_plural
