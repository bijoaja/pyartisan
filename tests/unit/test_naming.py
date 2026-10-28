from pyartisan.utils.naming import name_parts


def test_name_parts():
    assert name_parts("blog") == ("blog", "Blog", "blog", "blogs")
    assert name_parts("blog_post") == ("blog_post", "BlogPost", "blog_post", "blog_posts")
    assert name_parts("blog-post") == ("blog_post", "BlogPost", "blog_post", "blog_posts")
    assert name_parts("category") == ("category", "Category", "category", "categories")
