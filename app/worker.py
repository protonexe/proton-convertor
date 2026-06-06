import os
from celery import Celery
from pathlib import Path
from app.core.graph import engine
import shutil

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(bind=True)
def conversion_task(self, input_path_str: str, target_format: str, output_path_str: str, options: dict = None, tool_id: str = None):
    """
    Asynchronous task to handle file conversion or tool execution.
    """
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)
    
    # Setup Redis for real-time progress updates
    import redis
    r = redis.from_url(REDIS_URL)
    
    def update_progress(status, progress):
        r.publish(f"task_progress_{self.request.id}", json.dumps({"status": status, "progress": progress}))

    try:
        update_progress("processing", 10)
        import asyncio
        
        if tool_id:
            # Execute tool directly
            from app.core.registry_instance import registry
            tool = registry.get_tool(tool_id)
            if not tool:
                raise ValueError(f"Tool {tool_id} not found in registry")
            result_path = asyncio.run(tool.convert(input_path, output_path, options=options))
        else:
            # Execute graph-based conversion
            result_path = asyncio.run(engine.convert(input_path, target_format, options=options))
        
        update_progress("processing", 90)
        if result_path.exists():
            # If the tool already wrote to output_path, result_path might be output_path
            if result_path != output_path:
                shutil.move(str(result_path), str(output_path))
            
        update_progress("completed", 100)
        return {"status": "completed", "output_path": str(output_path)}
    except Exception as e:
        update_progress("failed", 0)
        self.update_state(state='FAILURE', meta={'exc': str(e)})
        raise e
