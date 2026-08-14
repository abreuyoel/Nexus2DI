# crear_estructura_epran_qa.py
from azure.storage.blob import BlobServiceClient

connection_string = ""
container_name = "epran-qa"

carpetas = [
    "activaciones",
    "activaciones_auditor",
    "activaciones_auditor_campo",
    "auditor_campo",
    "auditor_categoria",
    "desactivacion",
    "desactivaciones",
    "desactivaciones_auditor_campo",
    "exhibiciones",
    "fotos",
    "gestion",
    "materialpop",
    "precios",
    "etiquetas",
]

blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# 1) Crear el contenedor si no existe
container_client = blob_service_client.get_container_client(container_name)
if not container_client.exists():
    container_client.create_container()
    print(f"Contenedor '{container_name}' creado.")
else:
    print(f"Contenedor '{container_name}' ya existía, no lo toco.")

# 2) Un blob vacío "carpeta/.keep" por cada carpeta -- hace que el prefijo
#    aparezca como carpeta en el Explorador de almacenamiento del portal,
#    sin copiar ninguna foto real.
for carpeta in carpetas:
    blob_name = f"{carpeta}/.keep"
    container_client.upload_blob(name=blob_name, data=b"", overwrite=True)
    print(f"Carpeta creada: {carpeta}/")

print("Listo.")