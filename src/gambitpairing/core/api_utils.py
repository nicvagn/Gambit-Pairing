"""Utilities for talking with chess federation and FIDE web endpoints.

This module provides helper functions to retrieve player information from
various chess federation sources. Implementations prefer lightweight HTTP
requests and BeautifulSoup parsing (when available) and avoid optional
third-party SDKs that are not used in the project.
"""

# Copyright (C) 2024  Nicolas Vaagen
#
# This program is free software.

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import httpx

from gambitpairing.core.utils import setup_logger

logger = setup_logger(__name__)

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

URL_STUB = "https://server.chess.ca"


def get_cfc_player_info(cfc_id: str):
    """Retrieve player information from CFC API.

    Gets player details including name, rating and membership status
    from the Chess Federation of Canada API.

    Parameters
    ----------
    cfc_id : str
        The CFC ID number of the player to look up.

    Returns
    -------
    dict - JSON response from the API.
        example:
        {'updated': '2025-04-24',
        'player': {
            'cfc_id': 123123,
            'cfc_expiry': '2020-01-02',
            'fide_id': 0,
            'name_first': 'Michael',
            'name_last': 'Williams',
            'addr_city': "St.John's",
            'addr_province': 'NL',
            'regular_rating': 200,
            'regular_indicator': 11,
            'quick_rating': 200,
            'quick_indicator': 11,
            'events': [{'id': 199806005,
                'name': 'MacDonald Dr RR',
                'date_end': '1998-05-14',
                'rating_type': 'R',
                'games_played': 11,
                'score': 0.0,
                'rating_pre': 0,
                'rating_perf': 0,
                'rating_post': 200,
                'rating_indicator': 11}],
            'orgarb': [],
            'is_organizer': False,
            'is_arbiter': False
        },
        'apicode': 0,
        'error': ''}

        Player information from the API response.
        Contains fields like name, rating, expiry date, etc.

    Raises
    ------
    httpx.exceptions.RequestException
        If the API request fails for any reason
    ValueError
        If the response is not valid JSON
    """
    api_path = f"/api/player/v1/{cfc_id}"

    try:
        r = httpx.get(URL_STUB + api_path)
        r.raise_for_status()

        api_info = r.json()
        logger.debug("CFC API response: %s", api_info)

        if "name_last" not in api_info["player"]:
            raise ValueError(f"{api_path} did not return a player")

        return api_info["player"]

    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"HTTP error: {e}")


def get_uscf_player_info(uscf_id):
    """Get the player info from uscf API"""
    raise NotImplementedError()


def get_fide_player_info(fide_id: int) -> Optional[Dict[str, Any]]:
    """Get basic player information from the FIDE public profile page.

    This function performs a best-effort extraction from the public FIDE
    profile page. It does not require the `python-fide` package.

    Returns None if the profile cannot be fetched or does not appear valid.
    """
    player_info = {
        "fide_id": fide_id,
        "name": None,
        "federation": None,
        "title": None,
        "standard_rating": None,
        "rapid_rating": None,
        "blitz_rating": None,
        "birth_year": None,
        "gender": None,
        "active": None,
    }

    profile_url = f"https://ratings.fide.com/profile/{fide_id}"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(profile_url)
            if resp.status_code != 200:
                logger.debug(
                    f"FIDE profile {fide_id} returned status {resp.status_code}"
                )
                return None

            content = resp.text

            # Prefer BeautifulSoup if available for robust parsing
            if BS4_AVAILABLE:
                try:
                    soup = BeautifulSoup(content, "html.parser")

                    # Name: often in <title> or an h1/h2 on the page
                    title_tag = soup.find("title")
                    if title_tag and title_tag.string:
                        name_candidate = re.sub(
                            r"\s+FIDE.*$", "", title_tag.string
                        ).strip()
                        if name_candidate and name_candidate.lower() != "fide ratings":
                            player_info["name"] = name_candidate

                    if not player_info["name"]:
                        h1 = soup.find(["h1", "h2"]) or soup.find(
                            class_=re.compile("player|profile", re.I)
                        )
                        if h1:
                            text = h1.get_text(strip=True)
                            if text:
                                player_info["name"] = text

                    # Federation: try to find flag image or country text
                    flag = soup.find("img", src=re.compile(r"/images/flags/", re.I))
                    if flag and flag.get("src"):
                        m = re.search(
                            r"/images/flags/([a-z]{2})\.svg", flag["src"], re.I
                        )
                        if m:
                            code = m.group(1).upper()
                            # map common 2-letter -> 3-letter where possible (partial)
                            two_to_three = {
                                "US": "USA",
                                "CA": "CAN",
                                "GB": "ENG",
                                "RU": "RUS",
                                "CN": "CHN",
                                "IN": "IND",
                            }
                            player_info["federation"] = two_to_three.get(code, code)

                    # Title: look for profile-info-title or similar
                    title_el = soup.find(
                        class_=re.compile(r"profile-info-title|title", re.I)
                    )
                    if title_el:
                        txt = title_el.get_text(" ", strip=True)
                        txt = re.sub(r"\s+FIDE.*$", "", txt).strip()
                        if txt:
                            player_info["title"] = txt

                    # Birth year and sex
                    byear = soup.find(
                        class_=re.compile(r"profile-info-byear|byear|birth", re.I)
                    )
                    if byear:
                        m = re.search(r"(19|20)\d{2}", byear.get_text())
                        if m:
                            player_info["birth_year"] = int(m.group(0))

                    sex = soup.find(class_=re.compile(r"profile-info-sex|sex", re.I))
                    if sex:
                        sval = sex.get_text(strip=True).lower()
                        if "male" in sval and "female" not in sval:
                            player_info["gender"] = "M"
                        elif "female" in sval:
                            player_info["gender"] = "F"

                    # Ratings: look for common rating labels and numbers
                    text = soup.get_text(" ", strip=True)
                    for label, key in [
                        (r"Standard", "standard_rating"),
                        (r"Rapid", "rapid_rating"),
                        (r"Blitz", "blitz_rating"),
                    ]:
                        m = re.search(rf"{label}[^0-9]*(\d{{2,4}})", text, re.I)
                        if m:
                            try:
                                player_info[key] = int(m.group(1))
                            except Exception:
                                pass

                    # If we found any useful info, mark active True
                    if any(
                        player_info[k]
                        for k in (
                            "name",
                            "standard_rating",
                            "rapid_rating",
                            "blitz_rating",
                        )
                    ):
                        player_info["active"] = True
                    else:
                        player_info["active"] = None

                except Exception as e:
                    logger.debug(
                        f"BeautifulSoup parsing failed for FIDE {fide_id}: {e}"
                    )
                    # fall through to regex parsing

            # Fallback: regex-based extraction (less reliable but avoids dependency)
            if not BS4_AVAILABLE or player_info["name"] is None:
                # Name from title tag
                name_match = re.search(
                    r"<title>\s*([^<|]+?)(?:\s+FIDE.*)?</title>", content, re.I
                )
                if name_match:
                    nm = name_match.group(1).strip()
                    nm = re.sub(r"\s+FIDE.*$", "", nm, flags=re.I)
                    if nm and nm.lower() != "fide ratings":
                        player_info["name"] = nm

                # Federation from flag image
                flag_match = re.search(r"/images/flags/([a-z]{2})\.svg", content, re.I)
                if flag_match:
                    code = flag_match.group(1).upper()
                    two_to_three = {
                        "US": "USA",
                        "CA": "CAN",
                        "GB": "ENG",
                        "RU": "RUS",
                        "CN": "CHN",
                        "IN": "IND",
                    }
                    player_info["federation"] = two_to_three.get(code, code)

                # Birth year
                birth_match = re.search(
                    r"profile-info-byear[^>]*>(\d{4})", content, re.I
                )
                if birth_match:
                    try:
                        player_info["birth_year"] = int(birth_match.group(1))
                    except Exception:
                        pass

                # Sex
                sex_match = re.search(r"profile-info-sex[^>]*>([^<]+)<", content, re.I)
                if sex_match:
                    s = sex_match.group(1).strip().lower()
                    if "male" in s and "female" not in s:
                        player_info["gender"] = "M"
                    elif "female" in s:
                        player_info["gender"] = "F"

                # Ratings
                for label, key in [
                    (r"Standard", "standard_rating"),
                    (r"Rapid", "rapid_rating"),
                    (r"Blitz", "blitz_rating"),
                ]:
                    m = re.search(rf"{label}[^0-9]*(\d{{2,4}})", content, re.I)
                    if m:
                        try:
                            player_info[key] = int(m.group(1))
                        except Exception:
                            pass

                if any(
                    player_info[k]
                    for k in ("name", "standard_rating", "rapid_rating", "blitz_rating")
                ):
                    player_info["active"] = True

        return player_info

    except httpx.RequestError as e:
        logger.debug(f"Network error fetching FIDE profile {fide_id}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error fetching FIDE profile {fide_id}: {e}")
        return None


def search_fide_players(name=None, fide_id=None, limit=50, is_cancelled=None):
    """
    Search for players in the FIDE database by name or FIDE ID using the official search endpoint.

    Args:
        name (str, optional): Name to search for
        fide_id (str, optional): FIDE ID to search for
        limit (int): Maximum number of results to return

    Returns:
        list: List of dictionaries containing player information
    """
    if not BS4_AVAILABLE:
        logger.error("BeautifulSoup4 library not installed")
        return []

    # Validate input - need at least one search parameter
    if not name and not fide_id:
        logger.warning("No search parameters provided")
        return []

    try:
        base_url = "https://ratings.fide.com"

        # Create a session with connection pooling and optimized settings
        session = httpx.Client(
            timeout=15,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )

        # First get the main page to establish session
        session.get(f"{base_url}/index.phtml")

        # Use the official FIDE search endpoint
        search_url = f"{base_url}/incl_search_l.php"

        # Parameters matching the official FIDE search
        params = {
            "search": name or fide_id or "",
            "search_rating": "all",
            "search_country": "all",
            "search_title": "all",
            "search_other_title": "all",
            "search_low": "0",
            "search_high": "3500",
            "search_inactive": "off",
            "search_exrated": "off",
            "search_radio": "fide_id" if fide_id else "name",
            "search_bday_start": "all",
            "search_bday_end": "all",
            "search_asc": "descending",
            "search_gender": "All",
            "simple": "0",
        }

        headers = {
            "Referer": f"{base_url}/advanced_search.phtml",
            "X-Requested-With": "XMLHttpRequest",
        }

        if is_cancelled and is_cancelled():
            try:
                session.close()
            finally:
                return []

        response = session.get(search_url, params=params, headers=headers)

        if response.status_code != 200:
            logger.error(f"FIDE search failed with status {response.status_code}")
            return []

        # Parse the HTML response
        soup = BeautifulSoup(response.content, "html.parser")

        players = []

        # Find all tables containing player data
        tables = soup.find_all("table")

        for table in tables:
            if is_cancelled and is_cancelled():
                break
            rows = table.find_all("tr")
            if not rows:
                continue

            # Check if this looks like a player table (should have FIDE ID, Name, etc.)
            header_row = rows[0]
            header_cells = [
                cell.get_text().strip() for cell in header_row.find_all(["td", "th"])
            ]

            # Look for expected columns
            if not ("FIDE ID" in header_cells and "Name" in header_cells):
                continue

            # Process data rows
            for row in rows[1:]:  # Skip header row
                if is_cancelled and is_cancelled():
                    break
                cells = row.find_all(["td", "th"])
                if len(cells) < 6:  # Need at least basic info
                    continue

                try:
                    cell_texts = [cell.get_text().strip() for cell in cells]

                    # Extract player data based on standard FIDE table structure:
                    # [FIDE ID, Name, Title, Tr.T., Fed, Std., Rpd., Blz., B-Year]
                    fide_id = cell_texts[0] if cell_texts[0] else ""
                    name_text = cell_texts[1] if len(cell_texts) > 1 else ""
                    title = cell_texts[2] if len(cell_texts) > 2 else ""
                    federation = cell_texts[4] if len(cell_texts) > 4 else ""
                    std_rating = cell_texts[5] if len(cell_texts) > 5 else ""
                    rapid_rating = cell_texts[6] if len(cell_texts) > 6 else ""
                    blitz_rating = cell_texts[7] if len(cell_texts) > 7 else ""
                    birth_year = cell_texts[8] if len(cell_texts) > 8 else ""

                    # Skip rows without essential data
                    if not fide_id or not name_text:
                        continue

                    # Try to extract profile link
                    profile_url = ""
                    name_cell = cells[1] if len(cells) > 1 else None
                    if name_cell:
                        link = name_cell.find("a")
                        if link and link.get("href"):
                            profile_url = f"{base_url}{link['href']}"

                    # Try to get gender from the player profile if available
                    # Fetch gender for every result (was previously limited to first 25),
                    # but keep a short timeout to avoid long delays.
                    gender = None
                    if profile_url and not (is_cancelled and is_cancelled()):
                        try:
                            profile_response = session.get(profile_url, timeout=3)
                            if profile_response.status_code == 200:
                                profile_soup = BeautifulSoup(
                                    profile_response.content, "html.parser"
                                )
                                # Look for gender information in multiple possible locations
                                sex_element = (
                                    profile_soup.find(
                                        "p", class_=re.compile("profile-info-sex", re.I)
                                    )
                                    or profile_soup.find(
                                        "span", class_=re.compile("sex", re.I)
                                    )
                                    or profile_soup.find(
                                        text=re.compile(r"Sex[:\s]", re.IGNORECASE)
                                    )
                                )

                                if sex_element:
                                    try:
                                        sex_text = (
                                            sex_element.get_text(strip=True).lower()
                                            if hasattr(sex_element, "get_text")
                                            else str(sex_element).lower()
                                        )
                                        if (
                                            "male" in sex_text
                                            and "female" not in sex_text
                                        ):
                                            gender = "M"
                                        elif "female" in sex_text:
                                            gender = "F"
                                    except Exception:
                                        # Parsing error for this profile; leave gender as None
                                        pass

                        except (httpx.TimeoutException, httpx.RequestError):
                            # Skip gender lookup on timeout/network error
                            pass
                        except Exception as e:
                            logger.debug(f"Error parsing profile for gender: {e}")
                            pass

                    # Fallback: Try to infer gender from titles even for players beyond the limit
                    # (Bug fix) use local title variable instead of undefined player_data here
                    if not gender and str(title or "").upper().startswith("W"):
                        gender = "F"

                    # Convert rating strings to integers, handling empty strings
                    def parse_rating(rating_str):
                        if not rating_str or rating_str.strip() == "":
                            return None
                        try:
                            return int(rating_str.strip())
                        except (ValueError, TypeError):
                            return None

                    player_data = {
                        "fide_id": fide_id,
                        "name": name_text,
                        "title": title if title else None,
                        "federation": federation if federation else None,
                        "standard_rating": parse_rating(std_rating),
                        "rapid_rating": parse_rating(rapid_rating),
                        "blitz_rating": parse_rating(blitz_rating),
                        "birth_year": parse_rating(birth_year),
                        "gender": gender,
                        "profile_url": profile_url,
                    }

                    players.append(player_data)

                    if len(players) >= limit:
                        break

                except (IndexError, AttributeError, ValueError) as e:
                    logger.debug(f"Error parsing player row: {e}")
                    continue

            if len(players) >= limit or (is_cancelled and is_cancelled()):
                break

        # Ensure session is properly closed
        try:
            session.close()
        except Exception:
            pass

        search_term = name or fide_id or "unknown"
        if is_cancelled and is_cancelled():
            logger.info(
                f"Cancelled FIDE search for '{search_term}' after collecting {len(players)} players"
            )
            return players
        logger.info(f"Found {len(players)} FIDE players for search '{search_term}'")
        return players

    except httpx.TimeoutException:
        logger.error(f"FIDE search timed out")
        return []
    except httpx.RequestError as e:
        logger.error(f"FIDE search network error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error searching FIDE players: {e}")
        return []


def search_fide_players_by_name(
    name: str,
    max_results: int = 20,
    *,
    country: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Search for FIDE players by name with optional filters.

    Methods used:
    1. Direct FIDE website search (with country and birth-year constraints when provided)
    2. Known players database fallback

    Parameters
    ----------
    name : str
        Player name or partial name to search for (flexible order: 'First Last' or 'Last, First').
    max_results : int, default 20
        Maximum number of results to return.
    country : Optional[str]
        3-letter FIDE federation code (e.g., 'USA', 'IND').
    min_age : Optional[int]
        Minimum age to filter (inclusive).
    max_age : Optional[int]
        Maximum age to filter (inclusive).

    Returns
    -------
    List[Dict[str, Any]]
        List of player dictionaries matching the search criteria.
        Each dict contains same fields as get_fide_player_info.
    """
    logger.debug(f"Searching FIDE players by name: '{name}'")

    search_term = name.lower().strip()
    if not search_term:
        return []

    results = []
    seen_fide_ids = set()

    # Helper to compute birth year range from ages
    def _birth_year_range_from_ages(
        min_age: Optional[int], max_age: Optional[int]
    ) -> Tuple[Optional[int], Optional[int]]:
        try:
            from datetime import datetime

            current_year = datetime.today().year
            # age = current_year - birth_year -> birth_year = current_year - age
            by_min = (
                current_year - max_age if (max_age is not None) else None
            )  # oldest birth year
            by_max = (
                current_year - min_age if (min_age is not None) else None
            )  # youngest birth year
            return (by_min, by_max)
        except Exception:
            return (None, None)

    # Helper: normalize strings (remove diacritics, collapse whitespace)
    def _normalize(s: str) -> str:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"\s+", " ", s)
        return s.strip().casefold()

    # Helper to generate flexible name variants (handles 'First Last' vs 'Last, First')
    def _generate_name_variants(q: str) -> List[str]:
        q = q.strip()
        variants = {q}
        # If contains comma, try swapping
        if "," in q:
            parts = [p.strip() for p in q.split(",", 1)]
            if len(parts) == 2:
                variants.add(f"{parts[1]} {parts[0]}")
                variants.add(f"{parts[0]} {parts[1]}")
        else:
            tokens = [t for t in q.replace(",", " ").split() if t]
            if len(tokens) >= 2:
                first = tokens[0]
                last = tokens[-1]
                variants.add(f"{last}, {first}")
                variants.add(f"{last} {first}")
                # Try middle names swapped as well
                if len(tokens) >= 3:
                    variants.add(f"{tokens[-1]}, {' '.join(tokens[:-1])}")
        # Limit to reasonable number and preserve order preference
        ordered = []
        for v in [q] + [x for x in variants if x != q]:
            if v not in ordered:
                ordered.append(v)
        return ordered[:5]

    # Method 1: Search FIDE website directly (try variants)
    try:
        import httpx

        search_url = "https://ratings.fide.com/a_search.php"
        birth_min, birth_max = _birth_year_range_from_ages(min_age, max_age)

        with httpx.Client(timeout=15.0) as http_client:
            for variant in _generate_name_variants(name):
                # Try searching by variant name with optional filters
                search_data = {
                    "name": variant,
                    "country": (country or "").upper(),
                    "title": "",
                    "rating1": "",
                    "rating2": "",
                    "birthday1": str(birth_min or ""),  # older (min year)
                    "birthday2": str(birth_max or ""),  # younger (max year)
                }

                response = http_client.post(search_url, data=search_data)
                if response.status_code != 200:
                    continue

                content = response.text

                # Parse search results using regex
                # Look for player entries in the results table
                player_pattern = r'<a href="[^"]*profile/(\d+)"[^>]*>([^<]+)</a>'
                matches = re.findall(player_pattern, content)

                for fide_id_str, player_name in matches:
                    fide_id = int(fide_id_str)
                    if fide_id in seen_fide_ids:
                        continue

                    # Get detailed info for this player
                    try:
                        full_info = get_fide_player_info(fide_id)
                        if full_info:
                            # Ensure we have the name from search results
                            if not full_info["name"]:
                                full_info["name"] = player_name.strip()
                            # Server-side country filter may fail; enforce client-side too
                            if (
                                country
                                and full_info.get("federation")
                                and full_info["federation"].upper() != country.upper()
                            ):
                                continue
                            # Client-side age filter if birth_year available
                            if birth_min or birth_max:
                                by = full_info.get("birth_year")
                                if by is not None:
                                    if birth_min and by < birth_min:
                                        continue
                                    if birth_max and by > birth_max:
                                        continue
                            results.append(full_info)
                            seen_fide_ids.add(fide_id)
                            logger.debug(
                                f"Found player via web search: {player_name} (ID: {fide_id})"
                            )
                    except Exception as e:
                        logger.debug(
                            f"Could not get details for {player_name} (ID: {fide_id}): {e}"
                        )
                        # Add basic info even if we can't get full details
                        basic_info = {
                            "fide_id": fide_id,
                            "name": player_name.strip(),
                            "federation": None,
                            "title": None,
                            "standard_rating": None,
                            "rapid_rating": None,
                            "blitz_rating": None,
                            "birth_year": None,
                            "gender": None,
                            "active": True,
                        }
                        results.append(basic_info)
                        seen_fide_ids.add(fide_id)

                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break
    except Exception as e:
        logger.debug(f"FIDE web search failed: {e}")

    logger.info(f"Found {len(results)} players matching '{name}'")
    return results


def get_fide_top_players(count: int = 50) -> List[Dict[str, Any]]:
    """Get top-rated FIDE players.

    This function is currently not implemented and returns an empty list.

    Parameters
    ----------
    count : int, default 50
        Number of top players to return

    Returns
    -------
    List[Dict[str, Any]]
        Empty list (function not implemented)
    """
    logger.debug(f"Getting top {count} FIDE players - not implemented")
    return []
