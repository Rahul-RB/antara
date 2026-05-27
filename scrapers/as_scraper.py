import logging
import re

import requests
from bs4 import BeautifulSoup

from config import AS_BASE_URL, REQUEST_TIMEOUT, USER_AGENT
from mappings.height_map import as_range
from mappings.rashi_map import to_as_rashi
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


def _nakshatra_variants(nakshatra: str) -> list[str]:
    base = nakshatra.strip()
    # If it already has a pada suffix, include both the base and the specific pada
    if re.search(r"\d Pada$", base):
        base_name = re.sub(r"\s*\d Pada$", "", base).strip()
        return [base_name, base]
    # Otherwise include base + all 4 padas
    variants = [base]
    for i in range(1, 5):
        variants.append(f"{base} {i} Pada")
    return variants


def _parse_height_cm(text: str) -> int | None:
    m = re.search(r"(\d+)cm", text)
    return int(m.group(1)) if m else None


class AseemaScraper(BaseScraper):
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "DNT": "1",
            }
        )
        self._app_no = None
        self._user_email = None

    def login(self, email: str, password: str) -> bool:
        # Get login page to set ci_session cookie
        resp = self._session.get(
            f"{AS_BASE_URL}/login",
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return False

        # POST credentials
        resp = self._session.post(
            f"{AS_BASE_URL}/login/check_login",
            data={"emailid": email, "password": password},
            headers={
                "Referer": f"{AS_BASE_URL}/login",
                "Origin": AS_BASE_URL,
            },
            allow_redirects=False,
            timeout=REQUEST_TIMEOUT,
        )
        success = resp.status_code == 302 and "dashboard" in resp.headers.get("Location", "")
        if success:
            logger.info("AS login successful")
            self._fetch_search_hidden_fields()
        else:
            logger.warning(
                "AS login failed (status %d, location %s)",
                resp.status_code,
                resp.headers.get("Location", ""),
            )
        return success

    def _fetch_search_hidden_fields(self) -> None:
        resp = self._session.get(
            f"{AS_BASE_URL}/browseprofile/search/1",
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("AS: could not fetch search form (status %d)", resp.status_code)
            return
        soup = BeautifulSoup(resp.text, "html.parser")
        app_no_tag = soup.find("input", {"name": "application_no"})
        email_tag = soup.find("input", {"name": "email_id"})
        if app_no_tag:
            self._app_no = app_no_tag.get("value", "")
        if email_tag:
            self._user_email = email_tag.get("value", "")
        logger.info("AS hidden fields: app_no=%s email=%s", self._app_no, self._user_email)

    def get_profile(self, profile_id: str) -> dict | None:
        logger.info("AS: fetching profile %s", profile_id)
        resp = self._session.post(
            f"{AS_BASE_URL}/browseprofile/searchbyid",
            files=[("registration_no", (None, profile_id))],
            headers={
                "Referer": f"{AS_BASE_URL}/account/dashboard",
                "Origin": AS_BASE_URL,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("AS: search-by-id failed (status %d)", resp.status_code)
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = self._parse_profile_cards(soup)
        if not cards:
            logger.warning("AS: no cards found for profile %s", profile_id)
            return None

        card = None
        for c in cards:
            if c["profile_id"].strip() == profile_id.strip():
                card = c
                break
        if not card:
            logger.info("AS: exact ID not in results, using first card")
            card = cards[0]

        logger.info("AS: profile %s found (url_id=%s)", profile_id, card.get("url_id"))

        # Fetch full profile page to get nakshatra, rashi, gotra and images
        full = self._fetch_profile_page(card["url_id"])
        if full:
            card.update({k: v for k, v in full.items() if v is not None})
        else:
            card["image_urls"] = self.get_profile_images(card)

        return card

    def _fetch_profile_page(self, url_id: str) -> dict | None:
        resp = self._session.get(
            f"{AS_BASE_URL}/profile/view/{url_id}",
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning(
                "AS: profile page failed for url_id=%s (status %d)", url_id, resp.status_code
            )
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        def txt(selector: str) -> str | None:
            tag = soup.select_one(selector)
            return tag.get_text(strip=True) if tag else None

        _table = "#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-7.row_1 > table > tbody"
        _astro = "#home > form:nth-child(2) > div > div:nth-child(2) > table > tbody"
        _photos = "#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-5.row_2 > div > div > ul"

        name_str = txt(f"{_table} > tr:nth-child(1) > td.day_value")
        age_str = txt(f"{_table} > tr.opened_1 > td.day_value")
        dob_str = txt(f"{_table} > tr:nth-child(4) > td.day_value")
        height_str = txt(f"{_table} > tr:nth-child(5) > td.day_value")
        nak_str = txt(f"{_astro} > tr:nth-child(1) > td.day_value.closed > span")
        gotra_str = txt(f"{_astro} > tr:nth-child(2) > td.day_value.closed > span")
        rashi_str = txt(f"{_astro} > tr:nth-child(3) > td.day_value.closed > span")

        age = None
        if age_str:
            m = re.search(r"(\d+)", age_str)
            age = int(m.group(1)) if m else None

        height_cm = _parse_height_cm(height_str) if height_str else None

        # Images: up to 4 from the photo slider
        image_urls = []
        for i in range(1, 5):
            img_tag = soup.select_one(f"{_photos} > li:nth-child({i}) > img")
            if not img_tag:
                continue
            src = img_tag.get("src", "").strip()
            if not src:
                continue
            if not src.startswith("http"):
                src = AS_BASE_URL + ("/" if not src.startswith("/") else "") + src
            image_urls.append(src)

        logger.info(
            "AS: profile page url_id=%s — nakshatra=%s rashi=%s images=%d",
            url_id,
            nak_str,
            rashi_str,
            len(image_urls),
        )

        return {
            "name": name_str,
            "age": age,
            "height_cm": height_cm,
            "nakshatra": nak_str,
            "gotra": gotra_str,
            "rashi": rashi_str,
            "dob": dob_str,
            "image_urls": image_urls if image_urls else None,
        }

    def search_candidates(
        self, age: int, height_cm: int | None, nakshatra: str, rashi: str
    ) -> list[dict]:
        from_age = max(18, age - 1)
        to_age = min(71, age + 1)
        from_height, to_height = as_range(height_cm)
        nak_variants = _nakshatra_variants(nakshatra)
        rashi_value = to_as_rashi(rashi) if rashi else "Any Rashi"

        _edu = [
            "Bachelors - B Ed",
            "Bachelors - B Tech",
            "Bachelors - BDS",
            "Bachelors - BE",
            "Bachelors - MBBS",
            "CFA",
            "CMA",
            "Masters",
            "Masters - CA",
            "Masters - ICWA",
            "Masters - M Ed",
            "Masters - M Sc",
            "Masters - M Tech",
            "Masters - MBA",
            "Masters - MD",
            "Masters - MDS",
            "Masters - ME",
            "Masters - MS",
            "Masters - MS Engg",
            "Masters - MS Medical",
            "MPH",
            "CPA",
        ]

        fields = [
            ("from_age_preference", (None, str(from_age))),
            ("to_age_preference", (None, str(to_age))),
            ("from_height_preference", (None, from_height)),
            ("to_height_preference", (None, to_height)),
            ("caste_preference[]", (None, "Smartha")),
            ("marital_status", (None, "yes")),
            ("occupation_country", (None, "India")),
            ("residentpreference[]", (None, "Indian Resident")),
            ("rashi_nakshatra[]", (None, rashi_value)),
        ]
        for v in nak_variants:
            fields.append(("rashi_nakshatra1[]", (None, v)))
        for edu in _edu:
            fields.append(("educationpreference[]", (None, edu)))

        if self._app_no:
            fields.append(("application_no", (None, self._app_no)))
        if self._user_email:
            fields.append(("email_id", (None, self._user_email)))

        logger.info(
            "AS: searching — age %d-%d, height %s-%s, rashi=%s, nakshatra=%s",
            from_age,
            to_age,
            from_height,
            to_height,
            rashi_value,
            ", ".join(nak_variants),
        )
        resp = self._session.post(
            f"{AS_BASE_URL}/browseprofile/searchpreference/1",
            files=fields,
            headers={
                "Referer": f"{AS_BASE_URL}/browseprofile/search/1",
                "Origin": AS_BASE_URL,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("AS: search failed (status %d)", resp.status_code)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        profiles = self._parse_profile_cards(soup)
        total = self._parse_total_count(soup)
        logger.info(
            "AS: search returned %d total profiles, parsed %d from page 1", total, len(profiles)
        )

        page_size = 20
        total_pages = ((total - 1) // page_size) if total else 0

        for page in range(1, total_pages + 1):
            start = page * page_size
            page_resp = self._session.get(
                f"{AS_BASE_URL}/browseprofile/search.html",
                params={"start": start},
                timeout=REQUEST_TIMEOUT,
            )
            if page_resp.status_code != 200:
                logger.warning(
                    "AS: pagination page %d failed (status %d)", page + 1, page_resp.status_code
                )
                break
            page_soup = BeautifulSoup(page_resp.text, "html.parser")
            new = self._parse_profile_cards(page_soup)
            profiles.extend(new)
            logger.debug("AS: page %d fetched %d profiles", page + 1, len(new))

        logger.info("AS: total candidates collected: %d", len(profiles))
        return profiles

    def get_profile_images(self, profile: dict) -> list[str]:
        if profile.get("image_urls"):
            return profile["image_urls"]
        url_id = profile.get("url_id")
        if not url_id:
            img = profile.get("first_image_url")
            return [img] if img else []

        full = self._fetch_profile_page(url_id)
        if full and full.get("image_urls"):
            return full["image_urls"]

        # Fallback to the thumbnail from the search card
        img = profile.get("first_image_url")
        return [img] if img else []

    @staticmethod
    def _parse_profile_cards(soup: BeautifulSoup) -> list[dict]:
        profiles = []
        cards = soup.select("tr.item")
        for card in cards:
            try:
                link_tag = card.select_one(".item-img-info a.product-image")
                if not link_tag:
                    continue
                profile_url = link_tag.get("href", "")
                url_id = profile_url.rstrip("/").split("/")[-1]

                img_tag = card.select_one('img[src*="/uploads/"]')
                first_image = img_tag["src"] if img_tag else None

                name_tag = card.select_one(".item-title a")
                name = name_tag.text.strip() if name_tag else ""

                display_id_tag = card.select_one("h6")
                display_id = display_id_tag.text.strip() if display_id_tag else ""

                info_paras = card.select('.item-content p[style*="font-size:13px"]')
                age = nakshatra = height_cm = gotra = None

                if len(info_paras) >= 1:
                    # "26 Yrs ,Purva Ashadha" or "26 Yrs ,Ashwini 4 Pada"
                    parts = [p.strip() for p in info_paras[0].text.split(",")]
                    m = re.search(r"(\d+)", parts[0])
                    if m:
                        age = int(m.group(1))
                    if len(parts) >= 2:
                        nakshatra = parts[1].strip()

                if len(info_paras) >= 2:
                    # "5' - 152cm , Smartha"
                    height_cm = _parse_height_cm(info_paras[1].text)

                if len(info_paras) >= 3:
                    # "Kannada ,Vishwamitra"
                    parts = [p.strip() for p in info_paras[2].text.split(",")]
                    if len(parts) >= 2:
                        gotra = parts[1].strip()

                if not display_id:
                    continue

                profiles.append(
                    {
                        "site": "as",
                        "profile_id": display_id,
                        "url_id": url_id,
                        "profile_url": profile_url,
                        "name": name,
                        "age": age,
                        "height_cm": height_cm,
                        "nakshatra": nakshatra,
                        "gotra": gotra,
                        "first_image_url": first_image,
                    }
                )
            except Exception:
                continue
        return profiles

    @staticmethod
    def _parse_total_count(soup: BeautifulSoup) -> int:
        btn = soup.find("a", string=re.compile(r"Total Record"))
        if not btn:
            return 0
        m = re.search(r"(\d+)", btn.text)
        return int(m.group(1)) if m else 0
