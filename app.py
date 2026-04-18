import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime, date
import pandas as pd

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

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        accion TEXT,
        fecha TEXT
    )
    """)
    conn.commit()

crear_tablas()

# =================================
# SEGURIDAD
# =================================
def hash_password(password):
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + hashed.hex()

def verificar_password(password, stored):
    try:
        salt = bytes.fromhex(stored[:32])
        stored_hash = stored[32:]
        new_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()
        return new_hash == stored_hash
    except:
        return False

def log(usuario, accion):
    c.execute(
        "INSERT INTO logs VALUES (NULL, ?, ?, ?)",
        (usuario, accion, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

def obtener_saldo(usuario):
    c.execute("SELECT saldo FROM usuarios WHERE usuario=?", (usuario,))
    row = c.fetchone()
    return row[0] if row else 0

# =================================
# UI
# =================================
st.title("🏦 Banco Educativo PRO - Seguro")

menu = st.sidebar.selectbox("Menú", ["Inicio", "Registro", "Ingreso"])

# =================================
# SESIÓN
# =================================
if "usuario" in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 {st.session_state['usuario']} ({st.session_state['rol']})")

    if st.sidebar.button("Cerrar sesión", key="logout"):
        log(st.session_state["usuario"], "Cierre de sesión")
        st.session_state.clear()
        st.rerun()

# =================================
# REGISTRO
# =================================
if menu == "Registro":
    st.subheader("Registro de Usuario")

    nombre = st.text_input("Nombre", key="reg_nombre")
    usuario = st.text_input("Usuario", key="reg_usuario")
    password = st.text_input("Contraseña", type="password", key="reg_pass")
    rol = st.selectbox("Rol", ["estudiante", "docente"], key="reg_rol")

    if st.button("Registrar", key="btn_reg"):
        try:
            c.execute(
                "INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                (nombre, usuario, hash_password(password), rol, 0)
            )
            conn.commit()
            st.success("Usuario registrado")
            log(usuario, "Registro de usuario")
        except:
            st.error("Usuario ya existe")

# =================================
# LOGIN
# =================================
elif menu == "Ingreso":
    st.subheader("Ingreso")

    usuario = st.text_input("Usuario", key="login_user")
    password = st.text_input("Contraseña", type="password", key="login_pass")

    if st.button("Ingresar", key="btn_login"):
        c.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,))
        user = c.fetchone()

        if user and verificar_password(password, user[3]):
            st.session_state["usuario"] = user[2]
            st.session_state["rol"] = user[4]
            log(usuario, "Inicio de sesión")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

# =================================
# PANEL DOCENTE (CONTROL TOTAL)
# =================================
if st.session_state.get("rol") == "docente":

    st.header("👨‍🏫 Panel Docente")

    estudiantes = [e[0] for e in c.execute(
        "SELECT usuario FROM usuarios WHERE rol='estudiante'"
    ).fetchall()]

    # =========================
    # RESET CONTRASEÑA (DOCENTE)
    # =========================
    st.subheader("🔑 Reset contraseña estudiante")

    if estudiantes:
        est = st.selectbox("Estudiante", estudiantes, key="reset_est_doc")
        nueva = st.text_input("Nueva contraseña", type="password", key="reset_doc_pass")

        if st.button("Resetear", key="btn_reset_doc"):
            if nueva.strip():
                c.execute(
                    "UPDATE usuarios SET password=? WHERE usuario=?",
                    (hash_password(nueva), est)
                )
                conn.commit()
                log(st.session_state["usuario"], f"Reset contraseña de {est}")
                st.success("Contraseña actualizada")
            else:
                st.error("No puede estar vacía")

    st.divider()

    # =========================
    # CRÉDITOS
    # =========================
    st.subheader("💳 Créditos")

    creditos = c.execute("""
        SELECT id, estudiante, monto, interes, total, estado, fecha
        FROM creditos ORDER BY id DESC
    """).fetchall()

    for cr in creditos:
        with st.expander(f"{cr[1]} | {cr[5]} | ${cr[2]:,.2f}"):

            st.write(f"Monto: ${cr[2]:,.2f}")
            st.write(f"Estado: {cr[5]}")

            if cr[5] == "Pendiente":

                if st.button("Aprobar", key=f"ap_{cr[0]}"):
                    c.execute(
                        "UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?",
                        (cr[2], cr[1])
                    )
                    c.execute("UPDATE creditos SET estado='Aprobado' WHERE id=?", (cr[0],))
                    conn.commit()
                    log(st.session_state["usuario"], f"Aprobó crédito {cr[0]}")
                    st.rerun()

                if st.button("Negar", key=f"ng_{cr[0]}"):
                    c.execute("UPDATE creditos SET estado='Negado' WHERE id=?", (cr[0],))
                    conn.commit()
                    log(st.session_state["usuario"], f"Negó crédito {cr[0]}")
                    st.rerun()

# =================================
# PANEL ESTUDIANTE (AUTOGESTIÓN)
# =================================
if st.session_state.get("rol") == "estudiante":

    st.header("🎓 Panel Estudiante")

    usuario = st.session_state["usuario"]
    saldo = obtener_saldo(usuario)

    st.info(f"Saldo: ${saldo:,.2f}")

    # =========================
    # CAMBIO DE CONTRASEÑA
    # =========================
    st.subheader("🔑 Cambiar contraseña")

    actual = st.text_input("Actual", type="password", key="est_act")
    nueva = st.text_input("Nueva", type="password", key="est_new")

    if st.button("Actualizar contraseña", key="btn_est_pass"):

        c.execute("SELECT password FROM usuarios WHERE usuario=?", (usuario,))
        saved = c.fetchone()

        if saved and verificar_password(actual, saved[0]):

            if nueva.strip():
                c.execute(
                    "UPDATE usuarios SET password=? WHERE usuario=?",
                    (hash_password(nueva), usuario)
                )
                conn.commit()
                log(usuario, "Cambio de contraseña")
                st.success("Actualizada")
            else:
                st.error("No puede estar vacía")
        else:
            st.error("Contraseña actual incorrecta")
