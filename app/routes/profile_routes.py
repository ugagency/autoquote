from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import UserModel

profile_bp = Blueprint("profile", __name__)

# --------------------------
# Página de Configuração
# --------------------------
@profile_bp.route("/", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    vale_config = UserModel.get_user_vale_config(user_id)

    if request.method == "POST":
        vale_email = request.form.get("vale_email")
        vale_password = request.form.get("vale_password")

        try:
            UserModel.update_user_vale_config(user_id, vale_email, vale_password)
            flash("Configurações do Vale atualizadas com sucesso!", "success")
            return redirect(url_for("profile.profile"))
        except Exception as e:
            flash("Erro ao salvar configurações.", "error")
            current_app.logger.error(f"Erro ao salvar config Vale: {str(e)}")

    return render_template("profile.html", vale_config=vale_config)


# --------------------------
# Alterar Senha do AutoQuote
# --------------------------
@profile_bp.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        flash("Usuário não autenticado.", "danger")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    senha_atual = request.form.get("senha_atual")
    nova_senha = request.form.get("nova_senha")
    confirmar_senha = request.form.get("confirmar_senha")

    if not senha_atual or not nova_senha or not confirmar_senha:
        flash("Preencha todos os campos.", "warning")
        return redirect(url_for("profile.profile"))

    if nova_senha != confirmar_senha:
        flash("As senhas não conferem.", "danger")
        return redirect(url_for("profile.profile"))

    # Busca o usuário atual
    user = UserModel.get_user_by_id(user_id)
    if not user:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], senha_atual):
        flash("Senha atual incorreta.", "danger")
        return redirect(url_for("profile.profile"))

    # Atualiza senha no banco
    nova_hash = generate_password_hash(nova_senha)
    UserModel.update_password(user_id, nova_hash)

    flash("Senha atualizada com sucesso!", "success")
    return redirect(url_for("profile.profile"))
