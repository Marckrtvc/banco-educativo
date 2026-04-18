import streamlit as st
import sqlite3
import hashlib
import random
from datetime import datetime

# ---------------------------------
# CONFIGURACIÓN
# ---------------------------------
st.set_page_config(page_title="Banco Educativo", layout="centered")

# ---------------------------------
# BASE DE DATOS
# ---------------------------------
conn = sqlite3.connect("banco_educativo.db", check_same_thread=False)
c = conn.cursor()

def crear_tablas():
    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        usuario TEXT UNIQUE,
        password TEXT,
        rol TEXT,
        saldo REAL DEFAULT 0
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        tipo TEXT,
        monto REAL,
        fecha TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS creditos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        monto REAL,
        interes REAL,
        total REAL,
        estado TEXT,
        fecha TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS retiros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        monto REAL,
        estado TEXT,
        fecha TEXT
    )
    """)
    conn.commit()

crear_tablas()

# ---------------------------------
# FUNCIONES
# ---------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def registrar_usuario(nombre, usuario, password, rol):
    try:
        c.execute(
            "INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
            (nombre, usuario, hash_password(password), rol, 0)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def autenticar(usuario, password):
    c.execute(
        "SELECT * FROM usuarios WHERE usuario=? AND password=?",
        (usuario, hash_password(password))
    )
    return c.fetchone()

def obtener_usuario(usuario):
    c.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,))
    return c.fetchone()

def actualizar_saldo(usuario, monto):
    c.execute(
        "UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?",
        (monto, usuario)
    )
    conn.commit()

def registrar_movimiento(usuario, tipo, monto):
    c.execute(
        "INSERT INTO movimientos VALUES (NULL, ?, ?, ?, ?)",
        (usuario, tipo, monto, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()

# ---------------------------------
# INTERFAZ GENERAL
# ---------------------------------
st.title("🏦 Banco Educativo Virtual")

menu = st.sidebar.selectbox("Menú", ["Inicio", "Registro", "Ingreso"])

# ---------------------------------
# REGISTRO
# ---------------------------------
if menu == "Registro":
    st.subheader("Registro de Usuario")

    nombre = st.text_input("Nombre completo")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    rol = st.selectbox("Rol", ["estudiante", "docente"])

    if st.button("Registrar"):
        if nombre and usuario and password:
            if registrar_usuario(nombre, usuario, password, rol):
                st.success("Usuario registrado correctamente")
            else:
                st.error("El usuario ya existe")
        else:
            st.warning("Complete todos los campos")

# ---------------------------------
# INGRESO
# ---------------------------------
elif menu == "Ingreso":
    st.subheader("Ingreso al Sistema")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        user = autenticar(usuario, password)
        if user:
            st.session_state["usuario"] = user[2]
            st.success("Ingreso exitoso")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

# ---------------------------------
# PANEL PRINCIPAL
# ---------------------------------
if "usuario" in st.session_state:
    user = obtener_usuario(st.session_state["usuario"])
    nombre, usuario, rol, saldo = user[1], user[2], user[4], user[5]

    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 {nombre}")
    st.sidebar.write(f"💰 Saldo: ${saldo:,.2f}")
    st.sidebar.write(f"🎓 Rol: {rol}")

    if st.sidebar.button("Cerrar sesión"):
        del st.session_state["usuario"]
        st.rerun()

    st.sidebar.markdown("---")

    # ---------------------------------
    # ESTUDIANTE
    # ---------------------------------
    if rol == "estudiante":
        opcion = st.selectbox(
            "Opciones",
            ["Solicitar retiro", "Solicitar crédito", "Historial"]
        )

        if opcion == "Solicitar retiro":

            # ✅ CORRECCIÓN DEL ERROR
            if saldo <= 0:
                st.warning("No tienes saldo disponible para solicitar un retiro.")
            else:
                monto = st.number_input(
                    "Monto a retirar",
                    min_value=1.0,
                    max_value=float(saldo)
                )

                if st.button("Solicitar retiro"):
                    c.execute(
                        "INSERT INTO retiros VALUES (NULL, ?, ?, ?, ?)",
                        (usuario, monto, "Pendiente",
                         datetime.now().strftime("%Y-%m-%d %H:%M"))
                    )
                    conn.commit()
                    st.success("Solicitud de retiro enviada al docente")

        elif opcion == "Solicitar crédito":
            monto = st.number_input("Monto solicitado", min_value=1.0)
            if st.button("Solicitar crédito"):
                interes = round(random.uniform(0.02, 0.04), 2)
                total = monto * (1 + interes)
                c.execute(
                    "INSERT INTO creditos VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                    (usuario, monto, interes, total, "Pendiente",
                     datetime.now().strftime("%Y-%m-%d"))
                )
                conn.commit()
                st.success("Solicitud de crédito enviada al docente")

        elif opcion == "Historial":
            c.execute(
                "SELECT tipo, monto, fecha FROM movimientos WHERE usuario=?",
                (usuario,)
            )
            st.table(c.fetchall())

    # ---------------------------------
    # DOCENTE
    # ---------------------------------
    elif rol == "docente":

        # DEPÓSITO A ESTUDIANTES
        st.subheader("Depósito a estudiantes")

        c.execute("SELECT usuario FROM usuarios WHERE rol='estudiante'")
        estudiantes = [e[0] for e in c.fetchall()]

        estudiante = st.selectbox("Estudiante", estudiantes)
        monto = st.number_input("Monto a depositar", min_value=1.0)

        if st.button("Depositar"):
            actualizar_saldo(estudiante, monto)
            registrar_movimiento(estudiante, "Depósito docente", monto)
            st.success("Depósito realizado")
            st.rerun()

        # CRÉDITOS
        st.subheader("Aprobación de Créditos")
        c.execute("SELECT * FROM creditos WHERE estado='Pendiente'")
        for cr in c.fetchall():
            st.markdown(f"""
            **Usuario:** {cr[1]}  
            **Monto:** ${cr[2]:,.2f}  
            **Interés:** {cr[3]*100:.0f}%
            """)

            col1, col2 = st.columns(2)

            if col1.button("Aprobar crédito", key=f"ap_c_{cr[0]}"):
                actualizar_saldo(cr[1], cr[2])
                registrar_movimiento(cr[1], "Crédito aprobado", cr[2])
                c.execute("UPDATE creditos SET estado='Aprobado' WHERE id=?", (cr[0],))
                conn.commit()
                st.rerun()

            if col2.button("Negar crédito", key=f"ng_c_{cr[0]}"):
                c.execute("UPDATE creditos SET estado='Negado' WHERE id=?", (cr[0],))
                conn.commit()
                st.rerun()

        # RETIROS
        st.subheader("Aprobación de Retiros")
        c.execute("SELECT * FROM retiros WHERE estado='Pendiente'")
        for r in c.fetchall():
            st.markdown(f"""
            **Usuario:** {r[1]}  
            **Monto:** ${r[2]:,.2f}
            """)

            col1, col2 = st.columns(2)

            if col1.button("Aprobar retiro", key=f"ap_r_{r[0]}"):
                actualizar_saldo(r[1], -r[2])
                registrar_movimiento(r[1], "Retiro aprobado", r[2])
                c.execute("UPDATE retiros SET estado='Aprobado' WHERE id=?", (r[0],))
                conn.commit()
                st.rerun()

            if col2.button("Negar retiro", key=f"ng_r_{r[0]}"):
                c.execute("UPDATE retiros SET estado='Negado' WHERE id=?", (r[0],))
                conn.commit()
                st.rerun()
