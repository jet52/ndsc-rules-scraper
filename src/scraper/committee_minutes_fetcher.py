"""
Committee Minutes Fetcher for ND Court Rules.
Fetches meeting list from JSON API, downloads committee minutes PDFs,
extracts text with pdfplumber, and caches results.
"""

import io
import os
import re
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import requests


class MeetingRecord:
    """A single committee meeting record from the JSON API."""

    def __init__(self, meeting_date: date, minutes_path: Optional[str], autoroute_path: Optional[str]):
        self.meeting_date = meeting_date
        self.minutes_path = minutes_path
        self.autoroute_path = autoroute_path


class CommitteeMinutesFetcher:
    """Fetches and caches committee minutes text from PDF documents."""

    MEETING_LIST_URL = (
        "https://www.ndcourts.gov/supreme-court/committees/"
        "GetMeetingHistory/Joint%20Procedure%20Committee"
    )
    BASE_URL = "https://www.ndcourts.gov"

    def __init__(
        self,
        session: requests.Session,
        cache_dir: str,
        logger=None,
        request_delay: float = 1.0,
    ):
        self.session = session
        self.cache_dir = cache_dir
        self.logger = logger
        self.request_delay = request_delay
        self._meetings_by_date: Dict[date, MeetingRecord] = {}
        self._index_loaded = False

    def load_meeting_index(self) -> None:
        """Fetch the meeting list JSON API and build the date lookup table."""
        if self._index_loaded:
            return

        try:
            if self.logger:
                self.logger.info("Fetching committee meeting index from JSON API...")

            response = self.session.get(self.MEETING_LIST_URL, timeout=30)
            if response.status_code != 200:
                if self.logger:
                    self.logger.warning(
                        f"Meeting list API returned HTTP {response.status_code}"
                    )
                self._index_loaded = True
                return

            meetings = response.json()
            for record in meetings:
                date_str = record.get("DateAndTime", "")
                meeting_date = self._parse_dotnet_date(date_str)
                if meeting_date is None:
                    continue

                minutes_path = record.get("MinutesFilePath")
                autoroute_path = record.get("AutoroutePath")

                self._meetings_by_date[meeting_date] = MeetingRecord(
                    meeting_date=meeting_date,
                    minutes_path=minutes_path,
                    autoroute_path=autoroute_path,
                )

            self._index_loaded = True
            if self.logger:
                self.logger.info(
                    f"Loaded {len(self._meetings_by_date)} committee meetings"
                )

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load meeting index: {e}")
            self._index_loaded = True

    def fetch_minutes_text(self, meeting_date: date) -> Optional[str]:
        """
        Fetch and extract text from committee minutes for a given meeting date.

        Uses fuzzy matching (+-1 day) to handle multi-day meetings.
        Results are cached permanently as text files.

        Args:
            meeting_date: The date of the committee meeting

        Returns:
            Extracted text from the minutes PDF, or None if unavailable
        """
        self.load_meeting_index()

        # Check cache first
        cached = self._read_cache(meeting_date)
        if cached is not None:
            return cached

        # Look up meeting by date (fuzzy: +/- 1 day for multi-day meetings)
        record = self._find_meeting(meeting_date)
        if record is None:
            if self.logger:
                self.logger.debug(
                    f"No meeting found for date {meeting_date}"
                )
            return None

        # Try to download the minutes PDF
        pdf_url = None
        if record.minutes_path:
            pdf_url = record.minutes_path
            if not pdf_url.startswith("http"):
                pdf_url = self.BASE_URL + pdf_url

        if not pdf_url and record.autoroute_path:
            # Fallback: try to find PDF URL from gateway page
            pdf_url = self._extract_pdf_url_from_gateway(record.autoroute_path)

        if not pdf_url:
            if self.logger:
                self.logger.debug(
                    f"No minutes PDF available for {meeting_date}"
                )
            return None

        # Download and extract text
        try:
            if self.logger:
                self.logger.info(f"Downloading minutes PDF for {meeting_date}...")

            time.sleep(self.request_delay)
            response = self.session.get(pdf_url, timeout=60)
            if response.status_code != 200:
                if self.logger:
                    self.logger.warning(
                        f"Minutes PDF returned HTTP {response.status_code}: {pdf_url}"
                    )
                return None

            text = self._extract_text_from_pdf(response.content)
            if not text or not text.strip():
                if self.logger:
                    self.logger.warning(
                        f"No extractable text in minutes PDF for {meeting_date}"
                    )
                return None

            # Cache the extracted text
            self._write_cache(meeting_date, text)
            return text

        except Exception as e:
            if self.logger:
                self.logger.warning(
                    f"Failed to fetch minutes for {meeting_date}: {e}"
                )
            return None

    def _find_meeting(self, target_date: date) -> Optional[MeetingRecord]:
        """Find a meeting by date with fuzzy matching (+/- 1 day)."""
        # Exact match first
        if target_date in self._meetings_by_date:
            return self._meetings_by_date[target_date]

        # Fuzzy match: +/- 1 day
        for delta in (1, -1):
            fuzzy_date = target_date + timedelta(days=delta)
            if fuzzy_date in self._meetings_by_date:
                return self._meetings_by_date[fuzzy_date]

        return None

    def _parse_dotnet_date(self, date_str: str) -> Optional[date]:
        """Parse .NET JSON date format /Date(milliseconds)/ to Python date."""
        if not date_str:
            return None
        match = re.search(r'/Date\((-?\d+)', date_str)
        if not match:
            return None
        ms = int(match.group(1))
        try:
            return datetime.fromtimestamp(ms // 1000).date()
        except (OSError, ValueError):
            return None

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes using pdfplumber."""
        try:
            import pdfplumber
        except ImportError:
            if self.logger:
                self.logger.warning(
                    "pdfplumber not installed. Install with: pip install pdfplumber"
                )
            return ""

        try:
            pages_text = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
            return "\n\n".join(pages_text)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"PDF text extraction failed: {e}")
            return ""

    def _extract_pdf_url_from_gateway(self, autoroute_path: str) -> Optional[str]:
        """Fallback: fetch gateway page and parse onclick to find PDF URL."""
        try:
            url = autoroute_path
            if not url.startswith("http"):
                url = self.BASE_URL + url

            time.sleep(self.request_delay)
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None

            # Look for window.open('...minutes...pdf') in onclick handlers
            match = re.search(
                r"window\.open\('([^']*[Mm]inutes[^']*\.pdf)'",
                response.text,
            )
            if match:
                pdf_path = match.group(1)
                if not pdf_path.startswith("http"):
                    pdf_path = self.BASE_URL + pdf_path
                return pdf_path

            return None

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Gateway page fetch failed: {e}")
            return None

    def _read_cache(self, meeting_date: date) -> Optional[str]:
        """Read cached minutes text for a meeting date."""
        cache_path = os.path.join(self.cache_dir, f"{meeting_date.isoformat()}.txt")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return None
        return None

    def _write_cache(self, meeting_date: date, text: str) -> None:
        """Write extracted text to cache."""
        os.makedirs(self.cache_dir, exist_ok=True)
        cache_path = os.path.join(self.cache_dir, f"{meeting_date.isoformat()}.txt")
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to write cache for {meeting_date}: {e}")
