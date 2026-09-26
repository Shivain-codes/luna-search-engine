"""Bundled offline demo corpus (no network required).

A small, interlinked set of HTML pages across a few domains so the demo
exercises crawling, indexing, ranking, and PageRank on a real link graph.
"""

from __future__ import annotations

DEMO_PAGES: dict[str, str] = {
    "https://docs.luna.dev/python": """
        <html lang="en"><head><title>Python Programming Guide</title>
        <meta name="description" content="A complete guide to the Python programming language"></head>
        <body><h1>Python Programming</h1>
        <p>Python is a high-level, general-purpose programming language known for
        readable syntax. It is widely used in web development, data science,
        automation, and machine learning. Learn Python programming step by step.</p>
        <a href="https://docs.luna.dev/data-science">Data science with Python</a>
        <a href="https://docs.luna.dev/web">Web development</a></body></html>
    """,
    "https://docs.luna.dev/data-science": """
        <html lang="en"><head><title>Data Science Fundamentals</title>
        <meta name="description" content="Data science with statistics and Python"></head>
        <body><h1>Data Science</h1>
        <p>Data science combines statistics, programming, and domain knowledge to
        extract insight from data. Python is the most popular language for data
        science, with libraries for analysis and machine learning.</p>
        <a href="https://docs.luna.dev/python">Python programming</a>
        <a href="https://docs.luna.dev/ml">Machine learning</a></body></html>
    """,
    "https://docs.luna.dev/ml": """
        <html lang="en"><head><title>Machine Learning Basics</title>
        <meta name="description" content="Introduction to machine learning"></head>
        <body><h1>Machine Learning</h1>
        <p>Machine learning is a branch of artificial intelligence where systems
        learn patterns from data. Common tasks include classification, regression,
        and clustering. Python and data science skills are essential.</p>
        <a href="https://docs.luna.dev/data-science">Data science</a></body></html>
    """,
    "https://docs.luna.dev/web": """
        <html lang="en"><head><title>Web Development with Python</title>
        <meta name="description" content="Build web applications using Python frameworks"></head>
        <body><h1>Web Development</h1>
        <p>Web development covers building websites and web applications. Python
        frameworks like FastAPI and Django make it fast to build APIs and servers.
        Frontend development uses HTML, CSS, and JavaScript.</p>
        <a href="https://docs.luna.dev/python">Python programming</a></body></html>
    """,
    "https://blog.luna.dev/search-engines": """
        <html lang="en"><head><title>How Search Engines Work</title>
        <meta name="description" content="Crawling, indexing, and ranking explained"></head>
        <body><h1>How Search Engines Work</h1>
        <p>A search engine crawls web pages, builds an inverted index, and ranks
        results using algorithms like BM25 and PageRank. Crawling discovers pages,
        indexing makes them searchable, and ranking orders them by relevance.</p>
        <a href="https://docs.luna.dev/python">Python programming</a>
        <a href="https://blog.luna.dev/bm25">BM25 ranking</a></body></html>
    """,
    "https://blog.luna.dev/bm25": """
        <html lang="en"><head><title>Understanding BM25 Ranking</title>
        <meta name="description" content="The BM25 relevance ranking function"></head>
        <body><h1>BM25 Ranking</h1>
        <p>BM25 is a ranking function used by search engines to score documents by
        relevance to a query. It builds on term frequency and inverse document
        frequency, adding document length normalization for better ranking.</p>
        <a href="https://blog.luna.dev/search-engines">How search engines work</a>
        <a href="https://blog.luna.dev/pagerank">PageRank</a></body></html>
    """,
    "https://blog.luna.dev/pagerank": """
        <html lang="en"><head><title>The PageRank Algorithm</title>
        <meta name="description" content="How PageRank measures page authority"></head>
        <body><h1>PageRank</h1>
        <p>PageRank measures the importance of web pages based on the link graph.
        A page linked to by many important pages is considered authoritative. It is
        computed with power iteration over the graph of links between pages.</p>
        <a href="https://blog.luna.dev/bm25">BM25 ranking</a>
        <a href="https://blog.luna.dev/search-engines">How search engines work</a></body></html>
    """,
    "https://news.luna.dev/ai-today": """
        <html lang="en"><head><title>AI News Today</title>
        <meta name="description" content="Latest in artificial intelligence"></head>
        <body><h1>Artificial Intelligence Today</h1>
        <p>Artificial intelligence continues to advance in machine learning, natural
        language processing, and computer vision. Researchers apply data science and
        programming to build smarter systems.</p>
        <a href="https://docs.luna.dev/ml">Machine learning</a></body></html>
    """,
}

# Example queries seeded into query logs so analytics/autocomplete have data.
DEMO_QUERIES = [
    ("python programming", 4),
    ("machine learning", 2),
    ("how search engines work", 3),
    ("bm25 ranking", 2),
    ("pagerank algorithm", 2),
    ("data science", 3),
    ("web development", 2),
    ("quantum teleportation recipe", 0),  # zero-result example
]

__all__ = ["DEMO_PAGES", "DEMO_QUERIES"]
