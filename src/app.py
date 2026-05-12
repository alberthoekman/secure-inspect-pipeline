"""FastAPI application for secure inspection pipeline."""

import uuid
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from .model import ObjectDetectionModel
from .validation import validate_image_file, get_validation_summary, ValidationError
from .monitoring import InferenceMetrics, log_inference_metrics, log_validation_error, log_api_request


# Initialize app
app = FastAPI(
    title="Secure Inspect Pipeline",
    description="Production ML inspection system with YOLOv8",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
model_instance: Optional[ObjectDetectionModel] = None


@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    global model_instance
    try:
        model_instance = ObjectDetectionModel(
            model_name="yolov8n.pt",
            confidence_threshold=0.5,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize model: {str(e)}")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Log request/response times."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    log_api_request(request.method, request.url.path, response.status_code, process_time)
    
    return response

@app.post("/inspect")
async def inspect_image(file: UploadFile = File(...)):
    """
    Main inspection endpoint.

    Accepts image file, validates, runs detection, returns results.
    """
    request_id = str(uuid.uuid4())
    metrics = InferenceMetrics(request_id)

    try:
        if not model_instance:
            raise HTTPException(status_code=503, detail="Model not initialized")

        # Read file bytes
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file")

        # Validate image
        try:
            image, image_metadata = validate_image_file(file_bytes)
        except ValidationError as e:
            log_validation_error(request_id, str(e))
            raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")

        # Run inference
        detections = model_instance.predict(image, metrics)

        # Log metrics
        metrics_dict = metrics.get_metrics()
        log_inference_metrics(metrics_dict)

        # Return response
        return {
            "request_id": request_id,
            "status": "success",
            "image_metadata": {
                "width": image_metadata.width,
                "height": image_metadata.height,
                "format": image_metadata.format,
                "file_size_bytes": image_metadata.file_size_bytes,
            },
            "detections": detections,
            "summary": {
                "total_detections": len(detections),
                "avg_confidence": (
                    sum(d["confidence"] for d in detections) / len(detections)
                    if detections
                    else 0.0
                ),
            },
            "metrics": {
                "inference_time_ms": metrics_dict["inference_time_ms"],
                "total_request_time_ms": metrics_dict["total_request_time_ms"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        metrics.record_error(str(e))
        log_inference_metrics(metrics.get_metrics())
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/batch")
async def batch_inspect(files: list[UploadFile] = File(...)):
    """
    Batch inspection endpoint.

    Process multiple images in one request.
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Max 10 files per batch")

    batch_id = str(uuid.uuid4())
    results = []

    for file in files:
        try:
            file_bytes = await file.read()
            image, image_metadata = validate_image_file(file_bytes)

            metrics = InferenceMetrics(f"{batch_id}-{file.filename}")
            detections = model_instance.predict(image, metrics)
            metrics_dict = metrics.get_metrics()
            log_inference_metrics(metrics_dict)

            results.append({
                "filename": file.filename,
                "status": "success",
                "detections": detections,
                "metrics": metrics_dict,
            })
        except ValidationError as e:
            results.append({
                "filename": file.filename,
                "status": "validation_error",
                "error": str(e),
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e),
            })

    return {
        "batch_id": batch_id,
        "total_files": len(files),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] != "success"),
        "results": results,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Secure Inspect Pipeline",
        "endpoints": {
            "GET /health": "Health check",
            "GET /info": "API info and validation rules",
            "POST /inspect": "Single image inspection",
            "POST /batch": "Batch image inspection",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
