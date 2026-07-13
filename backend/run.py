import sys
import uvicorn

if __name__ == "__main__":
    print(f"Starting backend with Python: {sys.executable}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
