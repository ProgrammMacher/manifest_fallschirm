MANIFEST Fallschirm - PDF-Runtime-Helfer (Entwickler-only)
===========================================================

Zweck:
build_offline_pdf_runtime.bat kopiert eine lokal installierte GTK3-Runtime
(WeasyPrint-Abhaengigkeit fuer PDF-Export) nach runtime\gtk im Projektordner
und erzeugt optional runtime\gtk-runtime-win64.zip.

Kein Bestandteil des produktiven Installer-Builds (tools\Installer bauen.bat).
Wird nur einmalig auf dem Entwicklungsrechner benoetigt, bevor ein Offline-
Paket mit PDF-Unterstuetzung gebaut oder verteilt wird.

Benutzung:
Doppelklick auf build_offline_pdf_runtime.bat.
Voraussetzung: GTK3-Runtime Win64 ist lokal unter "Program Files" installiert.
