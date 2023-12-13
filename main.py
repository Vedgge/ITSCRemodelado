from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['encoding'] = 'UTF-8'

from werkzeug.utils import secure_filename

import mysql.connector, os, hashlib, time
from datetime import datetime

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
            titulo VARCHAR(25) NOT NULL,
            descripcion TEXT NOT NULL,
            imagen VARCHAR(255) NOT NULL,
            fechaCreacion DATETIME NOT NULL)''')
        self.conn.commit()
        
        #Cierra el cursor inicial y abrir uno nuevo con parámetro dictorionary=True
        self.cursor.close()
        self.cursor = self.conn.cursor(dictionary=True)
        
    #----------------------------------------------------------------
    def agregar_novedad(self, codigo, titulo, descripcion, imagen, fechaCreacion):
        self.cursor.execute(f"SELECT * FROM novedades WHERE codigo = {codigo}")
        novedad_existe = self.cursor.fetchone()
        if novedad_existe:
            return False
        
        sql = "INSERT INTO novedades (codigo, titulo, descripcion, imagen, fechaCreacion) VALUES (%s, %s, %s, %s, %s)"
        
        valores = (codigo, titulo, descripcion, imagen, fechaCreacion)
        
        
        self.cursor.execute(sql, valores)
        self.conn.commit()
        return True
    #----------------------------------------------------------------
    def consultar_novedad(self, codigo):
        # Consulta una novedad a partir de su código
        self.cursor.execute(f"SELECT * FROM novedades WHERE codigo = {codigo}")
        return self.cursor.fetchone()

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
    def eliminar_novedades(self, codigo):
        # Elimina una novedad de la tabla a partir de su código
        self.cursor.execute(f"DELETE FROM novedades WHERE codigo = {codigo}")
        self.conn.commit()
        return self.cursor.rowcount > 0

    #----------------------------------------------------------------
    def mostrar_novedades(self, codigo):
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
def mostrar_novedades(codigo):
    novedad = catalogoNovedades.consultar_novedad(codigo)
    if novedad:
        return jsonify(novedad), 201
    else:
        return "Novedad no encontrada", 404

@app.route('/novedades', methods=['POST'])
def agregar_novedad():
    #Agarra los datos del form
    codigo = request.form.get('codigo')
    titulo = request.form['titulo']
    descripcion = request.form['descripcion']
    #fechaCreacion = request.form[]
    imagen = request.files['imagen']
    nombre_imagen = ""
    

    #Verifica existencia de la novedad
    novedad = catalogoNovedades.consultar_novedad(codigo)
    if not novedad: # Si no existe la novedad
        # Genera el nombre de la imagen
        nombre_imagen = secure_filename(imagen.filename)
        nombre_base, extension = os.path.splitext(nombre_imagen)
        nombre_imagen = f"{nombre_base}_{int(time.time())}{extension}"
        # Obtiene la fecha actual
        fecha_creacion = datetime.now()
    
    if catalogoNovedades.agregar_novedad(codigo, titulo, descripcion, nombre_imagen, fecha_creacion):
        imagen.save(os.path.join(RUTA_DESTINO, nombre_imagen))
        return jsonify({"mensaje": "Novedad agregada"}), 201
    else:
        return jsonify({"mensaje": "Novedad ya existe"}), 400
#--------------------------------------------------------------------
@app.route("/novedades/<int:codigo>", methods=["PUT"])
def modificar_novedad(codigo):
    #Agarra los datos del form
    nuevo_titulo = request.form.get("titulo")
    nueva_descripcion = request.form.get("descripcion")
    imagen = request.files['imagen']
    nombre_imagen = ""

    # Procesamiento de la imagen
    nombre_imagen = secure_filename(imagen.filename)
    nombre_base, extension = os.path.splitext(nombre_imagen)
    nombre_imagen = f"{nombre_base}_{int(time.time())}{extension}"
    imagen.save(os.path.join(RUTA_DESTINO, nombre_imagen))

    # Busca la novedad guardado
    novedad = novedad = catalogoNovedades.consultar_novedad(codigo)
    if novedad: # Si existe la novedad
        imagen_vieja = novedad["imagen_url"]
        # Arma la ruta a la imagen
        ruta_imagen = os.path.join(RUTA_DESTINO, imagen_vieja)

        # Y si existe la borra
        if os.path.exists(ruta_imagen):
            os.remove(ruta_imagen)
    
    if catalogoNovedades.modificar_novedad(codigo, nuevo_titulo, nueva_descripcion, nombre_imagen):
        return jsonify({"mensaje": "Novedad modificada"}), 200
    else:
        return jsonify({"mensaje": "Novedad no encontrada"}), 403

#--------------------------------------------------------------------
@app.route("/novedades/<int:codigo>", methods=["DELETE"])
def eliminar_novedades(codigo):
    # Busca la novedad guardada
    novedad = novedad = catalogoNovedades.consultar_novedad(codigo)
    if novedad: # Si existe la novedad
        imagen_vieja = novedad["imagen_url"]
        # Arma la ruta a la imagen
        ruta_imagen = os.path.join(RUTA_DESTINO, imagen_vieja)

        # Y si existe la borra
        if os.path.exists(ruta_imagen):
            os.remove(ruta_imagen)

    # Luego, elimina la novedad del catálogo
    if catalogoNovedades.eliminar_novedades(codigo):
        return jsonify({"mensaje": "Novedad eliminada"}), 200
    else:
        return jsonify({"mensaje": "Error al eliminar la novedad"}), 500
    
#--------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)