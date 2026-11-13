
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
import uuid
from dotenv import load_dotenv
from supabase import create_client

app = Flask(__name__)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
print("Carpeta actual:", os.getcwd())
print("Archivo .env encontrado:", os.path.exists(".env"))
print("URL encontrada:", bool(os.getenv("SUPABASE_URL")))
print("KEY encontrada:", bool(os.getenv("SUPABASE_KEY")))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("Carpeta actual:", os.getcwd())
print("Archivo .env encontrado:", os.path.exists(".env"))
print("URL encontrada:", bool(SUPABASE_URL))
print("KEY encontrada:", bool(SUPABASE_KEY))

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Conexión inicializada correctamente")
else:
    print("Faltan las credenciales de Supabase")
    exit()
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-temporal-para-desarrollo")

# Carpeta de fotografías
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Formatos permitidos
EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}


@app.route("/")
def inicio():
    fotografias = sorted(os.listdir(app.config["UPLOAD_FOLDER"]))

    return render_template(
        "index.html",
        fotografias=fotografias
    )


@app.route("/subir", methods=["POST"])
def subir():
    fotografias = request.files.getlist("fotografias")

    for foto in fotografias:

        if foto and foto.filename:
            nombre = secure_filename(foto.filename)
            extension = nombre.rsplit(".", 1)[-1].lower()

            if extension in EXTENSIONES_PERMITIDAS:
                if not foto.mimetype.startswith("image/"):
                    continue

                nuevo_nombre = f"{uuid.uuid4().hex}.{extension}"

                ruta = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    nuevo_nombre
                )

                foto.save(ruta)

    return redirect(url_for("inicio"))

@app.route("/uploads/<nombre>")
def mostrar_foto(nombre):
    from flask import send_from_directory

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        nombre
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

