import os
import re
import time
from datetime import datetime
from app.models import UserModel

def executar_robo_vale(data_coleta, user_id=None, log_callback=None):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from openpyxl import Workbook, load_workbook
    from webdriver_manager.chrome import ChromeDriverManager

    # ===============================
    # LOG SETUP
    # ===============================
    def log(msg, progresso=None):
        if log_callback:
            log_callback(msg, progresso)
        print(msg)

    # ===============================
    # CREDENCIAIS DO USUÁRIO (SUPABASE)
    # ===============================
    if not user_id:
        raise ValueError("❌ user_id é obrigatório para buscar as credenciais do Vale.")

    log("🔑 Buscando credenciais do Vale...", 5)
    config = UserModel.get_user_vale_config(user_id)

    if not config or not config.get("vale_email") or not config.get("vale_password"):
        raise ValueError("⚠️ Configurações do Vale não encontradas para este usuário.")

    # senha já vem descriptografada pelo UserModel
    USER = config["vale_email"]
    PASS = config["vale_password"]

    if not USER or not PASS:
        raise ValueError("⚠️ Credenciais inválidas ou ausentes.")

    log(f"✅ Credenciais carregadas para {USER}", 8)

    # ===============================
    # VALIDAÇÃO DA DATA
    # ===============================
    if not (data_coleta and len(data_coleta.strip()) == 6 and data_coleta.isdigit()):
        raise ValueError("Data inválida! Use o formato DDMMAA (ex: 191025).")

    HOJE_str = f"{data_coleta[:2]}/{data_coleta[2:4]}/{data_coleta[4:]}"
    HOJE = datetime.strptime(HOJE_str, "%d/%m/%y").date()
    log(f"📅 Executando coleta para {HOJE.strftime('%d/%m/%Y')}", 10)

    # ===============================
    # PREPARAÇÃO DE PLANILHA
    # ===============================
    filename = f"planilha_vale_{HOJE.strftime('%d%m%y')}.xlsx"
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'output',str(user_id))
    EXCEL_PATH = os.path.join(OUTPUT_DIR, filename)
    log(f"💾 Caminho do Excel: {EXCEL_PATH}")

    if os.path.exists(EXCEL_PATH):
        try:
            os.remove(EXCEL_PATH)
        except Exception as e:
            log(f"⚠️ Erro ao remover arquivo anterior: {e}")

    wb = Workbook()
    ws = wb.active
    ws.title = "Eventos"
    ws.append(["Número do evento", "UF(VALE)", "DATA", "DESCRIÇÃO", "QTDE", "UNID. MED", "Página de descrição"])
    wb.save(EXCEL_PATH)
    log("📗 Planilha inicial criada.", 15)

    # ===============================
    # CONFIGURAÇÃO DO SELENIUM
    # ===============================
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    base_driver_path = ChromeDriverManager().install()

    def find_chromedriver(base_path):
        if os.path.isfile(base_path) and "THIRD_PARTY_NOTICES" in base_path:
            base_path = os.path.dirname(base_path)
        possible_paths = [
            os.path.join(base_path, "chromedriver"),
            os.path.join(base_path, "chromedriver-linux64", "chromedriver"),
            os.path.join(os.path.dirname(base_path), "chromedriver"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        raise FileNotFoundError(f"Chromedriver não encontrado em: {possible_paths}")

    driver_path = find_chromedriver(base_driver_path)
    os.chmod(driver_path, 0o755)
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)
    log("🚀 Selenium WebDriver iniciado com sucesso.", 20)

    # ===============================
    # LOGIN NO PORTAL VALE
    # ===============================
    log("🌐 Acessando portal Vale...", 25)
    driver.get("https://vale.coupahost.com/sessions/supplier_login")

    wait.until(EC.presence_of_element_located((By.ID, "user_login")))
    driver.find_element(By.ID, "user_login").send_keys(USER)
    driver.find_element(By.ID, "user_password").send_keys(PASS, Keys.RETURN)
    log("🔐 Login efetuado com sucesso!", 30)


    # ===============================
    # BUSCA DE EVENTOS
    # ===============================
    # Clica no elemento de data duas vezes
    try:
        time_filter = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ch_start_time"]')))
        time_filter.click()
        time.sleep(5)
        time_filter = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ch_start_time"]')))
        time_filter.click()
    except:
        pass

    ESTADOS = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
        'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]

    def parse_date_str(s: str):
        """Tenta converter uma string em data válida"""
        if not s:
            return None
        s = s.strip()
        for fmt in ("%d/%m/%y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except:
                continue
        m = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', s)
        if m:
            for fmt in ("%d/%m/%y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(m.group(1), fmt).date()
                except:
                    continue
        return None

    encontrou_ontem = False
    total_eventos = 0

    log("🔎 Iniciando coleta de eventos...", 35)
    while True:
        time.sleep(2)
        try:
            tbody = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="quote_request_table_tag"]')))
        except Exception:
            log("⚠️ Não encontrou tabela de eventos. Encerrando coleta.")
            break

        linhas = tbody.find_elements(By.TAG_NAME, "tr")
        log(f"📊 {len(linhas)} linhas encontradas nesta página.")

        for linha in linhas:

            try:
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 7:
                    continue
                # pula a linha se existir o ícone amarelo (flag_yellow) em qualquer lugar da linha
                yellow_flags = linha.find_elements(By.CSS_SELECTOR, "img[src*='flag_yellow']")
                if yellow_flags:
                    print("Pulando linha porque contém flag_yellow")
                    continue

                data_inicio_str = colunas[2].text.strip()
                data_inicio = parse_date_str(data_inicio_str)
                if not data_inicio:
                    continue

                if data_inicio < HOJE:
                    encontrou_ontem = True
                    log("📆 Encontrou data anterior, encerrando varredura.")
                    break

                if data_inicio != HOJE:
                    continue

                numero_evento = colunas[0].find_element(By.TAG_NAME, "a").text.strip()
                data_final = colunas[3].text.strip()
                ws.append([numero_evento, '', data_final, '', '', '', ''])
                total_eventos += 1
            except Exception:
                continue

        wb.save(EXCEL_PATH)
        log(f"💾 {total_eventos} eventos coletados até agora.", 50)

        if encontrou_ontem:
            break

        try:
            proximo = driver.find_element(By.CLASS_NAME, "next_page")
            if "disabled" in proximo.get_attribute("class"):
                break
            driver.execute_script("arguments[0].scrollIntoView(true);", proximo)
            proximo.click()
        except Exception:
            break

    log("📄 Coleta principal concluída.", 60)

    # ===============================
    # DETALHAMENTO DE EVENTOS
    # ===============================
    try:
        wb = load_workbook(EXCEL_PATH)
        ws = wb["Eventos"]
    except Exception as e:
        driver.quit()
        log(f"❌ Falha ao abrir planilha: {e}")
        raise
    eventos_unicos = list(set([row[0].value for row in ws.iter_rows(min_row=2) if row[0].value]))
    total_eventos_detalhar = len(eventos_unicos)
    eventos_processados_global = 0

    log("🔍 Iniciando detalhamento dos eventos...", 70)
    for row in ws.iter_rows(min_row=2):
        evento = row[0].value
        if not evento:
            continue
        driver.get(f"https://vale.coupahost.com/quotes/external_responses/{evento}/edit")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # --- VERIFICA EXISTÊNCIA DA PÁGINA DE DESCRIÇÃO ---
        try:
            botoes1 = driver.find_elements(By.XPATH, '//*[@id="pageContentWrapper"]/div[3]/div[2]/a[2]/span')
            if not botoes1:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                botoes2 = driver.find_elements(By.ID, 'quote_response_submit')
                if botoes2:
                    botoes2[0].click()
        except Exception:
            row[6].value = "Erro ao verificar página de descrição"

        # Scroll e abre seção das informações
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "s-expandLines")))
        elementos = driver.find_elements(By.CLASS_NAME, "s-expandLines")

        if not elementos:
            print(f"⚠️ Nenhum s-expandLines encontrado no evento {evento}")
            continue

        # Duplicar a linha do evento pelo número de elementos encontrados
        linhas_evento = [row]
        if len(elementos) > 1:
            for i in range(len(elementos) - 1):
                nova_linha = [evento, row[1].value, row[2].value, '', '', '', '']
                ws.append(nova_linha)
            wb.save(EXCEL_PATH)
            linhas_evento = [r for r in ws.iter_rows(min_row=2) if r[0].value == evento]

        # Percorre cada s-expandLines e coleta os dados (re-fetch a cada iteração, marca processed via JS)
        def click_element_retry(el, attempts=4, pause=0.4):
            from selenium.common.exceptions import (
                StaleElementReferenceException,
                ElementClickInterceptedException,
                ElementNotInteractableException,
                WebDriverException,
            )
            for _ in range(attempts):
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.15)
                    el.click()
                    return True
                except (StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException, WebDriverException):
                    try:
                        driver.execute_script("arguments[0].click();", el)
                        return True
                    except Exception:
                        time.sleep(pause)
            return False

        # determina quantos existem no DOM no momento (evita usar lista obsoleta)
        total = driver.execute_script("return document.querySelectorAll('.s-expandLines').length")
        if total == 0:
            print(f"⚠️ Nenhum s-expandLines encontrado no evento {evento}")
            continue

        # duplicar linha já feito acima; garante linhas_evento atualizado
        linhas_evento = [r for r in ws.iter_rows(min_row=2) if r[0].value == evento]

        processed = 0
        max_attempts_per_index = 5
        idx = 0
        while processed < total and idx < total:
            # re-obtem a lista sempre
            try:
                elementos = driver.find_elements(By.CLASS_NAME, "s-expandLines")
            except Exception:
                time.sleep(0.3)
                elementos = driver.find_elements(By.CLASS_NAME, "s-expandLines")

            if idx >= len(elementos):
                # DOM encolheu — tenta refetch algumas vezes
                retry_try = 0
                while retry_try < 3 and idx >= len(elementos):
                    time.sleep(0.4)
                    elementos = driver.find_elements(By.CLASS_NAME, "s-expandLines")
                    retry_try += 1
                if idx >= len(elementos):
                    print(f"⚠️ Índice {idx} fora do range atual ({len(elementos)}). Pulando.")
                    idx += 1
                    continue

            el = elementos[idx]

            # evita re-processar elemento já marcado
            already = driver.execute_script("return arguments[0].getAttribute('data-processed')", el)
            if already:
                idx += 1
                processed += 1
                continue

            # tenta clicar de forma robusta
            if not click_element_retry(el, attempts=4, pause=0.4):
                print(f"⚠️ Falha ao clicar no expandLines index {idx} do evento {evento}")
                # marca como processado para não travar loop
                try:
                    driver.execute_script("arguments[0].setAttribute('data-processed','1')", el)
                except Exception:
                    pass
                idx += 1
                processed += 1
                continue

            # após clique, espera conteúdo de detalhe carregar (xpath de descrição)
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="itemsAndServicesApp"]/div/div/div[1]')))
                time.sleep(0.25)
            except Exception:
                time.sleep(0.4)

            # atualiza linhas_evento porque podem ter sido adicionadas
            linhas_evento = [r for r in ws.iter_rows(min_row=2) if r[0].value == evento]
            try:
                linha_atual = linhas_evento[idx]
            except Exception:
                # se não existir, tenta mapear para próxima disponível
                if linhas_evento:
                    linha_atual = linhas_evento[-1]
                else:
                    print(f"⚠️ Não há linha disponível para evento {evento} no idx {idx}")
                    # marca e segue
                    try:
                        driver.execute_script("arguments[0].setAttribute('data-processed','1')", el)
                    except Exception:
                        pass
                    idx += 1
                    processed += 1
                    continue

            # coleta campos (mesma lógica, com pequenos waits)
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="itemsAndServicesApp"]/div/div/div[1]/div[2]/div[2]/div/form/div/div/div[2]/div/div[2]/div/p/span[1]')))
            except Exception:
                time.sleep(1)
            try:
                quantidade_el = driver.find_element(By.XPATH, '//*[@id="itemsAndServicesApp"]/div/div/div[1]/div[2]/div[2]/div/form/div/div/div[2]/div/div[2]/div/p/span[1]')
                linha_atual[4].value = quantidade_el.text
            except Exception:
                linha_atual[4].value = 'Não foi possivel coletar a quantidade'

            try:
                unidade_el = driver.find_element(By.XPATH, '//*[@id="itemsAndServicesApp"]/div/div/div[1]/div[2]/div[2]/div/form/div/div/div[2]/div/div[2]/div/p/span[2]')
                linha_atual[5].value = unidade_el.text
            except Exception:
                linha_atual[5].value = 'Não foi possivel coletar a unidade'

            try:
                descri_el = driver.find_element(By.XPATH, '//*[@id="itemsAndServicesApp"]/div/div/div[1]/div[2]/div[2]/div/form/div/div/div[1]/div/div[2]/div/p')
                descri = descri_el.text
                desejado = re.search(r'PT\s*\|\|\s*(.*?)\*{3,}', descri, re.DOTALL)
                linha_atual[3].value = desejado.group(1).strip() if desejado else descri
            except Exception:
                linha_atual[3].value = 'Não foi possivel coletar a descrição'

            # UF (versão mais robusta)
            try:
                uf_spans = driver.find_elements(
                    By.XPATH,
                    '//*[@id="itemsAndServicesApp"]/div/div/div[1]/div[2]/div[2]/div/form/div/div/div[1]/div/div[8]/div/ul/li/span'
                )

                found = None
                # tenta primeiro padrão explícito "- XX - BR" em cada span
                for elem in uf_spans:
                    text = (elem.text or "").strip().upper()
                    if not text:
                        continue
                    m = re.search(r'-\s*([A-Z]{2})\s*-\s*BR', text)
                    if m and m.group(1) in ESTADOS:
                        found = m.group(1)
                        break
                    # procura tokens isolados de 2 letras e valida contra ESTADOS
                    tokens = re.findall(r'\b[A-Z]{2}\b', text)
                    for t in tokens:
                        if t in ESTADOS:
                            found = t
                            break
                    if found:
                        break

                # fallback: junta todo o texto e procura por siglas com bordas de palavra
                if not found:
                    combined = " ".join([(e.text or "") for e in uf_spans]).upper()
                    for sig in ESTADOS:
                        if re.search(r'\b' + re.escape(sig) + r'\b', combined):
                            found = sig
                            break

                linha_atual[1].value = found if found else 'UF não encontrada'
            except Exception:
                linha_atual[1].value = 'Não foi possivel coletar a UF'

            # fecha o detalhe (tenta vários métodos)
            try:
                time.sleep(0.2)
                fechar = None
                try:
                    fechar = driver.find_element(By.CSS_SELECTOR, "button.button.s-cancel")
                except Exception:
                    try:
                        fechar = driver.find_element(By.XPATH, "//button[contains(concat(' ', normalize-space(@class), ' '), ' s-cancel ') and contains(., 'Cancelar')]")
                    except Exception:
                        fechar = None
                if fechar:
                    click_element_retry(fechar, attempts=3, pause=0.2)
                    time.sleep(0.25)
            except Exception:
                pass

            # marca como processado (para não reprocessar se DOM reorganizar)
            try:
                driver.execute_script("arguments[0].setAttribute('data-processed','1')", el)
            except Exception:
                pass

            processed += 1
            idx += 1
            progresso_global = 70 + int(25 * (eventos_processados_global / total_eventos_detalhar))
            log(f"📝 Detalhado evento {evento} ({eventos_processados_global}/{total_eventos_detalhar})", progresso_global)
         
        

        wb.save(EXCEL_PATH)

    log("📘 Detalhamento concluído.", 95)

    try:
        wb.save(EXCEL_PATH)
        driver.quit()
        log(f"✅ Robô finalizado com {total_eventos} eventos coletados.", 100)
    except Exception as e:
        log(f"⚠️ Finalização com erro: {e}")

    return {
        "sucesso": True,
        "arquivo": filename,
        "eventos_coletados": total_eventos,
        "logs": f"Execução concluída com {total_eventos} eventos coletados."
    }

import threading
import tempfile
import shutil
import os
from app import create_app

# controle de execuções ativas
EXECUCOES_ATIVAS = {}

def executar_robo_vale_async(data_coleta, user_id, log_callback=None):
    """Executa o robô do Vale em thread separada e isolada por usuário."""
    app = create_app()

    # não deixar dois robôs do mesmo usuário rodarem
    if user_id in EXECUCOES_ATIVAS:
        print(f"⚠️ Robô já em execução para user_id={user_id}. Ignorando nova chamada.")
        return

    def tarefa():
        temp_dir = tempfile.mkdtemp(prefix=f"vale_{user_id[:6]}_")
        os.environ["WDM_LOCAL"] = temp_dir  # força webdriver_manager a usar pasta isolada
        print(f"🧵 [Thread-{user_id[:6]}] Iniciando robô no diretório {temp_dir}")

        try:
            with app.app_context():
                EXECUCOES_ATIVAS[user_id] = True
                from app.services.vale_service import executar_robo_vale
                executar_robo_vale(
                    data_coleta=data_coleta,
                    user_id=user_id,
                    log_callback=log_callback
                )
        except Exception as e:
            print(f"❌ [Thread-{user_id[:6]}] Erro: {e}")
            import traceback
            traceback.print_exc()
        finally:
            EXECUCOES_ATIVAS.pop(user_id, None)
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🧹 [Thread-{user_id[:6]}] Finalizou e limpou {temp_dir}")

    thread = threading.Thread(target=tarefa, daemon=True)
    thread.start()

