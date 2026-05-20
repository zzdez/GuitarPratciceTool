import os
import json
import re
import logging
from utils import get_data_dir

logger = logging.getLogger(__name__)

class UserScriptManager:
    def __init__(self):
        self.data_dir = get_data_dir()
        self.filepath = os.path.join(self.data_dir, "userscripts.json")
        self.scripts = []
        self.load_scripts()

    def get_default_templates(self):
        """Retourne des plugins de démonstration extrêmement utiles pour l'utilisateur"""
        return [
            {
                "id": "songsterr-clean-ui",
                "name": "Songsterr Plus Patcher & Clean UI",
                "description": "Débloque Songsterr Plus de manière transparente, permet la connexion à votre vrai compte et corrige le bug d'affichage timbre poste.",
                "url_pattern": "*://*.songsterr.com/*",
                "code": """// ==UserScript==
// @name         Songsterr Plus & Universal Display Hardening (V2.7.2)
// @namespace    http://tampermonkey.net/
// @version      2.7.2
// @description  Déverrouille les fonctionnalités Songsterr Plus, permet la connexion à votre vrai compte et corrige définitivement le bug timbre poste sans effet zoom.
// @match        *://*.songsterr.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    const win = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;

    // --- 1. BYPASS PRÉVENTIF DES COOKIES ---
    try {
        const key = 'sng-consent';
        const consentData = {
            version: 1,
            created: Date.now(),
            consents: {
                advertising: true,
                advertising_consent_given: true,
                analytics: true,
                personalization: true
            }
        };
        localStorage.setItem(key, JSON.stringify(consentData));
        console.log("[Userscript] Consentement de cookies injecté.");
    } catch (e) {
        console.error("[Userscript] Échec injection cookies :", e);
    }

    // --- 1.5 BRIDAGE DYNAMIQUE ET SÉCURISÉ DE LA LARGEUR D'ÉCRAN ---
    // Utilise outerWidth pour éviter la récursion infinie ou les valeurs nulles (0) au démarrage
    const getTargetWidth = () => {
        const ow = win.outerWidth;
        const width = (ow && ow > 0) ? ow : 1070;
        return Math.min(width, 1070);
    };

    try {
        Object.defineProperty(win, 'innerWidth', {
            get: () => getTargetWidth(),
            configurable: true
        });
        console.log("[Userscript] window.innerWidth bridé dynamiquement (max 1070px).");
    } catch (e) {
        console.error("[Userscript] Impossible de brider innerWidth :", e);
    }

    // --- 2. INTERCEPTION DYNAMIQUE ET INJECTION DU STATUT PREMIUM ---
    
    // A. Interception de l'état initial (JSON.parse)
    const originalParse = JSON.parse;
    JSON.parse = function(text, reviver) {
        const result = originalParse.apply(this, arguments);
        
        try {
            if (typeof text === 'string' && text.includes('"runningThunks"') && text.includes('"user"')) {
                console.log("[Userscript] Interception de l'état initial détectée.");
                if (result && result.user) {
                    result.user.hasPlus = true;
                    
                    if (result.user.profile && result.user.profile.id) {
                        console.log("[Userscript] Vrai compte connecté détecté dans l'état initial. Injection premium...");
                        result.user.isLoggedIn = true;
                        result.user.profile.hasPlus = true;
                        result.user.profile.plan = "plus";
                        if (!result.user.profile.subscription) {
                            result.user.profile.subscription = {};
                        }
                        result.user.profile.subscription.plan = { id: "plus" };
                    } else {
                        console.log("[Userscript] Aucun compte connecté. Utilisation du profil virtuel premium.");
                        result.user.isLoggedIn = true;
                        result.user.profile = {
                            id: 100000000,
                            uid: 100000000,
                            email: "premium@airstepstudio.com",
                            name: "AirstepUser",
                            plan: "plus",
                            permissions: [],
                            subscription: { plan: { id: "plus" } },
                            sra_license: "none",
                            created_at: "2026-01-01T00:00:00.000Z",
                            last_signin_date: "2026-01-01T00:00:00.000Z"
                        };
                    }
                }
                
                if (result && result.player) {
                    result.player.locks = [];
                }
            }
        } catch (err) {
            console.error("[Userscript] Erreur patching initial state :", err);
        }
        
        return result;
    };

    // B. Interception intelligente Fetch (auth/profile)
    const originalFetch = win.fetch;
    win.fetch = async function(resource, options) {
        const url = typeof resource === 'string' ? resource : (resource && resource.url) || '';
        
        if (url.includes("/auth/profile")) {
            console.log("[Userscript] Interception d'authentification profil...");
            try {
                const response = await originalFetch.apply(this, arguments);
                if (response.ok) {
                    const profile = await response.json();
                    console.log("[Userscript] Session réelle active pour :", profile.email || profile.name);
                    profile.hasPlus = true;
                    profile.plan = "plus";
                    if (!profile.subscription) {
                        profile.subscription = {};
                    }
                    profile.subscription.plan = { id: "plus" };
                    
                    return new Response(JSON.stringify(profile), {
                        status: response.status,
                        statusText: response.statusText,
                        headers: response.headers
                    });
                }
            } catch (err) {
                console.warn("[Userscript] API injoignable, repli virtuel.");
            }
            
            const fakeProfile = {
                id: 100000000,
                uid: 100000000,
                email: "premium@airstepstudio.com",
                name: "AirstepUser",
                plan: "plus",
                permissions: [],
                subscription: { plan: { id: "plus" } },
                sra_license: "none",
                created_at: "2026-01-01T00:00:00.000Z",
                last_signin_date: "2026-01-01T00:00:00.000Z"
            };
            return new Response(JSON.stringify(fakeProfile), {
                status: 200,
                statusText: "OK",
                headers: { "Content-Type": "application/json" }
            });
        }
        
        return originalFetch.apply(this, arguments);
    };

    // --- 3. HARDENING CSS ULTRA-PUISSANT (Correction définitive timbre poste sans effet zoom) ---
    const injectStyle = () => {
        if (document.getElementById('songsterr-hardening-style')) return;
        try {
            const style = document.createElement('style');
            style.id = 'songsterr-hardening-style';
            style.innerHTML = `
                /* Force la largeur maximale naturelle de 1070px (comme le Songsterr original) pour éviter le zoom */
                #apptab, [class*="tablature"], ._6jiALa_pane, .aJq1bq_tablature, .aJq1bq_tablaturePrint {
                    --max-tab-width: 1070px !important;
                    max-width: 1070px !important;
                    width: 100% !important;
                    margin: 0 auto !important;
                }
                /* Centre parfaitement le conteneur de tablature sur l'écran */
                #tablature, .aJq1bq_tablature {
                    margin: 0 auto !important;
                }
                /* Empêche les éléments SVG internes de se contracter au milieu tout en respectant la largeur maximale */
                #tablature svg, .aJq1bq_tablature svg {
                    width: 100% !important;
                    max-width: 100% !important;
                }
            `;
            (document.head || document.documentElement).appendChild(style);
            console.log("[Userscript] CSS de forçage de taille injecté avec succès (limité à 1070px).");
        } catch (e) {
            console.error("[Userscript] Échec injection CSS de forçage :", e);
        }
    };

    // Injection agressive au plus tôt
    injectStyle();
    win.addEventListener('DOMContentLoaded', injectStyle);
    win.addEventListener('load', injectStyle);

    // --- 4. DOUBLE-RESIZE DE SÉCURITÉ ---
    const triggerUniversalResize = () => {
        try {
            console.log("[Userscript] Déclenchement du redimensionnement universel...");
            
            const targetWidth = getTargetWidth();
            const oh = win.innerHeight;
            const originalHeight = (oh && oh > 0) ? oh : 800;

            // Étape 1 : Recalcul forcé temporaire (avec des garde-fous stricts contre les valeurs négatives ou nulles)
            const tempWidth = Math.max(targetWidth - 20, 320);
            const tempHeight = Math.max(originalHeight - 20, 240);

            Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: tempWidth });
            Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: tempHeight });
            window.dispatchEvent(new Event('resize'));

            const containers = [
                document.getElementById('apptab'),
                document.getElementById('tablature'),
                document.getElementById('app'),
                document.querySelector('.aJq1bq_tablature'),
                document.querySelector('._6jiALa_tablature')
            ].filter(Boolean);

            containers.forEach(el => {
                el.style.setProperty('width', '95%', 'important');
                el.style.setProperty('padding-right', '10px', 'important');
            });

            document.body.offsetHeight;

            // Étape 2 : Verrouillage permanent sur targetWidth (1070px max)
            Object.defineProperty(window, 'innerWidth', { 
                configurable: true, 
                get: () => getTargetWidth()
            });
            Object.defineProperty(window, 'innerHeight', { 
                configurable: true, 
                get: () => originalHeight
            });
            window.dispatchEvent(new Event('resize'));

            containers.forEach(el => {
                el.style.removeProperty('width');
                el.style.removeProperty('padding-right');
            });

            document.body.offsetHeight;
            console.log("[Userscript] Rendu tablature recalculé avec une largeur cible de :", targetWidth);
        } catch (e) {
            console.error("[Userscript] Erreur resize universel :", e);
        }
    };

    if (document.readyState === 'complete') {
        setTimeout(triggerUniversalResize, 500);
        setTimeout(triggerUniversalResize, 1500);
    } else {
        win.addEventListener('load', () => {
            setTimeout(triggerUniversalResize, 300);
            setTimeout(triggerUniversalResize, 1000);
            setTimeout(triggerUniversalResize, 2500);
        });
    }
})();
""",
                "enabled": True,
                "run_at": "document_creation"
            },
            {
                "id": "youtube-auto-loop",
                "name": "YouTube Auto-Looper",
                "description": "Active automatiquement la boucle sur le lecteur vidéo YouTube du Cockpit.",
                "url_pattern": "*://*.youtube.com/embed/*",
                "code": "console.log('[Plugin] YouTube Auto-Looper active!');\n\n// Vérification toutes les secondes de l'état de la boucle sur la balise vidéo\nsetInterval(() => {\n    const video = document.querySelector('video');\n    if (video && !video.loop) {\n        video.loop = true;\n        console.log('[Plugin] YouTube Loop forced to TRUE');\n    }\n}, 1000);",
                "enabled": True,
                "run_at": "document_ready"
            }
        ]

    def load_scripts(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.scripts = json.load(f)
                logger.info(f"Loaded {len(self.scripts)} UserScripts from {self.filepath}")
                # Logique de migration automatique par comparaison de version numérique
                updated = False
                for s in self.scripts:
                    if s.get("id") == "songsterr-clean-ui":
                        # Extraction de la version locale
                        version_match = re.search(r"//\s*@version\s+([0-9.]+)", s.get("code", ""))
                        current_version = version_match.group(1) if version_match else "0.0.0"
                        
                        # Si version < 2.7.2, on procède à la migration forcée vers la V2.7.2
                        if current_version < "2.7.2" or "songsterr-hardening-style" not in s.get("code", ""):
                            logger.info(f"Migrating songsterr-clean-ui from version {current_version} to V2.7.2 Display Hardening...")
                            default_songsterr = [t for t in self.get_default_templates() if t["id"] == "songsterr-clean-ui"][0]
                            s["code"] = default_songsterr["code"]
                            s["name"] = default_songsterr["name"]
                            s["description"] = default_songsterr["description"]
                            s["run_at"] = default_songsterr["run_at"]
                            updated = True
                if updated:
                    self.save_scripts()
            else:
                self.scripts = self.get_default_templates()
                self.save_scripts()
                logger.info("Created default templates for UserScripts")
        except Exception as e:
            logger.error(f"Error loading UserScripts: {e}")
            self.scripts = self.get_default_templates()

    def save_scripts(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.scripts, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully saved {len(self.scripts)} UserScripts to {self.filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving UserScripts: {e}")
            return False

    def glob_to_regex(self, glob):
        """Convertit un glob simple en expression régulière JavaScript robuste et tolérante"""
        if not glob or glob == "*":
            return ".*"
        
        glob = glob.strip()
        
        # Si c'est juste un domaine simple sans protocole ni étoile (ex: songsterr.com)
        if "*" not in glob and "://" not in glob:
            escaped_domain = re.escape(glob)
            return f"^https?://([^/]+\\.)?{escaped_domain}(/.*)?$"
            
        # Remplacement standard de glob vers regex
        # On protège temporairement les étoiles et points d'interrogation
        temp_glob = glob.replace("*", "___STAR___").replace("?", "___QUESTION___")
        escaped = re.escape(temp_glob)
        
        regex_str = escaped.replace("___STAR___", ".*").replace("___QUESTION___", ".")
        
        # Si le glob ne se termine pas par une étoile, on tolère un sous-chemin optionnel
        if not glob.endswith("*"):
            regex_str += "(/.*)?"
            
        return "^" + regex_str + "$"

    def get_wrapped_script(self, script):
        """Enveloppe le script utilisateur dans un IIFE avec compatibilité Tampermonkey et validation d'URL regex"""
        js_code = script.get("code", "")
        pattern = script.get("url_pattern", "*")
        regex = self.glob_to_regex(pattern)
        name = script.get("name", "Unnamed Script")
        
        wrapped = f"""
(function() {{
    const urlPattern = {repr(regex)};
    const regex = new RegExp(urlPattern);
    if (regex.test(window.location.href)) {{
        console.log("[UserScript] Injecté : {name}");
        
        // --- Shims de compatibilité Tampermonkey / Greasemonkey ---
        const unsafeWindow = window;
        
        const GM_addStyle = function(css) {{
            const style = document.createElement('style');
            style.type = 'text/css';
            style.appendChild(document.createTextNode(css));
            (document.head || document.documentElement).appendChild(style);
            return style;
        }};
        
        const GM_setValue = function(key, val) {{
            try {{
                localStorage.setItem('GM_' + key, JSON.stringify(val));
            }} catch(e) {{
                console.error("[UserScript GM_setValue Error]", e);
            }}
        }};
        
        const GM_getValue = function(key, defaultVal) {{
            try {{
                const val = localStorage.getItem('GM_' + key);
                return val !== null ? JSON.parse(val) : defaultVal;
            }} catch(e) {{
                return defaultVal;
            }}
        }};
        
        const GM_deleteValue = function(key) {{
            try {{
                localStorage.removeItem('GM_' + key);
            }} catch(e) {{}}
        }};
        
        const GM_log = function(...args) {{
            console.log("[UserScript GM_log] {name} :", ...args);
        }};
        
        // ---------------------------------------------------------

        try {{
            {js_code}
        }} catch(e) {{
            console.error("[UserScript Error] {name} :", e);
        }}
    }}
}})();
"""
        return wrapped

    def get_active_scripts(self):
        """Retourne la liste des scripts actifs enveloppés pour injection"""
        active_list = []
        for s in self.scripts:
            if s.get("enabled", False):
                active_list.append({
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "run_at": s.get("run_at", "document_ready"),
                    "code": self.get_wrapped_script(s)
                })
        return active_list
