import os
from pathlib import Path
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

mail = Mail(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


def send_contact_email(name, email, message, redirect_endpoint):
    # Honeypot: bots fill hidden fields, humans don't see them
    if request.form.get('website', '').strip():
        flash('Message sent successfully.', 'success')
        return redirect(url_for(redirect_endpoint))

    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

    try:
        recipient = os.environ.get('MAIL_RECIPIENT')
        msg = Message(
            subject=f'New message from {name}',
            sender=app.config['MAIL_USERNAME'],
            recipients=[recipient]
        )
        body = f"Someone reached out via your website!\n\nName:    {name}\nEmail:   {email}\nIP:      {ip}\n"
        if message:
            body += f"\nMessage:\n{message}\n"
        msg.body = body
        mail.send(msg)
        flash('Message sent successfully.', 'success')
    except Exception:
        flash('Something went wrong. Please try again later.', 'error')

    return redirect(url_for(redirect_endpoint))


def photo_exists():
    return (Path(app.static_folder) / 'dan.jpg').exists()


@app.route('/')
def landing():
    return render_template('landing.html', photo_exists=photo_exists())

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/education')
def education():
    return render_template('education.html')

@app.route('/work')
def work():
    return render_template('work.html')

@app.route('/contact', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()[:300]
        if not name or not email:
            flash('Please fill out both fields.', 'error')
            return redirect(url_for('contact'))
        return send_contact_email(name, email, message, 'contact')
    return render_template('contact.html')


@app.route('/simple')
def simple_landing():
    return render_template('simple/landing.html', photo_exists=photo_exists())

@app.route('/simple/about')
def simple_about():
    return render_template('simple/about.html')

@app.route('/simple/education')
def simple_education():
    return render_template('simple/education.html')

@app.route('/simple/work')
def simple_work():
    return render_template('simple/work.html')

@app.route('/simple/contact', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def simple_contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()[:300]
        if not name or not email:
            flash('Please fill out both fields.', 'error')
            return redirect(url_for('simple_contact'))
        return send_contact_email(name, email, message, 'simple_contact')
    return render_template('simple/contact.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
