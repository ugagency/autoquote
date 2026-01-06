-- Script de inicialização do banco (para uso futuro)
CREATE SCHEMA IF NOT EXISTS autoquote;

-- Tabela para logs de execução do robô
CREATE TABLE IF NOT EXISTS autoquote.execution_logs (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50),
    data_coleta VARCHAR(6),
    events_collected INTEGER,
    excel_file_path VARCHAR(500),
    error_message TEXT
);