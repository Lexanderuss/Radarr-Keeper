# radarr-tool/app/main.py
# FINALE VERSION MIT SYNTAX-KORREKTUR

import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from radarr_client import RadarrClient
from dotenv import load_dotenv

load_dotenv()

# --- SETUP FÜR PERSISTENTES LOGGING ---
os.makedirs('/config', exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = logging.FileHandler('/config/log.txt')
log_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(log_handler)
# --- ENDE LOGGING SETUP ---

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Config
RADARR_DE_URL, RADARR_DE_API_KEY = os.getenv("RADARR_DE_URL"), os.getenv("RADARR_DE_API_KEY")
RADARR_EN_URL, RADARR_EN_API_KEY = os.getenv("RADARR_EN_URL"), os.getenv("RADARR_EN_API_KEY")

# --- HILFSFUNKTIONEN ---
def get_resolution_value(movie):
    try:
        return int(movie['movieFile']['quality']['quality']['resolution'])
    except: return 0

def get_quality_source(movie):
    try:
        return movie['movieFile']['quality']['quality']['source'].upper()
    except: return "UNBEKANNT"

# --- KERNLOGIK ---
def find_deletion_candidates():
    ui_logs, candidates = [], []
    try:
        client_de = RadarrClient(RADARR_DE_URL, RADARR_DE_API_KEY)
        client_en = RadarrClient(RADARR_EN_URL, RADARR_EN_API_KEY)
        log_msg = "INFO: Verbindung zu beiden Radarr-Instanzen wird versucht..."
        logger.info(log_msg)
        ui_logs.append(log_msg)
    except ValueError as e:
        log_msg = f"FEHLER: Konfiguration unvollständig. {e}"
        logger.error(log_msg)
        flash(log_msg, "error")
        return None, [log_msg]

    log_msg = "INFO: Verbindung erfolgreich hergestellt. Lade Filmlisten..."
    logger.info(log_msg)
    ui_logs.append(log_msg)

    movies_de = {m['tmdbId']: m for m in client_de.get_movies() or [] if m.get('hasFile')}
    movies_en = {m['tmdbId']: m for m in client_en.get_movies() or [] if m.get('hasFile')}
    
    log_msg = f"INFO: DE: {len(movies_de)} Filme | EN: {len(movies_en)} Filme"
    logger.info(log_msg)
    ui_logs.append(log_msg)

    duplicates = set(movies_de.keys()).intersection(movies_en.keys())
    log_msg = f"INFO: {len(duplicates)} Duplikate gefunden. Starte Einzelprüfung...\n"
    logger.info(log_msg)
    ui_logs.append(log_msg)
    
    for tmdb_id in duplicates:
        m_de, m_en = movies_de[tmdb_id], movies_en[tmdb_id]
        
        res_de, res_en = get_resolution_value(m_de), get_resolution_value(m_en)
        source_de, source_en = get_quality_source(m_de), get_quality_source(m_en)
        title, year = m_de.get('title'), m_de.get('year')
        
        log_msg_prüfung = f"[Prüfung] '{title}' ({year})"
        log_msg_gefunden = f"  -> Gefunden - DE: {res_de}p ({source_de}) | EN: {res_en}p ({source_en})"
        logger.info(f"{log_msg_prüfung} - {log_msg_gefunden}")
        ui_logs.append(log_msg_prüfung)
        ui_logs.append(log_msg_gefunden)
        
        if res_de >= res_en:
            log_msg_urteil = "  -> Urteil: DE-Version ist besser oder gleichwertig. Zum Löschen vorgeschlagen. ✔️"
            logger.info(f"  -> Urteil für '{title}': DE besser/gleich. Wird vorgeschlagen.")
            ui_logs.append(log_msg_urteil)
            
            poster_url = next((img['remoteUrl'] for img in m_de.get('images', []) if img['coverType'] == 'poster'), None)
            
            candidates.append({
                'title': title, 'year': year, 'tmdbId': tmdb_id, 
                'en_movie_id': m_en['id'], 
                'de_res': res_de, 'en_res': res_en, 
                'de_source': source_de, 'en_source': source_en,
                'poster_url': poster_url or ""
            })
        else:
            log_msg_urteil = "  -> Urteil: Keine Aktion nötig (DE-Version ist schlechter). ❌"
            logger.info(f"  -> Urteil für '{title}': Keine Aktion.")
            ui_logs.append(log_msg_urteil)

    log_msg_abschluss = f"\nINFO: Analyse abgeschlossen. {len(candidates)} Filme als Löschkandidaten identifiziert."
    logger.info(log_msg_abschluss)
    ui_logs.append(log_msg_abschluss)
    
    return sorted(candidates, key=lambda x: x['title']), ui_logs

def execute_deletions(selected_movies):
    ui_logs = []
    if not selected_movies: 
        log_msg = "INFO: Keine Filme zum Löschen ausgewählt."
        logger.info(log_msg)
        return [log_msg]

    client_en = RadarrClient(RADARR_EN_URL, RADARR_EN_API_KEY)
    log_msg = f"INFO: Starte Löschvorgang für {len(selected_movies)} Filme..."
    logger.info(log_msg)
    ui_logs.append(log_msg)

    for movie_info in selected_movies:
        # Hier ist der korrigierte Block:
        try:
            en_movie_id, tmdb_id, title, year = movie_info.split('|||', 3)
        except (ValueError, IndexError):
            continue # Diese Zeile hat in Ihrer Datei gefehlt
        
        log_msg_aktion = f"AKTION für '{title}':"
        logger.info(log_msg_aktion)
        ui_logs.append(log_msg_aktion)

        if client_en.delete_movie(int(en_movie_id), delete_files=True):
            log_msg_del = "  -> Erfolgreich gelöscht."
            logger.info(f"  -> '{title}' erfolgreich gelöscht.")
            ui_logs.append(log_msg_del)

            success, response_msg = client_en.add_exclusion(int(tmdb_id), title, int(year))
            if success:
                if "Conflict" in response_msg:
                    log_msg_bl = "  -> Bereits auf der Blacklist. ✔️"
                    logger.warning(f"  -> '{title}' war bereits auf der Blacklist.")
                    ui_logs.append(log_msg_bl)
                else:
                    log_msg_bl = "  -> Zur Blacklist hinzugefügt. ✔️"
                    logger.info(f"  -> '{title}' zur Blacklist hinzugefügt.")
                    ui_logs.append(log_msg_bl)
            else:
                log_msg_bl = f"  -> FEHLER beim Hinzufügen zur Blacklist: {response_msg}"
                logger.error(f"  -> Fehler bei Blacklist für '{title}': {response_msg}")
                ui_logs.append(log_msg_bl)
        else:
            log_msg_del_err = "  -> FEHLER beim Löschen des Films."
            logger.error(f"  -> Fehler beim Löschen von '{title}'.")
            ui_logs.append(log_msg_del_err)
            
    return ui_logs

# --- Flask Routen (unverändert) ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_movies():
    candidates, logs = find_deletion_candidates()
    if candidates is None: return render_template('index.html', logs=logs)
    if not candidates:
        flash("Analyse abgeschlossen. Keine Kandidaten für eine Löschung gefunden.", "success")
        return render_template('index.html', logs=logs)
    return render_template('results.html', candidates=candidates, logs=logs)

@app.route('/execute', methods=['POST'])
def execute_selection():
    logs = execute_deletions(request.form.getlist('movie_to_delete'))
    return render_template('index.html', logs=logs)

@app.route('/blacklist')
def view_blacklist():
    client_en = RadarrClient(RADARR_EN_URL, RADARR_EN_API_KEY)
    return render_template('blacklist.html', exclusions=client_en.get_exclusions() or [])

@app.route('/blacklist/delete/<int:exclusion_id>', methods=['POST'])
def delete_from_blacklist(exclusion_id):
    client_en = RadarrClient(RADARR_EN_URL, RADARR_EN_API_KEY)
    if client_en.remove_exclusion(exclusion_id):
        flash("Eintrag erfolgreich von der Blacklist entfernt.", "success")
    else: flash("Fehler beim Entfernen des Eintrags.", "error")
    return redirect(url_for('view_blacklist'))