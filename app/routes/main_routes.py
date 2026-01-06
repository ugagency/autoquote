from flask import Blueprint, render_template, session, redirect, url_for, session, redirect, url_for, flash
from app.models import UserModel
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:  # Mudei de 'user' para 'user_id'
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', user=session['user'])  # Mantém 'user' aqui

@main_bp.before_request
def verificar_usuario_ativo():
    """Impede acesso se o usuário estiver desativado"""
    user_id = session.get("user_id")
    if user_id:
        user = UserModel.get_user_by_id(user_id)
        if user and not user.get("is_active", True):
            session.clear()
            flash("Sua conta foi desativada. Acesso bloqueado.", "error")
            return redirect(url_for("auth.login"))