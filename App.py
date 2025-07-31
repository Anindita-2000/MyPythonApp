from flask import Flask, render_template, request, redirect, url_for, session, abort, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
import pandas as pd
import io
import re
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

print("XlsxWriter is installed and ready to use!")

App = Flask(__name__)
App.secret_key = 'your_secret_key'  # Required for session management

# MongoDB connection
uri = "mongodb+srv://Anindita_Das:Ani2000@myapp.iqxwi6f.mongodb.net/"
client = MongoClient(uri)
db = client["taskdb"]
tasks = db["tasks"]
print("Connected to MongoDB")

# Dummy credentials with roles
USERS = {
    'admin': {'password': 'pass123', 'role': 'admin'},
    'moderator': {'password': 'pass1234', 'role': 'moderator'}
}

@App.route('/')
def home():
    return redirect(url_for('login'))

@App.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = USERS.get(username)
        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            return render_template('welcome.html', username=username, role=user['role'])
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

@App.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@App.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    if request.method == 'POST':
        username = request.form['username']
        user = USERS.get(username)
        if user:
            session['reset_user'] = username
            return redirect(url_for('reset_password'))
        else:
            message = 'Username not found.'
    return render_template('forgot_password.html', message=message)

def is_valid_password(password):
    pattern = r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{6,}$'
    return re.match(pattern, password)

@App.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user' not in session:
        return redirect(url_for('login'))

    message = None
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            message = '❌ Passwords do not match.'
        elif not is_valid_password(new_password):
            message = '❌ Password must be at least 6 characters long and include at least one digit, one uppercase letter, and one lowercase letter.'
        else:
            username = session['reset_user']
            USERS[username]['password'] = new_password
            session.pop('reset_user', None)
            return redirect(url_for('login'))

    return render_template('reset_password.html', message=message)

@App.route("/login/all", methods=["GET", "POST"])
def find_all():
    if 'role' not in session:
        return redirect(url_for('login'))

    page = int(request.args.get("page", 1))
    per_page = 10
    skip = (page - 1) * per_page

    sort_order = request.args.get("sort", "asc")
    sort_direction = 1 if sort_order == "asc" else -1
    total_tasks = tasks.count_documents({})
    all_tasks = list(tasks.find().sort("content", sort_direction).skip(skip).limit(per_page))

    total_pages = (total_tasks + per_page - 1) // per_page
    return render_template("index.html", all_tasks=all_tasks, page=page, total_pages=total_pages,
                           sort_order=sort_order, username=session.get('username'), role=session.get('role'))

@App.route("/add", methods=["GET", "POST"])
def add_task():
    if session.get('role') != 'admin':
        abort(403)
    if request.method == "POST":
        task_id = ObjectId()
        tasks.insert_one({
            "_id": task_id,
            "content": request.form.get("content"),
            "company": request.form.get("company"),
            "email": request.form.get("email"),
            "name": request.form.get("name"),
            "notice_period": request.form.get("notice_period"),
            "salary": request.form.get("salary")
        })
        return render_template("success.html")
    return render_template("add.html", tasks=tasks)

@App.route("/find/<task_id>", methods=["GET", "POST"])
def find_task(task_id):
    if 'role' not in session:
        return redirect(url_for('login'))
    user = tasks.find_one({"_id": ObjectId(task_id)})
    return render_template("find.html", tasks=[user])

@App.route("/login/findbyname", methods=["GET", "POST"])
def find_task_by_name():
    if session.get('role') not in ['admin', 'moderator']:
        abort(403)
    if request.method == "POST":
        name = request.form.get("name")
        user = tasks.find({"name": name})
        return render_template("findbyname.html", tasks=user)
    return redirect("/login")

@App.route("/delete/<task_id>", methods=["POST", "DELETE"])
def delete_task(task_id):
    if session.get('role') != 'admin':
        abort(403)
    tasks.delete_one({"_id": ObjectId(task_id)})
    return redirect("/login/all")

@App.route("/update/<task_id>", methods=["POST", "GET", "PUT"])
def update_task(task_id):
    if session.get('role') != 'admin':
        abort(403)
    task = tasks.find_one({"_id": ObjectId(task_id)})
    if request.method == "POST":
        updated_fields = {
            "content": request.form.get("content"),
            "company": request.form.get("company"),
            "email": request.form.get("email"),
            "name": request.form.get("name"),
            "notice_period": request.form.get("notice_period"),
            "salary": request.form.get("salary")
        }
        tasks.update_one({"_id": ObjectId(task_id)}, {"$set": updated_fields})
        return render_template("success.html")
    return render_template("update.html", task=task)

# Download content list as Excel file
@App.route("/download-tasks")
def download_tasks():
    if 'role' not in session:
        return redirect(url_for('login'))
    task_list = list(tasks.find())
    for task in task_list:
        task['_id'] = str(task['_id'])
    # Sort by 'content' in excel
    task_list.sort(key=lambda x: x.get('content', ''))
    df = pd.DataFrame(task_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Tasks')
    output.seek(0)
    return send_file(output, download_name="task_details.xlsx", as_attachment=True)

# Download content list as PDF file
@App.route('/download-tasks-pdf')
def download_tasks_pdf():
    if 'role' not in session:
        return redirect(url_for('login'))
    task_list = list(tasks.find())
    for task in task_list:
        task['_id'] = str(task['_id'])
    # Sort by 'content' in pdf
    task_list.sort(key=lambda x: x.get('content', ''))
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y, "Content Details")
    y -= 30
    c.setFont("Helvetica", 10)
    serial = 1
    for task in task_list:
        c.drawString(40, y, f"{serial}. Content: {task.get('content', '')}")
        y -= 15
        c.drawString(40, y, f"Company: {task.get('company', '')}")
        y -= 15
        c.drawString(40, y, f"Email: {task.get('email', '')}")
        y -= 15
        c.drawString(40, y, f"Name: {task.get('name', '')}")
        y -= 15
        c.drawString(40, y, f"Notice Period: {task.get('notice_period', '')}")
        y -= 15
        c.drawString(40, y, f"Salary: {task.get('salary', '')}")
        y -= 20
        serial += 1
        if y < 60:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 10)
    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name="task_details.pdf", as_attachment=True)

if __name__ == "__main__":
    App.run(debug=True, port=5000, use_reloader=False)
