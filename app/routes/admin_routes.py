from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.models import UserModel
from werkzeug.security import generate_password_hash
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

@admin_bp.before_request
def check_admin():
    """Garante que apenas administradores acessem as rotas"""
    if not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("main.dashboard"))

@admin_bp.route("/users")
def manage_users():
    users = UserModel.get_all_users()
    return render_template("admin/users.html", users=users)

@admin_bp.route("/users/create", methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        nome = request.form.get("nome")
        is_admin = request.form.get("is_admin") == "on"

        try:
            UserModel.create_user(
                email=email,
                password_hash=generate_password_hash(password),
                nome=nome,
                is_admin=is_admin
            )
            flash("Usuário criado com sucesso!", "success")
            return redirect(url_for("admin.manage_users"))
        except Exception as e:
            flash("Erro ao criar usuário.", "error")
            current_app.logger.error(f"Erro ao criar usuário: {str(e)}")
            return redirect(url_for("admin.manage_users"))

    # Se for GET → renderiza o formulário
    return render_template("admin/create_user.html")        

@admin_bp.route("/users/<user_id>/delete", methods=["POST"])
def delete_user(user_id):
    """Exclui um usuário do Supabase"""
    try:
        client = UserModel.get_client()
        client.table("users").delete().eq("id", user_id).execute()

        flash("Usuário excluído com sucesso!", "success")
    except Exception as e:
        flash("Erro ao excluir usuário.", "error")
        current_app.logger.error(f"Erro ao excluir usuário: {str(e)}")

    return redirect(url_for("admin.manage_users"))

@admin_bp.route("/toggle_user/<user_id>", methods=["POST"])
def toggle_user(user_id):
    """Ativa ou desativa um usuário via requisição AJAX"""
    from flask import jsonify
    if not session.get("is_admin"):
        return jsonify({"erro": "Acesso negado."}), 403

    ativo = request.json.get("ativo")
    try:
        UserModel.toggle_user_status(user_id, ativo)
        return jsonify({"sucesso": True, "status": ativo})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
