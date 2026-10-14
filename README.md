# Peaje Inteligente — versión azul

Dashboard Streamlit para análisis de flujo vehicular conectado a `public.flujo_vehicular` en Supabase.

## Funciones
- Filtros compactos tipo desplegable con opciones marcables, búsqueda y selección múltiple para departamento, peajes, años, meses y administración. Si un filtro queda vacío, incluye todos sus valores.
- Dashboard azul con indicadores, tendencias y composición vehicular.
- Comparaciones y ranking de peajes.
- Exportación de datos a CSV y Excel.
- Chat IA para preguntas analíticas (Groq).
- Chat especializado en gráficos.
- Chat de correo con borrador editable y envío del Excel por Gmail únicamente cuando el usuario escribe exactamente `ENVIAR`.

## Estructura
```text
PeajeInteligente_Azul/
├── .streamlit/
│   └── secrets.toml.example
├── sql/
│   └── 00_verificar_tabla.sql
├── app.py
├── ai_agent.py
├── chart_agent.py
├── mail_agent.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Instalar en Windows / VS Code
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```
Edita `.streamlit/secrets.toml` y agrega las credenciales reales. Después:
```powershell
python -m streamlit run app.py
```

## Secretos
- `SUPABASE_URL`: URL del proyecto Supabase.
- `SUPABASE_KEY`: utiliza una clave publicable/anon con políticas de acceso apropiadas para lectura. **No uses `service_role` en una app pública.**
- `GROQ_API_KEY`: clave de Groq.
- `GROQ_MODEL`: opcional; por defecto `openai/gpt-oss-120b`.
- `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, `GMAIL_REPORT_TO`: opcionales; requeridos para enviar desde el chat de correo.

En Streamlit Community Cloud, pega el contenido equivalente en **App → Settings → Secrets**. Nunca incluyas claves reales en GitHub ni las compartas en capturas.

## Tabla esperada
La app espera `public.flujo_vehicular` con columnas como:
`codigo_peaje`, `nombre_peaje`, `departamento`, `anio`, `mes`, `administ`, `veh_total`, `veh_ligeros_total`, `veh_pesados_total`, `veh_imd`.

Los campos `veh_ligeros_total`, `veh_pesados_total`, `veh_imd` se crean con cero en memoria si no están presentes, pero los campos base de filtrado y `veh_total` deben existir.

## Importante
- El chatbot y el chat de gráficos analizan únicamente las filas devueltas por los filtros actuales.
- La fuente disponible es mensual; no permite inferir horas punta ni flujo por hora.
- El chat de correo nunca envía al preparar un borrador: revisa destinatario, asunto y mensaje; después escribe `ENVIAR` para autorizar el envío.
- Si la aplicación se comparte públicamente, protege el acceso a Supabase mediante políticas/RLS adecuadas. No utilices una clave privilegiada de Supabase en la app.
