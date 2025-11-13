from fastapi import APIRouter, UploadFile
from .langgraph_core import chef_graph

router = APIRouter(prefix="/api/chef", tags=["ChefAI"])

@router.post("/run")
async def run_pipeline(image: UploadFile):
    # قراءة الصورة وتحويلها إلى base64
    data = await image.read()
    image_b64 = base64.b64encode(data).decode()
    
    # تشغيل LangGraph
    result = chef_graph.invoke({"image": image_b64})
    return result
