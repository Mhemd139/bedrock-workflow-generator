from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from fastapi import Body

from src.models.events import SessionTimeline
from src.models.workflow import WorkflowDefinition
from src.core.workflow_generator import WorkflowGenerator


app = FastAPI(
    title="Bedrock Workflow Generator",
    description="AI-powered workflow generation from user session recordings",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize generator
generator = WorkflowGenerator()


class GenerateRequest(BaseModel):
    session: SessionTimeline
    use_ai: bool = True


class GenerateResponse(BaseModel):
    success: bool
    workflow: Optional[WorkflowDefinition] = None
    error: Optional[str] = None


@app.get("/")
def root():
    return {
        "service": "Bedrock Workflow Generator",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    # Test Bedrock connection
    connected = generator.bedrock.test_connection()
    return {
        "status": "healthy" if connected else "degraded",
        "bedrock_connected": connected,
        "model": generator.bedrock.model_id
    }


@app.post("/generate", response_model=GenerateResponse)
def generate_workflow(request: GenerateRequest):
    """Generate a workflow definition from a recorded session"""
    
    try:
        if request.use_ai:
            workflow = generator.generate_from_session(request.session)
        else:
            workflow = generator.generate_from_events_only(request.session)
        
        return GenerateResponse(
            success=True,
            workflow=workflow
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow generation failed: {str(e)}"
        )



@app.post("/generate/friend-format")
async def generate_from_friend_format(friend_data: dict = Body(...)):
    """Accept friend's recording format and convert it"""
    try:
        from src.tools.format_converter import convert_friend_format
        
        # Convert to our format
        session = convert_friend_format(friend_data)
        
        # Generate workflow with AI
        workflow = generator.generate_from_session(session)
        
        # Return as dict (not Pydantic model to avoid serialization issues)
        return {
            "success": True,
            "workflow": workflow.model_dump(mode="json")
        }
    except Exception as e:
        import traceback
        print(f"Error converting format: {e}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)