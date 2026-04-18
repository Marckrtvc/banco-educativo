import streamlit as st

st.set_page_config(page_title="Banco Educativo", layout="centered")

# -----------------------------
# Inicialización del estado
# -----------------------------
if "usuarios" not in st.session_state:
    st.session_state.usuarios = {
        "Juan": {"rol": "estudiante", "saldo": 0.0, "retiro_pendiente": None},
        "María": {"rol": "estudiante", "saldo": 0.0, "retiro_pendiente": None},
        "Docente": {"rol": "docente"}
    }

# -----------------------------
# Selección de usuario
# -----------------------------
st.title("Banco Educativo 💰")

usuario = st.selectbox(
    "Selecciona tu usuario",
    list(st.session_state.usuarios.keys())
)

rol = st.session_state.usuarios[usuario]["rol"]

st.divider()

# ======================================================
# INTERFAZ DOCENTE
# ======================================================
if rol == "docente":
    st.subheader("Panel del Docente")

    estudiantes = [
        u for u, d in st.session_state.usuarios.items()
        if d.get("rol") == "estudiante"
    ]

    estudiante = st.selectbox("Selecciona estudiante", estudiantes)

    monto = st.number_input(
        "Monto a depositar",
        min_value=1.0,
        step=1.0
    )

    if st.button("Depositar"):
        st.session_state.usuarios[estudiante]["saldo"] += monto
        st.success(f"Se depositaron ${monto} a {estudiante}")

    st.divider()
    st.subheader("Solicitudes de retiro")

    for nombre, datos in st.session_state.usuarios.items():
        if datos.get("rol") == "estudiante" and datos["retiro_pendiente"]:
            st.info(
                f"{nombre} solicita retirar ${datos['retiro_pendiente']}"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button(f"Aprobar retiro de {nombre}"):
                    datos["saldo"] -= datos["retiro_pendiente"]
                    datos["retiro_pendiente"] = None
                    st.success(f"Retiro aprobado para {nombre}")

            with col2:
                if st.button(f"Rechazar retiro de {nombre}"):
                    datos["retiro_pendiente"] = None
                    st.warning(f"Retiro rechazado para {nombre}")

# ======================================================
# INTERFAZ ESTUDIANTE
# ======================================================
else:
    st.subheader(f"Bienvenido, {usuario}")

    saldo = st.session_state.usuarios[usuario]["saldo"]
    retiro_pendiente = st.session_state.usuarios[usuario]["retiro_pendiente"]

    st.metric("Saldo actual", f"${saldo}")

    st.divider()

    if retiro_pendiente:
        st.warning(
            f"Tienes un retiro pendiente por ${retiro_pendiente}. "
            "Espera aprobación del docente."
        )

    else:
        if saldo <= 0:
            st.info("No tienes saldo disponible para solicitar retiro.")
        else:
            monto = st.number_input(
                "Monto a solicitar",
                min_value=1.0,
                max_value=saldo,
                step=1.0
            )

            if st.button("Solicitar retiro"):
                st.session_state.usuarios[usuario]["retiro_pendiente"] = monto
                st.success("Solicitud de retiro enviada al docente")
