# website_daisy — Project Notes

## Overview
Flask web application for Daisy's personal/business website. Deployed on Namecheap shared hosting via Passenger WSGI.

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

## Notes
- `passenger_wsgi.py` is the Namecheap-specific WSGI entry point
- Contact form uses IP/geo filtering (added to block spam)
- `requests` import is optional in contact form handler to prevent 500 errors if not installed
