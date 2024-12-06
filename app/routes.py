from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import uuid
import sqlite3
from datetime import datetime
import os
from fpdf import FPDF
from flask import send_file
from werkzeug.utils import secure_filename

main = Blueprint('main', __name__)

# Initialize SQLite database and create table if not exists
def init_db():
    conn = sqlite3.connect('document_requests.db')
    c = conn.cursor()

    # Drop the existing table if it exists (use carefully)
    c.execute('DROP TABLE IF EXISTS requests')

    # Create the requests table
    c.execute(''' 
    CREATE TABLE IF NOT EXISTS requests (
        request_id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        message TEXT,
        phone TEXT,
        document_type TEXT,
        status TEXT,
        rejection_reason TEXT,  -- For rejected requests
        start_date DATE,
        end_date DATE,
        year INTEGER,
        semester TEXT,
        academic_year TEXT,
        specialization TEXT,
        company TEXT,
        duration TEXT,
        created_at DATETIME,
        filename TEXT -- Added field for storing the filename
    )
    ''')

    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('document_requests.db')
    conn.row_factory = sqlite3.Row  # Fetch rows as dictionaries
    return conn

# Route to display the home page
@main.route('/')
def home():
    return render_template('index1.html', title="Home")

# Route to display the Étudiant section
@main.route('/etudiant')
def etudiant():
    return render_template('etudiant.html', title="Étudiant")

# Route to display the Administration section
@main.route('/admin')
def admin():
    return render_template('admin.html', title="Administration")

# Route to handle document request form submission
@main.route('/request', methods=['GET', 'POST'])
def request_document():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        phone = request.form.get('phone')
        document_type = request.form.get('document_type')

        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Default status for the request
        status = 'En cours'

        # Save request data to the database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO requests (request_id, name, email, message, phone, document_type, status, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (request_id, name, email, message, phone, document_type, status, datetime.now()))
        conn.commit()
        conn.close()

        # Store request_id in session
        session['request_id'] = request_id

        # Redirect to the status page with the unique request ID
        return redirect(url_for('main.check_status', request_id=request_id))

    return render_template('request.html', title="Request Document")

# Route for the admin panel
@main.route('/administration', methods=['GET', 'POST'])
def administration():
    if request.method == 'POST':
        # Get the request_id and the new status from the form
        request_id = request.form.get('request_id')
        new_status = request.form.get('status')

        # Update the status of the request in the database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''UPDATE requests SET status = ? WHERE request_id = ?''', (new_status, request_id))
        conn.commit()
        conn.close()

        # Flash a success message
        flash(f'Your demand has been {new_status.lower()}!', 'success')

        # Redirect back to the administration page to reflect changes
        return redirect(url_for('main.administration'))

    # If it's a GET request, show all requests as usual
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM requests')
    all_requests = c.fetchall()
    conn.close()

    return render_template('admin.html', all_requests=all_requests)

# Route to handle status checking of a request
@main.route('/check_status/<request_id>')
def check_status(request_id):
    if not request_id:
        # Flash a message and redirect to the request page if no ID is provided
        flash("Vous n'avez aucune requête.", 'warning')
        return redirect(url_for('main.request'))

    conn = get_db_connection()
    c = conn.cursor()

    # Retrieve request data based on the request_id
    c.execute('SELECT * FROM requests WHERE request_id = ?', (request_id,))
    request_data = c.fetchone()
    conn.close()

    if request_data is None:
        # If no request found, flash a message and redirect
        flash("Requête introuvable. Veuillez vérifier votre ID de requête.", 'warning')
        return redirect(url_for('main.request_document'))  # Or redirect to another page if desired

    # Convert Row to a dictionary for rendering
    request_data = dict(request_data)

    return render_template('status.html', request_data=request_data)


# Route to handle status updates (simplified)
@main.route('/update_request_status', methods=['POST'])
def update_request_status():
    request_id = request.form.get('request_id')
    new_status = request.form.get('status')

    # Update the status in the database
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE requests SET status = ? WHERE request_id = ?', (new_status, request_id))
    conn.commit()
    conn.close()

    # Flash success message
    flash(f'Your request has been updated to {new_status}.', 'success')

    return redirect(url_for('main.administration'))  # Redirect back to the admin page

# Route to download the document
@main.route('/download/<filename>')
def download_document(filename):
    # Send the file for download from the 'static/docs' directory
    return send_file(os.path.join(os.getcwd(), 'static', 'docs', filename), as_attachment=True)

UPLOAD_FOLDER = 'static/docs'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to upload the document
@main.route('/upload_document', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Ensure the directory exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # Save the file
        file.save(filepath)

        # Save the filename to the database
        request_id = request.form.get('request_id')
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''UPDATE requests SET filename = ? WHERE request_id = ?''', (filename, request_id))
        conn.commit()
        conn.close()

        # Flash a success message and send a JSON response
        flash(f'Document {filename} uploaded successfully!', 'success')
        return jsonify({"message": "Document uploaded successfully", "filename": filename})

    return jsonify({"error": "File not allowed"}), 400
    
# Initialize the database when the application starts
init_db()
