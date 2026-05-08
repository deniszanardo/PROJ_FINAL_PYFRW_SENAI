# frontend/app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from dotenv import load_dotenv

load_dotenv()  # carrega variáveis do .env se existir

API_URL = os.getenv("API_URL", "http://localhost:8000")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "troque_esta_chave")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Helpers
def api_headers():
    token = session.get("access_token")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def api_get(path, params=None):
    return requests.get(f"{API_URL}{path}", params=params, headers=api_headers())

def api_post(path, json_data):
    return requests.post(f"{API_URL}{path}", json=json_data, headers=api_headers())

def api_put(path, json_data):
    return requests.put(f"{API_URL}{path}", json=json_data, headers=api_headers())

def api_delete(path):
    return requests.delete(f"{API_URL}{path}", headers=api_headers())

# Rotas
@app.route("/")
def index():
    if "access_token" in session:
        return redirect(url_for("tasks"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = {
            "email": request.form["email"],
            "password": request.form["password"],
            "full_name": request.form.get("full_name", "")
        }
        resp = requests.post(f"{API_URL}/register", json=data)
        if resp.status_code == 200 or resp.status_code == 201:
            flash("Registrado com sucesso. Faça login.", "success")
            return redirect(url_for("login"))
        else:
            flash(f"Erro ao registrar: {resp.text}", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = {"email": request.form["email"], "password": request.form["password"]}
        resp = requests.post(f"{API_URL}/token", json=data)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            session["access_token"] = token
            flash("Logado com sucesso!", "success")
            return redirect(url_for("tasks"))
        else:
            flash("Login falhou: verifique email/senha", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu.", "info")
    return redirect(url_for("login"))

@app.route("/tasks")
def tasks():
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    skip = (page - 1) * size
    params = {"skip": skip, "limit": size}
    resp = api_get("/tasks", params=params)
    if resp.status_code == 200:
        tasks = resp.json()
    else:
        tasks = []
        flash(f"Erro ao buscar tarefas: {resp.text}", "danger")
    return render_template("tasks.html", tasks=tasks, page=page, size=size)

@app.route("/tasks/create", methods=["GET", "POST"])
def create_task():
    if request.method == "POST":
        data = {
            "title": request.form["title"],
            "description": request.form.get("description", ""),
            "status": request.form.get("status", "pending")
        }
        resp = api_post("/tasks", data)
        if resp.status_code in (200, 201):
            flash("Tarefa criada.", "success")
            return redirect(url_for("tasks"))
        else:
            flash(f"Erro ao criar tarefa: {resp.text}", "danger")
    return render_template("task_form.html", task=None)

@app.route("/tasks/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    # Para obter o detalhe, vamos solicitar um chunk maior e filtrar (se sua API tiver GET /tasks/{id}, prefira usá-lo)
    if request.method == "POST":
        data = {
            k: v for k, v in {
                "title": request.form.get("title"),
                "description": request.form.get("description"),
                "status": request.form.get("status")
            }.items() if v is not None and v != ""
        }
        resp = api_put(f"/tasks/{task_id}", data)
        if resp.status_code == 200:
            flash("Tarefa atualizada.", "success")
            return redirect(url_for("tasks"))
        else:
            flash(f"Erro ao atualizar: {resp.text}", "danger")

    # GET: buscar tarefa (simples: pegar varias e filtrar)
    resp = api_get("/tasks", params={"skip": 0, "limit": 200})
    task = None
    if resp.status_code == 200:
        for t in resp.json():
            if t.get("id") == task_id:
                task = t
                break
    if not task:
        flash("Tarefa não encontrada.", "warning")
        return redirect(url_for("tasks"))
    return render_template("task_form.html", task=task)

@app.route("/tasks/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    resp = api_delete(f"/tasks/{task_id}")
    if resp.status_code == 200:
        flash("Tarefa deletada.", "success")
    elif resp.status_code == 403:
        flash("Apenas administradores podem deletar tarefas.", "danger")
    else:
        flash(f"Erro ao deletar: {resp.text}", "danger")
    return redirect(url_for("tasks"))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("FLASK_PORT", 5000)))