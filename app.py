from flask import Flask, render_template_string, request, redirect, url_for
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash
import subprocess
import sys
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATASET_PATH = ""

keywords = [
    'state','district','region','location',
    'crop','commodity',
    'area','land',
    'production','yield',
    'income','price',
    'id','number'
]

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
animation:fadeIn 1s ease;
}

@keyframes fadeIn{
from{opacity:0; transform:translateY(40px);}
to{opacity:1; transform:translateY(0);}
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

<h2>🌾 Privacy-Preserving Datalinkage Framework for Secure Agriculture Research</h2>

<form method="post">

<input name="username" placeholder="Username" required>

<input name="password" type="password" placeholder="Password" required>

<br>

<button>Login</button>

</form>

<br>

<a href="/register">Register New User</a>

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
background:rgba(255,255,255,0.95);
padding:40px;
width:350px;
border-radius:12px;
text-align:center;
box-shadow:0 10px 25px rgba(0,0,0,0.4);
animation:fadeIn 1s ease;
}

@keyframes fadeIn{
from{opacity:0; transform:translateY(40px);}
to{opacity:1; transform:translateY(0);}
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

<h2>Create New Account</h2>

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
height:100vh;
background:url("https://images.unsplash.com/photo-1500382017468-9049fed747ef");
background-size:cover;
overflow:hidden;
}

.overlay{
background:rgba(0,0,0,0.5);
height:100vh;
display:flex;
justify-content:center;
align-items:center;
}

.container{
background:rgba(255,255,255,0.95);
padding:40px;
width:700px;
border-radius:12px;
text-align:left;
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

button:hover{
background:#1B5E20;
}

textarea{
width:100%;
height:120px;
margin-top:15px;
}

/* spinner */

.spinner{
border:6px solid #f3f3f3;
border-top:6px solid #2E7D32;
border-radius:50%;
width:50px;
height:50px;
animation:spin 1s linear infinite;
margin:auto;
}

@keyframes spin{
0%{transform:rotate(0deg);}
100%{transform:rotate(360deg);}
}

/* floating leaves */

.leaf{
position:absolute;
width:20px;
height:20px;
background:green;
border-radius:50%;
opacity:0.5;
animation:float 12s infinite linear;
}

@keyframes float{
0%{transform:translateY(100vh);}
100%{transform:translateY(-10vh);}
}

</style>

</head>

<body>

<div class="leaf" style="left:10%;animation-delay:0s;"></div>
<div class="leaf" style="left:30%;animation-delay:2s;"></div>
<div class="leaf" style="left:60%;animation-delay:5s;"></div>

<div class="overlay">

<div class="container">

<h2>🌾 Agriculture Research</h2>

<div id="loading" style="display:none;text-align:center;">

<div class="spinner"></div>

<p style="color:#2E7D32;font-weight:bold;">
Processing dataset... Please wait
</p>

</div>

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

<button name="action" value="run" onclick="showSpinner()">
Run Privacy Processing
</button>

{% endif %}

</form>

<textarea readonly>{{result}}</textarea>

</div>

</div>

<script>

function showSpinner(){
document.getElementById("loading").style.display="block";
}

</script>

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

        if action=="upload":

            file=request.files["dataset"]

            if file.filename!="":

                DATASET_PATH=os.path.join(UPLOAD_FOLDER,file.filename)

                file.save(DATASET_PATH)

                result="Dataset uploaded successfully."

        elif action=="load":

            if DATASET_PATH=="":

                result="Upload dataset first."

            else:

                df=pd.read_csv(DATASET_PATH,nrows=1)

                columns=df.columns.tolist()

                detected=[
                    c for c in columns
                    if any(k in c.lower() for k in keywords)
                ]

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

            detected=[
                c for c in columns
                if any(k in c.lower() for k in keywords)
            ]

    return render_template_string(
        DASHBOARD_HTML,
        columns=columns,
        detected=detected,
        result=result
    )

# ---------------- RUN SERVER ---------------- #

if __name__=="__main__":
    app.run(debug=True)