import supabase
from flask import current_app
from datetime import datetime, timedelta
import secrets
from cryptography.fernet import Fernet
import base64
import hashlib

class Database:
    _instance = None
    
    @classmethod
    def get_client(cls):
        if cls._instance is None:
            cls._instance = supabase.create_client(
                current_app.config['SUPABASE_URL'],
                current_app.config['SUPABASE_KEY']
            )
        return cls._instance


class UserModel:
    
    # ============================
    # Criptografia de Senha Vale
    # ============================
    @staticmethod
    def encrypt_password(password: str) -> str:
        """Criptografa senha do Vale"""
        secret_key = current_app.config['SECRET_KEY']
        key = hashlib.pbkdf2_hmac('sha256', secret_key.encode(), b'salt', 100000, 32)
        fernet_key = base64.urlsafe_b64encode(key)
        fernet = Fernet(fernet_key)
        return fernet.encrypt(password.encode()).decode()

    @staticmethod
    def decrypt_password(encrypted_password: str) -> str:
        """Descriptografa senha do Vale"""
        secret_key = current_app.config['SECRET_KEY']
        key = hashlib.pbkdf2_hmac('sha256', secret_key.encode(), b'salt', 100000, 32)
        fernet_key = base64.urlsafe_b64encode(key)
        fernet = Fernet(fernet_key)
        return fernet.decrypt(encrypted_password.encode()).decode()

    # ============================
    # Usuários
    # ============================
    @staticmethod
    def create_user(email: str, password_hash: str, nome: str, is_admin=False):
        client = Database.get_client()
        try:
            result = client.table('users').insert({
                'email': email,
                'password_hash': password_hash,
                'nome': nome,
                'is_admin': is_admin
            }).execute()
            return result
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")
            raise

    @staticmethod
    def get_user_by_email(email: str):
        client = Database.get_client()
        try:
            response = client.table('users').select('*').eq('email', email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao buscar usuário: {e}")
            return None

    @staticmethod
    def get_user_by_id(user_id: str):
        client = Database.get_client()
        try:
            response = client.table('users').select('*').eq('id', user_id).eq('is_active', True).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao buscar usuário por ID: {e}")
            return None

    # ============================
    # Configuração do Vale
    # ============================
    @staticmethod
    def update_user_vale_config(user_id: str, vale_email: str, vale_password: str):
        client = Database.get_client()
        try:
            existing = client.table('user_vale_config').select('*').eq('user_id', user_id).execute()
            encrypted_password = UserModel.encrypt_password(vale_password)
            
            if existing.data:
                return client.table('user_vale_config').update({
                    'vale_email': vale_email,
                    'vale_password': encrypted_password,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('user_id', user_id).execute()
            else:
                return client.table('user_vale_config').insert({
                    'user_id': user_id,
                    'vale_email': vale_email,
                    'vale_password': encrypted_password
                }).execute()
        except Exception as e:
            print(f"Erro ao atualizar config Vale: {e}")
            raise

    @staticmethod
    def get_user_vale_config(user_id: str):
        client = Database.get_client()
        try:
            response = client.table('user_vale_config').select('*').eq('user_id', user_id).execute()
            if response.data:
                config = response.data[0]
                try:
                    config['vale_password'] = UserModel.decrypt_password(config['vale_password'])
                except:
                    config['vale_password'] = None
                return config
            return None
        except Exception as e:
            print(f"Erro ao buscar config Vale: {e}")
            return None

    # ============================
    # Administração / Logs
    # ============================
    @staticmethod
    def get_all_users():
        client = Database.get_client()
        try:
            response = client.table('users').select('*').order('created_at', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Erro ao buscar usuários: {e}")
            return []

    @staticmethod
    def create_password_reset_token(user_id: str):
        client = Database.get_client()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        try:
            client.table('password_reset_tokens').insert({
                'user_id': user_id,
                'token': token,
                'expires_at': expires_at.isoformat()
            }).execute()
            return token
        except Exception as e:
            print(f"Erro ao criar token: {e}")
            raise

    @staticmethod
    def validate_reset_token(token: str):
        client = Database.get_client()
        try:
            response = client.table('password_reset_tokens')\
                .select('*')\
                .eq('token', token)\
                .eq('used', False)\
                .gt('expires_at', datetime.utcnow().isoformat())\
                .execute()
            
            if response.data:
                token_data = response.data[0]
                user = UserModel.get_user_by_id(token_data['user_id'])
                if user:
                    token_data['users'] = {'email': user['email'], 'nome': user['nome']}
                return token_data
            return None
        except Exception as e:
            print(f"Erro ao validar token: {e}")
            return None

    @staticmethod
    def use_reset_token(token: str):
        client = Database.get_client()
        try:
            return client.table('password_reset_tokens').update({'used': True}).eq('token', token).execute()
        except Exception as e:
            print(f"Erro ao usar token: {e}")
            raise

    @staticmethod
    def create_execution_log(user_id: str, data_coleta: str):
        client = Database.get_client()
        try:
            response = client.table('execution_logs').insert({
                'user_id': user_id,
                'data_coleta': data_coleta,
                'status': 'running'
            }).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            print(f"Erro ao criar log: {e}")
            return None

    @staticmethod
    def update_execution_log(log_id: str, **kwargs):
        client = Database.get_client()
        try:
            return client.table('execution_logs').update(kwargs).eq('id', log_id).execute()
        except Exception as e:
            print(f"Erro ao atualizar log: {e}")
            raise

    @staticmethod
    def get_user_execution_logs(user_id: str, limit=50):
        client = Database.get_client()
        try:
            response = client.table('execution_logs')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('start_time', desc=True)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Erro ao buscar logs: {e}")
            return []

    # ============================
    # Atualização de Senha AutoQuote
    # ============================
    @staticmethod
    def update_password(user_id, new_hash):
        """Atualiza a senha do usuário no Supabase."""
        client = Database.get_client()
        try:
            response = (
                client.table("users")
                .update({"password_hash": new_hash})
                .eq("id", user_id)
                .execute()
            )
            print(f"✅ Senha atualizada com sucesso para user_id={user_id}")
            return response
        except Exception as e:
            print(f"❌ Erro ao atualizar senha: {e}")
            raise

    # ============================
    # Ativar / Desativar Usuário
    # ===========================    
    @staticmethod
    def toggle_user_status(user_id: str, ativo: bool):
     client = Database.get_client()
     try:
        return client.table("users").update({"is_active": ativo}).eq("id", user_id).execute()
     except Exception as e:
        print(f"Erro ao alterar status: {e}")
        raise
    