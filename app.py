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

def existe_docente():
    c.execute("SELECT COUNT(*) FROM usuarios WHERE rol='docente'")
    return c.fetchone()[0] > 0

def obtener_saldo(usuario):
    c.execute("SELECT saldo FROM usuarios WHERE usuario=?", (usuario,))
    row = c.fetchone()
    return row[0] if row else 0

# =================================
# UI GENERAL
# =================================
st.title("🏦 Banco Educativo PRO")

menu = st.sidebar.selectbox("Menú", ["Inicio", "Registro", "Ingreso"])

# =================================
# SESIÓN
# =================================
if "usuario" in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 {st.session_state['usuario']}")

    if st.sidebar.button("Cerrar sesión", key="logout"):
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
        if rol == "docente" and existe_docente():
            st.error("Ya existe un docente registrado")
        else:
            try:
                c.execute(
                    "INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                    (nombre, usuario, hash_password(password), rol, 0)
                )
                conn.commit()
                st.success("Usuario registrado correctamente")
            except:
                st.error("El usuario ya existe")

# =================================
# LOGIN
# =================================
elif menu == "Ingreso":
    st.subheader("Ingreso al Sistema")

    usuario = st.text_input("Usuario", key="login_user")
    password = st.text_input("Contraseña", type="password", key="login_pass")

    if st.button("Ingresar", key="btn_login"):
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

    estudiantes_data = c.execute(
        "SELECT usuario FROM usuarios WHERE rol='estudiante'"
    ).fetchall()

    estudiantes = [e[0] for e in estudiantes_data]

    # =========================
    # BALANCE GENERAL
    # =========================
    st.subheader("📊 Balance General")

    total_dep = c.execute("SELECT SUM(monto) FROM depositos").fetchone()[0] or 0
    total_cre = c.execute("SELECT SUM(monto) FROM creditos WHERE estado='Aprobado'").fetchone()[0] or 0
    total_ret = c.execute("SELECT SUM(monto) FROM retiros").fetchone()[0] or 0

    balance = total_dep - total_ret

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Depósitos", f"${total_dep:,.2f}")
    col2.metric("Créditos", f"${total_cre:,.2f}")
    col3.metric("Retiros", f"${total_ret:,.2f}")
    col4.metric("Balance", f"${balance:,.2f}")

    st.divider()

    # =========================
    # DEPÓSITOS
    # =========================
    st.subheader("📥 Depósitos")

    if estudiantes:
        estudiante = st.selectbox("Estudiante", estudiantes, key="doc_est")
        monto = st.number_input("Monto", min_value=1.0, key="doc_monto")
        fecha = st.date_input("Fecha", value=date.today(), key="doc_fecha")

        if st.button("Depositar", key="btn_dep"):
            c.execute(
                "UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?",
                (monto, estudiante)
            )
            c.execute(
                "INSERT INTO depositos VALUES (NULL, ?, ?, ?)",
                (estudiante, monto, fecha.strftime("%Y-%m-%d"))
            )
            conn.commit()
            st.success("Depósito realizado")

    st.divider()

    # =========================
    # HISTORIAL DEPÓSITOS
    # =========================
    st.subheader("📜 Historial de Depósitos")

    depositos = c.execute("""
        SELECT id, estudiante, monto, fecha
        FROM depositos ORDER BY id DESC
    """).fetchall()

    st.metric("Total depositado", f"${sum([d[2] for d in depositos]) if depositos else 0:,.2f}")

    if depositos:
        df = pd.DataFrame(depositos, columns=["ID", "Estudiante", "Monto", "Fecha"])
        df["Monto"] = df["Monto"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sin depósitos")

    st.divider()

    # =========================
    # CRÉDITOS
    # =========================
    st.subheader("💳 Créditos")

    creditos = c.execute("""
        SELECT id, estudiante, monto, interes, total, estado, fecha
        FROM creditos ORDER BY id DESC
    """).fetchall()

    st.metric("Total prestado", f"${sum([c[2] for c in creditos if c[5]=='Aprobado']) if creditos else 0:,.2f}")

    for cr in creditos:
        with st.expander(f"Crédito #{cr[0]} | {cr[1]} | {cr[5]}"):

            st.write(f"Monto: ${cr[2]:,.2f}")
            st.write(f"Interés: {cr[3]}%")
            st.write(f"Total: ${cr[4]:,.2f}")
            st.write(f"Estado: {cr[5]}")

            if cr[5] == "Pendiente":

                if st.button("Aprobar", key=f"ap_{cr[0]}"):
                    c.execute(
                        "UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?",
                        (cr[2], cr[1])
                    )
                    c.execute("UPDATE creditos SET estado='Aprobado' WHERE id=?", (cr[0],))
                    conn.commit()
                    st.success("Aprobado")
                    st.rerun()

                if st.button("Negar", key=f"ng_{cr[0]}"):
                    c.execute("UPDATE creditos SET estado='Negado' WHERE id=?", (cr[0],))
                    conn.commit()
                    st.warning("Negado")
                    st.rerun()

    st.divider()

    # =========================
    # RETIROS
    # =========================
    st.subheader("🏧 Historial de Retiros")

    retiros = c.execute("""
        SELECT id, estudiante, monto, fecha
        FROM retiros ORDER BY id DESC
    """).fetchall()

    st.metric("Total retirado", f"${sum([r[2] for r in retiros]) if retiros else 0:,.2f}")

    if retiros:
        df = pd.DataFrame(retiros, columns=["ID", "Estudiante", "Monto", "Fecha"])
        df["Monto"] = df["Monto"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sin retiros")

    st.divider()

    # =========================
    # RESET PASSWORD
    # =========================
    st.subheader("🔑 Restablecer contraseña")

    if estudiantes:
        est = st.selectbox("Estudiante", estudiantes, key="reset_est")
        nueva = st.text_input("Nueva contraseña", type="password", key="reset_pass")

        if st.button("Restablecer", key="btn_reset"):
            if nueva.strip():
                c.execute(
                    "UPDATE usuarios SET password=? WHERE usuario=?",
                    (hash_password(nueva), est)
                )
                conn.commit()
                st.success("Contraseña actualizada")
            else:
                st.error("No puede estar vacía")

# =================================
# PANEL ESTUDIANTE
# =================================
if st.session_state.get("rol") == "estudiante":

    st.header("🎓 Panel Estudiante")

    saldo = obtener_saldo(st.session_state["usuario"])

    st.info(f"Saldo: ${saldo:,.2f}")

    # Crédito
    st.subheader("💳 Solicitar crédito")

    monto = st.number_input("Monto", min_value=1.0, key="est_credito")
    interes = st.selectbox("Interés", [2, 3, 4], key="est_interes")

    if st.button("Solicitar", key="btn_credito"):
        total = monto + (monto * interes / 100)

        c.execute("""
            INSERT INTO creditos
            VALUES (NULL, ?, ?, ?, ?, ?, ?)
        """, (
            st.session_state["usuario"],
            monto,
            interes,
            total,
            "Pendiente",
            datetime.now().strftime("%Y-%m-%d")
        ))
        conn.commit()
        st.success("Solicitud enviada")

    # Retiro
    st.subheader("🏧 Retiro")

    retiro = st.number_input("Monto retiro", min_value=1.0, key="est_retiro")

    if st.button("Retirar", key="btn_retiro"):
        if retiro <= saldo:
            c.execute(
                "UPDATE usuarios SET saldo = saldo - ? WHERE usuario=?",
                (retiro, st.session_state["usuario"])
            )
            conn.commit()
            st.success("Retiro realizado")
            st.rerun()
        else:
            st.error("Saldo insuficiente")
