from typing import Optional
from google.oauth2.service_account import Credentials
import json, re, trafilatura, validators
import logging, os, gspread, threading
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


class Sheetdb():
    def __init__(self):
        self.lock = threading.Lock()
        self.lookup = self._calculate_lookup()

    def _calculate_lookup(self):
        try:
            existing_organization_names = sheet.col_values(1)
            return {name: i for i, name in enumerate(existing_organization_names)}
        except Exception as e:
            logger.error(f"Failed to calculate lookup: {e}")
            return {}

    def get_credentials(self, input_list: list[str]):
        organization_names = list(input_list)
        non_existing_organization_names = set()

        for name in input_list:
            if name not in self.lookup:
                non_existing_organization_names.add(name)

        if non_existing_organization_names:
            logger.info(f"[fn:Credentials] non existing data: {non_existing_organization_names}")
            self._add_data(non_existing_organization_names)

        return self._get_data(organization_names)

    def _single_add_data(self, name: str):
        if not isinstance(name, str):
            logger.error(f"[dataUpdate] Invalid organization name: {name}")
            return

        try:
            output_raw = scraper(name)
            if output_raw:
                output = json.loads(output_raw)
                row_data = [
                    name,
                    output.get("bias_rating_str"),
                    output.get("bias_rating_int"),
                    output.get("factual_reporting_str"),
                    output.get("factual_reporting_int"),
                    output.get("country"),
                    output.get("mbfc_country_freedom_rating"),
                    output.get("media_type"),
                    output.get("traffic_popularity"),
                    output.get("mbfc_credibility_rating")
                ]
                sheet.append_row(row_data)
                logger.info(f"[dataUpdate] Data added successfully for: {name}")
            else:
                logger.warning(f"[dataUpdate] No data for '{name}'; adding empty entry.")
                sheet.append_row([name])

        except Exception as e:
            logger.error(f"[dataUpdate] Error adding data for '{name}': {e}")

    def _add_data(self, names_set: set):
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(self._single_add_data, names_set)

        with self.lock:
            self.lookup = self._calculate_lookup()

    def _single_Get_Data(self, name: str):
        try:
            if name not in self.lookup:
                logger.warning(f"[GetData] '{name}' not found in lookup after add attempt.")
                return name, None
            
            data = sheet.row_values(self.lookup[name] + 1)
            output = self._reform(data)
        except Exception as e:
            logger.error(f"[GetData] Unable to get data for '{name}'. Error: {e}")
            return name, None

        return name, output

    def _get_data(self, names_set: list):
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = dict(executor.map(self._single_Get_Data, names_set))
        return results

    def _reform(self, dataList: list[str]):
        if len(dataList) < 10:
            for _ in range(10 - len(dataList)):
                dataList.append("")

        attributes = {
            "bias_rating_str":          dataList[1] if dataList[1] else None,
            "bias_rating_int":          dataList[2] if dataList[2] else None,
            "factual_reporting_str":    dataList[3] if dataList[3] else None,
            "factual_reporting_int":    dataList[4] if dataList[4] else None,
            "country":                  dataList[5] if dataList[5] else None,
            "mbfc_country_freedom_rating": dataList[6] if dataList[6] else None,
            "media_type":               dataList[7] if dataList[7] else None,
            "traffic_popularity":       dataList[8] if dataList[8] else None,
            "mbfc_credibility_rating":  dataList[9] if dataList[9] else None,
        }
        return attributes


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
            downloaded = trafilatura.fetch_url(sourceLink)
            soup = BeautifulSoup(downloaded, 'html.parser')

            content = soup.find('div', class_='entry-content')
            if content is None:
                logger.warning(f"[credibilityDataExtraction] No entry-content div found at: {sourceLink}")
                return None

            target_p = content.find(lambda t: t.name == 'p' and "Bias Rating:" in t.text)

            if target_p:
                full_text = [l.strip() for l in target_p.get_text(separator="\n").split('\n') if l.strip()]
                result = _extract_mbfc_data(full_text)
                return result

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
    link = None

    try:
        downloaded = trafilatura.fetch_url(url)

        if downloaded:
            result = trafilatura.extract(
                downloaded,
                include_links=True,
                output_format="html",
                include_comments=False,
                include_tables=True
            )
            soup = BeautifulSoup(result, 'html.parser')

            all_links = soup.find_all('a', href=True)
            link = next(
                (
                    a['href'] for a in all_links
                    if 'mediabiasfactcheck.com' in a['href']
                    and '?s=' not in a['href']         
                    and a['href'].rstrip('/') != 'https://mediabiasfactcheck.com'
                ),
                None
            )

    except Exception:
        logger.error(f"[scraper] Unable to fetch search page for: {orgName}")

    if link:
        if validators.url(link):
            return link
        else:
            return None
    else:
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
        result["mbfc_country_freedom_rating"] = get_value("MBFC's Country Freedom Rating:")
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