import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime, date

# =================================
# CONFIGURACIÓN
# =================================
st.set_page_config(page_title="Banco Educativo PRO", layout="centered")

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
        estado TEXT DEFAULT 'Pendiente',
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

def actualizar_tablas():
    c.execute("PRAGMA table_info(creditos)")
    columnas = [col[1] for col in c.fetchall()]

    if "estado" not in columnas:
        c.execute("ALTER TABLE creditos ADD COLUMN estado TEXT DEFAULT 'Pendiente'")

    if "total" not in columnas:
        c.execute("ALTER TABLE creditos ADD COLUMN total REAL")

    conn.commit()

crear_tablas()
actualizar_tablas()

# =================================
# FUNCIONES SEGURIDAD
# =================================
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verificar_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def existe_docente():
    c.execute("SELECT COUNT(*) FROM usuarios WHERE rol='docente'")
    return c.fetchone()[0] > 0

def safe_date(fecha_str):
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d")
    except:
        return datetime.today()

# =================================
# INTERFAZ
# =================================
st.title("🏦 Banco Educativo PRO")

menu = st.sidebar.selectbox("Menú", ["Inicio", "Registro", "Ingreso"])

# =================================
# SESIÓN
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
    st.subheader("Registro")

    nombre = st.text_input("Nombre")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    rol = st.selectbox("Rol", ["estudiante", "docente"])

    if st.button("Registrar"):
        if rol == "docente" and existe_docente():
            st.error("Ya existe un docente")
        else:
            try:
                c.execute(
                    "INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                    (nombre, usuario, hash_password(password), rol, 0)
                )
                conn.commit()
                st.success("Registrado correctamente")
            except:
                st.error("Usuario ya existe")

# =================================
# LOGIN
# =================================
elif menu == "Ingreso":
    st.subheader("Ingreso")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        c.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,))
        user = c.fetchone()

        if user and verificar_password(password, user[3]):
            st.session_state["usuario"] = user[2]
            st.session_state["rol"] = user[4]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

# =================================
# PANEL DOCENTE
# =================================
if st.session_state.get("rol") == "docente":

    st.header("👨‍🏫 Panel Docente")

    estudiantes = [e[0] for e in c.execute(
        "SELECT usuario FROM usuarios WHERE rol='estudiante'"
    ).fetchall()]

    # DEPÓSITOS
    st.subheader("📥 Depósitos")
    estudiante = st.selectbox("Estudiante", estudiantes)
    monto = st.number_input("Monto", min_value=1.0)
    fecha = st.date_input("Fecha", value=date.today())

    if st.button("Depositar"):
        c.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (monto, estudiante))
        c.execute("INSERT INTO depositos VALUES (NULL, ?, ?, ?)",
                  (estudiante, monto, fecha.strftime("%Y-%m-%d")))
        conn.commit()
        st.success("Depósito realizado")

    # CRÉDITOS
    st.subheader("💳 Solicitudes de Crédito")

    try:
        solicitudes = c.execute(
            "SELECT * FROM creditos WHERE estado='Pendiente'"
        ).fetchall()
    except:
        solicitudes = []

    for cr in solicitudes:
        with st.expander(f"#{cr[0]} | {cr[1]} | ${cr[2]:,.0f}"):

            if st.button("Aprobar", key=f"a{cr[0]}"):
                c.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (cr[2], cr[1]))
                c.execute("UPDATE creditos SET estado='Aprobado' WHERE id=?", (cr[0],))
                conn.commit()
                st.success("Aprobado")
                st.rerun()

            if st.button("Negar", key=f"n{cr[0]}"):
                c.execute("UPDATE creditos SET estado='Negado' WHERE id=?", (cr[0],))
                conn.commit()
                st.warning("Negado")
                st.rerun()

    # RESET PASSWORD
    st.subheader("🔄 Restablecer contraseña")

    est = st.selectbox("Estudiante", estudiantes, key="reset")
    nueva = st.text_input("Nueva contraseña", type="password")

    if st.button("Restablecer"):
        c.execute("UPDATE usuarios SET password=? WHERE usuario=?",
                  (hash_password(nueva), est))
        conn.commit()
        st.success("Contraseña actualizada")

# =================================
# PANEL ESTUDIANTE
# =================================
if st.session_state.get("rol") == "estudiante":

    st.header("🎓 Panel Estudiante")

    c.execute("SELECT saldo FROM usuarios WHERE usuario=?", (st.session_state["usuario"],))
    saldo = c.fetchone()[0]

    st.info(f"Saldo: ${saldo:,.0f}")

    # CRÉDITO
    st.subheader("💳 Solicitar Crédito")

    monto = st.number_input("Monto", min_value=1.0)
    interes = st.selectbox("Interés (%)", [2, 3, 4])

    if st.button("Solicitar"):
        total = monto + (monto * interes / 100)

        c.execute("INSERT INTO creditos VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                  (st.session_state["usuario"], monto, interes, total, "Pendiente",
                   datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        st.success("Solicitud enviada")

    # RETIRO
    st.subheader("🏧 Retiro")

    retiro = st.number_input("Monto a retirar", min_value=1.0)

    if st.button("Retirar"):
        if retiro <= saldo:
            c.execute("UPDATE usuarios SET saldo = saldo - ? WHERE usuario=?",
                      (retiro, st.session_state["usuario"]))
            c.execute("INSERT INTO retiros VALUES (NULL, ?, ?, ?)",
                      (st.session_state["usuario"], retiro,
                       datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Retiro realizado")
            st.rerun()
        else:
            st.error("Saldo insuficiente")

    # CAMBIAR CONTRASEÑA
    st.subheader("🔑 Cambiar contraseña")

    actual = st.text_input("Contraseña actual", type="password")
    nueva = st.text_input("Nueva contraseña", type="password")

    if st.button("Actualizar contraseña"):
        c.execute("SELECT password FROM usuarios WHERE usuario=?", (st.session_state["usuario"],))
        saved = c.fetchone()[0]

        if verificar_password(actual, saved):
            c.execute("UPDATE usuarios SET password=? WHERE usuario=?",
                      (hash_password(nueva), st.session_state["usuario"]))
            conn.commit()
            st.success("Contraseña actualizada")
        else:
            st.error("Contraseña incorrecta")
