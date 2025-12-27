from fastapi import APIRouter, Depends, HTTPException
from app.schemas import IssueGenerateRequest, IssueGenerateResponse, IssueCreateRequest, IssueCreateResponse
from app.services.issue_service import IssueService
from app.routers.auth import get_github_token

router = APIRouter(prefix="/issue", tags=["Issue"])
issue_service = IssueService()

@router.post("/generate", response_model=IssueGenerateResponse)
async def generate_issue_draft(request: IssueGenerateRequest, token: str = Depends(get_github_token)):
    """
    生成 Issue 草稿
    """
    try:
        result = await issue_service.generate_draft(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=IssueCreateResponse, status_code=201)
async def create_issue(request: IssueCreateRequest, token: str = Depends(get_github_token)):
    """
    提交 Issue 到 GitHub
    """
    try:
        result = await issue_service.submit_issue(request, token)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))