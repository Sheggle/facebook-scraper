import dspy
from schemas import Article
import json
import os
from random import shuffle
import subprocess
from pathlib import Path
import shutil
from datetime import datetime


lm = dspy.LM("openai/gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
dspy.configure(lm=lm)

screenshots_dir = Path('screenshots')
annotated_dir = Path('annotated')
storage_dir = Path('storage2')


class SeedSearch(dspy.Signature):
    """
    Create 5 search queries for facebook that are likely to find messages that are Rijswijk citizens reacting to the content of the article.
    Start your queries with 'rijswijk', and aim for 3-5 words.
    """

    article: Article = dspy.InputField()
    search_queries: list[str] = dspy.OutputField()


get_queries = dspy.Predict(SeedSearch)
with open('unified_articles.json') as f:
    articles = [Article.model_validate(article) for article in json.load(f)['articles']]

os.makedirs(storage_dir, exist_ok=True)

while True:
    shuffle(articles)
    article = articles[0]
    print(article.title)
    queries = get_queries(article=article).search_queries
    print(f"Queries: {queries}")
    shuffle(queries)
    query = queries[0]
    print(f"Chosen query: {query}")
    snake_query = '_'.join(query.split())
    cmd = ['uv', 'run', 'scraper.py', '--keyword', f"'{query}'"]
    subprocess.run(cmd)
    for dir in os.listdir('screenshots'):
        cmd = ['uv', 'run', 'run_ocr.py', str(screenshots_dir / dir)]
        subprocess.run(cmd)
        with open(annotated_dir / dir / 'parsed_data.json', 'r') as f:
            data = json.load(f)
        data['query'] = query
        data['scrape_date'] = str(datetime.now())
        with open(storage_dir / f'{dir}.json', 'w') as f:
            json.dump(data, f, indent=2)

    if os.path.exists(annotated_dir):
        shutil.rmtree(annotated_dir)
    if os.path.exists(screenshots_dir):
        shutil.rmtree(screenshots_dir)
