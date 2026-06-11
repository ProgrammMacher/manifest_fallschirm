import os
import smtplib
import html
import socket
import subprocess
import ipaddress
import time
from email.message import EmailMessage
from email.utils import make_msgid

from app.models.billing_config import BillingConfig


class TransientSmtpError(RuntimeError):
    """Temporärer SMTP-Fehler (typisch 4xx), für Retry geeignet."""


def _decode_smtp_error_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _is_connectivity_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            socket.timeout,
            TimeoutError,
            ConnectionError,
            socket.gaierror,
            smtplib.SMTPConnectError,
            smtplib.SMTPServerDisconnected,
        ),
    )


def _smtp_host_candidates(primary_host: str, fallback_host: str | None = None) -> list[str]:
    host = (primary_host or "").strip().lower()
    if not host:
        return []

    candidates = [host]
    if fallback_host:
        fb = fallback_host.strip().lower()
        if fb and fb != host:
            candidates.append(fb)

    # dedupe, Reihenfolge beibehalten
    out = []
    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _resolve_host_via_public_dns(hostname: str) -> list[str]:
    """
    DNS-Fallback fuer Umgebungen mit defektem lokalem Resolver.
    Liefert eine Liste IPv4-Adressen fuer den Hostnamen.
    """
    host = (hostname or "").strip()
    if not host:
        return []

    resolvers = ["1.1.1.1", "9.9.9.9", "8.8.8.8"]
    resolver_set = set(resolvers)
    found: list[str] = []

    for resolver in resolvers:
        try:
            cp = subprocess.run(
                ["nslookup", host, resolver],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
        except Exception:
            continue

        if cp.returncode != 0:
            continue

        in_answer_block = False
        host_lower = host.lower()

        for raw in cp.stdout.splitlines():
            line = raw.strip()
            if not line:
                continue

            # Erst ab dem Ziel-Host die folgenden Address(es)-Zeilen auswerten.
            if line.lower().startswith("name:"):
                in_answer_block = host_lower in line.lower()
                continue

            if not in_answer_block:
                continue

            if "Address:" not in line and "Addresses:" not in line:
                continue

            _, rhs = line.split(":", 1)
            for part in rhs.replace(",", " ").split():
                candidate = part.strip()
                try:
                    ip = ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                if ip.version != 4:
                    continue
                ip_s = str(ip)
                if ip_s in resolver_set:
                    continue
                found.append(ip_s)

    # stabil deduplizieren
    deduped: list[str] = []
    seen = set()
    for ip in found:
        if ip in seen:
            continue
        seen.add(ip)
        deduped.append(ip)
    return deduped


def _smtp_send(
    *,
    connect_host: str,
    smtp_host_for_tls: str,
    smtp_port: int,
    cfg: BillingConfig,
    msg: EmailMessage,
    envelope_from: str,
) -> None:
    smtp_client_cls = smtplib.SMTP_SSL if bool(getattr(cfg, "smtp_use_ssl", False)) else smtplib.SMTP

    with smtp_client_cls(connect_host, smtp_port, timeout=10) as server:
        # Bei IP-Connect weiterhin den eigentlichen SMTP-Hostnamen fuer TLS/SNI nutzen.
        # EHLO mit dem Zielhostnamen senden (nicht dem lokalen Maschinennamen), da
        # IONOS den lokalen Maschinennamen mit 451 ablehnt.
        try:
            server._host = smtp_host_for_tls
        except Exception:
            pass

        server.ehlo(smtp_host_for_tls)

        if (not bool(getattr(cfg, "smtp_use_ssl", False))) and cfg.smtp_use_tls:
            server.starttls()
            server.ehlo(smtp_host_for_tls)

        if cfg.smtp_username and cfg.smtp_password:
            server.login((cfg.smtp_username or "").strip(), cfg.smtp_password)

        try:
            refused = server.send_message(msg, from_addr=envelope_from)
        except smtplib.SMTPSenderRefused as exc:
            msg = (
                f"SMTP-Server hat den Absender abgelehnt "
                f"({exc.smtp_code}): {_decode_smtp_error_text(exc.smtp_error)} | "
                f"Absender: {exc.sender}"
            )
            if 400 <= int(exc.smtp_code or 0) < 500:
                raise TransientSmtpError(msg) from exc
            raise RuntimeError(msg) from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise RuntimeError(
                f"SMTP-Server hat den Empfänger abgelehnt: {exc.recipients}"
            ) from exc
        except smtplib.SMTPDataError as exc:
            msg = f"SMTP-Datenfehler ({exc.smtp_code}): {_decode_smtp_error_text(exc.smtp_error)}"
            if 400 <= int(exc.smtp_code or 0) < 500:
                raise TransientSmtpError(msg) from exc
            raise RuntimeError(msg) from exc

        if refused:
            raise RuntimeError(
                f"E-Mail konnte nicht zugestellt werden. Abgelehnte Empfänger: {refused}"
            )


def _image_content_subtype(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1].lstrip('.')
    if ext in {'jpg', 'jpeg'}:
        return 'jpeg'
    if ext in {'png', 'gif', 'bmp', 'webp'}:
        return ext
    return 'png'


def _read_image_bytes(image_path: str) -> bytes:
    with open(image_path, 'rb') as fh:
        return fh.read()


def _normalize_external_url(url: str | None) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "mailto:", "tel:")):
        return raw
    return f"https://{raw}"


def _iter_qr_config_items(cfg):
    """Liefert (cid, label, filename, target_url)-Tupel fuer konfigurierte QR-Codes."""
    if not cfg:
        return []
    return [
        (
            "qr_instagram",
            "Instagram",
            getattr(cfg, "qr_instagram_filename", None),
            _normalize_external_url(getattr(cfg, "instagram_url", None)),
        ),
        (
            "qr_facebook",
            "Facebook",
            getattr(cfg, "qr_facebook_filename", None),
            _normalize_external_url(getattr(cfg, "facebook_url", None)),
        ),
        (
            "qr_website",
            "Website",
            getattr(cfg, "qr_website_filename", None),
            _normalize_external_url(getattr(cfg, "website", None)),
        ),
    ]


def _build_qr_footer_html(cfg, *, top_margin_px: int = 14) -> str:
    """
    Baut den QR-Block als HTML.
    - Einheitliche Kachelgroesse fuer alle QR-Codes
    - Bewusst kleiner als das Logo (Logo max-height: 80px)
    """
    qr_size_px = 88
    qr_cell_width_px = 104
    qr_cells = []
    for cid_name, label, filename, target_url in _iter_qr_config_items(cfg):
        if not (filename or "").strip():
            continue
        img_html = (
            f'<img src="cid:{cid_name}" alt="QR {html.escape(label)}" '
            f'width="{qr_size_px}" height="{qr_size_px}" '
            f'class="qr-footer-img" style="width:{qr_size_px}px !important; min-width:{qr_size_px}px !important; max-width:{qr_size_px}px !important; height:{qr_size_px}px !important; max-height:{qr_size_px}px !important; object-fit:contain; border:0; display:block; margin:0 auto; pointer-events:none;" />'
        )
        if target_url:
            img_html = (
                f'<a href="{html.escape(target_url)}" target="_blank" rel="noopener noreferrer" '
                'style="display:inline-block; text-decoration:none; border:0;">'
                + img_html
                + '</a>'
            )
        qr_cells.append(
            f'<td class="qr-footer-cell" width="{qr_cell_width_px}" style="width:{qr_cell_width_px}px; min-width:{qr_cell_width_px}px; max-width:{qr_cell_width_px}px; vertical-align:top; text-align:center; padding:0 18px 0 0;">'
            f'<div class="qr-footer-label" style="font-size:12px; color:#555; margin-bottom:4px; line-height:1.2; white-space:nowrap; word-break:keep-all;">{html.escape(label)}</div>'
            + img_html
            +
            '</td>'
        )

    if not qr_cells:
        return ""

    return (
        f'<div style="margin-top:{int(top_margin_px)}px;">'
        '<table style="border-collapse:collapse; border:none; table-layout:fixed; width:auto;">'
        '<tr>'
        + "".join(qr_cells)
        + '</tr>'
        '</table>'
        '</div>'
    )


def _attach_configured_qr_images(msg: EmailMessage, cfg) -> None:
    """Bindet konfigurierte QR-Dateien als inline related images ein (falls vorhanden)."""
    if not cfg:
        return

    try:
        html_part = msg.get_payload()[1]
    except Exception:
        return

    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    qr_dir = os.path.join(static_dir, "img", "qr")

    for cid_name, _label, filename, _target_url in _iter_qr_config_items(cfg):
        fn = (filename or "").strip()
        if not fn:
            continue
        qr_path = os.path.join(qr_dir, fn)
        if not os.path.exists(qr_path):
            continue
        try:
            html_part.add_related(
                _read_image_bytes(qr_path),
                maintype="image",
                subtype=_image_content_subtype(qr_path),
                cid=cid_name,
            )
        except Exception:
            # Fehler beim optionalen QR-Embed sollen den Versand nicht blockieren.
            continue


def _render_html_email(
    text: str,
    billing_config: BillingConfig | None = None,
    *,
    include_qr: bool = True,
) -> str:
    """
    Wandelt einen Plain-Text-Mailbody in einfache, sichere HTML-Struktur um.
    - Escaping gegen HTML/XSS
    - Absätze aus Leerzeilen
    - Zeilenumbrüche bleiben erhalten
    """
    escaped = html.escape(text)

    paragraphs = []
    for block in escaped.split("\n\n"):
        if block.strip():
            paragraphs.append(
                "<p>" + block.replace("\n", "<br>") + "</p>"
            )

    footer_html = ""
    if billing_config:
        footer_lines = []
        if billing_config.company_name:
            footer_lines.append(billing_config.company_name)
        if billing_config.street:
            footer_lines.append(billing_config.street)
        if billing_config.zip_code or billing_config.city:
            address_line = f"{billing_config.zip_code or ''} {billing_config.city or ''}".strip()
            if address_line:
                footer_lines.append(address_line)
        if billing_config.website:
            footer_lines.append(f"Internet: {billing_config.website}")
        if billing_config.email:
            footer_lines.append(f"E-Mail: {billing_config.email}")
        if billing_config.tax_number:
            footer_lines.append(f"Steuernummer: {billing_config.tax_number}")

        footer_text = ""
        if footer_lines:
            footer_text = (
                '<div style="font-size:13px; line-height:1.35; color:#222;">'
                + '<br>'.join(html.escape(line) for line in footer_lines)
                + '</div>'
            )

        logo_html = ""
        if billing_config.logo_filename:
            logo_html = (
                '<div style="text-align:right;">'
                '<img src="cid:logo" alt="Logo" '
                'style="max-height:80px; width:auto; object-fit:contain;" />'
                '</div>'
            )

        qr_html = _build_qr_footer_html(billing_config, top_margin_px=14) if include_qr else ""

        if footer_text or logo_html or qr_html:
            footer_html = (
                '<div style="margin-top:10px; padding-top:14px;">'
                '<table style="width:100%; border-collapse:collapse; border:none;">'
                '<tr>'
                '<td style="vertical-align:top; padding:0; width:70%;">'
                + footer_text
                + '</td>'
                '<td style="vertical-align:top; padding:0 0 0 12px; width:30%;">'
                + logo_html
                + '</td>'
                '</tr>'
                '</table>'
                + qr_html
                + '</div>'
            )

    return f"""\
<!doctype html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @media only screen and (max-width: 640px) {{
                .qr-footer-cell {{
                    width: 86px !important;
                    min-width: 86px !important;
                    max-width: 86px !important;
                    padding-right: 12px !important;
                }}

                .qr-footer-img {{
                    width: 70px !important;
                    min-width: 70px !important;
                    max-width: 70px !important;
                    height: 70px !important;
                    max-height: 70px !important;
                }}

                .qr-footer-label {{
                    font-size: 12px !important;
                    white-space: nowrap !important;
                    word-break: keep-all !important;
                }}
            }}
        </style>
    </head>
  <body style="
    font-family: Arial, Helvetica, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    color: #222;
  ">
    {''.join(paragraphs)}
    {footer_html}
  </body>
</html>
"""


class MailerService:
    @staticmethod
    def send_invoice_email(
        *,
        to_email: str,
        subject: str,
        body: str,
        pdf_bytes: bytes | None = None,
        filename: str | None = None,
        billing_config: BillingConfig | None = None,
    ) -> dict[str, str | None]:
        # ------------------------------------------------------------------
        # SMTP / Absender-Konfiguration aus BillingConfig
        # ------------------------------------------------------------------
        cfg = billing_config or BillingConfig.query.first()
        smtp_server = (cfg.smtp_server or "").strip() if cfg else ""
        sender_address = (cfg.mail_sender_address or "").strip() if cfg else ""
        to_email = (to_email or "").strip()

        if not cfg or not smtp_server:
            raise RuntimeError("SMTP-Konfiguration unvollständig.")
        if not sender_address:
            raise RuntimeError("Absender-E-Mail-Adresse fehlt in der Konfiguration.")
        if not to_email:
            raise RuntimeError("Empfänger-E-Mail-Adresse fehlt.")

        # ------------------------------------------------------------------
        # E-Mail aufbauen (multipart/alternative)
        # ------------------------------------------------------------------
        msg = EmailMessage()
        msg["From"] = sender_address
        msg["To"] = to_email
        msg["Subject"] = subject
        sender_domain = sender_address.split("@", 1)[1].strip() if "@" in sender_address else None
        msg["Message-ID"] = make_msgid(domain=sender_domain or None)

        # ✅ Plain-Text (Fallback)
        msg.set_content(body)

        # ✅ HTML-Version (aus Plain-Text erzeugt)
        msg.add_alternative(
            _render_html_email(body, billing_config=billing_config),
            subtype="html",
        )

        if billing_config:
            html_part = msg.get_payload()[1]
            static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

            if billing_config.logo_filename:
                logo_path = os.path.join(static_dir, "img", billing_config.logo_filename)
                if os.path.exists(logo_path):
                    html_part.add_related(
                        _read_image_bytes(logo_path),
                        maintype="image",
                        subtype=_image_content_subtype(logo_path),
                        cid="logo",
                    )

            _attach_configured_qr_images(msg, billing_config)

        if pdf_bytes is not None and filename:
            msg.add_attachment(
                pdf_bytes,
                maintype="application",
                subtype="pdf",
                filename=filename,
            )

        auth_sender = (cfg.smtp_username or "").strip()

        sender_candidates = [sender_address]
        if auth_sender and auth_sender.lower() != sender_address.lower():
            sender_candidates.append(auth_sender)

        def _prepare_sender_headers(sender_value: str) -> None:
            if "From" in msg:
                msg.replace_header("From", sender_value)
            else:
                msg["From"] = sender_value

            # Wenn wir mit technischem SMTP-User senden, bleibt der
            # fachliche Absender als Reply-To erhalten.
            if sender_value.lower() != sender_address.lower():
                if "Reply-To" in msg:
                    msg.replace_header("Reply-To", sender_address)
                else:
                    msg["Reply-To"] = sender_address
            elif "Reply-To" in msg:
                del msg["Reply-To"]

        def _try_smtp_with_sender_candidates(connect_host: str, smtp_host_for_tls: str, smtp_port: int) -> dict[str, str | None]:
            last_error: Exception | None = None
            for sender_value in sender_candidates:
                retry_delays = [0.0, 1.5, 3.0]
                for attempt, delay in enumerate(retry_delays, start=1):
                    if delay > 0:
                        time.sleep(delay)
                    try:
                        _prepare_sender_headers(sender_value)
                        _smtp_send(
                            connect_host=connect_host,
                            smtp_host_for_tls=smtp_host_for_tls,
                            smtp_port=smtp_port,
                            cfg=cfg,
                            msg=msg,
                            envelope_from=sender_value,
                        )
                        return {
                            "recipient": to_email,
                            "message_id": msg.get("Message-ID"),
                            "smtp_host": smtp_host_for_tls,
                            "envelope_from": sender_value,
                        }
                    except TransientSmtpError as exc:
                        last_error = exc
                        # Bei transienten Fehlern den Retry-Plan ausfahren.
                        if attempt < len(retry_delays):
                            continue
                        # Nach dem letzten Retry kann ggf. noch Sender-Fallback helfen.
                    except Exception as exc:
                        last_error = exc
                        # Nur bei Absenderproblemen den naechsten Sender-Kandidaten testen.
                        if "Absender abgelehnt" not in str(exc):
                            raise
                        break
            if last_error is not None:
                raise last_error

        # ------------------------------------------------------------------
        # SMTP-Versand
        # ------------------------------------------------------------------
        smtp_port = int(cfg.smtp_port or 587)
        host_candidates = _smtp_host_candidates(
            smtp_server,
            fallback_host=(getattr(cfg, "smtp_fallback_host", None) or None),
        )
        last_connectivity_exc: Exception | None = None
        host_errors: list[str] = []

        for host_candidate in host_candidates:
            try:
                return _try_smtp_with_sender_candidates(
                    connect_host=host_candidate,
                    smtp_host_for_tls=host_candidate,
                    smtp_port=smtp_port,
                )
            except Exception as host_exc:
                if not _is_connectivity_error(host_exc):
                    raise
                last_connectivity_exc = host_exc
                host_errors.append(f"{host_candidate}: {host_exc}")

                fallback_ips = _resolve_host_via_public_dns(host_candidate)
                if not fallback_ips:
                    continue

                last_error: Exception | None = None
                non_connectivity_errors: list[str] = []
                for ip in fallback_ips:
                    try:
                        return _try_smtp_with_sender_candidates(
                            connect_host=ip,
                            smtp_host_for_tls=host_candidate,
                            smtp_port=smtp_port,
                        )
                    except Exception as ip_exc:
                        last_error = ip_exc
                        if not _is_connectivity_error(ip_exc):
                            non_connectivity_errors.append(f"{ip}: {ip_exc}")

                if non_connectivity_errors:
                    unique_errors = []
                    seen = set()
                    for item in non_connectivity_errors:
                        if item in seen:
                            continue
                        seen.add(item)
                        unique_errors.append(item)
                    detail = " | ".join(unique_errors[:3])
                    host_errors.append(
                        f"{host_candidate} (IP-Fallback Versandfehler): {detail}"
                    )
                    continue

                host_errors.append(f"{host_candidate} (IP-Fallback): {last_error}")

        detail = " | ".join(host_errors[:3]) if host_errors else str(last_connectivity_exc)
        raise RuntimeError(
            f"SMTP-Server-Verbindung fehlgeschlagen. Geprüfte Hosts: {', '.join(host_candidates)}. "
            f"Details: {detail}"
        ) from last_connectivity_exc

    # ------------------------------------------------------------------
    # Generischer E-Mail-Versand (für Newsletter / eigene E-Mails)
    # Akzeptiert jedes cfg-Objekt mit SMTP-Attributen (duck typing).
    # attachments: Liste von (filename, bytes)
    # inline_images: Liste von (cid_name, bytes, content_subtype)
    #                -> in HTML-Body eingebettet, unten angefügt
    # ------------------------------------------------------------------
    @staticmethod
    def send_custom_email(
        *,
        to_email: str,
        subject: str,
        body: str,
        cfg,
        sender_address: str | None = None,
        attachments: list | None = None,
        inline_images: list | None = None,
        inline_images_intro: str | None = None,
    ) -> dict[str, str | None]:
        smtp_server = (getattr(cfg, "smtp_server", None) or "").strip()
        _sender = (
            sender_address
            or (getattr(cfg, "mail_sender_address", None) or "").strip()
            or ""
        )
        to_email = (to_email or "").strip()

        if not smtp_server:
            raise RuntimeError("SMTP-Konfiguration unvollständig (smtp_server fehlt).")
        if not _sender:
            raise RuntimeError("Absender-E-Mail-Adresse fehlt.")
        if not to_email:
            raise RuntimeError("Empfänger-E-Mail-Adresse fehlt.")

        msg = EmailMessage()
        msg["From"] = _sender
        msg["To"] = to_email
        msg["Subject"] = subject
        sender_domain = _sender.split("@", 1)[1].strip() if "@" in _sender else None
        msg["Message-ID"] = make_msgid(domain=sender_domain or None)

        # Plain-Text
        plain_text_body = body
        if inline_images and inline_images_intro:
            plain_text_body = body.rstrip() + "\n\n" + inline_images_intro.strip() + "\n"
        msg.set_content(plain_text_body)

        # HTML – inline images ggf. anhängen
        inline_image_html = ""
        if inline_images:
            intro_html = ""
            if inline_images_intro:
                intro_html = (
                    '<div style="margin-top:16px;white-space:pre-line;">'
                    + html.escape(inline_images_intro)
                    + '</div><div style="height:1em;"></div>'
                )
            parts = []
            for cid_name, _img_bytes, _img_subtype in inline_images:
                safe_cid = html.escape(cid_name)
                parts.append(
                    f'<div style="margin-top:8px;">'
                    f'<img src="cid:{safe_cid}" alt="" '
                    f'style="max-width:100%;height:auto;" /></div>'
                )
            if parts:
                inline_image_html = (
                    '<div style="margin-top:16px;">' + intro_html + "".join(parts) + "</div>"
                )

        html_body = _render_html_email(body, billing_config=cfg, include_qr=False)
        bottom_html = inline_image_html + _build_qr_footer_html(cfg, top_margin_px=12)
        if bottom_html:
            html_body = html_body.replace("</body>", bottom_html + "</body>")

        msg.add_alternative(html_body, subtype="html")

        # Inline-Bilder als related-Part einbetten
        if inline_images:
            html_part = msg.get_payload()[1]
            for cid_name, img_bytes, img_subtype in inline_images:
                html_part.add_related(
                    img_bytes,
                    maintype="image",
                    subtype=img_subtype or "png",
                    cid=cid_name,
                )

        # Logo aus cfg einbetten (falls vorhanden)
        if getattr(cfg, "logo_filename", None):
            import os as _os
            static_dir = _os.path.abspath(
                _os.path.join(_os.path.dirname(__file__), "..", "static")
            )
            logo_path = _os.path.join(static_dir, "img", cfg.logo_filename)
            if _os.path.exists(logo_path):
                try:
                    html_part = msg.get_payload()[1]
                    html_part.add_related(
                        _read_image_bytes(logo_path),
                        maintype="image",
                        subtype=_image_content_subtype(logo_path),
                        cid="logo",
                    )
                except Exception:
                    pass

        _attach_configured_qr_images(msg, cfg)

        # Datei-Anhänge
        if attachments:
            for att_filename, att_bytes in attachments:
                ext = (att_filename.rsplit(".", 1)[-1]).lower() if "." in att_filename else ""
                subtype = "pdf" if ext == "pdf" else "octet-stream"
                msg.add_attachment(
                    att_bytes,
                    maintype="application",
                    subtype=subtype,
                    filename=att_filename,
                )

        smtp_port = int(getattr(cfg, "smtp_port", None) or 587)
        host_candidates = _smtp_host_candidates(
            smtp_server,
            fallback_host=(getattr(cfg, "smtp_fallback_host", None) or None),
        )
        auth_sender = (getattr(cfg, "smtp_username", None) or "").strip()
        sender_candidates = [_sender]
        if auth_sender and auth_sender.lower() != _sender.lower():
            sender_candidates.append(auth_sender)

        def _prepare(sender_value: str) -> None:
            if "From" in msg:
                msg.replace_header("From", sender_value)
            else:
                msg["From"] = sender_value
            if sender_value.lower() != _sender.lower():
                if "Reply-To" in msg:
                    msg.replace_header("Reply-To", _sender)
                else:
                    msg["Reply-To"] = _sender
            elif "Reply-To" in msg:
                del msg["Reply-To"]

        def _try_send(connect_host: str, smtp_host_for_tls: str) -> dict:
            last_err = None
            for sv in sender_candidates:
                retry_delays = [0.0, 1.5, 3.0]
                for attempt, delay in enumerate(retry_delays, start=1):
                    if delay > 0:
                        time.sleep(delay)
                    try:
                        _prepare(sv)
                        _smtp_send(
                            connect_host=connect_host,
                            smtp_host_for_tls=smtp_host_for_tls,
                            smtp_port=smtp_port,
                            cfg=cfg,
                            msg=msg,
                            envelope_from=sv,
                        )
                        return {
                            "recipient": to_email,
                            "message_id": msg.get("Message-ID"),
                            "smtp_host": smtp_host_for_tls,
                            "envelope_from": sv,
                        }
                    except TransientSmtpError as exc:
                        last_err = exc
                        if attempt < len(retry_delays):
                            continue
                    except Exception as exc:
                        last_err = exc
                        if "Absender abgelehnt" not in str(exc):
                            raise
                        break
            if last_err is not None:
                raise last_err

        last_connectivity_exc = None
        host_errors: list[str] = []
        for host_candidate in host_candidates:
            try:
                return _try_send(host_candidate, host_candidate)
            except Exception as host_exc:
                if not _is_connectivity_error(host_exc):
                    raise
                last_connectivity_exc = host_exc
                host_errors.append(f"{host_candidate}: {host_exc}")
                fallback_ips = _resolve_host_via_public_dns(host_candidate)
                if not fallback_ips:
                    continue
                for ip in fallback_ips:
                    try:
                        return _try_send(ip, host_candidate)
                    except Exception as ip_exc:
                        if not _is_connectivity_error(ip_exc):
                            host_errors.append(f"{ip}: {ip_exc}")
                        last_connectivity_exc = ip_exc

        detail = " | ".join(host_errors[:3]) if host_errors else str(last_connectivity_exc)
        raise RuntimeError(
            f"SMTP-Verbindung fehlgeschlagen. Hosts: {', '.join(host_candidates)}. {detail}"
        ) from last_connectivity_exc