from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_file
)
from werkzeug.utils import secure_filename
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from dotenv import load_dotenv
from supabase import create_client
import os
import uuid
import mimetypes

app = Flask(__name__)

# CONFIGURACIÓN
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app.secret_key = os.getenv("SECRET_KEY", "clave-temporal-desarrollo")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BUCKET = "Fotos evento"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan las credenciales de Supabase")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Conexión con Supabase inicializada correctamente")

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}


# OBTENER FOTOGRAFÍAS
def obtener_fotografias():
    archivos = supabase.storage.from_(BUCKET).list()

    fotografias = []

    for archivo in archivos:
        nombre = archivo.get("name") if isinstance(archivo, dict) else archivo.name

        if nombre and "." in nombre:
            extension = nombre.rsplit(".", 1)[-1].lower()

            if extension in EXTENSIONES_PERMITIDAS:
                fotografias.append(nombre)

    return sorted(fotografias)


# INICIO Y GALERÍA
@app.route("/")
def inicio():
    try:
        fotografias = obtener_fotografias()

        return render_template(
            "index.html",
            fotografias=fotografias
        )

    except Exception as e:
        print("Error al cargar la galería:", repr(e))
        return "No se pudo cargar la galería.", 500


# SUBIR FOTOGRAFÍAS
@app.route("/subir", methods=["POST"])
def subir():
    fotografias = request.files.getlist("fotografias")
    exitos = 0

    for foto in fotografias:
        if not foto or not foto.filename:
            continue

        nombre = secure_filename(foto.filename)

        if "." not in nombre:
            continue

        extension = nombre.rsplit(".", 1)[-1].lower()

        if extension not in EXTENSIONES_PERMITIDAS:
            continue

        if not foto.mimetype or not foto.mimetype.startswith("image/"):
            continue

        nuevo_nombre = f"{uuid.uuid4().hex}.{extension}"

        try:
            contenido = foto.read()

            if not contenido:
                continue

            supabase.storage.from_(BUCKET).upload(
                path=nuevo_nombre,
                file=contenido,
                file_options={
                    "content-type": foto.mimetype,
                    "cache-control": "3600",
                    "upsert": "false"
                }
            )

            exitos += 1
            print("Fotografía subida:", nuevo_nombre)

        except Exception as e:
            print("Error al subir fotografía:", repr(e))

    flash(f"Se subieron {exitos} fotografía(s).")
    return redirect(url_for("inicio"))


# MOSTRAR FOTOGRAFÍAS
@app.route("/uploads/<nombre>")
def mostrar_foto(nombre):
    try:
        if secure_filename(nombre) != nombre:
            return "Nombre inválido.", 400

        url = supabase.storage.from_(BUCKET).get_public_url(nombre)
        return redirect(url)

    except Exception as e:
        print("Error al mostrar fotografía:", repr(e))
        return "No se pudo mostrar la fotografía.", 500


# ELIMINAR FOTOGRAFÍA
@app.route("/eliminar/<nombre>", methods=["POST"])
def eliminar_foto(nombre):
    if secure_filename(nombre) != nombre:
        return "Nombre inválido.", 400

    try:
        supabase.storage.from_(BUCKET).remove([nombre])
        flash("Fotografía eliminada correctamente.")

    except Exception as e:
        print("Error al eliminar fotografía:", repr(e))
        flash("No se pudo eliminar la fotografía.")

    return redirect(url_for("inicio"))


# DESCARGAR UNA FOTOGRAFÍA
@app.route("/descargar/<nombre>")
def descargar_foto(nombre):
    if secure_filename(nombre) != nombre:
        return "Nombre inválido.", 400

    try:
        contenido = supabase.storage.from_(BUCKET).download(nombre)

        tipo = mimetypes.guess_type(nombre)[0] or "application/octet-stream"

        return send_file(
            BytesIO(contenido),
            mimetype=tipo,
            as_attachment=True,
            download_name=nombre
        )

    except Exception as e:
        print("Error al descargar fotografía:", repr(e))
        return "No se pudo descargar la fotografía.", 500


# DESCARGAR TODO EL ÁLBUM EN ZIP
@app.route("/descargar-album")
def descargar_album():
    try:
        fotografias = obtener_fotografias()

        if not fotografias:
            flash("Todavía no hay fotografías para descargar.")
            return redirect(url_for("inicio"))

        memoria = BytesIO()

        with ZipFile(memoria, "w", ZIP_DEFLATED) as zip_album:
            for nombre in fotografias:
                try:
                    contenido = supabase.storage.from_(BUCKET).download(nombre)
                    zip_album.writestr(nombre, contenido)

                except Exception as e:
                    print("Error al incluir fotografía:", nombre, repr(e))

        memoria.seek(0)

        return send_file(
            memoria,
            mimetype="application/zip",
            as_attachment=True,
            download_name="Album_Daniel_y_Laura.zip"
        )

    except Exception as e:
        print("Error al crear álbum ZIP:", repr(e))
        return "No se pudo generar el álbum.", 500


# INICIAR SERVIDOR
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

