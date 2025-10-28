"""Content ingestion service for Aletheia."""

from typing import Optional
import httpx
from bs4 import BeautifulSoup
import feedparser
from PyPDF2 import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
from agent_sdk.utils import setup_logger

logger = setup_logger("aletheia.ingestion")


class ContentIngestionService:
    """Service for ingesting content from various sources."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def ingest_url(self, url: str) -> dict:
        """
        Fetch and parse content from a URL.

        Args:
            url: The URL to fetch

        Returns:
            Dict with title, content, and metadata
        """
        logger.info("Ingesting URL", extra={"url": url})

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title
            title = ""
            if soup.find('title'):
                title = soup.find('title').text.strip()
            elif soup.find('h1'):
                title = soup.find('h1').text.strip()

            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Extract main content
            # Try to find article or main content area
            main_content = soup.find('article') or soup.find('main') or soup.find('body')
            text = main_content.get_text(separator='\n', strip=True) if main_content else ""

            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            content = '\n'.join(lines)

            logger.info(
                "URL ingested successfully",
                extra={"url": url, "content_length": len(content)}
            )

            return {
                "title": title,
                "content": content,
                "url": url,
                "word_count": len(content.split())
            }

        except Exception as e:
            logger.error(
                "Failed to ingest URL",
                exc_info=True,
                extra={"url": url, "error": str(e)}
            )
            raise

    async def ingest_rss(self, feed_url: str, max_entries: int = 10) -> list[dict]:
        """
        Parse RSS feed and return entries.

        Args:
            feed_url: URL of the RSS feed
            max_entries: Maximum number of entries to return

        Returns:
            List of dicts with entry data
        """
        logger.info("Ingesting RSS feed", extra={"feed_url": feed_url})

        try:
            feed = feedparser.parse(feed_url)

            entries = []
            for entry in feed.entries[:max_entries]:
                entries.append({
                    "title": entry.get('title', ''),
                    "content": entry.get('summary', entry.get('description', '')),
                    "url": entry.get('link', ''),
                    "published": entry.get('published', ''),
                    "author": entry.get('author', '')
                })

            logger.info(
                "RSS feed ingested",
                extra={"feed_url": feed_url, "entries_count": len(entries)}
            )

            return entries

        except Exception as e:
            logger.error(
                "Failed to ingest RSS feed",
                exc_info=True,
                extra={"feed_url": feed_url, "error": str(e)}
            )
            raise

    def ingest_pdf(self, pdf_path: str) -> dict:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with title, content, and metadata
        """
        logger.info("Ingesting PDF", extra={"pdf_path": pdf_path})

        try:
            reader = PdfReader(pdf_path)
            text = ""

            for page in reader.pages:
                text += page.extract_text() + "\n"

            # Try to get title from metadata
            title = pdf_path
            if reader.metadata and reader.metadata.get('/Title'):
                title = reader.metadata['/Title']

            logger.info(
                "PDF ingested",
                extra={"pdf_path": pdf_path, "pages": len(reader.pages)}
            )

            return {
                "title": title,
                "content": text.strip(),
                "pages": len(reader.pages),
                "word_count": len(text.split())
            }

        except Exception as e:
            logger.error(
                "Failed to ingest PDF",
                exc_info=True,
                extra={"pdf_path": pdf_path, "error": str(e)}
            )
            raise

    async def ingest_youtube(self, video_id: str) -> dict:
        """
        Get transcript from YouTube video.

        Args:
            video_id: YouTube video ID

        Returns:
            Dict with title, content (transcript), and metadata
        """
        logger.info("Ingesting YouTube video", extra={"video_id": video_id})

        try:
            # Get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([entry['text'] for entry in transcript_list])

            # Get video info
            url = f"https://youtube.com/watch?v={video_id}"
            video_info = await self._get_youtube_info(url)

            logger.info(
                "YouTube video ingested",
                extra={"video_id": video_id, "transcript_length": len(text)}
            )

            return {
                "title": video_info.get("title", f"YouTube: {video_id}"),
                "content": text,
                "url": url,
                "video_id": video_id,
                "word_count": len(text.split())
            }

        except Exception as e:
            logger.error(
                "Failed to ingest YouTube video",
                exc_info=True,
                extra={"video_id": video_id, "error": str(e)}
            )
            raise

    async def _get_youtube_info(self, url: str) -> dict:
        """Get YouTube video metadata."""
        try:
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            title = ""
            if soup.find('title'):
                title = soup.find('title').text.replace(' - YouTube', '').strip()

            return {"title": title}
        except:
            return {}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
