from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
import time
from celery import Celery
import requests

connection_link = "redis://redis:6379/0"

celery_app = Celery('tasks', backend=connection_link, broker=connection_link, result_expires=60 * 60 * 16)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    task_ignore_result=False,
    result_backend='redis://redis:6379/0'
)

llm = OllamaLLM(model="llama3.2", base_url="http://localhost:11434/api/generate")

prompt = PromptTemplate.from_template("""
    You are an experienced code reviewer. Given the following code, identify:
    1. Style issues (e.g., formatting, naming conventions).
    2. Potential bugs or errors.
    3. Performance improvements.
    4. Security vulnerabilities.

    Give me a response as array of issues (object) found with following variables:
    - type (anyone of the following types -> 'style', 'bug', 'performance', 'security')
    - line number (line number where the issue is found)
    - description (description of the issue)
    - suggestion (if applicable)

    Example of the response you are expected to provide:
    ```json
    "issues": [
        {
            "type": "style",
            "line": 15,
            "description": "Line too long",
            "suggestion": "Break line into multiple lines"
        },
        {
            "type": "bug",
            "line": 23,
            "description": "Potential null pointer",
            "suggestion": "Add null check"
        }
    ]```

    Here is the code:
    {code_changes}
""")

def parse_issues(raw_text, file_name):
    issues = []
    lines = raw_text.split("\n")

    categories = ["Style Issues", "Potential Bugs or Errors", "Performance Improvements", "Security Vulnerabilities"]
    current_category = None

    for line in lines:
        for category in categories:
            if category in line:
                current_category = category
                break
        
        if "Line Number" in line:
            issue_line = int(line.split(":")[1].strip())
            description = lines[lines.index(line) + 1].split(":")[1].strip()
            suggestion = lines[lines.index(line) + 2].split(":")[1].strip()

            issues.append({
                "type": current_category.split()[0].lower(),
                "line": issue_line,
                "description": description,
                "suggestion": suggestion
            })

    return {
        "name": file_name,
        "issues": issues
    }

chain = prompt | llm

@celery_app.task
def process_pr(repo_url, pr_number, files):
    try:
        start = time.time()
        print(f'Started on process {repo_url} of user with pr_number: {pr_number}.')

        reviewed_files = []

        total_issues = 0
        critical_issues = 0

        for file in files:
            file_name = file['filename']
            file_url = file['raw_url']
            file_content = requests.get(file_url).text
            review = chain.invoke({
                "code_changes": f"{file_content}"
            }, kwargs={
                "stream": False
            })
            reviewed_file = parse_issues(review, file_name)
            print(reviewed_file)
            reviewed_files.append(reviewed_file)

            total_issues += len(reviewed_file['issues'])
            critical_issues += sum(1 for issue in reviewed_file['issues'] if issue['type'] == 'security')

            elapsed_time = time.time() - start
            if elapsed_time > 900000:
                raise Exception("Time limit exceeded")

        end = time.time()
        print(f'Finished on process {repo_url} of user with pr_number: {pr_number}. Time taken: {end - start} seconds.')

        result = {
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "files": reviewed_files
        }

        return result
    except Exception as e:
        print(f'Error on process {repo_url} of user with pr_number: {pr_number}. Error: {e}')
        return {
            "total_issues": 0,
            "critical_issues": 0,
            "files": [],
            "error": str(e)
        }
