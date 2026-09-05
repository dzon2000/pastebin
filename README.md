# pastebin

Very simple self-hosted pastebin.

## Run locally

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The server listens on `http://localhost:5000`. Paste data is stored in
`data/pastes.db` by default. Set `PASTEBIN_DATABASE` to change its location.
Open the server URL in a browser to use the minimal editor, or use the API
below from the command line.

## CLI usage

Create a paste from a string:

```sh
curl -X POST http://localhost:5000/api/pastes \
  -H 'Content-Type: text/plain' \
  --data-binary 'text shared between machines'
```

Create a paste from a file:

```sh
curl -X POST http://localhost:5000/api/pastes \
  -H 'Content-Type: text/plain' \
  --data-binary @notes.txt
```

The response is JSON containing the generated URL:

```json
{"url":"http://localhost:5000/amber-river"}
```

Retrieve the paste with:

```sh
curl http://localhost:5000/amber-river
```

Pastes expire after 24 hours and are not served after expiration.
