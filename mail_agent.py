"""Chat de email: redacta y prepara adjuntos; solo envía al recibir el comando exacto ENVIAR."""
import os
import smtplib
from email.message import EmailMessage
import streamlit as st


def _secret(name, default=None):
    try:
        value = st.secrets.get(name, default)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def _draft_email(request, df):
    """Usa Groq para redactar; si falla, genera un borrador de respaldo con datos reales."""
    api_key = _secret("GROQ_API_KEY")
    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model=_secret("GROQ_MODEL", "openai/gpt-oss-120b"),
                temperature=0.2,
                messages=[
                    {"role": "system", "content": (
                        "Redacta en español un correo profesional. No inventes cifras. "
                        "Devuelve exactamente dos secciones: ASUNTO: una línea; MENSAJE: texto."
                    )},
                    {"role": "user", "content": (
                        f"Solicitud: {request}\n"
                        f"Resumen real del conjunto filtrado: {len(df)} registros, "
                        f"{df['nombre_peaje'].nunique() if 'nombre_peaje' in df else 0} peajes, "
                        f"{int(df['veh_total'].sum()) if 'veh_total' in df else 0} vehículos. "
                        "Indica que se adjunta el Excel con los datos filtrados."
                    )}
                ],
            )
            text = completion.choices[0].message.content or ""
            subject, body = "Reporte de flujo vehicular", text
            if "ASUNTO:" in text:
                rest = text.split("ASUNTO:", 1)[1]
                if "MENSAJE:" in rest:
                    subject, body = rest.split("MENSAJE:", 1)
            return subject.strip()[:160], body.strip()
        except Exception:
            pass
    return (
        "Reporte de flujo vehicular - Peaje Inteligente",
        f"Buen día,\n\nComparto el reporte de flujo vehicular según los filtros seleccionados. "
        f"El archivo Excel adjunto contiene {len(df)} registros.\n\nSaludos."
    )


def _excel_attachment(df, excel_bytes):
    return excel_bytes(df)


def _send_email(to_email, subject, body, attachment_bytes):
    sender = _secret("GMAIL_SENDER")
    password = _secret("GMAIL_APP_PASSWORD")
    if not sender or not password:
        raise RuntimeError("Faltan GMAIL_SENDER o GMAIL_APP_PASSWORD en Secrets.")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)
    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="reporte_peaje_inteligente.xlsx",
    )
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)


def render_mail_agent(df, excel_bytes, numero):
    st.markdown("""
    <style>
    .mail-hero { padding:18px 20px; border-radius:16px; background:linear-gradient(110deg,#f4eaff 0%,#eef9ef 100%); margin-bottom:12px; }
    .mail-hero h3 { margin:0 0 5px 0; font-size:20pt; color:#24304c; }
    .mail-hero p { margin:0; font-size:14pt; color:#45536d; }
    .mail-status { padding:14px 18px; border-radius:12px; background:#dff4e8; color:#087443; margin:10px 0 18px; font-size:14pt; }
    .mail-card { border:1px solid #bd39ff; border-radius:20px; padding:18px; margin:14px 0; background:rgba(255,255,255,.62); }
    </style>
    <div class="mail-hero">
      <h3>✉️ PeajeMail · Envío de reportes</h3>
      <p>Redacta el correo con el agente y envía el Excel de los datos filtrados cuando lo revises.</p>
    </div>
    """, unsafe_allow_html=True)
    sender = _secret("GMAIL_SENDER", "")
    if sender:
        st.markdown(f'<div class="mail-status">Gmail configurado: <u>{sender}</u></div>', unsafe_allow_html=True)
    st.write("El correo adjunta un Excel con los datos filtrados. Preparar un borrador no envía ningún mensaje.")
    st.caption("Ejemplo: «Redacta un correo formal para mi profesor con un resumen de los datos filtrados».")

    if "email_chat_history" not in st.session_state:
        st.session_state.email_chat_history = []
    if "email_draft" not in st.session_state:
        st.session_state.email_draft = None
    if "email_draft_to" not in st.session_state:
        st.session_state.email_draft_to = _secret("GMAIL_REPORT_TO", "")

    st.session_state.email_draft_to = st.text_input(
        "Correo destinatario", value=st.session_state.email_draft_to,
        placeholder="profesor@ejemplo.com", key="email_recipient_input"
    )

    draft = st.session_state.email_draft
    if draft:
        st.markdown("#### Borrador pendiente")
        st.markdown('<div class="mail-card">', unsafe_allow_html=True)
        draft["to"] = st.text_input("Correo destinatario", value=draft.get("to", ""), key="email_draft_to")
        draft["subject"] = st.text_input("Asunto", value=draft.get("subject", ""), key="email_draft_subject")
        draft["body"] = st.text_area("Mensaje", value=draft.get("body", ""), height=155, key="email_draft_body")
        st.caption(f"📎 Archivo adjunto: Excel con {numero(len(df))} registros del filtro actual.")
        confirmed = st.checkbox(
            "Confirmo que deseo enviar este reporte al destinatario indicado.",
            key="email_send_confirm"
        )
        if st.button("✉️ ENVIAR AHORA", key="email_send_now", type="primary", use_container_width=True):
            current = {
                "to": st.session_state.get("email_draft_to", "").strip(),
                "subject": st.session_state.get("email_draft_subject", "").strip(),
                "body": st.session_state.get("email_draft_body", "").strip(),
            }
            if not confirmed:
                st.warning("Marca la casilla de confirmación antes de enviar.")
            elif not current["to"] or "@" not in current["to"]:
                st.error("El correo destinatario no parece válido.")
            elif not current["subject"] or not current["body"]:
                st.error("Completa el asunto y el mensaje antes de enviar.")
            else:
                try:
                    _send_email(current["to"], current["subject"], current["body"], _excel_attachment(df, excel_bytes))
                    st.success(f"Correo enviado correctamente a {current['to']} con el Excel adjunto.")
                    st.session_state.email_draft = None
                    st.session_state.email_chat_history.append({"role": "assistant", "content": f"Correo enviado correctamente a {current['to']} con el Excel adjunto."})
                    st.session_state.email_send_confirm = False
                    st.rerun()
                except Exception as exc:
                    st.error(f"No se pudo enviar el correo: {exc}")
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("También puedes escribir exactamente ENVIAR en el chat para confirmar el envío.")
    else:
        st.info("Todavía no hay un borrador. Describe el correo en el chat para prepararlo.")

    for item in st.session_state.email_chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    prompt = st.chat_input("Escribe una solicitud o ENVIAR…", key="email_chat_input")
    if prompt:
        st.session_state.email_chat_history.append({"role": "user", "content": prompt})
        normalized = prompt.strip().upper()

        if normalized == "ENVIAR":
            draft = st.session_state.get("email_draft")
            if not draft:
                reply = "No hay un borrador pendiente. Primero pídeme que redacte un correo."
                st.session_state.email_chat_history.append({"role": "assistant", "content": reply})
            elif not draft.get("to") or "@" not in draft["to"]:
                reply = "No puedo enviarlo: el destinatario no parece válido. Corrige el campo «Para» y vuelve a escribir ENVIAR."
                st.session_state.email_chat_history.append({"role": "assistant", "content": reply})
            elif not draft.get("subject", "").strip() or not draft.get("body", "").strip():
                reply = "No puedo enviarlo: completa el asunto y el mensaje antes de escribir ENVIAR."
                st.session_state.email_chat_history.append({"role": "assistant", "content": reply})
            else:
                try:
                    _send_email(
                        draft["to"].strip(), draft["subject"].strip(), draft["body"].strip(),
                        _excel_attachment(df, excel_bytes)
                    )
                    reply = f"Correo enviado correctamente a {draft['to']} con el Excel adjunto."
                    st.session_state.email_draft = None
                    st.session_state.email_chat_history.append({"role": "assistant", "content": reply})
                except Exception as exc:
                    reply = f"No se pudo enviar el correo: {exc}"
                    st.session_state.email_chat_history.append({"role": "assistant", "content": reply})
        else:
            subject, body = _draft_email(prompt, df)
            recipient = st.session_state.get("email_recipient_input", "") or _secret("GMAIL_REPORT_TO", "")
            st.session_state.email_draft = {"to": recipient, "subject": subject, "body": body}
            reply = (
                "Preparé un borrador editable. Revisa el destinatario, el asunto y el mensaje arriba. "
                "Si todo está correcto, escribe exactamente **ENVIAR** aquí. No se enviará hasta recibir ese comando."
            )
            st.session_state.email_chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    if st.button("Descartar borrador", key="discard_email_draft", disabled=not bool(st.session_state.email_draft)):
        st.session_state.email_draft = None
        st.session_state.email_chat_history.append({"role": "assistant", "content": "Borrador descartado. No se envió ningún correo."})
        st.rerun()
