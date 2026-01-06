from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import UserModel
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')  # Mudei de 'senha' para 'password'
        
        user = UserModel.get_user_by_email(email)
        print("🧩 Usuário retornado:", user)

        if not user.get("is_active", True):
         flash("Sua conta está desativada. Entre em contato com o administrador.", "error")
         return redirect(url_for("auth.login"))
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_nome'] = user['nome']
            session['is_admin'] = user['is_admin']
            session['user'] = user  # ← ADICIONAR ESTA LINHA
            
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Email ou senha incorretos!', 'error')
    
    return render_template('login.html')
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('auth.login'))
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = UserModel.get_user_by_email(email)

        if not user:
            flash("Email não encontrado!", "error")
        else:
            flash("Link de recuperação enviado (simulado).", "success")

    return render_template('forgot_password.html')