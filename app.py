import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date

# =================================
# CONFIGURACIÓN
# =================================
st.set_page_config(page_title="Banco Educativo", layout="centered")

# =================================
# BASE DE DATOS
# =================================
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
    CREATE TABLE IF NOT EXISTS depositos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante TEXT,
        monto REAL,
        fecha TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS creditos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante TEXT,
        monto REAL,
        interes INTEGER,
        total REAL,
        fecha TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS retiros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante TEXT,
        monto REAL,
        fecha TEXT
    )
    """)
    conn.commit()

crear_tablas()

# =================================
# FUNCIONES
# =================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def existe_docente():
    c.execute("SELECT COUNT(*) FROM usuarios WHERE rol='docente'")
    return c.fetchone()[0] > 0

# =================================
# MENÚ PRINCIPAL
# =================================
st.title("🏦 Banco Educativo Virtual")

menu = st.sidebar.selectbox(
    "Menú",
    ["Inicio", "Registro", "Ingreso"]
)

# =================================
# CERRAR SESIÓN
# =================================
if "usuario" in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 {st.session_state['usuario']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

# =================================
# REGISTRO
# =================================
if menu == "Registro":
    st.subheader("Registro de Usuario")

    nombre = st.text_input("Nombre completo")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    rol = st.selectbox("Rol", ["estudiante", "docente"])

    if st.button("Registrar"):
        if rol == "docente" and existe_docente():
            st.error("Ya existe un docente registrado.")
        else:
            try:
                c.execute(
                    "INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                    (nombre, usuario, hash_password(password), rol, 0)
                )
                conn.commit()
                st.success("Usuario registrado correctamente")
            except sqlite3.IntegrityError:
                st.error("El usuario ya existe")

# =================================
# INGRESO
# =================================
elif menu == "Ingreso":
    st.subheader("Ingreso al Sistema")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        c.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND password=?",
            (usuario, hash_password(password))
        )
        user = c.fetchone()

        if user:
            st.session_state["usuario"] = user[2]
            st.session_state["rol"] = user[4]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

# =================================
# PANEL DOCENTE
# =================================
if "rol" in st.session_state and st.session_state["rol"] == "docente":

    st.header("👨‍🏫 Panel del Docente")

    estudiantes = [
        e[0] for e in
        c.execute("SELECT usuario FROM usuarios WHERE rol='estudiante'").fetchall()
    ]

    # -------------------------------
    # DEPÓSITOS
    # -------------------------------
    st.subheader("📥 Depósito a Estudiantes")

    estudiante = st.selectbox("Estudiante", estudiantes)
    monto = st.number_input("Monto", min_value=1.0)
    fecha = st.date_input("Fecha del depósito", value=date.today())

    if st.button("Realizar Depósito"):
        c.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (monto, estudiante))
        c.execute(
            "INSERT INTO depositos VALUES (NULL, ?, ?, ?)",
            (estudiante, monto, fecha.strftime("%Y-%m-%d"))
        )
        conn.commit()
        st.success("Depósito realizado")

    st.subheader("📜 Historial de Depósitos")
    st.dataframe(c.execute("SELECT * FROM depositos").fetchall(), use_container_width=True)

    # -------------------------------
    # CRÉDITOS
    # -------------------------------
    st.subheader("💳 Aprobar Crédito")

    estudiante_c = st.selectbox("Estudiante crédito", estudiantes)
    monto_c = st.number_input("Monto crédito", min_value=1.0)
    interes = st.selectbox("Interés (%)", [2, 3, 4])

    if st.button("Aprobar Crédito"):
        total = monto_c + (monto_c * interes / 100)
        c.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (monto_c, estudiante_c))
        c.execute(
            "INSERT INTO creditos VALUES (NULL, ?, ?, ?, ?, ?)",
            (estudiante_c, monto_c, interes, total, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
        st.success(f"Crédito aprobado. Total a pagar: ${total:,.2f}")

    st.subheader("📜 Historial de Créditos")
    st.dataframe(c.execute("SELECT * FROM creditos").fetchall(), use_container_width=True)

    # -------------------------------
    # RETIROS
    # -------------------------------
    st.subheader("🏧 Historial de Retiros")
    st.dataframe(c.execute("SELECT * FROM retiros").fetchall(), use_container_width=True)

# =================================
# PANEL ESTUDIANTE
# =================================
if "rol" in st.session_state and st.session_state["rol"] == "estudiante":

    st.header("🎓 Panel del Estudiante")

    c.execute("SELECT saldo FROM usuarios WHERE usuario=?", (st.session_state["usuario"],))
    saldo = c.fetchone()[0]
    st.info(f"Saldo actual: ${saldo:,.2f}")

    st.subheader("🏧 Retiro")
    monto_r = st.number_input("Monto a retirar", min_value=1.0)

    if st.button("Retirar"):
        if monto_r <= saldo:
            c.execute("UPDATE usuarios SET saldo = saldo - ? WHERE usuario=?", (monto_r, st.session_state["usuario"]))
            c.execute(
                "INSERT INTO retiros VALUES (NULL, ?, ?, ?)",
                (st.session_state["usuario"], monto_r, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            st.success("Retiro exitoso")
        else:
            st.error("Saldo insuficiente")

    st.subheader("📜 Mi Historial de Retiros")
    st.dataframe(
        c.execute(
            "SELECT * FROM retiros WHERE estudiante=?",
            (st.session_state["usuario"],)
        ).fetchall(),
        use_container_width=True
    )
