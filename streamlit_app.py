import os
from dotenv import load_dotenv

import streamlit as st
from supabase import create_client
from email_sender import send_via_smtp, send_via_resend

# Charger .env au démarrage
load_dotenv()

st.set_page_config(page_title="Mail Groups Sender", page_icon="📧", layout="centered")

# --- Connexion Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Variables Supabase manquantes. Vérifie SUPABASE_URL et SUPABASE_ANON_KEY dans ton fichier .env.")
    st.stop()

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Sidebar: gestion des groupes ---
st.sidebar.header("👥 Groupes")
with st.sidebar.expander("Créer un groupe", expanded=True):
    new_group = st.text_input("Nom du groupe")
    if st.button("➕ Ajouter"):
        if new_group.strip():
            sb.table("email_groups").insert({"name": new_group.strip()}).execute()
            st.success("Groupe créé.")
        else:
            st.warning("Nom invalide.")

group_list = sb.table("email_groups").select("*").order("created_at").execute().data or []
group_names = {g["name"]: g["id"] for g in group_list}
sel_group_name = st.sidebar.selectbox("Groupes existants", list(group_names.keys()) if group_names else ["—"])

if group_names:
    gid = group_names[sel_group_name]
    st.sidebar.subheader(f"✉️ Membres de « {sel_group_name} »")

    with st.sidebar.form("add_member", clear_on_submit=True):
        email = st.text_input("Email à ajouter")
        add = st.form_submit_button("Ajouter l'email")
        if add and email:
            sb.table("group_members").insert({"group_id": gid, "email": email.strip()}).execute()
            st.toast("Email ajouté.")

    members = sb.table("group_members").select("id,email").eq("group_id", gid).order("created_at").execute().data or []
    if members:
        st.sidebar.write("\n".join(f"• {m['email']}" for m in members))
        # suppression simple
        to_remove = st.sidebar.multiselect("Supprimer des emails", [m["email"] for m in members])
        if st.sidebar.button("🗑️ Supprimer sélection"):
            for em in to_remove:
                mid = next(m["id"] for m in members if m["email"] == em)
                sb.table("group_members").delete().eq("id", mid).execute()
            st.sidebar.success("Supprimé.")

# --- Main: formulaire d'envoi ---
st.title("📨 Envoi d’e-mail à des groupes")
st.caption("Saisis l’objet, le contenu, sélectionne un groupe et ajoute des pièces jointes.")

with st.form("send_form"):
    subject = st.text_input("Objet")
    body = st.text_area("Contenu (HTML autorisé)", height=220, placeholder="Bonjour,\n\n...")
    selected_groups = st.multiselect(
        "Groupes de destinataires",
        options=list(group_names.keys()) if group_names else [],
        default=[sel_group_name] if group_names else []
    )
    files = st.file_uploader("Pièces jointes (multiple)", accept_multiple_files=True)
    submit = st.form_submit_button("✉️ Envoyer")

if submit:
    # Récup emails uniques
    emails = set()
    for gname in selected_groups:
        gid = group_names[gname]
        mem = sb.table("group_members").select("email").eq("group_id", gid).execute().data or []
        emails |= {m["email"] for m in mem}
    emails = sorted(list(emails))

    if not subject or not body or not emails:
        st.error("Objet, contenu et au moins un destinataire sont requis.")
    else:
        # Préparer pièces jointes
        attachments = []
        for f in files or []:
            attachments.append((f.name, f.read()))

        # Choix du mode d’envoi selon .env
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pwd = os.getenv("SMTP_PASSWORD", "")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "465"))

        resend_key = os.getenv("RESEND_API_KEY", "")
        from_addr = os.getenv("RESEND_FROM", smtp_user or "no-reply@example.com")

        try:
            if resend_key:
                # Mode API Resend si clé fournie
                send_via_resend(
                    api_key=resend_key,
                    from_addr=from_addr,
                    recipients=emails,
                    subject=subject,
                    html_body=body,
                    attachments=attachments
                )
            else:
                # Sinon SMTP
                if not smtp_user or not smtp_pwd:
                    st.error("Pas de RESEND_API_KEY et identifiants SMTP incomplets. Renseigne .env.")
                    st.stop()

                send_via_smtp(
                    sender=from_addr,
                    recipients=emails,
                    subject=subject,
                    html_body=body,
                    attachments=attachments,
                    host=smtp_host,
                    port=smtp_port,
                    user=smtp_user,
                    password=smtp_pwd
                )

            st.success(f"Email envoyé à {len(emails)} destinataire(s).")
        except Exception as e:
            st.exception(e)
