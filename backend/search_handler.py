import requests, json, random
from dotenv import load_dotenv
import logging, os
from credibility_scorer import get_credibility_scorer, Sheetdb

load_dotenv()
sdb = Sheetdb()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class search_and_filter():

    def _filter(fx):
        # return top 3 organizations result
        def wrapper(self, *args, **kwargs):
            output = fx(self, *args, **kwargs)

            organizations_names = set()

            for id, data in output.items():
                if data["name"] not in organizations_names:
                    organizations_names.add(data["name"])
            
            scores_dict = self._load_credibility_scores(organizations_names) # temporary function
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
            apikey: str
    ):
        if not isinstance(searchquerys, list):
            logger.error("[searchAndFilter] Invalid input: searchquerys must be a list")
            return {}
        
        if len(searchquerys) == 0:
            logger.info("[searchAndFilter] get null input")
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
                logger.error(f"[searchAndFilter] Error: {str(e)}")
                continue

            if response.status_code == (400 or 401):
                logger.error("[searchAndFilter] Somthing wrrong with the Api key!")
                return {}
            
            if response.status_code == 200:
                articals = response.json()['articles']
                logger.info(f"[searchAndFilter] Request successful collected {len(articals)} articles")
                for artical in articals:
                    new_format[artical["id"]] = {
                        "name": artical["source"].get("name", "unknown"),
                        "url": artical['url']
                    }
            else:
                logger.error(f"[searchAndFilter] Request failed with status code: {response.status_code}")
                return {}

        data = json.loads(json.dumps(new_format))
        return data
    

# --- Testing ---
if __name__ == "__main__":

    gnewsObject = search_and_filter()
    data = gnewsObject.gnews(["New anime release"], os.getenv("gnewsApi"))
    print(json.dumps(data, indent=4))