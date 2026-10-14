"""Agente de análisis de Peaje Inteligente. Solo calcula sobre el DataFrame filtrado."""
import json
import os
import pandas as pd


def _secret(name, default=None):
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def _build_tools(df: pd.DataFrame):
    def resumen_general():
        return {
            "registros": int(len(df)),
            "peajes_distintos": int(df["codigo_peaje"].nunique()),
            "anios": sorted(int(v) for v in df["anio"].dropna().unique()),
            "flujo_total": int(df["veh_total"].sum()),
            "vehiculos_ligeros": int(df["veh_ligeros_total"].sum()),
            "vehiculos_pesados": int(df["veh_pesados_total"].sum()),
            "imd_media_simple": round(float(df["veh_imd"].mean()), 2) if df["veh_imd"].notna().any() else None,
        }

    def flujo_por_anio():
        result = df.groupby("anio", as_index=False).agg(
            veh_total=("veh_total", "sum"),
            veh_ligeros=("veh_ligeros_total", "sum"),
            veh_pesados=("veh_pesados_total", "sum"),
        ).sort_values("anio")
        return result.to_dict(orient="records")

    def evolucion_mensual():
        result = df.groupby(["anio", "mes"], as_index=False).agg(
            veh_total=("veh_total", "sum"),
            veh_ligeros=("veh_ligeros_total", "sum"),
            veh_pesados=("veh_pesados_total", "sum"),
        ).sort_values(["anio", "mes"])
        result["periodo"] = result["anio"].astype(int).astype(str) + "-" + result["mes"].astype(int).astype(str).str.zfill(2)
        return result[["periodo", "veh_total", "veh_ligeros", "veh_pesados"]].to_dict(orient="records")

    def ranking_peajes():
        result = df.groupby(["codigo_peaje", "nombre_peaje", "departamento"], as_index=False).agg(
            veh_total=("veh_total", "sum"), imd_promedio=("veh_imd", "mean")
        ).sort_values("veh_total", ascending=False).head(20)
        return result.round(2).to_dict(orient="records")

    def flujo_por_departamento():
        result = df.groupby("departamento", as_index=False).agg(
            veh_total=("veh_total", "sum"),
            veh_ligeros=("veh_ligeros_total", "sum"),
            veh_pesados=("veh_pesados_total", "sum"),
        ).sort_values("veh_total", ascending=False)
        return result.to_dict(orient="records")

    def comparar_tipos_vehiculo():
        return [
            {"tipo":"Ligeros","vehiculos":int(df["veh_ligeros_total"].sum())},
            {"tipo":"Pesados","vehiculos":int(df["veh_pesados_total"].sum())},
        ]

    functions = {
        "resumen_general": resumen_general,
        "flujo_por_anio": flujo_por_anio,
        "evolucion_mensual": evolucion_mensual,
        "ranking_peajes": ranking_peajes,
        "flujo_por_departamento": flujo_por_departamento,
        "comparar_tipos_vehiculo": comparar_tipos_vehiculo,
    }
    tools = [
        {"type":"function","function":{"name":"resumen_general","description":"Calcula indicadores generales reales del conjunto filtrado.","parameters":{"type":"object","properties":{},"required":[]}}},
        {"type":"function","function":{"name":"flujo_por_anio","description":"Agrupa flujo por año para comparar tendencias.","parameters":{"type":"object","properties":{},"required":[]}}},
        {"type":"function","function":{"name":"evolucion_mensual","description":"Agrupa el flujo por año y mes.","parameters":{"type":"object","properties":{},"required":[]}}},
        {"type":"function","function":{"name":"ranking_peajes","description":"Devuelve hasta 20 peajes ordenados por flujo vehicular.","parameters":{"type":"object","properties":{},"required":[]}}},
        {"type":"function","function":{"name":"flujo_por_departamento","description":"Agrupa el flujo por departamento.","parameters":{"type":"object","properties":{},"required":[]}}},
        {"type":"function","function":{"name":"comparar_tipos_vehiculo","description":"Compara vehículos ligeros y pesados.","parameters":{"type":"object","properties":{},"required":[]}}},
    ]
    return tools, functions


def preguntar_agente(pregunta: str, df: pd.DataFrame):
    """Retorna (respuesta, datos_para_grafico, tipo_grafico)."""
    api_key = _secret("GROQ_API_KEY")
    if not api_key:
        return "No está configurada GROQ_API_KEY. El dashboard seguirá funcionando; añade la clave para activar la IA.", None, None
    try:
        from groq import Groq
        tools, functions = _build_tools(df)
        client = Groq(api_key=api_key)
        messages = [
            {"role":"system","content":(
                "Eres el analista de Peaje Inteligente. Responde en español, usa herramientas para cifras reales "
                "y no inventes números. Solo analiza el DataFrame filtrado. Puedes solicitar un gráfico mediante "
                "una etiqueta final: [CHART:ANIO], [CHART:MENSUAL], [CHART:PEAJES], [CHART:DEPARTAMENTO] o "
                "[CHART:TIPOS]. El conjunto tiene datos por periodo mensual, no horarios."
            )},
            {"role":"user","content":pregunta},
        ]
        gathered = {}
        chart_map = {
            "anio":("flujo_por_anio","[CHART:ANIO]"),
            "mensual":("evolucion_mensual","[CHART:MENSUAL]"),
            "peajes":("ranking_peajes","[CHART:PEAJES]"),
            "departamento":("flujo_por_departamento","[CHART:DEPARTAMENTO]"),
            "tipos":("comparar_tipos_vehiculo","[CHART:TIPOS]"),
        }
        for _ in range(5):
            completion = client.chat.completions.create(
                model=_secret("GROQ_MODEL","openai/gpt-oss-120b"),
                temperature=0.1, messages=messages, tools=tools, tool_choice="auto"
            )
            message = completion.choices[0].message
            if not message.tool_calls:
                answer = message.content or "No se obtuvo respuesta del agente."
                kind = None
                for k, (_, label) in chart_map.items():
                    if label in answer:
                        answer = answer.replace(label,"").strip()
                        kind = k
                data = gathered.get(chart_map[kind][0]) if kind else None
                return answer, data, kind
            messages.append({
                "role":"assistant","content":message.content or "",
                "tool_calls":[{"id":c.id,"type":"function","function":{"name":c.function.name,"arguments":c.function.arguments}}
                              for c in message.tool_calls]
            })
            for call in message.tool_calls:
                name = call.function.name
                result = functions[name]() if name in functions else {"error":"Herramienta desconocida"}
                gathered[name] = result
                messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result,ensure_ascii=False,default=str)})
        return "La consulta requiere varios pasos. Intenta hacer una pregunta más concreta.", None, None
    except Exception as exc:
        return f"No se pudo consultar Groq: {exc}", None, None
