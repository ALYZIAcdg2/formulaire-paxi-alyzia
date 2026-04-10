async function actionFormulaire(typeAction) {
    // 1. Collecte des données
    const formData = {
        nom_passager: document.getElementById('nom_passager').value || "INCONNU",
        sexe: document.querySelector('input[name="sexe"]:checked')?.id || "M",
        date: document.querySelector('.date-picker').value || "",
        heure: document.querySelector('.time-picker').value || "",
        vol_destination: document.querySelector('.w-80').value || "",
        description: document.querySelector('.desc-area').value || "",
        // Récupère le texte de toutes les cases cochées
        lieu: Array.from(document.querySelectorAll('.form-block:nth-child(2) input:checked'))
                  .map(el => el.parentElement.textContent.trim()).join(", "),
        nature: Array.from(document.querySelectorAll('.form-block:nth-child(3) input:checked'))
                  .map(el => el.parentElement.textContent.trim()).join(", ")
    };

    if (formData.nom_passager === "INCONNU") {
        alert("Veuillez saisir le nom du passager.");
        return;
    }

    try {
        // 2. Envoi au serveur avec l'action spécifiée (email ou download)
        const response = await fetch(`/submit?action=${typeAction}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        });

        if (!response.ok) throw new Error("Le serveur a rencontré un problème.");

        if (typeAction === "download") {
            // Gestion propre du téléchargement binaire
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `QSE-FO-320_${formData.nom_passager.replace(/\s+/g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } else {
            alert("✅ Email envoyé avec succès !");
        }
    } catch (error) {
        console.error(error);
        alert("❌ Erreur : " + error.message);
    }
}