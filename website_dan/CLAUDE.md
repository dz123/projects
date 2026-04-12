# website_dan — Project Notes

## Overview
Flask web application for Dan's personal website. Deployed on Namecheap shared hosting via Passenger WSGI.

## Running Locally
```bash
pip install -r requirements.txt
python app.py
```

## Deployment (Namecheap)
- Entry point: `passenger_wsgi.py`
- Process manager: `Procfile`
- Static files served from `static/`
- Templates in `templates/`

## SSL
- `certificate.txt`, `csr.txt`, `encodedkey.txt`, `privatekey.txt` — SSL cert files (do not commit to public repos)

## Notes
- `passenger_wsgi.py` is the Namecheap-specific WSGI entry point
