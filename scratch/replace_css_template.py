# coding: utf-8
import os

filepath = "web/app.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Let's perform the replacement
old_code_substring = """    // --- 3. HARDENING CSS ULTRA-PUISSANT (Correction définitive timbre poste) ---
    const injectStyle = () => {
        if (document.getElementById('songsterr-hardening-style')) return;
        try {
            const style = document.createElement('style');
            style.id = 'songsterr-hardening-style';
            style.innerHTML = `
                /* Force le conteneur principal à occuper toute la largeur */
                #apptab, [class*="tablature"], ._6jiALa_pane, .aJq1bq_tablature, .aJq1bq_tablaturePrint {
                    --max-tab-width: 100% !important;
                    max-width: 100% !important;
                    width: 100% !important;
                }
                /* Empêche les éléments SVG internes de se contracter au milieu */
                #tablature svg, .aJq1bq_tablature svg {
                    width: 100% !important;
                    max-width: 100% !important;
                }
            `;
            (document.head || document.documentElement).appendChild(style);
            console.log("[Userscript] CSS de forçage de taille injecté avec succès.");
        } catch (e) {
            console.error("[Userscript] Échec injection CSS de forçage :", e);
        }
    };"""

new_code_substring = """    // --- 3. HARDENING CSS ULTRA-PUISSANT (Correction définitive timbre poste sans effet zoom) ---
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
    };"""

# Also update script version string
content = content.replace("V2.6.0", "V2.7.0")
content = content.replace("2.6.0", "2.7.0")

if old_code_substring in content:
    content = content.replace(old_code_substring, new_code_substring)
    print("SUCCESS: Code replaced successfully!")
else:
    # Let's search if there is a slightly different format (e.g. escaped newlines in js template string)
    print("WARNING: Exact match not found. Trying escaped representation...")
    
    # Let's escape the characters and try replacing with a standard python replacement
    # We will search for standard patterns in the file and print them to diagnose
    import re
    matches = [m.start() for m in re.finditer("HARDENING CSS ULTRA-PUISSANT", content)]
    print("Matches for 'HARDENING CSS ULTRA-PUISSANT':", matches)
    if matches:
        start = max(0, matches[0] - 100)
        end = min(len(content), matches[0] + 1200)
        print("Existing snippet in file:")
        print(repr(content[start:end]))

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
