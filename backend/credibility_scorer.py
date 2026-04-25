import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

from typing import Optional
from google.oauth2.service_account import Credentials
import json, re, validators
import logging, os, gspread, threading, requests
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
if creds_path is None:
    raise ValueError("Credentials path not found in environment variables.")

_creds = Credentials.from_service_account_file(creds_path, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
sheet = gspread.authorize(_creds).open("organizationsCredibility").sheet1

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})


class Sheetdb():
    def __init__(self):
        self.lock = threading.Lock()
        self._cache: dict[str, list] = {}
        self._load_cache()

    def _load_cache(self):
        try:
            all_rows = sheet.get_all_values() 
            self._cache = {row[0]: row for row in all_rows if row and row[0]}
            logger.info(f"[Cache] Loaded {len(self._cache)} entries.")
        except Exception as e:
            logger.error(f"[Cache] Failed to load: {e}")
            self._cache = {}


    def get_credentials(self, input_list: list[str]) -> dict:
        with self.lock:
            missing = [name for name in input_list if name not in self._cache]

        if missing:
            self._add_data(missing)

        with self.lock:
            return {
                name: self._reform(list(self._cache.get(name, [name])))
                for name in input_list
            }


    def _scrape_one(self, name: str) -> list:

        try:
            output_raw = scraper(name)
            if output_raw:
                output = json.loads(output_raw)
                return [
                    name,
                    output.get("bias_rating_str"),
                    output.get("bias_rating_int"),
                    output.get("factual_reporting_str"),
                    output.get("factual_reporting_int"),
                    output.get("country"),
                    output.get("mbfc_country_freedom_rating"),
                    output.get("media_type"),
                    output.get("traffic_popularity"),
                    output.get("mbfc_credibility_rating"),
                ]
            else:
                logger.warning(f"[Scrape] No data for '{name}'; storing empty entry.")
                return [name]
        except Exception as e:
            logger.error(f"[Scrape] Failed for '{name}': {e}")
            return [name]

    def _add_data(self, missing: list[str]):
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            scraped_rows = list(executor.map(self._scrape_one, missing))

        with self.lock:
            for row in scraped_rows:
                if row:
                    self._cache[row[0]] = row

        try:
            sheet.append_rows(scraped_rows)
            logger.info(f"[Add] Batch wrote {len(scraped_rows)} rows.")
        except Exception as e:
            logger.error(f"[Add] Batch write failed: {e}")


    def _reform(self, data: list) -> dict:
        
        data.extend([""] * max(0, 10 - len(data)))
        return {
            "bias_rating_str":             data[1] or None,
            "bias_rating_int":             data[2] or None,
            "factual_reporting_str":       data[3] or None,
            "factual_reporting_int":       data[4] or None,
            "country":                     data[5] or None,
            "mbfc_country_freedom_rating": data[6] or None,
            "media_type":                  data[7] or None,
            "traffic_popularity":          data[8] or None,
            "mbfc_credibility_rating":     data[9] or None,
        }


def _calculate_credibility_score(attrs: dict) -> float:

    if not attrs:
        return 0.5

    component_scores: dict[str, tuple[float, float]] = {}

    # FACTUAL REPORTING
    factual_score: Optional[float] = None

    val_int = attrs.get("factual_reporting_int")
    if val_int is not None:
        try:
            linear = max(0.0, min(1.0, 1.0 - (float(val_int) - 1.0) / 7.0))
            factual_score = linear ** 1.5
        except (TypeError, ValueError):
            pass

    if factual_score is None:
        val_str = str(attrs.get("factual_reporting_str") or "").lower().strip()
        factual_str_map: dict[str, float] = {
            "very high":      0.93,
            "high":           0.72,
            "mostly factual": 0.49,
            "mixed":          0.21,
            "low":            0.06,
            "very low":       0.01,
        }
        factual_score = factual_str_map.get(val_str)

    if factual_score is not None:
        component_scores["factual"] = (factual_score, 0.37)

    # MBFC CREDIBILITY RATING
    cred_val = str(attrs.get("mbfc_credibility_rating") or "").lower().strip()
    credibility_map: dict[str, float] = {
        "high credibility":     0.90,
        "medium credibility":   0.40,
        "low credibility":      0.12,
        "very low credibility": 0.02,
    }
    cred_score = credibility_map.get(cred_val)
    if cred_score is not None:
        component_scores["credibility"] = (cred_score, 0.25)

    # BIAS RATING
    bias_score: Optional[float] = None

    bias_int = attrs.get("bias_rating_int")
    if bias_int is not None:
        try:
            extremity = abs(float(bias_int)) / 10.0
            bias_score = max(0.0, 1.0 - extremity ** 1.4)
        except (TypeError, ValueError):
            pass

    if bias_score is None:
        bias_str = str(attrs.get("bias_rating_str") or "").lower().strip()
        bias_str_map: dict[str, float] = {
            "center":                   1.00,
            "pro-science":              0.95,
            "left-center":              0.82,
            "right-center":             0.82,
            "left":                     0.58,
            "right":                    0.58,
            "left bias":                0.58,
            "right bias":               0.58,
            "extreme left":             0.20,
            "extreme right":            0.20,
            "conspiracy-pseudoscience": 0.00,
            "satire":                   0.30,
        }
        bias_score = bias_str_map.get(bias_str)

    if bias_score is not None:
        component_scores["bias"] = (bias_score, 0.22)

    # COUNTRY PRESS FREEDOM
    freedom_val = str(attrs.get("mbfc_country_freedom_rating") or "").lower().strip()
    freedom_map: dict[str, float] = {
        "free":             1.00,
        "mostly free":      0.82,
        "moderate freedom": 0.52,
        "not free":         0.15,
    }
    freedom_score = freedom_map.get(freedom_val)
    if freedom_score is not None:
        component_scores["freedom"] = (freedom_score, 0.12)

    # TRAFFIC / POPULARITY
    traffic_val = str(attrs.get("traffic_popularity") or "").lower().strip()
    traffic_map: dict[str, float] = {
        "high traffic":   0.62,
        "medium traffic": 0.52,
        "low traffic":    0.42,
    }
    traffic_score = traffic_map.get(traffic_val)
    if traffic_score is not None:
        component_scores["traffic"] = (traffic_score, 0.025)

    # MEDIA TYPE
    media_val = str(attrs.get("media_type") or "").lower().strip()
    media_map: dict[str, float] = {
        "peer reviewed": 1.00,
        "science":       0.90,
        "newspaper":     0.70,
        "magazine":      0.65,
        "tv":            0.60,
        "television":    0.60,
        "radio":         0.60,
        "online":        0.50,
        "website":       0.50,
        "blog":          0.35,
        "tabloid":       0.20,
        "satire":        0.10,
    }
    media_score = media_map.get(media_val)
    if media_score is not None:
        component_scores["media"] = (media_score, 0.015)

    if not component_scores:
        return 0.5

    total_weight = sum(w for _, w in component_scores.values())
    weighted_sum = sum(s * w for s, w in component_scores.values())

    return round(weighted_sum / total_weight, 4)


def _fetch_credibility_details(fx):
    def wrapper(*args, **kwargs):
        sourceLink = fx(*args, **kwargs)

        if sourceLink is None:
            logger.error("[credibilityDataExtraction] Invalid extraction link: None")
            return None

        try:
            response = _session.get(sourceLink, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            content = soup.find("div", class_="entry-content")
            if content is None:
                logger.warning(f"[credibilityDataExtraction] No entry-content div found at: {sourceLink}")
                return None

            target_p = content.find(lambda t: t.name == "p" and "Bias Rating:" in t.text)
            if target_p:
                full_text = [l.strip() for l in target_p.get_text(separator="\n").split("\n") if l.strip()]
                return _extract_mbfc_data(full_text)

            logger.warning(f"[credibilityDataExtraction] 'Bias Rating:' paragraph not found at: {sourceLink}")
            return None

        except Exception as e:
            org_name = args[0] if args else "unknown"
            logger.error(f"[credibilityDataExtraction] Unable to extract details for '{org_name}'. Error: {e}")
            return None

    return wrapper


@_fetch_credibility_details
def scraper(orgName: str):
    search_query = orgName.replace(" ", "+")
    url = f"https://mediabiasfactcheck.com/?s={search_query}"

    try:
        response = _session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        articles = soup.find_all("article")

        link = next(
            (
                a["href"]
                for article in articles
                for a in article.find_all("a", href=True)
                if "mediabiasfactcheck.com" in a["href"]
                and "?s=" not in a["href"]
                and a["href"].rstrip("/") != "https://mediabiasfactcheck.com"
                and "membership" not in a["href"]
            ),
            None
        )

        if link and validators.url(link):
            return link

        logger.warning(f"[scraper] No valid result link found for: {orgName}")
        return None

    except Exception:
        logger.error(f"[scraper] Unable to fetch search page for: {orgName}")
        return None


def _extract_mbfc_data(input_list):
    result = {
        "bias_rating_str": None,
        "bias_rating_int": None,
        "factual_reporting_str": None,
        "factual_reporting_int": None,
        "country": None,
        "mbfc_country_freedom_rating": None,
        "media_type": None,
        "traffic_popularity": None,
        "mbfc_credibility_rating": None
    }

    if len(input_list) == 0:
        return json.dumps(result, indent=4)

    def get_value(key_name):
        try:
            if key_name in input_list:
                idx = input_list.index(key_name)
                if idx + 1 < len(input_list) and not input_list[idx + 1].endswith(':'):
                    return input_list[idx + 1].strip().lower()
        except (ValueError, IndexError):
            return None
        return None

    def parse_rating(raw_val):
        if not raw_val:
            return None, None
        match = re.search(r'\(([-+]?\d*\.?\d+)\)', raw_val)
        score = float(match.group(1)) if match else None
        label = raw_val.split('(')[0].strip().lower()
        return label, score

    try:
        bias_raw = get_value("Bias Rating:")
        result["bias_rating_str"], result["bias_rating_int"] = parse_rating(bias_raw)

        fact_raw = get_value("Factual Reporting:")
        result["factual_reporting_str"], result["factual_reporting_int"] = parse_rating(fact_raw)

        result["country"] = get_value("Country:")
        result["mbfc_country_freedom_rating"] = get_value("MBFC’s Country Freedom Rating:") or get_value("MBFC’s Country Freedom Rank:")
        result["media_type"] = get_value("Media Type:")
        result["traffic_popularity"] = get_value("Traffic/Popularity:")
        result["mbfc_credibility_rating"] = get_value("MBFC Credibility Rating:")

    except Exception as e:
        logger.error(f"[credibilityExtraction] Error during extraction: {e}")
        return json.dumps(result, indent=4)  

    return json.dumps(result, indent=4)


def get_credibility_scorer(org_names: list | set, dbObject: Sheetdb) -> dict:

    if not isinstance(org_names, (list, set)):
        logger.error("[get_credibility_scorer] Invalid input: org_names must be a list or set")
        return {}

    
    output_credentials = dbObject.get_credentials(list(org_names))
    final_output = {}

    for org, att in output_credentials.items():
        final_output[org] = _calculate_credibility_score(att)

    return final_output


# --- Testing ---
if __name__ == "__main__":

    sdb = Sheetdb()
    print(get_credibility_scorer([
        "times of india", "news18", "The New York Times", "vaccines revealed", "life news"
    ], sdb))