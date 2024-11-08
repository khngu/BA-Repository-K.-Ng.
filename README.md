# KI-gestützte Brille für Sehbeeinträchtigte

Dieses Repository beinhaltet den Quellcode eines Prototyps für eine KI-gestützte Brille, entwickelt von Khac Trong Nguyen im Rahmen seiner Bachelorarbeit in Digitale Medien an der HAW Fulda. Ziel dieses Projekts ist es, die Mobilität von sehbehinderten Menschen durch die Bereitstellung von Umgebungsinformationen mittels Bildverarbeitung, Spracherkennung und -synthese zu verbessern.

## Funktionen

* **Texterkennung:** Liest Text aus Bildern oder Dokumenten vor.
* **Objekterkennung:** Erkennt und beschreibt Objekte in der Umgebung.
* **Sprachinteraktion (Chatbot):** Ermöglicht es dem Benutzer, Fragen zu stellen und Informationen über einen Chatbot zu erhalten.

## Hardware-Komponenten

* **Raspberry Pi 4 (4GB):** Dient als Hauptprozessor und steuert die KI-Verarbeitung.
* **XIAO ESP32S3 Sense:** Mikrocontroller zur Steuerung der Kamera und des Touch-Sensors.
* **OV5640 Kamera-Modul:** Nimmt Bilder der Umgebung auf.
* **Apple Earpods:** Liefern Audio-Feedback und dienen zur Spracheingabe.
* **USB Sound Card:** Ermöglicht Audioausgabe und -eingabe am Raspberry Pi.
* **TTP223B Touch Sensor:** Ermöglicht die Steuerung der Brille durch Berührung.
* **Akku (Powerbank):** Versorgt das System mit Strom.

## Software-Komponenten

* **Flask Server (Python):** Verwaltet HTTP-Anfragen vom ESP32, kommuniziert mit den KI-Diensten und generiert Antworten.
* **ESP32 Firmware (C++):** Steuert die Hardware, erfasst Bilder und sendet diese an den Flask Server.
* **KI-Dienste:**
    * **Google Cloud Text-to-Speech API:** Wandelt Text in Sprache um.
    * **OpenAI GPT API:** Ermöglicht Text- und Objekterkennung sowie Chatbot-Funktionalität.
    * **Vosk API:** Implementiert für VAD.
    * **OpenAI Whisper API:** Spracherkennung und Transkribierung.

## Installation und Ausführung

1. **Hardware-Aufbau:** Verbinde die Hardware-Komponenten wie im Schaltplan beschrieben.
2. **Software-Installation:**
    * **Raspberry Pi:** Installiere die erforderlichen Python-Bibliotheken (`pip install -r requirements.txt`).
    * **ESP32:** Lade die C++-Firmware auf den ESP32 hoch.
3. **Konfiguration:**
    * **WLAN:** Konfiguriere die WLAN-Verbindung auf dem ESP32 und Raspberry Pi.
    * **API-Schlüssel:** Stelle sicher, dass die API-Schlüssel für Google Cloud und OpenAI korrekt in den Python-Skripten eingetragen sind.
4. **Ausführung:**
    * **Raspberry Pi:** Starte den Flask Server (`python app.py`).
    * **ESP32:** Starte die Firmware auf dem ESP32.

## Verwendung

1. **Einschalten:** Schalte den Raspberry Pi und den ESP32 ein.
2. **Modus auswählen:** Berühre den Touch-Sensor, um zwischen den Modi zu wechseln.
3. **Funktion ausführen:**
    * **Texterkennung/Objekterkennung:** Berühre den Touch-Sensor kurz, um ein Bild aufzunehmen und analysieren zu lassen.
    * **Chatbot:** Berühre den Touch-Sensor kurz, um den Chatbot zu aktivieren und deine Frage zu stellen.
4. **Audio-Feedback:** Die Ergebnisse der Analyse werden über die Kopfhörer ausgegeben.

## Hinweise

* **WLAN-Verbindung:** Eine stabile WLAN-Verbindung ist erforderlich, um die Cloud-basierten KI-Dienste nutzen zu können.
* **Akkulaufzeit:** Die Akkulaufzeit hängt von der Nutzung ab. Stelle sicher, dass du eine ausreichend große Powerbank verwendest.
* **Datenschutz:** Beachte, dass bei der Nutzung von Cloud-Diensten Daten übertragen werden. Stelle sicher, dass du die Datenschutzbestimmungen der Anbieter kennst und akzeptierst.

## Weiterentwicklung

* Integration einer Navigationsfunktion
* Verbesserung der Kameraqualität
* Entwicklung einer benutzerfreundlicheren WLAN-Konfiguration
* Unterstützung mehrerer Sprachen
* Optimierung der Gewichtsverteilung und Entwicklung einer kabellosen Version
