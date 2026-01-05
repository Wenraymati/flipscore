import streamlit as st
import httpx
import json
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import gspread
from google.oauth2.service_account import Credentials

# ============ CONFIG ============
import os

# Config
# Prioridad: Env Var (Railway/Docker) > Streamlit Secrets > Localhost
if "API_URL" in os.environ:
    API_URL = os.environ["API_URL"]
elif "API_URL" in st.secrets:
    API_URL = st.secrets["API_URL"]
else:
    API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="FlipScore - Evalúa Deals",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============ CSS PERSONALIZADO ============
st.markdown("""
<style>
    .score-high { color: #00C853; font-size: 48px; font-weight: bold; }
    .score-medium { color: #FFB300; font-size: 48px; font-weight: bold; }
    .score-low { color: #FF1744; font-size: 48px; font-weight: bold; }
    .decision-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
    }
    .comprar { background-color: #E8F5E9; border: 2px solid #4CAF50; }
    .negociar { background-color: #FFF8E1; border: 2px solid #FFC107; }
    .pasar { background-color: #FFEBEE; border: 2px solid #F44336; }
</style>
""", unsafe_allow_html=True)

# ============ TRACKING SIMPLE ============
def track_event(event_name: str, data: dict = None):
    """Guarda eventos en session para análisis."""
    if "events" not in st.session_state:
        st.session_state.events = []
    st.session_state.events.append({
        "event": event_name,
        "timestamp": datetime.now().isoformat(),
        "data": data or {}
    })

# ============ SHEETS INTEGRATION ============
def save_lead_to_sheets(email: str, data: dict):
    """Guarda lead en Google Sheets."""
    if not st.secrets.get("gcp_service_account"):
        return False # Silent fail if not configured
        
    try:
        # Configurar credenciales (desde secrets)
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        
        # Abrir sheet
        sheet = client.open("FlipScore Leads").sheet1
        
        # Agregar fila
        sheet.append_row([
            datetime.now().isoformat(),
            email,
            data.get("wants_more", False),
            data.get("would_pay", False),
            data.get("feedback", ""),
            data.get("evaluations_done", 0)
        ])
        return True
    except Exception as e:
        print(f"Error saving to sheets: {e}")
        return False

# ============ CONTADOR DE USO & COOKIES ============
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

def init_usage():
    # 1. Intentar recuperar de cookie
    cookie_val = cookie_manager.get("flipscore_usage")
    
    if "evaluations_count" not in st.session_state:
        if cookie_val is not None:
            st.session_state.evaluations_count = int(cookie_val)
        else:
            st.session_state.evaluations_count = 0
            
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

init_usage()

def increment_usage():
    st.session_state.evaluations_count += 1
    # Persistir en cookie por 30 días
    expires = datetime.now() + timedelta(days=30)
    cookie_manager.set("flipscore_usage", st.session_state.evaluations_count, expires_at=expires)

# ============ LÍMITE GRATUITO ============
FREE_LIMIT = 5  # Evaluaciones gratis antes de pedir email

def check_limit():
    """Verifica si usuario alcanzó límite."""
    return st.session_state.evaluations_count >= FREE_LIMIT

# ============ FUNCIONES HELPER ============
def display_results(result):
    """Muestra resultados de evaluación."""
    st.divider()
    
    # Score y decisión principal
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Fallback fields
        eval_data = result.get("evaluacion", {})
        score = eval_data.get("score_total", 0)
        score_class = "high" if score >= 7 else "medium" if score >= 5 else "low"
        
        st.markdown(f"""
        <div style="text-align: center;">
            <p style="margin: 0; color: #666;">SCORE</p>
            <p class="score-{score_class}">{score:.1f}/10</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        rec_data = result.get("recomendacion", {})
        decision = rec_data.get("decision", "N/A")
        decision_class = "comprar" if "COMPRAR" in decision else "negociar" if "NEGOCIAR" in decision else "pasar"
        
        st.markdown(f"""
        <div class="decision-box {decision_class}">
            <h2>{decision}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        margen = eval_data.get("margen_estimado", 0)
        st.markdown(f"""
        <div style="text-align: center;">
            <p style="margin: 0; color: #666;">MARGEN ESTIMADO</p>
            <p style="font-size: 28px; font-weight: bold; color: #1976D2;">
                ${margen:,.0f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Razonamiento
    st.divider()
    st.subheader("💡 Razonamiento")
    st.info(rec_data.get("razonamiento", "Sin razonamiento disponible."))
    
    # Acciones sugeridas
    acciones = rec_data.get("acciones_sugeridas") or rec_data.get("acciones")
    if acciones:
        st.subheader("🎯 Acciones Sugeridas")
        for i, accion in enumerate(acciones, 1):
            st.markdown(f"**{i}.** {accion}")
            
    # Alertas
    if result.get("alertas"):
        st.error("⚠️ ALERTAS: " + ", ".join(result["alertas"]))

# ============ CAPTURA DE LEADS ============
def show_lead_capture():
    """Modal para capturar email cuando alcanza límite."""
    st.warning("🎉 ¡Has usado tus 5 evaluaciones gratis!")
    st.markdown("""
    ### ¿Te está sirviendo FlipScore?
    
    Déjanos tu email y te avisamos cuando lancemos la versión completa 
    con **evaluaciones ilimitadas**.
    """)
    
    email = st.text_input("Tu email", placeholder="tu@email.com")
    
    col1, col2 = st.columns(2)
    with col1:
        wants_more = st.checkbox("Quiero más evaluaciones")
    with col2:
        would_pay = st.checkbox("Pagaría por esto")
    
    feedback = st.text_area(
        "¿Qué mejorarías?", 
        placeholder="Tu feedback nos ayuda mucho...",
        height=100
    )
    
    if st.button("✅ Enviar y desbloquear 5 más", type="primary"):
        if email and "@" in email:
            # Datos lead
            lead_data = {
                "email": email,
                "wants_more": wants_more,
                "would_pay": would_pay,
                "feedback": feedback,
                "evaluations_done": st.session_state.evaluations_count
            }
            
            # Guardar en sheets o local tracking
            track_event("lead_captured", lead_data)
            save_lead_to_sheets(email, lead_data)
            
            st.session_state.user_email = email
            st.session_state.evaluations_count = 0 
            cookie_manager.set("flipscore_usage", 0) # Reset cookie también
            
            st.success("¡Gracias! Te desbloqueamos 5 evaluaciones más.")
            st.balloons()
            st.rerun()
        else:
            st.error("Ingresa un email válido")

# ============ HEADER ============
st.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <h1 style="margin: 0;">💰 FlipScore</h1>
    <p style="color: #666; margin: 0;">Foto → Decisión en 5 segundos</p>
</div>
""", unsafe_allow_html=True)

# Mostrar contador
remaining = FREE_LIMIT - st.session_state.evaluations_count
if remaining > 0:
    st.caption(f"⚡ {remaining} evaluaciones gratis restantes")
else:
    st.caption("🔒 Límite alcanzado")

st.divider()

# ============ VERIFICAR LÍMITE ============
if check_limit() and not st.session_state.user_email:
    show_lead_capture()
    st.stop()

# ============ APP PRINCIPAL ============
tab1, tab2 = st.tabs(["📝 Texto", "📸 Imagen"])

with tab1:
    producto = st.text_input(
        "Producto",
        placeholder="Ej: iPhone 13 128GB usado buen estado"
    )
    
    precio = st.number_input(
        "Precio (CLP)",
        min_value=1000,
        max_value=50000000,
        value=200000,
        step=5000
    )
    
    descripcion = st.text_area(
        "Descripción (opcional)",
        placeholder="Copia la descripción del vendedor...",
        height=80
    )
    
    if st.button("🔍 EVALUAR MANUAL", type="primary", use_container_width=True):
        if producto:
            track_event("evaluation_started", {"type": "text", "product": producto})
            
            with st.spinner("Analizando..."):
                try:
                    payload = {
                        "producto": producto,
                        "precio_publicado": precio,
                        "descripcion": descripcion
                    }
                    response = httpx.post(f"{API_URL}/api/evaluate", json=payload, timeout=30.0)
                    response.raise_for_status()
                    result = response.json()
                    
                    result = response.json()
                    
                    increment_usage()
                    track_event("evaluation_completed", {"type": "text"})
                    
                    display_results(result)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 422:
                        detail = e.response.json().get("detail", str(e))
                        st.error(f"Error de Validación (422): {detail}")
                    else:
                        st.error(f"Error del Servidor: {e.response.status_code}")
                except Exception as e:
                    st.error(f"Error de Conexión: {e}")
        else:
            st.warning("Ingresa el producto")

with tab2:
    st.info("Sube un screenshot de Facebook Marketplace")
    uploaded_file = st.file_uploader(
        "Sube imagen",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        st.image(uploaded_file, width=300)
        
        if st.button("🔍 ANALIZAR IMAGEN", type="primary", use_container_width=True):
            track_event("evaluation_started", {"type": "image"})
            
            with st.spinner("Procesando imagen..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    response = httpx.post(f"{API_URL}/api/evaluate-image", files=files, timeout=60.0)
                    response.raise_for_status()
                    result = response.json()
                    
                    if result.get("success", True): # Check success flag if backend sends it
                        increment_usage()
                        track_event("evaluation_completed", {"type": "image"})
                        
                        if "extraccion" in result:
                            st.success(f"Detectado: **{result['extraccion'].get('producto', 'Producto')}**")
                        display_results(result)
                    else:
                        st.error("Error analizando imagen.")

                except Exception as e:
                    st.error(f"Error al analizar imagen: {e}")

# ============ FOOTER CON FEEDBACK ============
st.divider()
st.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <p style="color: #999; font-size: 0.8rem;">
        🇨🇱 Hecho en Chile | 
        <a href="mailto:feedback@flipscore.app">¿Feedback?</a>
    </p>
</div>
""", unsafe_allow_html=True)
