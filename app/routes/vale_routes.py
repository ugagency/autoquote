import os
import glob
import time
import traceback
from flask import Blueprint, jsonify, send_file, request, session
from app.services.vale_service import executar_robo_vale_async, EXECUCOES_ATIVAS

vale_bp = Blueprint("vale", __name__)

# ============================
# ESTADO DE EXECUÇÃO POR USUÁRIO
# ============================
status_usuarios = {}

def get_status_usuario(user_id):
    """Retorna ou inicializa o status do robô de um usuário específico"""
    if user_id not in status_usuarios:
        status_usuarios[user_id] = {
            "executando": False,
            "mensagem": "Pronto para executar",
            "progresso": 0,
        }
    return status_usuarios[user_id]


# ============================
# FUNÇÃO: BUSCAR PLANILHAS DO USUÁRIO
# ============================
def buscar_planilhas_vale(user_id):
    """Busca planilhas do usuário em /app/output/<user_id>/"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /app
    output_dir = os.path.join(base_dir, "output", str(user_id))

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    arquivos = glob.glob(os.path.join(output_dir, "planilha_vale_*.xlsx"))
    arquivos.sort(key=os.path.getmtime, reverse=True)
    return arquivos


# ============================
# ROTA: STATUS DO ROBÔ
# ============================
@vale_bp.route("/status")
def vale_status():
    """Retorna o status da execução e as planilhas recentes do usuário"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"erro": "Usuário não autenticado."}), 401

    status = get_status_usuario(user_id)

    # ✅ Detecta fim da execução automaticamente
    if status["executando"] and user_id not in EXECUCOES_ATIVAS:
        status.update({
            "executando": False,
            "mensagem": "✅ Robô finalizado com sucesso. Planilha disponível para download.",
            "progresso": 100
        })

    arquivos_vale = buscar_planilhas_vale(user_id)

    status["planilha_disponivel"] = len(arquivos_vale) > 0
    status["planilhas"] = [os.path.basename(a) for a in arquivos_vale[:5]]
    status["arquivo_recente"] = os.path.basename(arquivos_vale[0]) if arquivos_vale else None
    status["total_arquivos"] = len(arquivos_vale)

    return jsonify(status)


# ============================
# ROTA: EXECUTAR ROBÔ
# ============================
@vale_bp.route("/executar", methods=["POST"])
def vale_executar():
    """Executa o robô do Vale para o usuário logado"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"erro": "Usuário não autenticado."}), 401
    if user_id in EXECUCOES_ATIVAS:
        return jsonify({"erro": "Robô já está em execução para este usuário."}), 400

    data = request.get_json() or {}
    data_coleta = data.get("data_coleta")

    status = get_status_usuario(user_id)
    if status["executando"]:
        return jsonify({"erro": "Robô já está em execução"}), 400

    if not data_coleta or len(data_coleta) != 6:
        return jsonify({"erro": "Data inválida. Use o formato DDMMAA"}), 400

    status.update({
        "executando": True,
        "mensagem": f"🚀 Iniciando coleta para {data_coleta}...",
        "progresso": 0,
    })

    def log_callback(msg, progresso=None):
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [{user_id}] {msg}")
        status["mensagem"] = msg
        if progresso is not None:
            status["progresso"] = progresso

    executar_robo_vale_async(
        data_coleta=data_coleta,
        user_id=user_id,
        log_callback=log_callback
    )

    return jsonify({"mensagem": "Robô iniciado em segundo plano."}), 202


# ============================
# ROTA: DOWNLOAD PLANILHA (COM NOME DE ARQUIVO)
# ============================
@vale_bp.route("/download/<filename>")
def vale_download_file(filename):
    """Faz download de um arquivo específico do usuário"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"erro": "Usuário não autenticado."}), 401

        # Busca todas as planilhas do usuário
        arquivos_vale = buscar_planilhas_vale(user_id)
        
        # Encontra o arquivo específico
        arquivo_encontrado = None
        for arquivo in arquivos_vale:
            if os.path.basename(arquivo) == filename:
                arquivo_encontrado = arquivo
                break
        
        if not arquivo_encontrado:
            return jsonify({"erro": "Arquivo não encontrado."}), 404

        caminho_absoluto = os.path.abspath(arquivo_encontrado)

        if not os.path.exists(caminho_absoluto):
            return jsonify({"erro": f"Arquivo não encontrado: {caminho_absoluto}"}), 404

        print(f"📦 Enviando planilha: {caminho_absoluto}")
        return send_file(
            caminho_absoluto,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ Erro no download: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro no download: {str(e)}"}), 500

# ============================
# ROTA: DOWNLOAD ÚLTIMA PLANILHA (COMPATIBILIDADE)
# ============================
@vale_bp.route("/download")
def vale_download():
    """Faz download da planilha mais recente (para compatibilidade)"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"erro": "Usuário não autenticado."}), 401

        arquivos_vale = buscar_planilhas_vale(user_id)
        if not arquivos_vale:
            return jsonify({"erro": "Nenhuma planilha encontrada. Execute o robô primeiro."}), 404

        arquivo_recente = arquivos_vale[0]
        caminho_absoluto = os.path.abspath(arquivo_recente)
        filename = os.path.basename(arquivo_recente)

        if not os.path.exists(caminho_absoluto):
            return jsonify({"erro": f"Arquivo não encontrado: {caminho_absoluto}"}), 404

        print(f"📦 Enviando planilha mais recente: {caminho_absoluto}")
        return send_file(
            caminho_absoluto,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ Erro no download: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro no download: {str(e)}"}), 500

# ============================
# FIM DO ARQUIVO