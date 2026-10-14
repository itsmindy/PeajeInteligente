"""Chat especializado en solicitar y presentar gráficos del flujo vehicular."""
import streamlit as st
import pandas as pd
import plotly.express as px
from ai_agent import preguntar_agente


def _quick_chart(prompt, df):
    p = prompt.lower()
    if any(w in p for w in ["por año", "por anio", "anual", "años", "anios", "evolución anual", "evolucion anual"]):
        data = df.groupby("anio", as_index=False)["veh_total"].sum().sort_values("anio")
        return "anio", data.rename(columns={"veh_total":"veh_total"}), "Evolución anual del flujo"
    if any(w in p for w in ["mensual", "por mes", "mes a mes", "evolución", "evolucion", "tendencia"]):
        data = df.groupby(["anio","mes"], as_index=False)["veh_total"].sum().sort_values(["anio","mes"])
        data["periodo"] = data["anio"].astype(int).astype(str) + "-" + data["mes"].astype(int).astype(str).str.zfill(2)
        return "mensual", data, "Evolución mensual del flujo"
    if any(w in p for w in ["departamento", "departamentos", "ciudad", "región", "region"]):
        data = df.groupby("departamento", as_index=False)["veh_total"].sum().sort_values("veh_total", ascending=False)
        return "departamento", data, "Flujo por departamento"
    if any(w in p for w in ["peaje", "peajes", "ranking", "top"]):
        data = df.groupby(["nombre_peaje","departamento"], as_index=False)["veh_total"].sum().sort_values("veh_total", ascending=False).head(20)
        return "peajes", data, "Ranking de peajes por flujo"
    if any(w in p for w in ["ligeros", "pesados", "tipo de vehículo", "tipos de vehículo", "composición", "composicion"]):
        data = pd.DataFrame({
            "tipo":["Vehículos ligeros","Vehículos pesados"],
            "vehiculos":[int(df["veh_ligeros_total"].sum()),int(df["veh_pesados_total"].sum())]
        })
        return "tipos", data, "Composición vehicular"
    return None, None, None


def render_chart_agent(df, mostrar_grafico, chart_layout):
    st.subheader("📈 Chat de gráficos")
    st.write("Pide una visualización en lenguaje natural. El chat genera gráficos con los registros que estén seleccionados en los filtros superiores.")
    st.caption("Prueba: «Grafica la evolución mensual», «Compara el flujo por departamento», «Muestra el top 10 de peajes».")

    if "chart_chat_history" not in st.session_state:
        st.session_state.chart_chat_history = []

    for history_index, item in enumerate(st.session_state.chart_chat_history):
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item.get("chart_type") == "custom":
                st.plotly_chart(item["figure"], use_container_width=True, key=f"chart_history_custom_{history_index}")
            elif item.get("chart_type"):
                mostrar_grafico(item["chart_type"], item.get("chart_data"), item.get("title"))

    prompt = st.chat_input("¿Qué gráfico necesitas?", key="chart_chat_input")
    if prompt:
        st.session_state.chart_chat_history.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Preparando la visualización…"):
                kind, data, title = _quick_chart(prompt, df)
                answer = ""
                if kind:
                    answer = f"Generé **{title.lower()}** con los datos filtrados."
                else:
                    answer, data, kind = preguntar_agente(prompt + " Devuelve un gráfico adecuado para esta solicitud.", df)
                    title = "Gráfico solicitado"
                st.markdown(answer)
                if kind and data is not None:
                    mostrar_grafico(kind, data.to_dict("records") if isinstance(data, pd.DataFrame) else data, title)
                elif not kind:
                    st.info("No pude identificar el tipo de gráfico. Prueba con evolución mensual, por año, por departamento, ranking de peajes o composición vehicular.")
        st.session_state.chart_chat_history.append({
            "role":"assistant","content":answer,"chart_type":kind,
            "chart_data":data.to_dict("records") if isinstance(data,pd.DataFrame) else data,
            "title":title
        })
    if st.button("Limpiar chat de gráficos", key="clear_chart_chat"):
        st.session_state.chart_chat_history = []
        st.rerun()
