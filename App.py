from flask import Flask, render_template, request, redirect, url_for, session, abort
from pymongo import MongoClient
from bson.objectid import ObjectId

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

@App.route("/login/all", methods=["GET", "POST"])
def find_all():
    if 'role' not in session:
        return redirect(url_for('login'))
    
    # Pagination logic
    page = int(request.args.get("page", 1))
    per_page = 10  # Number of tasks per page
    skip = (page - 1) * per_page

    sort_order = request.args.get("sort", "asc")
    sort_direction = 1 if sort_order == "asc" else -1
    total_tasks = tasks.count_documents({})
    all_tasks = list(tasks.find().sort("content", sort_direction).skip(skip).limit(per_page))

    total_pages = (total_tasks + per_page - 1) // per_page
    return render_template("index.html", all_tasks=all_tasks, page=page, total_pages=total_pages, sort_order=sort_order, username=session.get('username'), role=session.get('role'))

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

if __name__ == "__main__":
    App.run(debug=True, port=5000, use_reloader=False)
