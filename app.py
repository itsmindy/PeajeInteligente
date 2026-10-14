import os
from io import BytesIO
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client

from ai_agent import preguntar_agente
from chart_agent import render_chart_agent
from mail_agent import render_mail_agent

st.set_page_config(
    page_title="Peaje Inteligente",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BLUE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { --navy:#10194b; --blue:#263b91; --cyan:#27c3ee; --sky:#66d7ff; --ink:#19234d; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size:14pt; }
.stApp, .stApp p, .stApp label, .stApp li, .stApp .stMarkdown,
.stApp [data-testid="stWidgetLabel"], .stApp input, .stApp textarea,
.stApp [data-baseweb="select"], .stApp button, .stApp [data-testid="stCaptionContainer"] {
  font-size:14pt !important;
}
.stApp [data-testid="stCaptionContainer"] { line-height:1.45; }
.stApp input, .stApp textarea { min-height:44px; }
.stApp [data-testid="stMetricLabel"] { font-size:14pt !important; }
.stApp [data-testid="stMetricValue"] { font-size:20pt !important; }
.stApp { background: linear-gradient(180deg,#f7faff 0%,#eef4ff 100%); color:var(--ink); }
[data-testid="stHeader"] { background:rgba(247,250,255,.92); }
.block-container { padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1500px; }
.hero {
  background:linear-gradient(120deg,#11194f 0%,#24378b 58%,#087fb4 100%);
  color:#fff; border-radius:24px; padding:28px 32px; margin-bottom:20px;
  box-shadow:0 16px 38px rgba(27,52,130,.18);
}
.hero h1 { color:#fff; font-size:clamp(2rem,4vw,3.2rem); font-weight:800; letter-spacing:-1.4px; margin:0; }
.hero p { color:#d9eaff; margin:8px 0 0; font-size:14pt; }
.hero-pill { display:inline-block; padding:6px 11px; border-radius:999px; background:#ffffff20; color:#d7f5ff; font-size:.78rem; margin-bottom:12px; }
.kpi {
 background:#fff; border:1px solid #dce7ff; border-radius:18px; padding:15px 17px;
 box-shadow:0 6px 20px rgba(34,61,133,.06); min-height:108px;
}
.kpi-label { color:#64739b; font-size:14pt; font-weight:600; }
.kpi-value { color:#17255f; font-size:clamp(1.3rem,2.1vw,2rem); font-weight:800; margin-top:7px; }
.kpi-icon { color:#18a9dc; font-size:1.2rem; }
.section-card {
 background:#fff; border:1px solid #dce7ff; border-radius:20px; padding:18px 20px;
 box-shadow:0 8px 24px rgba(34,61,133,.05); margin-bottom:14px;
}
div[data-testid="stTabs"] button[role="tab"] { border-radius:12px 12px 0 0; font-weight:650; }
div[data-testid="stTabs"] button[aria-selected="true"] { color:#147ac2; border-bottom-color:#23b9e9; }
.stButton button, .stDownloadButton button {
 border-radius:11px; border:1px solid #cbdafa; font-weight:650;
}
.stButton button[kind="primary"] { background:linear-gradient(100deg,#263b91,#087fb4); border:0; color:white; }
div[data-baseweb="select"] > div { border-radius:12px; border-color:#b8cdfa; background:#fff; }
div[data-baseweb="tag"] { background:#2452b5 !important; border:1px solid #3977df !important; color:#fff !important; }
div[data-baseweb="tag"] span { color:#fff !important; }
div[role="listbox"] [aria-selected="true"] { background:#e8f2ff !important; }
div[data-testid="stMultiSelect"] { margin-bottom:.35rem; }
div[data-testid="stMultiSelect"] [data-baseweb="select"] { min-height:42px; }
[data-testid="stMetric"] { background:#fff; border:1px solid #dce7ff; border-radius:16px; padding:12px 15px; }
[data-testid="stMetricLabel"] { color:#64739b; }
[data-testid="stMetricValue"] { color:#17255f; }
div[data-testid="stDataFrame"] { border:1px solid #dce7ff; border-radius:14px; overflow:hidden; }
div[data-testid="stChatMessage"] { border:1px solid #e0e9fb; border-radius:16px; padding:10px 14px; background:#fff; }
.small-note { color:#6b789a; font-size:14pt; }
</style>
"""
st.markdown(BLUE_CSS, unsafe_allow_html=True)


def secret(name, default=None):
    try:
        value = st.secrets.get(name, default)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


@st.cache_resource
def supabase_client():
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Faltan SUPABASE_URL o SUPABASE_KEY. Configúralos en .streamlit/secrets.toml."
        )
    return create_client(url, key)


@st.cache_data(ttl=300)
def cargar_datos():
    client = supabase_client()
    records, start, size = [], 0, 1000
    while True:
        batch = (
            client.table("flujo_vehicular")
            .select("*")
            .range(start, start + size - 1)
            .execute()
            .data or []
        )
        records.extend(batch)
        if len(batch) < size:
            break
        start += size
    df = pd.DataFrame(records)
    if df.empty:
        return df

    numeric = [
        "veh_ligeros_tar_dif", "veh_ligeros_automoviles", "veh_pesados_tar_dif",
        "veh_pesados_2e", "veh_pesados_3e", "veh_pesados_4e", "veh_pesados_5e",
        "veh_pesados_6e", "veh_pesados_7e", "veh_ligeros_total", "veh_ligeros_imd",
        "veh_pesados_total", "veh_pesados_imd", "veh_total", "veh_imd", "anio", "mes", "periodo"
    ]
    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["administ", "codigo_peaje", "departamento", "nombre_peaje"]:
        if col in df.columns:
            df[col] = df[col].fillna("Sin dato").astype(str)

    required = ["departamento", "nombre_peaje", "anio", "mes", "administ", "veh_total"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Faltan columnas esperadas en flujo_vehicular: " + ", ".join(missing))
    for col in ["veh_ligeros_total", "veh_pesados_total", "veh_imd"]:
        if col not in df.columns:
            df[col] = 0
    if "codigo_peaje" not in df.columns:
        df["codigo_peaje"] = df["nombre_peaje"]
    return df


def numero(value):
    try:
        return f"{int(round(float(value))):,}".replace(",", " ")
    except (ValueError, TypeError):
        return "—"


def excel_bytes(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Flujo vehicular")
    return out.getvalue()


def chart_layout(fig, height=None):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="Inter, sans-serif", color="#24315f"),
        title=dict(font=dict(size=17, color="#17255f")),
        margin=dict(l=12, r=12, t=55, b=12),
        colorway=["#28c7f2", "#ffb347", "#4169e1", "#8b9cf6", "#ff6b8a", "#2dd4bf"],
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _plotly_key(prefix="plotly"):
    """Genera una clave única para cada gráfico renderizado durante la sesión."""
    counter = int(st.session_state.get("_plotly_chart_counter", 0)) + 1
    st.session_state["_plotly_chart_counter"] = counter
    return f"{prefix}_{counter}"


def mostrar_grafico(tipo, datos, titulo=None):
    if datos is None:
        return
    d = pd.DataFrame(datos)
    if d.empty:
        st.info("No hay suficientes datos para construir el gráfico.")
        return
    if tipo == "anio" and {"anio", "veh_total"}.issubset(d.columns):
        fig = px.line(d, x="anio", y="veh_total", markers=True, title=titulo or "Flujo vehicular por año",
                      labels={"anio": "Año", "veh_total": "Vehículos"})
    elif tipo == "mensual" and {"periodo", "veh_total"}.issubset(d.columns):
        fig = px.line(d, x="periodo", y="veh_total", markers=True, title=titulo or "Evolución mensual",
                      labels={"periodo": "Periodo", "veh_total": "Vehículos"})
        fig.update_layout(xaxis_tickangle=-45)
    elif tipo == "peajes" and {"nombre_peaje", "veh_total"}.issubset(d.columns):
        d = d.sort_values("veh_total").tail(20)
        fig = px.bar(d, x="veh_total", y="nombre_peaje", color="departamento" if "departamento" in d.columns else None,
                     orientation="h", title=titulo or "Ranking de peajes",
                     labels={"veh_total": "Vehículos", "nombre_peaje": "Peaje", "departamento": "Departamento"})
    elif tipo == "departamento" and {"departamento", "veh_total"}.issubset(d.columns):
        fig = px.bar(d, x="departamento", y="veh_total", title=titulo or "Flujo por departamento",
                     labels={"departamento": "Departamento", "veh_total": "Vehículos"})
    elif tipo == "tipos" and {"tipo", "vehiculos"}.issubset(d.columns):
        fig = px.pie(d, names="tipo", values="vehiculos", hole=.58, title=titulo or "Vehículos ligeros y pesados")
    else:
        st.info("El agente no devolvió una estructura compatible con el gráfico solicitado.")
        return
    st.plotly_chart(chart_layout(fig), use_container_width=True, key=_plotly_key("agent_chart"))


def filtro_multiselect(label, options, key, help_text=None):
    """Selector compacto: vacío significa Todos; el menú permite marcar varios elementos."""
    options = list(options)
    # No preseleccionar todo: así el campo queda limpio y las opciones aparecen en un menú
    # con casillas al abrirlo, en vez de llenar la pantalla con decenas de etiquetas.
    valid = set(options)
    if key in st.session_state:
        st.session_state[key] = [v for v in st.session_state[key] if v in valid]
    return st.multiselect(
        label,
        options=options,
        default=[],
        key=key,
        placeholder="Todos (sin filtro)" if not st.session_state.get(key) else "Buscar o agregar selección",
        help=help_text or "Marca varias opciones en el desplegable. Si lo dejas vacío, se incluyen todas.",
        label_visibility="visible",
    )


def aplicar_filtro(df, columna, seleccion):
    """Una selección vacía equivale a no aplicar ese filtro."""
    return df if not seleccion else df[df[columna].isin(seleccion)]


st.markdown(
    """
    <div class="hero">
      <span class="hero-pill">ANÁLISIS DE DATOS · 2014–2026 I</span>
      <h1>🚘 Peaje Inteligente</h1>
      <p>Panel de análisis del flujo vehicular de peajes · datos conectados a Supabase</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container():
    if st.button("↻ Actualizar datos", type="secondary"):
        cargar_datos.clear()
        st.rerun()
    try:
        df = cargar_datos()
    except Exception as exc:
        st.error(f"No se pudo conectar o leer la tabla: {exc}")
        st.info("Verifica SUPABASE_URL, SUPABASE_KEY y que exista public.flujo_vehicular.")
        st.stop()

if df.empty:
    st.warning("La tabla public.flujo_vehicular no contiene registros.")
    st.stop()

# Filtros compactos: los desplegables muestran opciones marcables y búsqueda.
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Filtros de análisis")
st.caption("Abre cada lista para marcar varios valores. Usa la búsqueda para encontrar un peaje o departamento. Si dejas un filtro vacío, se consideran todos sus valores.")

dept_options = sorted(df["departamento"].dropna().unique().tolist())
selected_dept = filtro_multiselect(
    "Departamento", dept_options, "filter_dept",
    "Puedes marcar varios departamentos. Vacío = todos."
)
scoped = aplicar_filtro(df, "departamento", selected_dept)

toll_options = sorted(scoped["nombre_peaje"].dropna().unique().tolist())
# Si cambia el departamento, se eliminan de la selección los peajes que ya no correspondan.
if "filter_toll" in st.session_state:
    st.session_state["filter_toll"] = [x for x in st.session_state["filter_toll"] if x in toll_options]
selected_tolls = filtro_multiselect(
    "Peajes", toll_options, "filter_toll",
    "Puedes marcar varios peajes. Vacío = todos los peajes de los departamentos considerados."
)

year_options = sorted(int(v) for v in df["anio"].dropna().unique())
selected_years = filtro_multiselect("Año", year_options, "filter_year", "Marca uno o varios años; vacío = todos.")

month_options = sorted(int(v) for v in df["mes"].dropna().unique())
month_names = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
month_labels = [month_names.get(m, str(m)) for m in month_options]
selected_month_labels = filtro_multiselect("Mes", month_labels, "filter_month", "Marca uno o varios meses; vacío = todos.")
selected_months = [m for m in month_options if month_names.get(m, str(m)) in selected_month_labels]

admin_options = sorted(df["administ"].dropna().unique().tolist())
selected_admin = filtro_multiselect("Administración", admin_options, "filter_admin", "Marca una o varias administraciones; vacío = todas.")
st.markdown("</div>", unsafe_allow_html=True)

filtered = df.copy()
filtered = aplicar_filtro(filtered, "departamento", selected_dept)
filtered = aplicar_filtro(filtered, "nombre_peaje", selected_tolls)
filtered = aplicar_filtro(filtered, "anio", selected_years)
filtered = aplicar_filtro(filtered, "mes", selected_months)
filtered = aplicar_filtro(filtered, "administ", selected_admin)

if filtered.empty:
    st.warning("Los filtros seleccionados no devuelven registros. Cambia los filtros o pulsa «Todos».")
    st.stop()

kpi_cols = st.columns(5)
kpis = [
    ("REGISTROS", numero(len(filtered)), "▦"),
    ("PEAJES", numero(filtered["codigo_peaje"].nunique()), "⌁"),
    ("FLUJO VEHICULAR", numero(filtered["veh_total"].sum()), "↗"),
    ("VEHÍCULOS LIGEROS", numero(filtered["veh_ligeros_total"].sum()), "🚗"),
    ("IMD PROMEDIO", numero(filtered["veh_imd"].mean()), "◷"),
]
for col, (label, value, icon) in zip(kpi_cols, kpis):
    with col:
        st.markdown(f'<div class="kpi"><div class="kpi-label">{icon} &nbsp; {label}</div><div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)

tab_dash, tab_compare, tab_data, tab_ai, tab_charts, tab_mail = st.tabs([
    "📊 Dashboard", "🏁 Comparaciones", "📋 Datos", "🤖 Chat IA", "📈 Chat de gráficos", "✉️ Chat de emails"
])

with tab_dash:
    monthly = filtered.groupby(["anio", "mes"], as_index=False)["veh_total"].sum().sort_values(["anio", "mes"])
    monthly["periodo"] = monthly["anio"].astype(int).astype(str) + "-" + monthly["mes"].astype(int).astype(str).str.zfill(2)
    by_year = filtered.groupby("anio", as_index=False)["veh_total"].sum()
    left, right = st.columns([1.55, 1])
    with left:
        fig = px.line(monthly, x="periodo", y="veh_total", markers=True, title="Evolución mensual del flujo",
                      labels={"periodo":"Año-mes", "veh_total":"Vehículos"})
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(chart_layout(fig, 380), use_container_width=True, key=_plotly_key("dashboard_chart"))
    with right:
        fig = px.pie(pd.DataFrame({
            "tipo": ["Vehículos ligeros", "Vehículos pesados"],
            "vehiculos": [int(filtered["veh_ligeros_total"].sum()), int(filtered["veh_pesados_total"].sum())]
        }), names="tipo", values="vehiculos", hole=.58, title="Composición vehicular")
        st.plotly_chart(chart_layout(fig, 380), use_container_width=True, key=_plotly_key("dashboard_chart"))
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_layout(px.bar(by_year, x="anio", y="veh_total", title="Flujo anual",
                                            labels={"anio":"Año","veh_total":"Vehículos"})), use_container_width=True, key=_plotly_key("annual_chart"))
    with c2:
        dept = filtered.groupby("departamento", as_index=False)["veh_total"].sum().sort_values("veh_total", ascending=False)
        st.plotly_chart(chart_layout(px.bar(dept, x="departamento", y="veh_total", title="Flujo por departamento",
                                            labels={"departamento":"Departamento","veh_total":"Vehículos"})), use_container_width=True, key=_plotly_key("department_chart"))

with tab_compare:
    st.subheader("Comparaciones y rankings")
    rank = filtered.groupby(["nombre_peaje", "departamento"], as_index=False)["veh_total"].sum().sort_values("veh_total", ascending=False)
    max_n = max(1, min(30, len(rank)))
    top_n = st.slider("Cantidad de peajes", min_value=1, max_value=max_n, value=min(10, max_n))
    fig = px.bar(rank.head(top_n).sort_values("veh_total"), x="veh_total", y="nombre_peaje", color="departamento",
                 orientation="h", title=f"Top {top_n} peajes por flujo",
                 labels={"veh_total":"Vehículos","nombre_peaje":"Peaje","departamento":"Departamento"})
    st.plotly_chart(chart_layout(fig), use_container_width=True, key=_plotly_key("agent_chart"))
    dept = filtered.groupby("departamento", as_index=False)["veh_total"].sum().sort_values("veh_total", ascending=False)
    st.plotly_chart(chart_layout(px.bar(dept, x="departamento", y="veh_total", title="Comparación por departamento",
                                        labels={"departamento":"Departamento","veh_total":"Vehículos"})), use_container_width=True, key=_plotly_key("department_chart"))

with tab_data:
    st.subheader("Registros filtrados")
    st.caption(f"{numero(len(filtered))} filas visibles según los filtros actuales.")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    c1.download_button("Descargar CSV", filtered.to_csv(index=False).encode("utf-8-sig"),
                       "peajeinteligente.csv", "text/csv")
    c2.download_button("Descargar Excel", excel_bytes(filtered), "peajeinteligente.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tab_ai:
    st.subheader("Asistente inteligente de datos")
    st.write("Consulta cifras, tendencias, rankings y composición del flujo vehicular. El agente responde con cálculos del conjunto filtrado.")
    st.caption("Ejemplos: ¿Cuál fue el año con mayor flujo? · Resume estos datos · Compara ligeros y pesados.")
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []
    for item in st.session_state.ai_chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item.get("chart_type"):
                mostrar_grafico(item["chart_type"], item.get("chart_data"))
    prompt = st.chat_input("Pregunta sobre los datos filtrados…", key="ai_chat_input")
    if prompt:
        st.session_state.ai_chat_history.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analizando los registros…"):
                answer, chart_data, chart_type = preguntar_agente(prompt, filtered)
            st.markdown(answer)
            if chart_type:
                mostrar_grafico(chart_type, chart_data)
        st.session_state.ai_chat_history.append({
            "role":"assistant","content":answer,"chart_data":chart_data,"chart_type":chart_type
        })
    if st.button("Limpiar historial IA", key="clear_ai"):
        st.session_state.ai_chat_history = []
        st.rerun()

with tab_charts:
    render_chart_agent(filtered, mostrar_grafico, chart_layout)

with tab_mail:
    render_mail_agent(filtered, excel_bytes, numero)

st.divider()
st.markdown(
    f'<p class="small-note">Peaje Inteligente · Supabase · Última actualización de la interfaz: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>',
    unsafe_allow_html=True,
)
