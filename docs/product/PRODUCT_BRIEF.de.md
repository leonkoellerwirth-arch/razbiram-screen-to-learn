# Produktbriefing — razbiram-screen-to-learn

## Ein-Satz-Pitch

`razbiram-screen-to-learn` verwandelt Screenshots, PDFs, Texte und sichtbare Lernaufgaben aus
Chrome oder Firefox nach menschlicher Prüfung in razbiram-kompatible Learncards.

## Problem

Viele Lerninhalte liegen nur in Webseiten, Canvas-Oberflächen, PDFs oder interaktiven
Prüfungssystemen vor. Manuelles Übertragen kostet Zeit und produziert typische Fehler:

- Frage und Optionen werden falsch getrennt;
- die gewählte Antwort wird mit der korrekten Antwort verwechselt;
- Seitenwechsel erzeugen Duplikate oder ausgelassene Fragen;
- Formeln, Hoch-/Tiefstellungen und Bilder gehen verloren;
- Mehrfachauswahl wird fälschlich als Einfachauswahl exportiert;
- Herkunft und Prüfbarkeit fehlen.

Ein Screenshot allein beweist zudem fast nie die richtige Antwort. Das Tool muss deshalb Frage-
und Lösungszustände als zusammengehörige Evidenz erfassen.

## Zielgruppe

- Lernende, die eigene oder rechtmäßig zugängliche Übungsinhalte in persönliche Learncards
  überführen;
- Lehrkräfte und Content-Redaktionen mit Nutzungsrechten;
- Razbiram-Maintainer, die kuratierte Pakete vorbereiten und validieren.

Nicht-Zielgruppen sind Betreiber automatischer Inhaltscrawler, Prüfungsbetrug, Paywall-/DRM-
Umgehung oder das massenhafte Kopieren fremder Fragenkataloge.

## Produktprinzipien

1. **Verstehen statt abschreiben:** DOM/ARIA zuerst, Bildanalyse nur ergänzend.
2. **Belegt statt geraten:** Unbekannte Lösungen bleiben `needs-review`.
3. **Review vor Export:** Automatisches Extrahieren, bewusste Freigabe.
4. **Lokal und privat:** Keine Accounts, keine Telemetrie, kurzlebige Evidenz.
5. **Eine Razbiram-Familie:** gleiche CI, gleiche Begriffe, gleiche ruhige Nutzerführung.
6. **Ehrliche Kompatibilität:** Ein Export ist nur verfügbar, wenn die Ziel-App den Kartentyp
   wirklich korrekt auswertet.
7. **Zwei Einstiege, ein Kern:** Standalone-Studio und Extension nutzen dieselbe Evidence-,
   Review- und Exportlogik.
8. **Werbung durch Nutzen:** Die Extension darf Razbiram sichtbar machen, aber keine Werbung in
   Lernkarten injizieren, keinen Account erzwingen und keine Browserinhalte für Marketing
   übertragen.

## Kern-Use-Cases

### A. Single-Choice und True/False

Der Nutzer öffnet eine Aufgabe, das Tool erkennt Frage und Optionen, beobachtet den sichtbaren
Lösungszustand und erstellt eine direkt kompatible MCQ-Karte. True/False bleibt im Capture-Modell
semantisch erkennbar und wird als Zwei-Optionen-MCQ exportiert.

### B. Multiple-Select

Das Tool erkennt Checkbox-/Mehrfachauswahlsemantik und mehrere korrekte Optionen. Solange
razbiram.com diese Karten nicht als Auswahlmenge auswertet, bleibt der Export blockiert. Nach dem
koordinierten Plattform-Patch werden die korrekten Options-IDs und der Bewertungsmodus
verlustfrei exportiert.

### C. Flashcard und Typed Recall

Vorder-/Rückseite oder Prompt-/Antwortzustand werden erkannt und auf die bereits vorhandenen
Razbiram-Typen abgebildet. Das Tool implementiert dafür keinen eigenen Lernmodus.

### D. Matching

Linke/rechte Elemente und sichtbare Paarauflösung werden als stabile IDs und `correctPairs`
erfasst.

### E. Image Occlusion

Ein Ausgangsbild und sichtbare Maskenregionen werden als lokale Medienartefakte erfasst. Vor dem
Export muss der Nutzer Nutzungsrechte und Alt-Texte bestätigen. Die bereits vorhandene
Razbiram-Logik bleibt Zielsystem.

## MVP

Der MVP enthält:

- lokales Studio ohne Account;
- Drag-and-drop/Paste für Screenshots, PDFs und Texte;
- `.razcapture`-Import und -Export;
- eine Chrome-/Firefox-Extension mit `Capture this question`, Bereichsauswahl und explizitem
  Observe-Modus;
- Capture Lite ohne laufendes Studio sowie eine bewusst gekoppelte lokale Übertragung;
- einen vom Tool gestarteten, sichtbaren Chromium-Browser als Fallback und Testadapter;
- DOM-/ARIA-/Screenshot-Capture;
- Frage-/Lösungszustands-Paarung;
- Single-Choice, True/False, Multiple-Select als Draft sowie vorhandene Kartentypen;
- Review-Editor mit Evidenzvergleich;
- deterministische Validierung, Duplikaterkennung und JSON-Download;
- Session-Löschung und konfigurierbare Aufbewahrung;
- synthetisches Golden-Set.

Nicht im MVP:

- vollautomatisches Durchklicken fremder Seiten;
- Plattform-spezifische Scraper;
- direkte Veröffentlichung in razbiram.com;
- generierte Erklärungen als Teil der Extraktion;
- Cloud-Pflicht;
- Safari-/iOS-Systemerweiterung;
- Hintergrundüberwachung, All-Sites-Berechtigung oder erzwungener Razbiram-Account.

## Extension als Razbiram-Einstieg

Die Browser-Stores sind ein eigenständiger Discovery-Kanal. Name, Icon, Popup, Onboarding und
Store-Screenshots folgen der aktuellen Razbiram Momentum Identity. Die Kommunikation verspricht
keine magische Antworterkennung, sondern einen überprüfbaren Weg von Lernmaterial zu JSON.

Nach einem erfolgreichen Export darf ein zurückhaltender Link razbiram.com als Lernziel zeigen.
Die eigentliche Karte, das Quelldokument und die Browserhistorie bleiben frei von Werbung und
Tracking. Damit entsteht Werbung durch ein nützliches, vertrauenswürdiges Produkt.

## Verbindung zu razbiram-anki

Nach der Prüfung kann derselbe freigegebene Kartensatz zwei Wege nehmen:

- nativer Razbiram-Learn-JSON-Download;
- Übergabe an `razbiram-anki` für CrowdAnki beziehungsweise `.apkg`.

Die Verbindung liegt bewusst nach dem Review. Screenshots, DOM-Evidenz und Browserdaten werden
nicht an Anki-Pakete weitergereicht. `razbiram-anki` bleibt Eigentümer der Anki-Modelle und des
`.apkg`-Roundtrips; screen-to-learn bleibt Eigentümer von Capture und Review.

Da die heutige razbiram-anki-App nur Anki/CrowdAnki als Eingang kennt, braucht diese Verbindung
einen neuen, Hub-gesteuerten Reviewed-Deck-Vertrag und einen Importadapter. Sie ist sinnvoll, aber
keine bereits vorhandene Funktion.

## Erfolgskriterien

- ≥ 98 % exakte Frage-/Optionsrekonstruktion im Golden-Set für DOM-basierte Seiten;
- 100 % Erkennung von Single-vs-Multiple-vs-True/False im Golden-Set;
- 0 exportierte Karten mit unbelegter korrekter Antwort;
- 0 stille Mehrfach-zu-Einfach-Konvertierungen;
- deterministisch identische IDs und Exportreihenfolge bei identischem Input;
- vollständige Bedienbarkeit mit Tastatur und 320–360 px Breite;
- vollständiger lokaler Testlauf ohne Netz.
- semantisch identische Chrome-/Firefox-Captures für dieselbe Fixture;
- kein dauerhafter Zugriff auf alle Webseiten und kein Captured-Content-Telemetriepfad.
