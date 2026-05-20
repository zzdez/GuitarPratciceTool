# coding: utf-8
import os
import re

userscript_manager_path = "src/userscript_manager.py"
print("Updating", userscript_manager_path, "...")

# On va restaurer le fichier userscript_manager.py original pour repartir sur une base propre
os.system("git checkout src/userscript_manager.py")

with open(userscript_manager_path, "r", encoding="utf-8") as f:
    code = f.read()

# Le code utilisateur complet que l'on veut injecter
new_songsterr_code = """// ==UserScript==
// @name         Songsterr Plus & Universal Display Hardening (V2.7.1)
// @namespace    http://tampermonkey.net/
// @version      2.7.1
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
                analytics: true,
                personalization: true
            }
        };
        localStorage.setItem(key, JSON.stringify(consentData));
        console.log("[Userscript] Consentement de cookies injecté.");
    } catch (e) {
        console.error("[Userscript] Échec injection cookies :", e);
    }

    // --- 1.5 BRIDAGE INITIAL DE LA LARGEUR D'ÉCRAN ---
    const originalWidth = win.innerWidth;
    const targetWidth = Math.min(originalWidth, 1070);
    try {
        Object.defineProperty(win, 'innerWidth', {
            get: () => targetWidth,
            configurable: true
        });
        console.log("[Userscript] window.innerWidth bridé initialement à :", targetWidth);
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
            
            const originalHeight = window.innerHeight;

            // Étape 1 : Recalcul forcé temporaire
            Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: targetWidth - 20 });
            Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: originalHeight - 20 });
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
                get: () => targetWidth
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
"""

# Mettons à jour le template dans src/userscript_manager.py
# On cherche le premier dictionnaire dans get_default_templates()
pattern_default = r'\{\s*"id":\s*"songsterr-clean-ui",\s*"name":\s*"Songsterr Clean UI",[\s\S]*?"run_at":\s*"document_ready"\s*\}'

# On va utiliser une chaîne de caractères brute triple guillemets en python
# Pour éviter tout problème avec les antislashs, on double les backslashes lors de l'écriture en fichier
escaped_code_python = new_songsterr_code.replace('\\', '\\\\').replace('\"', '\\\"').replace('\'', '\\\'')

replacement_template = f"""{{
                "id": "songsterr-clean-ui",
                "name": "Songsterr Plus Patcher & Clean UI",
                "description": "Débloque Songsterr Plus de manière transparente, permet la connexion à votre vrai compte et corrige le bug d'affichage timbre poste.",
                "url_pattern": "*://*.songsterr.com/*",
                "code": \"\"\"{new_songsterr_code}\"\"\",
                "enabled": True,
                "run_at": "document_creation"
            }}"""

code, count = re.subn(pattern_default, replacement_template, code)
print("Replaced default template in userscript_manager.py:", count)

# 2. Ajout de la logique de migration automatique dans load_scripts
migration_logic = """                # Logique de migration automatique : si un script songsterr-clean-ui existe mais n'a pas le durcissement,
                # on le met à jour automatiquement avec le code V2.7.1
                updated = False
                for s in self.scripts:
                    if s.get("id") == "songsterr-clean-ui" and ("songsterr-hardening-style" not in s.get("code", "") or "innerWidth" not in s.get("code", "")):
                        logger.info("Migrating songsterr-clean-ui to V2.7.1 Display Hardening...")
                        default_songsterr = [t for t in self.get_default_templates() if t["id"] == "songsterr-clean-ui"][0]
                        s["code"] = default_songsterr["code"]
                        s["name"] = default_songsterr["name"]
                        s["description"] = default_songsterr["description"]
                        s["run_at"] = default_songsterr["run_at"]
                        updated = True
                if updated:
                    self.save_scripts()"""

load_scripts_pattern = r'(def load_scripts\(self\):[\s\S]*?self\.scripts = json\.load\(f\)\s*\n\s*logger\.info\(f"Loaded .*? UserScripts from {self\.filepath}"\))'
code, count = re.subn(load_scripts_pattern, r'\1\n' + migration_logic, code)
print("Injected migration logic:", count)

with open(userscript_manager_path, "w", encoding="utf-8") as f:
    f.write(code)

print("userscript_manager.py update complete!")
