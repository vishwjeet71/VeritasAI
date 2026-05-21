import requests, json, random
from dotenv import load_dotenv
import logging, os
from backend.credibility_scorer import get_credibility_scorer, Sheetdb
import time

load_dotenv()
sdb = Sheetdb()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class search_and_filter():

    def _filter(fx):
        
        def wrapper(self, *args, **kwargs):
            output = fx(self, *args, **kwargs)

            organizations_names = set()

            for id, data in output.items():
                if data["name"] not in organizations_names:
                    organizations_names.add(data["name"])
            
            scores_dict = self._load_credibility_scores(organizations_names)
            top_3_orgs = sorted(scores_dict, key=scores_dict.get, reverse=True)[:3]
            print("Top 3 organizations based on credibility scores:", top_3_orgs)

            top_3_orgs_data = {
                item_id: details
                for item_id, details in output.items() 
                    if details['name'] in top_3_orgs
                    }
            return top_3_orgs_data
        
        return wrapper


    def _load_credibility_scores(self, orgnization_names: set[str]):

        if not isinstance(orgnization_names, set):
            logger.error("[load_credibility_scores] Invalid input: orgnization_names must be a list")
            return {}
        
        score_dict = get_credibility_scorer(orgnization_names, sdb)
        
        return score_dict
    
    @_filter
    def gnews(
            self, searchquerys: list[str],
            apikey: str = os.getenv("gnewsApi")
    ):
        time.sleep(2)

        if not isinstance(searchquerys, list):
            logger.error("[searchAndFilter][gnews] Invalid input: searchquerys must be a list")
            return {}
        
        if len(searchquerys) == 0:
            logger.info("[searchAndFilter][gnews] get null input")
            return {}
        
        new_format = {}

        for searchquery in searchquerys:
            url = "https://gnews.io/api/v4/search"
            params = {
                "q": searchquery,
                "lang": "en",
                "max": 10,
                "token": apikey
            }

            try:
                response = requests.get(url, params=params)
            except Exception as e:
                logger.error(f"[searchAndFilter][gnews] Error: {str(e)}")
                continue

            if response.status_code in (400, 401):
                logger.error("[searchAndFilter][gnews] Somthing wrrong with the Api key!")
                return {}
            
            if response.status_code == 200:
                articals = response.json()['articles']
                logger.info(f"[searchAndFilter][gnews] Request successful collected {len(articals)} articles")
                for artical in articals:
                    new_format[artical["id"]] = {
                        "name": artical["source"].get("name", "unknown"),
                        "url": artical['url']
                    }
            else:
                logger.error(f"[searchAndFilter][gnews] Request failed with status code: {response.status_code}")
                return {}

        data = json.loads(json.dumps(new_format))
        return data
    
    @_filter
    def serperdev(self, searchquerys: list[str],
                serperdevApi: str):
        if not isinstance(searchquerys, list):
                logger.error("[searchAndFilter][serperdev] Invalid input: searchquerys must be a list")
                return {}
            
        if len(searchquerys) == 0:
            logger.info("[searchAndFilter][serperdev] get null input")
            return {}
            
        new_format = {}

        for searchquery in searchquerys:
            url = "https://google.serper.dev/news"
            payload = json.dumps({
                "q": searchquery,
                "hl": "en"
            })
            headers = {
                'X-API-KEY': serperdevApi,
                'Content-Type': 'application/json'
            }
            try:
                response = requests.request("POST", url, headers=headers, data=payload)
            except Exception as e:
                logger.error(f"[searchAndFilter][serperdev] Error: {str(e)}")
                continue

            if response.status_code in (400, 401):
                    logger.error("[searchAndFilter][serperdev] Somthing wrrong with the Api key!")
                    return {}
                    
            if response.status_code == 200:
                    data = response.json()
                    articals = data.get("news", [])
                    logger.info(f"[searchAndFilter][serperdev] Request successful collected {len(articals)} articles")
                    for id, artical in enumerate(articals):
                        new_format[id] = {
                                "name": artical.get("source", "unknown"),
                                "url": artical["link"]
                        }
            else:
                    logger.error(f"[searchAndFilter][serperdev] Request failed with status code: {response.status_code}")
                    return {}

        data = json.loads(json.dumps(new_format, indent=4))
        return data