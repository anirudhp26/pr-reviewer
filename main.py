from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from reviews import process_pr
from celery.result import AsyncResult
import requests

app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def do_analyze(repo: str, pr: str, github_token: str):
    response = requests.get(f"https://api.github.com/repos/anirudhp26/{repo}/pulls/{pr}/files", headers={
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    })
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid request")
    task = process_pr.delay(repo, pr, response.json())
    return task.id

@app.get("/status/{id}", response_class=JSONResponse)
def read_item(id: str):
    print(f"Checking status of request {id}")
    task_result = AsyncResult(id=id, app=process_pr)
    result = {
        "task_id": id,
        "status": task_result.status,
        "result": task_result.result,
    }
    return JSONResponse(result)

@app.get("/results/{id}", response_class=JSONResponse)
def read_item(id: str):
    task_result = AsyncResult(id=id, app=process_pr)
    result = {
        "task_id": id,
        "status": task_result.status,
        "results": {
            "files": task_result.result.get('files'),
            "summary": {
                "total_files": len(task_result.result.get('files')),
                "total_issues": task_result.result.get('total_issues'),
                "critical_issues": task_result.result.get('critical_issues'),
            }
        }
    }
    return JSONResponse(result)

@app.post("/analyze-pr", response_class=JSONResponse)
async def create_item(request: Request):
    data = await request.json()
    repo_url = data.get("repo_url")
    repo_name = repo_url.split("/")[-1]
    pr_number = str(data.get("pr_number"))
    github_token = data.get("github_token")
    if not repo_url or not pr_number:
        raise HTTPException(status_code=400, detail="Invalid request")
    response = do_analyze(repo_name, pr_number, github_token)
    return {
        "message": "Request received, keep checking the status",
        "repo": repo_name,
        "pr_number": pr_number,
        "id": response
    }