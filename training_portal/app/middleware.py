"""
Middleware

Error handling, CORS, and request logging.
"""

import logging
import time
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Exception error handler."""
    
    @staticmethod
    async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all exceptions and return JSON response."""
        
        # Log error
        logger.error(
            f"Request {request.method} {request.url.path} failed: {str(exc)}",
            exc_info=True
        )
        
        # Map exception to response
        status_code = 500
        code = "INTERNAL_ERROR"
        message = "An error occurred"
        
        # Common exceptions
        if isinstance(exc, ValueError):
            status_code = 400
            code = "VALIDATION_ERROR"
            message = str(exc)
        elif isinstance(exc, KeyError):
            status_code = 404
            code = "NOT_FOUND"
            message = str(exc)
        elif isinstance(exc, PermissionError):
            status_code = 403
            code = "PERMISSION_DENIED"
            message = str(exc)
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": message,
                "code": code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class RequestLogger:
    """Request logging middleware."""
    
    @staticmethod
    async def log_request(request: Request, call_next):
        """Log incoming request and response."""
        
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - "
                f"{response.status_code} ({process_time:.2f}s)"
            )
            
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} ({process_time:.2f}s)",
                exc_info=exc
            )
            raise


def setup_middleware(app: FastAPI, config) -> None:
    """Setup all middleware."""
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5173",
        ] if not config.is_production else ["https://training.company.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request logging
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        return await RequestLogger.log_request(request, call_next)
    
    logger.info("Middleware setup complete")


def setup_error_handlers(app: FastAPI) -> None:
    """Setup all error handlers."""
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return await ErrorHandler.exception_handler(request, exc)
    
    logger.info("Error handlers setup complete")