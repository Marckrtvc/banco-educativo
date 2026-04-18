import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

# ===============================
# CONEXIÓN BASE DE DATOS
# ===============================
conn = sqlite3.connect("banco.db", check_same_thread=False)
c = conn.cursor()

# ===============================
# CREACIÓN DE TABLAS
# ===============================
def crear_tablas():
    c.execute("""
    CREATE TABLE IF NOT EXISTS docente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        password TEXT,
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

# ===============================
# FUNCIONES
# ===============================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def existe_docente():
    c.execute("SELECT COUNT(*) FROM docente")
    return c.fetchone()[0] > 0

# ===============================
# INTERFAZ
# ===============================
st.title("🏦 Banco Educativo")

menu = st.sidebar.selectbox(
    "Menú",
    ["Registrar Docente", "Login Docente", "Registrar Estudiante", "Login Estudiante"]
)

# ===============================
# REGISTRAR DOCENTE
# ===============================
if menu == "Registrar Docente":
    st.subheader("Registro de Docente")

    if existe_docente():
        st.warning("Ya existe un docente registrado.")
    else:
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")

        if st.button("Registrar"):
            c.execute(
                "INSERT INTO docente (usuario, password) VALUES (?, ?)",
                (usuario, hash_password(password))
            )
            conn.commit()
            st.success("Docente registrado correctamente")

# ===============================
# LOGIN DOCENTE
# ===============================
elif menu == "Login Docente":
    st.subheader("Ingreso Docente")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        c.execute(
            "SELECT * FROM docente WHERE usuario=? AND password=?",
            (usuario, hash_password(password))
        )
        docente = c.fetchone()

        if docente:
            st.success("Bienvenido Docente")

            estudiantes = [e[0] for e in c.execute("SELECT usuario FROM estudiantes").fetchall()]

            # -------------------------------
            # DEPÓSITOS
            # -------------------------------
            st.subheader("📥 Depósito a Estudiantes")

            estudiante = st.selectbox("Estudiante", estudiantes)
            monto = st.number_input("Monto", min_value=0.0)
            fecha = st.date_input("Fecha del depósito")

            if st.button("Realizar Depósito"):
                c.execute("UPDATE estudiantes SET saldo = saldo + ? WHERE usuario=?", (monto, estudiante))
                c.execute(
                    "INSERT INTO depositos (estudiante, monto, fecha) VALUES (?, ?, ?)",
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

            estudiante_credito = st.selectbox("Estudiante crédito", estudiantes)
            monto_credito = st.number_input("Monto crédito", min_value=0.0)
            interes = st.selectbox("Interés (%)", [2, 3, 4])

            if st.button("Aprobar Crédito"):
                valor_interes = monto_credito * (interes / 100)
                total = monto_credito + valor_interes

                c.execute("UPDATE estudiantes SET saldo = saldo + ? WHERE usuario=?", (monto_credito, estudiante_credito))
                c.execute(
                    "INSERT INTO creditos (estudiante, monto, interes, total, fecha) VALUES (?, ?, ?, ?, ?)",
                    (estudiante_credito, monto_credito, interes, total, datetime.now().strftime("%Y-%m-%d"))
                )
                conn.commit()
                st.success(f"Crédito aprobado. Total a pagar: ${total}")

            st.subheader("📜 Historial de Créditos")
            st.dataframe(c.execute("SELECT * FROM creditos").fetchall(), use_container_width=True)

            # -------------------------------
            # 🔴 HISTORIAL DE RETIROS (AQUÍ ESTABA LO QUE FALTABA)
            # -------------------------------
            st.subheader("🏧 Historial General de Retiros")
            st.dataframe(
                c.execute("SELECT * FROM retiros").fetchall(),
                use_container_width=True
            )

            st.subheader("🏧 Historial de Retiros por Estudiante")
            est_retiro = st.selectbox("Selecciona estudiante", estudiantes, key="retiros_docente")

            st.dataframe(
                c.execute(
                    "SELECT * FROM retiros WHERE estudiante=?",
                    (est_retiro,)
                ).fetchall(),
                use_container_width=True
            )

        else:
            st.error("Credenciales incorrectas")

# ===============================
# REGISTRAR ESTUDIANTE
# ===============================
elif menu == "Registrar Estudiante":
    st.subheader("Registro Estudiante")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Registrar"):
        c.execute(
            "INSERT INTO estudiantes (usuario, password) VALUES (?, ?)",
            (usuario, hash_password(password))
        )
        conn.commit()
        st.success("Estudiante registrado")

# ===============================
# LOGIN ESTUDIANTE
# ===============================
elif menu == "Login Estudiante":
    st.subheader("Ingreso Estudiante")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        c.execute(
            "SELECT * FROM estudiantes WHERE usuario=? AND password=?",
            (usuario, hash_password(password))
        )
        estudiante = c.fetchone()

        if estudiante:
            st.success("Bienvenido")
            saldo = estudiante[3]
            st.info(f"Saldo actual: ${saldo}")

            st.subheader("🏧 Retiro")
            monto = st.number_input("Monto a retirar", min_value=0.0)

            if st.button("Retirar"):
                if monto <= saldo:
                    c.execute("UPDATE estudiantes SET saldo = saldo - ? WHERE usuario=?", (monto, usuario))
                    c.execute(
                        "INSERT INTO retiros (estudiante, monto, fecha) VALUES (?, ?, ?)",
                        (usuario, monto, datetime.now().strftime("%Y-%m-%d"))
                    )
                    conn.commit()
                    st.success("Retiro exitoso")
                else:
                    st.error("Saldo insuficiente")

            st.subheader("📜 Mi Historial de Retiros")
            st.dataframe(
                c.execute("SELECT * FROM retiros WHERE estudiante=?", (usuario,)).fetchall(),
                use_container_width=True
            )

        else:
            st.error("Credenciales incorrectas")
