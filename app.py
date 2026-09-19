from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# Creación de la aplicación
app = Flask(__name__)

# Configuración obligatoria para usar sesiones en Flask
app.secret_key = "clave_secreta_tus_finanzas_360"

# Configuración de la conexión a MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Escribe aquí tu contraseña si tienes una en XAMPP/MySQL
    "database": "tusfinanzas360"
}

# Función para obtener una conexión
def get_connection():
    return mysql.connector.connect(**db_config)


def registrar_notificacion(id_usuario, mensaje, id_tipo):
    conexion = get_connection()
    cursor = conexion.cursor()
    try:
        sql = """
        INSERT INTO notificaciones (mensaje, id_usuario, ID_Tipo) 
        VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (mensaje, id_usuario, id_tipo))
        conexion.commit()
    except Exception as e:
        print(f"Error al crear notificación: {e}")
    finally:
        cursor.close()
        conexion.close()


def obtener_balance(id_usuario):

    conexion = get_connection()
    cursor = conexion.cursor()

    # Total ingresos
    cursor.execute("""
        SELECT COALESCE(SUM(monto),0)
        FROM ingresos
        WHERE id_usuario=%s
    """, (id_usuario,))
    ingresos = float(cursor.fetchone()[0])

    # Total gastos
    cursor.execute("""
        SELECT COALESCE(SUM(monto),0)
        FROM gastos
        WHERE id_usuario=%s
    """, (id_usuario,))
    gastos = float(cursor.fetchone()[0])

    # Total ahorrado en metas
    cursor.execute("""
        SELECT COALESCE(SUM(monto_aportado),0)
        FROM Aportes_Metas
        WHERE id_usuario=%s
    """, (id_usuario,))
    ahorros = float(cursor.fetchone()[0])

    cursor.close()
    conexion.close()

    balance = ingresos - gastos - ahorros

    return ingresos, gastos, balance


def obtener_movimientos(id_usuario):

    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            fecha,
            descripcion,
            monto,
            'income' AS tipo
        FROM ingresos
        WHERE id_usuario=%s
    """, (id_usuario,))
    ingresos = cursor.fetchall()

    cursor.execute("""
        SELECT
            fecha,
            descripcion,
            monto,
            'expense' AS tipo
        FROM gastos
        WHERE id_usuario=%s
    """, (id_usuario,))
    gastos = cursor.fetchall()

    cursor.close()
    conexion.close()

    movimientos = ingresos + gastos
    movimientos.sort(key=lambda x: x["fecha"], reverse=True)

    return movimientos

# --- RUTAS DE NAVEGACIÓN BÁSICA ---

# Página principal
@app.route("/")
def inicio():
    return render_template("index.html")

# Página Nosotros
@app.route("/nosotros")
def nosotros():
    return render_template("quienesomos.html")

# Página Misión y Visión
@app.route("/mision")
def mision():
    return render_template("mision.html")

# Página Términos
@app.route("/terminos")
def terminos():
    return render_template("terminos.html")


# --- RUTAS DE GESTIÓN DE USUARIOS ---

# Página Registro
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":

        nombre = request.form["nombre"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        

        contrasena_plana = request.form["password"]
        contrasena_encriptada = generate_password_hash(contrasena_plana)
        
        edad = request.form["edad"]
        genero = request.form["genero"]
        
        conexion = get_connection()
        cursor = conexion.cursor()

        sql = """
        INSERT INTO usuario
        (nombre, correo, telefono, contrasena, edad, genero, ID_Rol) 
        VALUES (%s, %s, %s, %s, %s, %s, 1)
        """

        datos = (
            nombre, correo, telefono, contrasena_encriptada, edad, genero
        )

        try:
            cursor.execute(sql, datos)
            conexion.commit()
            
            session['usuario_reciente_id'] = cursor.lastrowid
            
        except Exception as e:
            print(f"Error al registrar usuario: {e}")
        finally:
            cursor.close()
            conexion.close()

        return redirect(url_for('verificacion'))

    return render_template("registrousuario.html")


# Página de Pregunta de Verificación
@app.route("/verificacion", methods=["GET", "POST"])
def verificacion():

    if 'usuario_reciente_id' not in session:
        return redirect(url_for('registro'))

    if request.method == "POST":
        pregunta = request.form["pregunta"]
        respuesta = request.form["respuesta"]
        

        id_usuario = session['usuario_reciente_id']
        
        conexion = get_connection()
        cursor = conexion.cursor()

        try:

            sql = """
            UPDATE usuario
            SET pregunta_seguridad = %s, respuesta_seguridad = %s 
            WHERE id_usuario = %s
            """
            
            datos = (pregunta, respuesta, id_usuario)
            
            cursor.execute(sql, datos)
            conexion.commit()
            
            session.pop('usuario_reciente_id', None)
            
        except Exception as e:
            print(f"Error al registrar pregunta de seguridad: {e}")
            
        finally:
            cursor.close()
            conexion.close()

        return redirect(url_for('menu'))

    return render_template("verificacion.html")


# Página Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if 'usuario_id' in session:
        return redirect(url_for('menu'))

    error = None 

    if request.method == "POST":

        correo = request.form["correo"]
        contrasena_ingresada = request.form["password"]

        conexion = get_connection()

        cursor = conexion.cursor(dictionary=True)

        try:
            sql = "SELECT * FROM usuario WHERE correo = %s"
            cursor.execute(sql, (correo,))
            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario['contrasena'], contrasena_ingresada):
                
                session['usuario_id'] = usuario['id_usuario']
                session['nombre_usuario'] = usuario['nombre']
                session['rol_id'] = usuario['ID_Rol']
                
                # --- NUEVO: CREAR UN RECORDATORIO AL ENTRAR ---
                ingresos, gastos, balance = obtener_balance(usuario['id_usuario'])
                if balance < 50000: # Si tiene menos de 50,000 disponible
                    registrar_notificacion(usuario['id_usuario'], "¡Cuidado! Tu balance actual es bajo, cuida tus gastos.", 3)
                
                return redirect(url_for('menu'))
                
                return redirect(url_for('menu'))
            else:

                error = "Correo o contraseña incorrectos. Por favor, intenta de nuevo."

        except Exception as e:
            print(f"Error al iniciar sesión: {e}")
            error = "Ocurrió un error interno. Intenta más tarde."
        finally:
            cursor.close()
            conexion.close()


    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dinero")
def dinero():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    ingresos, gastos, balance = obtener_balance(session["usuario_id"])

    movimientos = obtener_movimientos(
        session["usuario_id"]
    )

    return render_template(

        "Dinero.html",

        ingresos=ingresos,
        gastos=gastos,
        balance=balance,
        movimientos=movimientos

    )

@app.route("/agregar_movimiento", methods=["POST"])
def agregar_movimiento():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    descripcion = request.form["descripcion"]
    monto = float(request.form["monto"])
    tipo = request.form["tipo"]

    conexion = get_connection()
    cursor = conexion.cursor()

    if tipo == "income":
        cursor.execute("""
            INSERT INTO ingresos (monto, descripcion, id_usuario)
            VALUES (%s, %s, %s)
        """, (monto, descripcion, session["usuario_id"]))
        
        # NOTIFICACIÓN DE INGRESO (Tipo 3)
        mensaje = f"Has registrado un ingreso de ${monto} ({descripcion})."
        registrar_notificacion(session["usuario_id"], mensaje, 3) 

    else:
        cursor.execute("""
            INSERT INTO gastos (monto, descripcion, id_usuario)
            VALUES (%s, %s, %s)
        """, (monto, descripcion, session["usuario_id"]))
        
        # NOTIFICACIÓN DE GASTO (Tipo 1)
        # Si es un gasto muy grande, puedes hacerlo más alarmante
        if monto > 100000:
            mensaje = f"¡Alerta de Gasto Mayor! Registraste un gasto de ${monto} en {descripcion}."
        else:
            mensaje = f"Has registrado un gasto de ${monto} ({descripcion})."
            
        registrar_notificacion(session["usuario_id"], mensaje, 1)

    conexion.commit()
    cursor.close()
    conexion.close()

    return redirect(url_for("dinero"))

@app.route("/menu")
def menu():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    id_usuario = session["usuario_id"]

    ingresos, gastos, balance = obtener_balance(id_usuario)

    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            ID_Metas,
            Nombre,
            Monto_Actual,
            Monto_Objetivo
        FROM Metas
        WHERE ID_usuario=%s
        ORDER BY ID_Metas DESC
        LIMIT 3
    """,(id_usuario,))

    metas = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "Menu.html",
        balance=balance,
        metas=metas
    )

@app.route('/api/datos-finanzas')
def api_datos_finanzas():
    # 1. Verificamos usando el nombre exacto que usaste en tu /login
    if 'usuario_id' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    id_usuario = session['usuario_id']

    try:
        # 2. Usamos tu función global para conectarnos (más limpio y seguro)
        db = get_connection()
        cursor = db.cursor(dictionary=True)
        
        # Consultamos INGRESOS agrupados por mes/año para el usuario actual
        cursor.execute("""
            SELECT DATE_FORMAT(fecha, '%Y-%m') AS mes, SUM(monto) AS total 
            FROM ingresos 
            WHERE id_usuario = %s
            GROUP BY mes
            ORDER BY mes ASC
        """, (id_usuario,))
        datos_ingresos = cursor.fetchall()

        # Consultamos GASTOS agrupados por mes/año para el usuario actual
        cursor.execute("""
            SELECT DATE_FORMAT(fecha, '%Y-%m') AS mes, SUM(monto) AS total 
            FROM gastos 
            WHERE id_usuario = %s
            GROUP BY mes
            ORDER BY mes ASC
        """, (id_usuario,))
        datos_gastos = cursor.fetchall()

        cursor.close()
        db.close()

        # Cruzamos la información en un diccionario para que los meses cuadren
        finanzas = {}

        # Cargamos los ingresos
        for row in datos_ingresos:
            mes = row['mes'] 
            finanzas[mes] = {
                'ingresos': float(row['total']),
                'gastos': 0.0
            }

        # Cargamos los gastos
        for row in datos_gastos:
            mes = row['mes']
            if mes not in finanzas:
                finanzas[mes] = {'ingresos': 0.0, 'gastos': 0.0}
            finanzas[mes]['gastos'] = float(row['total'])

        # Ordenamos los meses cronológicamente
        meses_ordenados = sorted(finanzas.keys())

        # Preparamos las listas finales para Chart.js
        labels = meses_ordenados
        ingresos = [finanzas[m]['ingresos'] for m in meses_ordenados]
        gastos = [finanzas[m]['gastos'] for m in meses_ordenados]

        return jsonify({
            'labels': labels, 
            'ingresos': ingresos, 
            'gastos': gastos
        })

    except Exception as e:
        print(f"Error en api_datos_finanzas: {e}") # Para que lo veas en la consola
        return jsonify({'error': str(e)}), 500

@app.route("/metas")
def meta():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)

    try:
        id_usuario = session["usuario_id"]

        cursor.execute("""
            SELECT *
            FROM Metas
            WHERE ID_usuario=%s
            ORDER BY ID_Metas DESC
        """, (id_usuario,))
        metas = cursor.fetchall()

        ingresos, gastos, balance = obtener_balance(id_usuario)

        return render_template(
            "Metas.html",
            metas=metas,
            balance=balance
        )

    finally:
        cursor.close()
        conexion.close()

@app.route("/crear_meta", methods=["POST"])
def crear_meta():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexion = get_connection()
    cursor = conexion.cursor()

    try:

        titulo = request.form["titulo"].strip()
        descripcion = request.form.get("descripcion", "").strip()

        monto_objetivo = float(request.form["monto_objetivo"])

        fecha_limite = request.form.get("fecha_limite")

        if fecha_limite == "":
            fecha_limite = None

        sql = """
        INSERT INTO Metas
        (
            Nombre,
            Descripcion,
            Monto_Actual,
            Monto_Objetivo,
            Fecha_limite,
            ID_usuario
        )
        VALUES
        (%s,%s,0,%s,%s,%s)
        """

        cursor.execute(sql, (
            titulo,
            descripcion,
            monto_objetivo,
            fecha_limite,
            session["usuario_id"]
        ))

        conexion.commit()

        # Justo después de: conexion.commit() en /crear_meta
        registrar_notificacion(session["usuario_id"], f"Has creado la meta: {titulo}", 2) 
# El '2' es el ID_Tipo de "Logro de Meta"

    finally:
        cursor.close()
        conexion.close()

    return redirect(url_for("meta"))

@app.route("/abonar_meta", methods=["POST"])
def abonar_meta():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    id_usuario = session["usuario_id"]
    id_meta = int(request.form["id_metas"])
    monto = float(request.form["monto_aportado"])

    if monto <= 0:
        return redirect(url_for("meta"))

    ingresos, gastos, balance = obtener_balance(id_usuario)

    if monto > balance:
        return redirect(url_for("meta"))

    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM Metas WHERE ID_Metas=%s AND ID_usuario=%s", (id_meta, id_usuario))
        meta = cursor.fetchone()

        if meta is None:
            return redirect(url_for("meta"))

        cursor.execute("UPDATE Metas SET Monto_Actual = Monto_Actual + %s WHERE ID_Metas = %s", (monto, id_meta))
        cursor.execute("INSERT INTO Aportes_Metas (id_metas, id_usuario, monto_aportado) VALUES (%s,%s,%s)", (id_meta, id_usuario, monto))
        conexion.commit()

        # --- AQUI EVALUAMOS LA NOTIFICACIÓN DE METAS ---
        nuevo_monto_actual = meta["Monto_Actual"] + monto
        
        if nuevo_monto_actual >= meta["Monto_Objetivo"]:
            # Si completó la meta (Tipo 2)
            mensaje = f"¡Felicidades! Has completado tu meta: '{meta['nombre']}' 🎉"
            registrar_notificacion(id_usuario, mensaje, 2)
        else:
            # Si solo avanzó (Tipo 3)
            porcentaje = (nuevo_monto_actual / meta["Monto_Objetivo"]) * 100
            mensaje = f"Abonaste ${monto} a tu meta '{meta['nombre']}'. Llevas el {porcentaje:.0f}%."
            registrar_notificacion(id_usuario, mensaje, 3)

    finally:
        cursor.close()
        conexion.close()

    return redirect(url_for("meta"))

@app.route("/notificacion")
def noti():
    # Validar que haya iniciado sesión
    if "usuario_id" not in session:
        return redirect(url_for("login"))
        
    id_usuario = session["usuario_id"]
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    
    try:
        # Traer notificaciones junto con el nombre del tipo
        cursor.execute("""
            SELECT n.mensaje, n.fecha, t.nombre_Tipo 
            FROM notificaciones n
            LEFT JOIN tipo t ON n.ID_Tipo = t.ID_Tipo
            WHERE n.id_usuario = %s
            ORDER BY n.fecha DESC
        """, (id_usuario,))
        
        lista_notificaciones = cursor.fetchall()
    except Exception as e:
        print(f"Error: {e}")
        lista_notificaciones = []
    finally:
        cursor.close()
        conexion.close()

    return render_template("Notificacion.html", notificaciones=lista_notificaciones)

@app.route("/configuracion")
def confi():
    return render_template("Confi.html")

@app.route("/usuario")
def usuario():
    return render_template("usuario.html")


@app.route("/usuarios")
def usuarios():
    # 1. Validación de seguridad estricta: si no hay sesión o el rol no es 2 (Admin), lo expulsamos.
    if "usuario_id" not in session or session.get("rol_id") != 2:
        return redirect(url_for("menu")) 

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True) 
        
        # 2. Consultamos la tabla 'usuario' (solo traemos datos éticos/necesarios)
        cursor.execute("SELECT id_usuario, nombre, correo, edad, ID_Rol FROM usuario")
        datos = cursor.fetchall()
        
        cursor.close()
        conexion.close()

        # 3. Renderizamos el nuevo HTML y le pasamos la lista
        return render_template("usuarios_admin.html", lista_usuarios=datos)

    except Exception as error:
        print(f"Error al cargar usuarios: {error}")
        return redirect(url_for("menu"))

@app.route("/cambiar_rol", methods=["POST"])
def cambiar_rol():
    # Validación de seguridad: ¡Solo otro Admin puede cambiar roles!
    if "usuario_id" not in session or session.get("rol_id") != 2:
        return redirect(url_for("menu"))

    try:
        id_objetivo = request.form["id_objetivo"]
        rol_actual = int(request.form["rol_actual"])
        
        # Invertimos el rol (Si es 1 pasa a 2, si es 2 pasa a 1)
        nuevo_rol = 2 if rol_actual == 1 else 1
        
        conexion = get_connection()
        cursor = conexion.cursor()
        
        sql = "UPDATE usuario SET ID_Rol = %s WHERE id_usuario = %s"
        cursor.execute(sql, (nuevo_rol, id_objetivo))
        conexion.commit()
        
        cursor.close()
        conexion.close()
        
    except Exception as e:
        print(f"Error al cambiar de rol: {e}")
        
    # Recargamos la página de administración para ver los cambios
    return redirect(url_for("usuarios"))


if __name__ == "__main__":
    app.run(debug=True)