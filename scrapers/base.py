from abc import ABC, abstractmethod

import requests


class BaseScraper(ABC):
    _session: requests.Session

    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """Authenticate. Returns True on success."""

    @abstractmethod
    def get_profile(self, profile_id: str) -> dict | None:
        """Fetch profile by user-facing ID. Returns profile dict or None."""

    @abstractmethod
    def search_candidates(
        self, age: int, height_cm: int | None, nakshatra: str, rashi: str
    ) -> list[dict]:
        """
        Search profiles matching the given attributes.
        Returns list of profile dicts (may be partial — first image only).
        """

    @abstractmethod
    def get_profile_images(self, profile: dict) -> list[str]:
        """
        Return all image URLs for the given profile.
        Visits the profile page if needed.
        """
