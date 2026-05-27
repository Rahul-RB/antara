import logging
import re

import requests
from bs4 import BeautifulSoup

from config import AN_BASE_URL, REQUEST_TIMEOUT, USER_AGENT
from mappings.height_map import an_range
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# AN uses "Sanskrit / Tamil" format; normalize to canonical names that AS uses
_AN_TO_CANONICAL = {
    "ashwini": "Ashwini",
    "bharani": "Bharani",
    "kruttika": "Krithika",
    "krithika": "Krithika",
    "krittika": "Krithika",
    "rohini": "Rohini",
    "mrigasira": "Mrigashirsha",
    "mrigashira": "Mrigashirsha",
    "mrigashirsha": "Mrigashirsha",
    "ardra": "Ardra",
    "punarvasu": "Punarvasu",
    "punarpusam": "Punarvasu",
    "pushya": "Pushya",
    "poosam": "Pushya",
    "ashlesha": "Ashlesha",
    "ayilyam": "Ashlesha",
    "makha": "Magha",
    "magha": "Magha",
    "magam": "Magha",
    "pubba": "Purva Phalguni",
    "poorvaphalguni": "Purva Phalguni",
    "purva phalguni": "Purva Phalguni",
    "uttara": "Uttara",
    "uttaram": "Uttara",
    "uttarphalguni": "Uttara",
    "hasta": "Hasta",
    "chitra": "Chitra",
    "chitta": "Chitta",
    "swati": "Swati",
    "vishaka": "Vishakha",
    "vishakha": "Vishakha",
    "vishakam": "Vishakha",
    "anuradha": "Anuradha",
    "jyeshta": "Jyeshtha",
    "jyeshtha": "Jyeshtha",
    "kettai": "Jyeshtha",
    "mula": "Mula",
    "poorvashada": "Purva Ashadha",
    "purva ashadha": "Purva Ashadha",
    "pooradam": "Purva Ashadha",
    "uttarashada": "Uttara Ashadha",
    "uttara ashadha": "Uttara Ashadha",
    "uthradam": "Uttara Ashadha",
    "shravana": "Shravana",
    "thiruvonam": "Shravana",
    "dhanishtha": "Dhanishtha",
    "avittam": "Dhanishtha",
    "shatabhisha": "Shatabhisha",
    "sadayam": "Shatabhisha",
    "poorvabhadra": "Purva Bhadrapada",
    "purva bhadrapada": "Purva Bhadrapada",
    "puratathi": "Purva Bhadrapada",
    "uttarabhadra": "Uttara Bhadrapada",
    "uttara bhadrapada": "Uttara Bhadrapada",
    "uthrattathi": "Uttara Bhadrapada",
    "revati": "Revati",
}


def _normalize_nakshatra(an_star: str) -> str:
    """Convert AN star string (e.g. 'Uttara / Uttaram') to canonical nakshatra name."""
    if not an_star:
        return ""
    part = an_star.split("/")[0].strip().lower()
    return _AN_TO_CANONICAL.get(part, an_star.split("/")[0].strip())


def _parse_height_from_an(text: str) -> int | None:
    """Parse height cm from AN format '5ft.4in-162cm' or '5ft.2in-157cm'."""
    m = re.search(r"-(\d+)cm", text)
    if m:
        return int(m.group(1))
    # fallback: feet+inches
    m = re.search(r"(\d+)ft\.(\d+)in", text)
    if m:
        return int(m.group(1)) * 30 + int(m.group(2)) * 3
    return None


class AnuragaScraper(BaseScraper):
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "DNT": "1",
            }
        )

    def login(self, username: str, password: str) -> bool:
        resp = self._session.get(
            f"{AN_BASE_URL}/login.php",
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return False

        resp = self._session.post(
            f"{AN_BASE_URL}/pages/login.php",
            data={"name": username, "passw": password},
            headers={
                "Referer": f"{AN_BASE_URL}/login.php",
                "Origin": AN_BASE_URL,
            },
            allow_redirects=False,
            timeout=REQUEST_TIMEOUT,
        )
        success = resp.status_code == 302 and "memberprofile" in resp.headers.get("Location", "")
        if success:
            logger.info("AN login successful")
        else:
            logger.warning(
                "AN login failed (status %d, location %s)",
                resp.status_code,
                resp.headers.get("Location", ""),
            )
        return success

    def get_profile(self, profile_id: str) -> dict | None:
        logger.info("AN: fetching profile %s", profile_id)
        resp = self._session.get(
            f"{AN_BASE_URL}/profile.php",
            params={"id": profile_id},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("AN: profile fetch failed (status %d)", resp.status_code)
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        profile = self._parse_profile_page(soup, profile_id)
        if profile:
            logger.info(
                "AN: profile %s parsed — age=%s height=%scm nakshatra=%s",
                profile_id,
                profile.get("age"),
                profile.get("height_cm"),
                profile.get("nakshatra"),
            )
        return profile

    def search_candidates(
        self, age: int, height_cm: int | None, nakshatra: str, rashi: str, sex: str = "Female"
    ) -> list[dict]:
        from_age = max(18, age - 1)
        to_age = min(71, age + 1)
        star_name = "Any"

        logger.info(
            "AN: searching — age %d-%d sex=%s height %s-%s",
            from_age,
            to_age,
            sex,
            an_range(height_cm)[0],
            an_range(height_cm)[1],
        )
        resp = self._session.post(
            f"{AN_BASE_URL}/searchresult.php",
            params={"mode": "advance"},
            data={
                "sex": sex,
                "mstatus": "Unmarried",
                "agefrom": str(from_age),
                "ageto": str(to_age),
                "heightfr": an_range(height_cm)[0],
                "heightto": an_range(height_cm)[1],
                "physical": "Normal",
                "cmbedu1": "Any",
                "cmbedu": "Any",
                "cmboccu1": "Any",
                "countryliving1": "Any",
                "star": star_name,
                "star1": star_name,
                "employedin": "Any",
                "chkothergotra": "Yes",
                "shortbydt": "All",
                "txtstar": f"'{star_name}'",
                "txtcountryliving": "'India'",
                "txtreligion": "'Smartha'",
                "txtcaste": "'Any'",
                "txteducation": "'Any'",
                "txtoccu": "'Any'",
                "txtmstatus": "'Unmarried'",
                "txtempin": "'Any'",
                "txtcastesource": "",
                "Submit": "Search",
            },
            headers={
                "Referer": f"{AN_BASE_URL}/search.php",
                "Origin": AN_BASE_URL,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("AN: search failed (status %d)", resp.status_code)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        profiles = self._parse_profile_cards(soup)
        total = self._parse_total_count(soup)
        logger.info(
            "AN: search returned %d total profiles, parsed %d from page 1", total, len(profiles)
        )

        total_pages = (total + 9) // 10 if total else 1

        for page in range(2, total_pages + 1):
            page_resp = self._session.get(
                f"{AN_BASE_URL}/searchresult.php",
                params={"page": page},
                timeout=REQUEST_TIMEOUT,
            )
            if page_resp.status_code != 200:
                logger.warning(
                    "AN: pagination page %d failed (status %d)", page, page_resp.status_code
                )
                break
            page_soup = BeautifulSoup(page_resp.text, "html.parser")
            new = self._parse_profile_cards(page_soup)
            profiles.extend(new)
            logger.info("AN: page %d fetched %d profiles", page, len(new))

        # Filter by nakshatra if provided
        if nakshatra:
            canonical = _normalize_nakshatra(nakshatra)
            base_nak = re.sub(r"\s*\d Pada$", "", canonical).strip().lower()
            filtered = [p for p in profiles if _matches_nakshatra(p.get("nakshatra", ""), base_nak)]
            if filtered:
                logger.info(
                    "AN: %d -> %d profiles after nakshatra filter (%s)",
                    len(profiles),
                    len(filtered),
                    nakshatra,
                )
                profiles = filtered
            else:
                logger.info("AN: nakshatra filter yielded 0 results, keeping all %d", len(profiles))

        logger.info("AN: final candidate count: %d", len(profiles))
        return profiles

    def get_profile_images(self, profile: dict) -> list[str]:
        if profile.get("image_urls"):
            return profile["image_urls"]
        profile_id = profile.get("profile_id")
        if not profile_id:
            img = profile.get("first_image_url")
            return [img] if img else []
        return self._fetch_photos_page(profile_id) or (
            [profile["first_image_url"]] if profile.get("first_image_url") else []
        )

    def _fetch_photos_page(self, profile_id: str) -> list[str]:
        logger.debug("AN: fetching photos page for %s", profile_id)
        resp = self._session.get(
            f"{AN_BASE_URL}/photos.php",
            params={"id": profile_id, "pp": "1"},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning(
                "AN: photos page failed for %s (status %d)", profile_id, resp.status_code
            )
            return []

        # breakpoint()
        soup = BeautifulSoup(resp.text, "html.parser")
        td = soup.select_one("table > tr > td:nth-child(1)")
        if not td:
            logger.warning("AN: photos page td not found for %s", profile_id)
            return []

        anchors = td.find_all("a", href=True)
        if len(anchors) == 1:
            selectors = ["table > tr > td:nth-child(1) > a > img"]
        else:
            selectors = [
                "table > tr > td:nth-child(1) > a:nth-child(1) > img",
                "table > tr > td:nth-child(1) > a:nth-child(4) > img",
                "table > tr > td:nth-child(1) > a:nth-child(7) > img",
            ]

        urls = []
        for sel in selectors:
            tag = soup.select_one(sel)
            if not tag:
                continue
            src = tag.get("src", "").strip()
            if not src or "default" in src.lower():
                continue
            if not src.startswith("http"):
                src = f"{AN_BASE_URL}/{src.lstrip('/')}"
            urls.append(src)
        logger.info(
            "AN: found %d image(s) for %s (%d anchor(s) in td)", len(urls), profile_id, len(anchors)
        )
        return urls

    def _parse_profile_page(self, soup: BeautifulSoup, profile_id: str) -> dict | None:
        def txt(selector: str) -> str | None:
            tag = soup.select_one(selector)
            return tag.get_text(strip=True) if tag else None

        age_str = txt("#tab_0 > div:nth-child(2) > span:nth-child(2)")
        height_str = txt("#tab_0 > div:nth-child(3) > span:nth-child(2)")
        dob = txt(
            "#tab_1 > div.group_el_5.field_socialsettings.member_profilefield > span:nth-child(2)"
        )
        tob = txt("#tab_1 > div:nth-child(6) > span:nth-child(2)")
        gotra_raw = txt("#tab_1 > div:nth-child(7) > span:nth-child(2)")
        nak_raw = txt("#tab_1 > div:nth-child(8) > span:nth-child(2)")
        rashi_raw = txt("#tab_1 > div:nth-child(9) > span:nth-child(2)")

        age = None
        if age_str:
            m = re.search(r"(\d+)", age_str)
            age = int(m.group(1)) if m else None

        height_cm = _parse_height_from_an(height_str) if height_str else None
        nakshatra = _normalize_nakshatra(nak_raw) if nak_raw else None
        gotra = gotra_raw.strip() if gotra_raw else None
        rashi = rashi_raw.strip() if rashi_raw else None

        # Detect gender from page text (AN doesn't expose it explicitly)
        page_text = soup.get_text()
        if re.search(r"\bBride\b", page_text, re.IGNORECASE):
            gender = "Female"
        elif re.search(r"\bGroom\b", page_text, re.IGNORECASE):
            gender = "Male"
        else:
            gender = None

        images = self._fetch_photos_page(profile_id)

        return {
            "site": "an",
            "profile_id": profile_id,
            "url_id": profile_id,
            "name": "",
            "age": age,
            "height_cm": height_cm,
            "nakshatra": nakshatra,
            "rashi": rashi,
            "gotra": gotra,
            "paada": None,
            "dob": dob,
            "tob": tob,
            "gender": gender,
            "image_urls": images,
        }

    @staticmethod
    def _parse_profile_cards(soup: BeautifulSoup) -> list[dict]:
        profiles = []
        cards = soup.select("section.b-team")
        for card in cards:
            try:
                link_tag = card.select_one(".b-team__name a")
                if not link_tag:
                    continue
                href = link_tag.get("href", "")
                m = re.search(r"[?&]id=([A-Z0-9]+)", href)
                if not m:
                    continue
                profile_id = m.group(1)

                img_tag = card.select_one(".b-team__media img.img-responsive")
                first_image = None
                if img_tag:
                    src = img_tag.get("src", "")
                    # Skip default/placeholder images
                    if "default_profile" not in src and src:
                        if not src.startswith("http"):
                            src = f"{AN_BASE_URL}/{src.lstrip('/')}"
                        first_image = src

                detail_paras = card.select(".b-team__category.search_detail p")
                age = height_cm = nakshatra = gotra = None

                for para in detail_paras:
                    text = para.get_text(" ").strip()
                    if text.startswith("Age/Height:"):
                        val = text.split(":", 1)[1].strip()
                        parts = val.split("/")
                        if parts:
                            m2 = re.search(r"(\d+)", parts[0])
                            if m2:
                                age = int(m2.group(1))
                        if len(parts) > 1:
                            height_cm = _parse_height_from_an(parts[1].strip())
                    elif text.startswith("Star:"):
                        nakshatra = _normalize_nakshatra(text.split(":", 1)[1].strip())
                    elif text.startswith("Gotra:"):
                        gotra = text.split(":", 1)[1].strip()

                profiles.append(
                    {
                        "site": "an",
                        "profile_id": profile_id,
                        "url_id": profile_id,
                        "name": "",
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
        h2 = soup.find("h2", string=re.compile(r"\d+\s+Profile\s+Match"))
        if h2:
            m = re.search(r"(\d+)", h2.text)
            if m:
                return int(m.group(1))
        return 0


def _matches_nakshatra(profile_nak: str, target_base: str) -> bool:
    if not profile_nak:
        return True  # unknown → include
    nak_lower = profile_nak.lower()
    return target_base in nak_lower or nak_lower in target_base
