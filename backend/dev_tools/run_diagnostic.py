import uvicorn
import sys

if __name__ == "__main__":
    print("Iniciando servidor de diagnóstico. Los errores se guardarán en diagnostic_error.log")
    
    # Redirigir stdout y stderr a un archivo para capturar cualquier crash duro o error de Uvicorn
    with open("diagnostic_error.log", "w", encoding="utf-8") as f:
        sys.stdout = f
        sys.stderr = f
        
        try:
            uvicorn.run(
                "app.main:app",
                host="0.0.0.0",
                port=8000,
                reload=False, # Desactivar reload para que los errores del proceso principal no se pierdan
                log_level="debug",
            )
        except Exception as e:
            print(f"Server crashed: {e}")
