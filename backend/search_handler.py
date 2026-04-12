import requests, json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class search_and_filter():

    def filter(self, data):
        # return top 3 organizations result
        pass

    def load_credibility_scores(self):
        # loading credibility of different organizations
        pass

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
            
            new_format = {}
            
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
    data = gnewsObject.gnews(["New anime release"], "<yourApiKey>")
    print(json.dumps(data, indent=4))