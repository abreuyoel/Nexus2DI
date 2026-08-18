# Pautas de Arquitectura - Nexus2DI

Este documento contiene lecciones aprendidas y directrices de arquitectura para evitar problemas recurrentes en este proyecto.

## 1. Mapeo de Rutas (Trailing Slashes) y Errores CSP en QA/Producción

### Contexto
En los entornos de QA y producción, la aplicación corre detrás de un proxy/balanceador de carga con terminación SSL (como Cloudflare Tunnel e Ingress de Kubernetes). 
El navegador se conecta vía **HTTPS**, pero la comunicación interna redirigida al contenedor de FastAPI (Python) ocurre sobre **HTTP**.

### Problema de Redirección (HTTP 307 / 301)
FastAPI tiene habilitada por defecto la redirección automática de barras inclinadas (`redirect_slashes=True`). Si un endpoint se define en el backend con una barra inclinada al final (ej. `@router.get("/")` bajo el prefijo `/api/users`), y el frontend realiza la llamada sin ella (`/api/users`), FastAPI responde con una redirección temporal `HTTP 307` apuntando a la ruta con barra inclinada.

Dado que la petición interna que recibe FastAPI es HTTP, FastAPI genera la dirección de redirección como `http://qa.nexus2di.net/api/users/`. Al recibir esta respuesta, el navegador intenta conectar por HTTP, lo cual viola inmediatamente la directiva de Content Security Policy (CSP) del frontend (`connect-src 'self' https://...`) y bloquea la petición arrojando un error en la consola y dejando la pantalla colgada (504 Gateway Timeout).

### Directriz de Solución
Para evitar cualquier redirección interna en FastAPI que rompa las políticas CSP:
1.  **Definir endpoints raíz sin barra inclinada**: Registra las rutas raíz en el backend utilizando path vacío `""` en lugar de `"/"` (ej. `@router.get("")` o `@router.post("")`).
2.  **Rutas de sub-recursos limpias**: Mantén las rutas sin barras finales (ej. `@router.get("/{id}")`).
3.  **Remover `redirect_slashes=False` de main.py**: Deja que FastAPI use su valor predeterminado para soportar ambas variantes cuando sea seguro, pero la regla primordial es definir los decorators del router sin slash al final para resolver la coincidencia exacta de inmediato.

---

## 2. Patrón de Carga Masiva (Carga Masiva con Excel)

### Directriz de Implementación
*   **Procesamiento en Servidor**: El análisis detallado de celdas y el upsert de base de datos se realiza en el backend (usando `pandas` y `openpyxl`). Esto evita sobrecargar la memoria del navegador con grids pesadas (300+ registros) y manuales.
*   **Validación Rápida en Cliente**: El frontend utiliza SheetJS únicamente para:
    1.  Verificar que el archivo corresponda al cliente seleccionado (leyendo el ID en la celda `B5`).
    2.  Validar la estructura del documento y avisar errores obvios antes de transferir bytes por red.
*   **Envío Seguro**: Si la validación local es exitosa, el frontend adjunta el archivo binario a un objeto `FormData` y lo envía al endpoint del backend `POST /api/frecuencias-pdvs-cliente/importar-excel`.
*   **Transaccional**: El backend procesa las filas a partir del renglón 10 e impacta la base de datos dentro de una única transacción, devolviendo un conteo de registros creados y modificados.
