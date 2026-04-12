import os
import smtplib
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from email.message import EmailMessage
from pyppeteer import launch

app = FastAPI()

# Modèle de données
class IncidentReport(BaseModel):
    nom_passager: str
    sexe: str
    date: str
    heure: str
    vol_destination: str
    lieu: str = ""
    nature: str = ""
    description: str = ""

# --- GÉNÉRATION PDF ---
async def generer_pdf_chrome(data: IncidentReport):
    nom_clean = data.nom_passager.replace(" ", "_").upper()
    fichier = f"QSE-FO-320_V02_{nom_clean}.pdf"
    
    # On laisse Pyppeteer trouver le Chrome qu'il a téléchargé tout seul
    browser = await launch(
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
        handleSIGINT=False, 
        handleSIGTERM=False, 
        handleSIGHUP=False
    )
    
    page = await browser.newPage()
    
    try:
        # On attend que le formulaire soit chargé
        await page.goto('http://localhost:10000', {'waitUntil': 'domcontentloaded', 'timeout': 60000})
        
        # Injection des données avec protection contre les caractères spéciaux
        # On transforme les données en JSON pour éviter les erreurs de "SyntaxError"
        json_data = data.model_dump_json() 

        await page.evaluate(f"""(dataStr) => {{
            const data = JSON.parse(dataStr);
            
            // Remplissage des textes
            document.getElementById('nom_passager').value = data.nom_passager;
            document.querySelector('.date-picker').value = data.date;
            document.querySelector('.time-picker').value = data.heure;
            document.querySelector('.w-80').value = data.vol_destination;
            document.querySelector('.desc-area').value = data.description;

            // Gestion du Sexe
            if (data.sexe === "sm") document.getElementById('sm').checked = true;
            if (data.sexe === "sf") document.getElementById('sf').checked = true;

            // Cocher les cases (Lieu, Nature)
            const selections = data.lieu + ", " + data.nature;
            document.querySelectorAll('input[type="checkbox"]').forEach(cb => {{
                const labelText = cb.parentElement.textContent.trim();
                if (selections.includes(labelText)) cb.checked = true;
            }});
        }}""", json_data)

        await page.pdf({
            'path': fichier,
            'format': 'A4',
            'printBackground': True,
            'margin': {'top': '0', 'right': '0', 'bottom': '0', 'left': '0'}
        })
    finally:
        await browser.close()
    
    return fichier

# --- ENVOI EMAIL ---
async def envoyer_email(fichier, nom):
    # La clé API sera stockée sur Render
    API_KEY = os.getenv("SENDGRID_API_KEY")
    SENDER_EMAIL = "alyzia.cdg2@gmail.com"
    RECEIVER_EMAIL = "xavier.oliere@alyzia.com"

    # Encodage du PDF en Base64 pour l'envoi API
    import base64
    with open(fichier, "rb") as f:
        encoded_pdf = base64.b64encode(f.read()).decode()

    data = {
        "personalizations": [{"to": [{"email": RECEIVER_EMAIL}]}],
        "from": {"email": SENDER_EMAIL, "name": "PAXI SYSTEM"},
        "subject": f"FORMULAIRE PAXI - {nom.upper()}",
        "content": [{"type": "text/plain", "value": f"Rapport d'incident : {nom}"}],
        "attachments": [
            {
                "content": encoded_pdf,
                "filename": fichier,
                "type": "application/pdf",
                "disposition": "attachment"
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.sendgrid.com/v3/mail/send", json=data, headers=headers)
        if response.status_code >= 400:
            print(f"Erreur API SendGrid: {response.text}")
            raise Exception("Erreur lors de l'envoi du mail via API")

# --- ROUTE ---
@app.post("/submit")
async def submit(report: IncidentReport, action: str = Query("email")):
    try:
        # 1. On génère toujours le PDF en premier
        fichier_path = await generer_pdf_chrome(report)
        
        if action == "email":
            # 2. AJOUT DU "await" ICI (indispensable pour la Solution 1)
            await envoyer_email(fichier_path, report.nom_passager)
            return {"status": "ok"}
        else:
            return FileResponse(
                path=fichier_path,
                filename=fichier_path,
                media_type='application/pdf'
            )
    except Exception as e:
        # En cas d'erreur, on l'affiche dans les Logs de Render
        print(f"ERREUR SERVEUR : {e}")
        raise HTTPException(status_code=500, detail=str(e))

# TOUJOURS EN DERNIER
app.mount("/", StaticFiles(directory=".", html=True), name="static")
