from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, template_folder="templates")
CORS(app)
app.config['encoding'] = 'UTF-8'

from werkzeug.utils import secure_filename

import mysql.connector, os, time

class centroNovedades:
    #Constructor de la clase centroNovedades
    def __init__(self, host, user, password, database):
        #Establece una conexión sin especificar la base de datos
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )
        self.cursor = self.conn.cursor()
        
        #Intenta seleccionar la base de datos
        try:
            self.cursor.execute(f"USE {database}")
        except mysql.connector.Error as err:
            #Si la base de datos no existe, la crea
            if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
                self.cursor.execute(f"CREATE DATABASE {database}")
                self.conn.database = database
            else:
                raise err
        
        # Si la tabla 'novedades' no existe, la crea
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
            codigo INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            titulo VARCHAR(255) NOT NULL,
            descripcion TEXT NOT NULL,
            imagen_url VARCHAR(255) NOT NULL,
            fechaCreacion DATETIME NOT NULL)''')
        self.conn.commit()
        
        #Cierra el cursor inicial y abrir uno nuevo con parámetro dictorionary=True
        self.cursor.close()
        self.cursor = self.conn.cursor(dictionary=True)
        
    #----------------------------------------------------------------
    def agregar_novedad(self, titulo, descripcion, imagen, fechaCreacion):
        # If no image is provided, use a default image name
        if not imagen:
            imagen = 'imagen-predeterminada-novedad.jpg'

        sql = "INSERT INTO novedades (titulo, descripcion, imagen_url, fechaCreacion) VALUES (%s, %s, %s, %s)"
        valores = (titulo, descripcion, imagen, fechaCreacion)

        self.cursor.execute(sql, valores)
        self.conn.commit()
        return True
    #----------------------------------------------------------------
    # def consultar_novedad(self, codigo):
    #     # Consulta una novedad a partir de su código
    #     self.cursor.execute(f"SELECT * FROM novedades WHERE codigo = {codigo}")
    #     return self.cursor.fetchone()
    
    def consultar_novedad(self, codigo):
        if codigo is not None:
            self.cursor.execute(f"SELECT * FROM novedades WHERE codigo = {codigo}")
            return self.cursor.fetchone()
        else:
            return None
    #----------------------------------------------------------------
    def modificar_novedad(self, codigo, nuevo_titulo, nueva_descripcion, nueva_imagen):
        sql = "UPDATE novedades SET titulo = %s, descripcion = %s, imagen_url = %s WHERE codigo = %s"
        valores = (nuevo_titulo, nueva_descripcion, nueva_imagen, codigo)
        self.cursor.execute(sql, valores)
        self.conn.commit()
        return self.cursor.rowcount > 0

    #----------------------------------------------------------------
    def listar_novedades(self):
        self.cursor.execute("SELECT * FROM novedades")
        novedades = self.cursor.fetchall()
        return novedades

    #----------------------------------------------------------------
    def eliminar_novedad(self, codigo):
        # Elimina una novedad de la tabla a partir de su código
        self.cursor.execute(f"DELETE FROM novedades WHERE codigo = {codigo}")
        self.conn.commit()
        return self.cursor.rowcount > 0

    #----------------------------------------------------------------
    def mostrar_novedad(self, codigo):
        # Muestra los datos de un novedad a partir de su código
        novedad = self.consultar_novedad(codigo)
        if novedad:
            print("-" * 40)
            print(f"Código...........: {novedad['codigo']}")
            print(f"Título...........: {novedad['titulo']}")
            print(f"Descripción......: {novedad['descripcion']}")
            print(f"Imagen...........: {novedad['imagen_url']}")
            print(f"Fecha de creación: {novedad['fechaCreacion']}")
            print("-" * 40)
        else:
            print("Novedad no encontrada.")

#--------------------------------------------------------------------
#--------------------------------------------------------------------
# Crea una instancia de la clase centroNovedades
catalogoNovedades = centroNovedades(host='localhost', user='root', password='', database='itsc')

# Carpeta para guardar las imagenes
RUTA_DESTINO = './static/imagenes-novedades/'

@app.route("/novedades", methods=["GET"])
def listar_novedades():
    novedades = catalogoNovedades.listar_novedades()
    return jsonify(novedades)

@app.route("/novedades/<int:codigo>", methods=["GET"])
def mostrar_novedad(codigo):
    novedad = catalogoNovedades.consultar_novedad(codigo)
    print("Novedad object:", novedad)
    if novedad:
        return render_template("mostrar-novedad.html", novedad=novedad)
    else:
        return "Novedad no encontrada", 404

@app.route('/novedades', methods=['POST'])
def agregar_novedad():
    codigo = request.form.get('codigo')
    titulo = request.form['titulo']
    descripcion = request.form['descripcion']
    
    # Usamos get en caso de que 'imagen' no este presente
    imagen = request.files.get('imagen')  

    # Verifica la existencia de la novedad
    novedad = catalogoNovedades.consultar_novedad(codigo)
    if not novedad:  # Si la novedad no existe
        # Genera el nombre de la imagen o usa el predeterminado
        if imagen:
            nombre_imagen = secure_filename(imagen.filename)
            nombre_base, extension = os.path.splitext(nombre_imagen)
            nombre_imagen = f"{nombre_base}_{int(time.time())}{extension}"
        else:
            nombre_imagen = 'imagen-predeterminada-novedad.jpg'
        # Obtiene la fecha y hora actual
        fecha_creacion = datetime.now()

    if catalogoNovedades.agregar_novedad(titulo, descripcion, nombre_imagen, fecha_creacion):
        if imagen:
            imagen.save(os.path.join(RUTA_DESTINO, nombre_imagen))
        return jsonify({"mensaje": "Novedad agregada"}), 201
    else:
        return jsonify({"mensaje": "Novedad ya existe"}), 400
#--------------------------------------------------------------------
@app.route("/novedades/<int:codigo>/editar", methods=["GET", "PUT"])
def editar_novedad(codigo):
    print(f'Solicitud PUT recibida para la novedad con código {codigo}')
    if request.method == "GET":
        # Muestra la plantilla de edición de novedad con los datos actuales
        novedad = catalogoNovedades.consultar_novedad(codigo)
        if novedad:
            return render_template("editar-novedad.html", novedad=novedad)
        else:
            return jsonify({"mensaje": "Novedad no encontrada"}), 403
    elif request.method == "PUT":
        # Agarra los datos del formulario
        nuevo_titulo = request.json.get("titulo")
        nueva_descripcion = request.json.get("descripcion")
        imagen = request.files.get('imagen')  # Usa get en lugar de ['imagen']
        nombre_imagen = ""

        # Procesamiento de la imagen
        if imagen:
            nombre_imagen = secure_filename(imagen.filename)
            nombre_base, extension = os.path.splitext(nombre_imagen)
            nombre_imagen = f"{nombre_base}_{int(time.time())}{extension}"
            imagen.save(os.path.join(RUTA_DESTINO, nombre_imagen))

        # Busca la novedad guardada
        novedad = catalogoNovedades.consultar_novedad(codigo)
        if novedad:  # Si existe la novedad
            imagen_vieja = novedad["imagen_url"]
            # Arma la ruta a la imagen
            ruta_imagen = os.path.join(RUTA_DESTINO, imagen_vieja)

            # Y si existe, la borra
            if os.path.exists(ruta_imagen):
                os.remove(ruta_imagen)

        if catalogoNovedades.modificar_novedad(codigo, nuevo_titulo, nueva_descripcion, nombre_imagen):
            return jsonify({"mensaje": "Novedad modificada"}), 200
        else:
            return jsonify({"mensaje": "Novedad no encontrada"}), 403

    if request.method == "GET":
        # Muestra la plantilla de edición de novedad con los datos actuales
        novedad = catalogoNovedades.consultar_novedad(codigo)
        if novedad:
            return render_template("editar-novedad.html", novedad=novedad)
        else:
            return jsonify({"mensaje": "Novedad no encontrada"}), 403
    elif request.method == "PUT":
        # Agarra los datos del formulario
        nuevo_titulo = request.form.get("titulo")
        nueva_descripcion = request.form.get("descripcion")
        imagen = request.files.get('imagen')  # Usa get en lugar de ['imagen']
        nombre_imagen = ""

        # Procesamiento de la imagen
        if imagen:
            nombre_imagen = secure_filename(imagen.filename)
            nombre_base, extension = os.path.splitext(nombre_imagen)
            nombre_imagen = f"{nombre_base}_{int(time.time())}{extension}"
            imagen.save(os.path.join(RUTA_DESTINO, nombre_imagen))

        # Busca la novedad guardada
        novedad = catalogoNovedades.consultar_novedad(codigo)
        if novedad:  # Si existe la novedad
            imagen_vieja = novedad["imagen_url"]
            # Arma la ruta a la imagen
            ruta_imagen = os.path.join(RUTA_DESTINO, imagen_vieja)

            # Y si existe, la borra
            if os.path.exists(ruta_imagen):
                os.remove(ruta_imagen)

        if catalogoNovedades.modificar_novedad(codigo, nuevo_titulo, nueva_descripcion, nombre_imagen):
            return jsonify({"mensaje": "Novedad modificada"}), 200
        else:
            return jsonify({"mensaje": "Novedad no encontrada"}), 403
#--------------------------------------------------------------------
@app.route("/novedades/<int:codigo>", methods=["DELETE"])
def eliminar_novedad(codigo):
    # Busca la novedad guardada
    novedad = catalogoNovedades.consultar_novedad(codigo)
    if novedad: # Si existe la novedad
        imagen_vieja = novedad["imagen_url"]
        imagen_predeterminada = 'imagen-predeterminada-novedad.jpg'
        if not imagen_vieja == imagen_predeterminada:
            # Arma la ruta a la imagen
            ruta_imagen = os.path.join(RUTA_DESTINO, imagen_vieja)

            # Y si existe la borra
            if os.path.exists(ruta_imagen):
                os.remove(ruta_imagen)

        # Luego, elimina la novedad del catálogo
        if catalogoNovedades.eliminar_novedad(codigo):
            return jsonify({"mensaje": "Novedad eliminada"}), 200
        else:
            return jsonify({"mensaje": "Error al eliminar la novedad"}), 500
    else:
        return jsonify({"mensaje": "Novedad no encontrada"}), 404

    
#--------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)