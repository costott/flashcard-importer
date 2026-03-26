import os.path
import sys
import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
import re

import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

# The ID of a sample document.
# DOCUMENT_ID = "1OlgOs8M3Q9s2tKpsWIXMvyBNIMfV8xsZlMWeH6o9QA8" #cs139
# DOCUMENT_ID = "166oi7cFZRvHnEy0RUK_onJuDDb4k1OE2P0r43o_OuLM" #cs126
# DOCUMENT_ID = "1zEK2BfbOYD6rImR4gup_YiuGyJc8DcmR8R6Zig7aYXs" #cs139 new
# DOCUMENT_ID = "1xHXNmCOiPDfUo7LkaV9A6h6xVYU1cqHrQw71x3QzWak"
# DOCUMENT_ID = "1SOe9TqwvKc4rjtEEL34JTPef4AdlWIXeIwEsJEAIMbY"
# DOCUMENT_ID = "1RSNWPzl5mBF2oThIkVptevnz6MB2p7Wzr7K6EmrjSGM"
DOCUMENT_ID = sys.argv[1]
USE_GENANKI = "--genanki" in sys.argv


def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    print("Credentials obtained successfully.\nFetching document...")

    try:
        service: Resource = build("docs", "v1", credentials=creds)

        # Retrieve the documents contents from the Docs service.
        document = service.documents().get(documentId=DOCUMENT_ID).execute()
        
        title = document.get('title')
        
        print(f"Reading document: {title} ...")
        
        # Prepare media dir and helper once, then process the document body exactly once
        media_dir = Path("media")
        media_dir.mkdir(exist_ok=True)

        # Helper: download image and return filename (relative)
        def download_image(url: str, prefix: str, counter: int) -> str:
            print(f"Downloading image: {url}")

            # Create a deterministic name based on the URL so we can reuse cached files
            url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
            # If a cached file exists for this url_hash, return it
            existing = list(media_dir.glob(f"{prefix}_{url_hash}*"))
            if existing:
                print(f"Using cached image: {existing[0]}")
                return str(existing[0])

            try:
                resp = requests.get(url, stream=True, timeout=20)
                resp.raise_for_status()
            except Exception as e:
                print(f"Failed to download image: {e}")
                return None

            content_type = resp.headers.get("content-type", "")
            ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
            # fallback
            if not ext:
                # try to preserve original filename extension if present in URL
                parsed = urlparse(url)
                possible = Path(parsed.path).suffix
                ext = possible if possible else ".jpg"

            filename = f"{prefix}_{url_hash}{ext}"
            filepath = media_dir / filename
            with open(filepath, "wb") as fh:
                for chunk in resp.iter_content(1024):
                    fh.write(chunk)
            print(f"Saved image to: {filepath}")
            return str(filepath)

        # Collect pairs and media
        pairs = []  # list of (front_html, back_html)
        media_files = []
        img_counter = 0
        heading_label = ""

        for content in document.get("body").get("content"):
            # track headings for tag/label
            if content.get("paragraph"):
                pstyle = content.get("paragraph").get("paragraphStyle", {}).get("namedStyleType", "")
                if "heading" in pstyle.lower():
                    elements = content.get("paragraph").get("elements", [])
                    if elements and elements[0].get("textRun"):
                        heading_title = elements[0].get("textRun").get("content").strip().replace(" ", "_")
                        heading_label = heading_title

            if not content.get("table"):
                continue

            for row in content.get("table").get("tableRows"):
                cell_texts = []
                for (i, cell) in enumerate(row.get("tableCells")):
                    cell_html = ""
                    for c in cell.get("content"):
                        if not c.get("paragraph"):
                            continue
                        for element in c.get("paragraph").get("elements"):
                            # text runs
                            if element.get("textRun"):
                                text_run = element.get("textRun")
                                final_text = text_run.get("content", "")
                                final_text = final_text.replace("<", "\\( \\lt \\)")
                                final_text = final_text.replace(">", "\\( \\gt \\)")
                                final_text = final_text.replace("\n", "<br>")
                                style = text_run.get("textStyle", {}) or {}
                                if style.get("bold"):
                                    final_text = "<b>" + final_text + "</b>"
                                if style.get("italic"):
                                    final_text = "<em>" + final_text + "</em>"
                                if style.get("underline"):
                                    final_text = "<u>" + final_text + "</u>"
                                cell_html += final_text

                            # inline images
                            elif element.get("inlineObjectElement"):
                                inline_id = element.get("inlineObjectElement", {}).get("inlineObjectId")
                                inline_obj = document.get("inlineObjects", {}).get(inline_id, {})
                                embedded = inline_obj.get("inlineObjectProperties", {}).get("embeddedObject", {})
                                image_uri = (
                                    embedded.get("imageProperties", {}).get("contentUri")
                                    or embedded.get("contentUri")
                                    or embedded.get("imageUri")
                                )
                                if image_uri:
                                    img_counter += 1
                                    fname = download_image(image_uri, title.replace(" ", "_"), img_counter)
                                    if fname:
                                        # genanki expects filenames only, package will include media files by path
                                        media_files.append(fname)
                                        # use just basename in the HTML so Anki shows it
                                        cell_html += f"<img src=\"{Path(fname).name}\">"

                    # If generating an apkg, remove any line that contains only the author's [image] placeholder
                    if USE_GENANKI:
                        # Remove "<br>[image]
                        cell_html = re.sub(r'(<br>\s*)?\[image\]', '', cell_html)
                        # Also remove any leftover standalone [image]
                        cell_html = cell_html.replace("[image]", "")
                    cell_texts.append(cell_html)

                # use first two columns as front/back
                if len(cell_texts) >= 2:
                    front = cell_texts[0]
                    back = cell_texts[1]
                    # store heading label separately as a tag (do not append to back)
                    tag = heading_label if heading_label else ""
                    pairs.append((front, back, tag))

        # If user didn't request genanki, fall back to writing txt as before
        if not USE_GENANKI:
            with open(f"{title}.txt", "w+", encoding="utf-8") as f:
                output = ""
                for (front, back, tag) in pairs:
                    output += '"' + front + '";'
                    output += '"' + back + '";'
                    output += '"' + tag + '";\n'
                f.write(output)
            print(f"Written to {title}.txt")
        else:
            try:
                import genanki

                # Use the provided default styling for cards
                model_css = ".card {\n  font-family: arial;\n  font-size: 20px;\n  text-align: center;\n  color: black;\n  background-color: white;\n}\n#back {\n\ttext-align: left;\n}\n"

                model = genanki.Model(
                    1607392319,
                    "Simple Model",
                    fields=[
                        {"name": "Front"},
                        {"name": "Back"},
                    ],
                    templates=[
                        {
                            "name": "Card 1",
                            "qfmt": "<div class=\"card\">{{Front}}</div>",
                            "afmt": "{{FrontSide}}<hr id=answer><div id=\"back\">{{Back}}</div>",
                        }
                    ],
                    css=model_css,
                )

                deck_id = int(hashlib.sha1(title.encode("utf-8")).hexdigest()[:8], 16)
                deck = genanki.Deck(deck_id, title)

                for (front, back, tag) in pairs:
                    note = genanki.Note(
                        model=model,
                        fields=[front, back],
                        tags=[tag] if tag else [],
                    )
                    deck.add_note(note)

                pkg = genanki.Package(deck)
                # genanki wants media file paths; pass the list
                if media_files:
                    pkg.media_files = media_files
                out_path = f"{title}.apkg"
                pkg.write_to_file(out_path)
                print(f"Written APKG to {out_path}")

            except ModuleNotFoundError:
                print("Please install genanki (pip install genanki) and requests to use --genanki")
    except HttpError as err:
        print(err)

main()
