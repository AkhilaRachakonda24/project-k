from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
import re

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages

# Set the upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# Define the File model
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

# Create the database
with app.app_context():
    db.create_all()

# Function to get the list of files and their passwords
def get_uploaded_files():
    files = File.query.all()
    valid_files = []
    for file in files:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        if os.path.exists(file_path):
            valid_files.append(file)
        else:
            # Delete the file record from the database if it doesn't exist in the upload folder
            db.session.delete(file)
            db.session.commit()
    return valid_files

def validate_password(password):
    # Password must be at least 8 characters long and contain at least one uppercase letter,
    # one digit, and one special character
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

@app.route('/')
def index():
    files = get_uploaded_files()
    return render_template('password.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    if file:
        # Check if the file already exists in the database
        existing_file = File.query.filter_by(filename=file.filename).first()
        if existing_file:
            flash('Failure: File already exists in the database.', 'danger')
            return redirect(url_for('index'))

        # Check if the file already exists in the upload folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        if os.path.exists(file_path):
            flash('Failure: File already exists in the upload folder.', 'danger')
            return redirect(url_for('index'))

        # Get the password entered by the user
        file_password = request.form.get('password')

        # Validate password
        if not validate_password(file_password):
            flash('Failure: Password must be at least 8 characters long and contain at least one uppercase letter, one digit, and one special character.', 'danger')
            return redirect(url_for('index'))

        # Save the file
        file.save(file_path)
        
        # Save the file name and password to the database
        new_file = File(filename=file.filename, password=file_password)
        db.session.add(new_file)
        db.session.commit()
        
        flash('Success: File uploaded successfully.', 'success')
        return redirect(url_for('index'))

@app.route('/verify', methods=['POST'])
def verify_password():
    file_id = request.form.get('file_id')
    entered_password = request.form.get('password')
    file = File.query.get(file_id)
    
    if file and file.password == entered_password:
        flash(f'Success: Correct password! <a href="{url_for("download_file", filename=file.filename)}" class="alert-link">Click here to open the file</a>', 'success')
    else:
        flash('Failure: Incorrect password.', 'danger')
    
    return redirect(url_for('index'))

@app.route('/delete/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    file = File.query.get(file_id)
    if file:
        # Delete the file from the upload folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete the file record from the database
        db.session.delete(file)
        db.session.commit()

        flash('Success: File deleted successfully.', 'success')
    else:
        flash('Failure: File not found.', 'danger')

    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
