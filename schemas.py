from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator
from enum import Enum

class NewsSource(str, Enum):
    OMROEP_WEST = "omroepwest"
    RODI = "rodi"
    INRIJSWIJK = "inrijswijk"
    RIJSWIJKS_DAGBLAD = "rijswijksdagblad"
    FEELGOOD_RADIO = "feelgoodradio"

class Article(BaseModel):
    """Unified news article model for all scrapers."""

    # Core required fields
    title: str = Field(..., description="Article headline")
    url: HttpUrl = Field(..., description="Full URL to the article")
    source: NewsSource = Field(..., description="Which news source this article came from")

    # Content fields
    summary: Optional[str] = Field(None, description="Article description/summary")
    body: Optional[str] = Field(None, description="Full article content")

    # Metadata fields
    published: Optional[datetime] = Field(None, description="When the article was published")
    category: Optional[str] = Field(None, description="Article category (if available)")

    # Scraping metadata
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When this article was scraped")

    @field_validator('published', mode='before')
    @classmethod
    def parse_published_date(cls, v):
        """Handle different date formats from various scrapers."""
        if v is None:
            return None
        if isinstance(v, str):
            # Handle ISO format with Z suffix
            if v.endswith('Z'):
                v = v[:-1] + '+00:00'
            try:
                parsed_dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                # Ensure timezone awareness
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                return parsed_dt
            except ValueError:
                # Handle YYYY-MM-DD format
                try:
                    return datetime.strptime(v, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                except ValueError:
                    # Log and return None for unparseable dates
                    print(f"Warning: Could not parse date '{v}'")
                    return None
        if isinstance(v, datetime):
            # Ensure timezone awareness for datetime objects
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        return v

    @field_validator('url', mode='before')
    @classmethod
    def ensure_full_url(cls, v):
        """Ensure URL is absolute."""
        if isinstance(v, str) and v.startswith('/'):
            raise ValueError("Relative URLs not allowed, must be absolute")
        return v

    class Config:
        # Use enum values for serialization
        use_enum_values = True

class ScrapingResult(BaseModel):
    """Container for a scraping session's results."""

    source: NewsSource = Field(..., description="Which news source was scraped")
    source_url: str = Field(..., description="The listing URL that was scraped")
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When scraping occurred")
    article_count: int = Field(..., description="Number of articles found")
    articles: list[Article] = Field(default_factory=list, description="The scraped articles")

    @field_validator('article_count', mode='before')
    @classmethod
    def validate_count(cls, v, info):
        """Ensure count matches actual articles list."""
        if hasattr(info, 'data') and 'articles' in info.data:
            return len(info.data['articles'])
        return v

    class Config:
        # Use enum values for serialization
        use_enum_values = True

class UnifiedArticleDatabase(BaseModel):
    """Container for all articles from all sources."""

    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the database was last updated")
    total_articles: int = Field(0, description="Total number of articles")
    sources: dict[str, datetime] = Field(default_factory=dict, description="Last scrape time per source")
    articles: list[Article] = Field(default_factory=list, description="All articles from all sources")

    @field_validator('total_articles', mode='before')
    @classmethod
    def validate_total(cls, v, info):
        """Ensure total matches actual articles list."""
        if hasattr(info, 'data') and 'articles' in info.data:
            return len(info.data['articles'])
        return v

    class Config:
        # Use enum values for serialization
        use_enum_values = True