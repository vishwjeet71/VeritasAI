from fastapi import FastAPI,  Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging, groq, os
from dotenv import load_dotenv
load_dotenv()

from backend.verification_pipeline import verification as vc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VeritasAI",
    description="AI-powered news fact-checking and trust analysis",
    version="1.2.0",
)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

users_info = {}

# Inputs
class CheckInput(BaseModel):
    userid: str
    input: str

class VerifyInput(BaseModel):
    userid: str
    claims: list[str]

class UserDetail(BaseModel):
    userid: str
    usergroq: str | None = None
    user_SerperDev: str | None = None

class Userinfo(BaseModel):
    userid: str

 # routes
@app.post("/api/setup")
async def setup(body: Userinfo, response: Response):
    try:
        users_info[body.userid] = {
            "user_groq": None,
            "user_SerperDev": None,
            "user_model" : vc()
        }
    except Exception as e:
        logger.error(f"[Backend] unable to save details for user {body.userid}: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {body.userid: "failed to save details"}
    
    return {body.userid: "setup done"}
    
@app.post("/api/check")
async def classify_input(body: CheckInput):
    try:
        user_info = users_info[body.userid]

        user_model = user_info["user_model"]
        user_groqApi = user_info["user_groq"]
        user_SerperDev = user_info["user_SerperDev"]

        if user_groqApi != None:
            user_model.groq_client = groq.Groq(api_key= user_groqApi)
            print("update-GroqApi:", user_groqApi)
        else:
            user_model.groq_client = groq.Groq(api_key= os.getenv("GroqApi"))
            
        
        if user_SerperDev != None:
            user_model.serperdev = user_SerperDev
            print("update-serperdev:", user_SerperDev)
        else:
            user_model.serperdev = None

        return user_model.input_handler(body.input)


    except Exception as e:
        logger.error(f"[Backend] unable to classify input for user {body.userid}: {e}")

@app.post("/api/verify")
async def verify_claims_batch(body: VerifyInput):
    return vc.verify_claims_batch(body.claims)

@app.post("/api/update")
async def update_user(body: UserDetail, response: Response):
    try:
        if body.userid not in users_info:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {body.userid: "user not found"}
        
        users_info[body.userid]["user_groq"] = body.usergroq
        users_info[body.userid]["user_SerperDev"] = body.user_SerperDev

    except Exception as e:
        logger.error(f"[Backend] unable to update details for user {body.userid}: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {body.userid: "failed to update details"}
    
    return {body.userid: "update done"}

@app.post("/api/clear-Api")
async def clear_user(body: Userinfo, response: Response):
    try:
        if body.userid not in users_info:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {body.userid: "user not found"}
        
        users_info[body.userid]["user_groq"] = None
        users_info[body.userid]["user_SerperDev"] = None
    except Exception as e:
        logger.error(f"[Backend] unable to clear details for user {body.userid}: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
      
@app.post("/api/delete-user")
async def delete_user(body: Userinfo, response: Response):
    if body.userid not in users_info:
        return {body.userid: "already deleted"}
    try:
        del users_info[body.userid]
        return {body.userid: "deleted"}
    except Exception as e:
        logger.error(f"[delete-user] failed for user {body.userid}: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {body.userid: "failed to clear details"}