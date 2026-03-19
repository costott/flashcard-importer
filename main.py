import os.path
import sys

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


def main():
    """Shows basic usage of the Docs API.
    Prints the title of a sample document.
    """
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

    try:
        service: Resource = build("docs", "v1", credentials=creds)

        # Retrieve the documents contents from the Docs service.
        document = service.documents().get(documentId=DOCUMENT_ID).execute()

        title = document.get('title')
        with open(f"{title}.txt", "w+", encoding="utf-8") as f:
            output = ""
            heading_label = ""

            for content in document.get('body').get('content'):
                if content.get('paragraph'):
                    elements = content.get('paragraph').get('elements')
                    if "heading" in content.get('paragraph').get('paragraphStyle').get('namedStyleType').lower():
                        heading_title = elements[0].get('textRun').get('content').strip().replace(" ", "_")
                        heading_label = heading_title
                
                if not content.get('table'):
                    continue

                for row in content.get('table').get('tableRows'):
                    for (i, cell) in enumerate(row.get('tableCells')):
                        cell_text = ""

                        for content in cell.get('content'):
                            if not content.get('paragraph'):
                                continue

                            for element in content.get('paragraph').get('elements'):
                                if not element.get('textRun'):
                                    continue

                                text_run = element.get('textRun')

                                final_text: str = text_run.get('content')

                                final_text = final_text.replace(
                                    "<", "\\( \\lt \\)")
                                final_text = final_text.replace(
                                    ">", "\\( \\gt \\)")
                                final_text = final_text.replace(
                                    "&", "\\( \\& \\)")

                                final_text = final_text.replace("\n", "<br>")

                                if text_run.get('textStyle').get('bold'):
                                    final_text = "<b>" + final_text + "</b>"
                                if text_run.get('textStyle').get('italic'):
                                    final_text = "<em>" + final_text + "</em>"
                                if text_run.get('textStyle').get('underline'):
                                    final_text = "<u>" + final_text + "</u>"

                                cell_text += final_text

                        cell_text = "\"" + cell_text + "\";"
                        if (i % 2 != 0):
                            if heading_label:
                                cell_text += heading_label
                            cell_text += "\n"
                        output += cell_text

            f.write(output)
        
        print(f"Written to {title}.txt")

    except HttpError as err:
        print(err)


if __name__ == "__main__":
    main()
