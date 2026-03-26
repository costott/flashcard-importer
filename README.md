# How to Run

`python main.py [DOCUMENT ID portion of google docs URL]`

Remember to delete token.json if the code isn't working, and that you have credentials.json from me.

## If genanki is installed

`python main.py [DOCUMENT ID portion of google docs URL] --genanki`

This will take a lot longer as it has to download every image in the flashcards, but avoids having to paste them over.

! Be aware I've added custom CSS so the back of the card is left instead of center aligned, if you don't want this, just change the css on line 196.
