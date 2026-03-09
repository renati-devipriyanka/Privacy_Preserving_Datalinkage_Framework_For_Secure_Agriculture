from flask import Flask, render_template_string, request, redirect, url_for
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash
import subprocess
import sys
import os

# IMPORT detection function from main ML framework
from ppdp import detect_sensitive_attributes

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATASET_PATH = ""

# create user file if not exists
if not os.path.exists("users.csv"):
    pd.DataFrame(columns=["username","password"]).to_csv("users.csv",index=False)

# ---------------- LOGIN PAGE ---------------- #

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Login</title>
<style>
body{
margin:0;
font-family:Arial;
height:100vh;
background:url("https://images.unsplash.com/photo-1500382017468-9049fed747ef");
background-size:cover;
display:flex;
justify-content:center;
align-items:center;
}
.card{
background:rgba(255,255,255,0.95);
padding:40px;
width:350px;
border-radius:12px;
text-align:center;
box-shadow:0 10px 25px rgba(0,0,0,0.4);
}
input{
width:90%;
padding:10px;
margin:10px 0;
}
button{
padding:10px 20px;
background:#2E7D32;
color:white;
border:none;
border-radius:6px;
cursor:pointer;
}
button:hover{
background:#1B5E20;
}
</style>
</head>
<body>
<div class="card">
<h2>🌾 Privacy-Preserving Agriculture Framework</h2>
<form method="post">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<br>
<button>Login</button>
</form>
<br>
<a href="/register">Register</a>
<p style="color:red;">{{error}}</p>
</div>
</body>
</html>
"""

# ---------------- REGISTER PAGE ---------------- #

REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Register</title>
<style>
body{
margin:0;
font-family:Arial;
height:100vh;
background:url("https://images.unsplash.com/photo-1500382017468-9049fed747ef");
background-size:cover;
display:flex;
justify-content:center;
align-items:center;
}
.card{
background:white;
padding:40px;
width:350px;
border-radius:12px;
text-align:center;
box-shadow:0 10px 25px rgba(0,0,0,0.4);
}
input{
width:90%;
padding:10px;
margin:10px 0;
}
button{
padding:10px 20px;
background:#2E7D32;
color:white;
border:none;
border-radius:6px;
cursor:pointer;
}
</style>
</head>
<body>
<div class="card">
<h2>Create Account</h2>
<form method="post">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<br>
<button>Register</button>
</form>
<br>
<a href="/">Back to Login</a>
<p style="color:red;">{{error}}</p>
</div>
</body>
</html>
"""

# ---------------- DASHBOARD ---------------- #

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Dashboard</title>
<style>
body{
margin:0;
font-family:Arial;
background:url("https://images.unsplash.com/photo-1500382017468-9049fed747ef");
background-size:cover;
}
.container{
background:rgba(255,255,255,0.95);
padding:40px;
width:700px;
margin:auto;
margin-top:80px;
border-radius:12px;
box-shadow:0 10px 25px rgba(0,0,0,0.4);
}
button{
margin-top:10px;
padding:10px 20px;
background:#2E7D32;
color:white;
border:none;
border-radius:6px;
cursor:pointer;
}
textarea{
width:100%;
height:120px;
margin-top:15px;
}
</style>
</head>
<body>

<div class="container">

<h2>🌾 Agriculture Research Dashboard</h2>

<form method="post" enctype="multipart/form-data">

<h3>Upload Dataset</h3>
<input type="file" name="dataset">
<br>
<button name="action" value="upload">Upload Dataset</button>

<br><br>

<button name="action" value="load">Load Attributes</button>

{% if columns %}

<h3>Select Sensitive Attributes</h3>

{% for col in columns %}

<input type="checkbox" name="sensitive" value="{{col}}"
{% if col in detected %}checked{% endif %}>
{{col}}<br>

{% endfor %}

<br>

<button name="action" value="run">
Run Privacy Processing
</button>

{% endif %}

</form>

<textarea readonly>{{result}}</textarea>

</div>

</body>
</html>
"""

# ---------------- LOGIN ROUTE ---------------- #

@app.route("/",methods=["GET","POST"])
def login():

    error=""

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        users=pd.read_csv("users.csv")
        user=users[users["username"]==username]

        if not user.empty:

            stored=user.iloc[0]["password"]

            if check_password_hash(stored,password):
                return redirect(url_for("dashboard"))
            else:
                error="Invalid password"

        else:
            error="User not found"

    return render_template_string(LOGIN_HTML,error=error)

# ---------------- REGISTER ROUTE ---------------- #

@app.route("/register",methods=["GET","POST"])
def register():

    error=""

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        users=pd.read_csv("users.csv")

        if username in users["username"].values:
            error="User already exists"
        else:

            hashed=generate_password_hash(password)

            new_user=pd.DataFrame([[username,hashed]],
                                  columns=["username","password"])

            users=pd.concat([users,new_user],ignore_index=True)
            users.to_csv("users.csv",index=False)

            return redirect(url_for("login"))

    return render_template_string(REGISTER_HTML,error=error)

# ---------------- DASHBOARD ROUTE ---------------- #

@app.route("/dashboard",methods=["GET","POST"])
def dashboard():

    global DATASET_PATH

    columns=[]
    detected=[]
    result=""

    if request.method=="POST":

        action=request.form["action"]

        # Upload dataset
        if action=="upload":

            file=request.files["dataset"]

            if file.filename!="":

                DATASET_PATH=os.path.join(UPLOAD_FOLDER,file.filename)
                file.save(DATASET_PATH)

                result="Dataset uploaded successfully."

        # Load attributes
        elif action=="load":

            if DATASET_PATH=="":

                result="Upload dataset first."

            else:

                df=pd.read_csv(DATASET_PATH,nrows=1)
                columns=df.columns.tolist()

                # CALL MAIN PROGRAM DETECTION
                detected=detect_sensitive_attributes(DATASET_PATH)

        # Run processing
        elif action=="run":

            selected=request.form.getlist("sensitive")
            sensitive_arg=",".join(selected)

            subprocess.run(
                [sys.executable,"ppdp.py",DATASET_PATH,sensitive_arg],
                check=True
            )

            result="Processing completed successfully."

            df=pd.read_csv(DATASET_PATH,nrows=1)
            columns=df.columns.tolist()

            detected=detect_sensitive_attributes(DATASET_PATH)

    return render_template_string(
        DASHBOARD_HTML,
        columns=columns,
        detected=detected,
        result=result
    )

# ---------------- RUN SERVER ---------------- #

if __name__=="__main__":
    app.run(debug=True)