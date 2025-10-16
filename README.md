# Hotmart Account Checker & Data Extractor

Um script assíncrono em Python que utiliza Playwright para automatizar o login em contas da Hotmart, verificar seu status e extrair dados de perfil e cursos. O script é projetado para ser robusto, salvando o progresso e gerenciando diferentes tipos de falhas de forma organizada.


## ⚠️ Aviso Legal e Isenção de Responsabilidade

**LEIA ESTA SEÇÃO COM ATENÇÃO ANTES DE USAR O SCRIPT.**

1.  **Uso Pessoal e Educacional:** Este script foi criado estritamente para fins educacionais e para uso pessoal em contas que **você possui** ou para as quais tem **permissão explícita** do proprietário para testar.

2.  **Sem Afiliação:** Este projeto não é afiliado, endossado ou patrocinado pela Hotmart.

3.  **Risco e Responsabilidade:** O uso deste script é de **sua inteira responsabilidade**. O autor não se responsabiliza por quaisquer consequências negativas que possam surgir do seu uso, incluindo, mas não se limitando a:
    *   **Bloqueio ou suspensão da sua conta** pela plataforma.
    *   **Banimento do seu endereço de IP**.
    *   Qualquer outra violação dos Termos de Serviço da plataforma.

4.  **Uso Não Autorizado:** O uso deste script para acessar contas que não lhe pertencem é antiético e potencialmente ilegal. O autor condena veementemente tais atividades.

5.  **Sem Garantia:** Este projeto é fornecido "COMO ESTÁ", sem garantia de qualquer tipo, expressa ou implícita. Não há garantia de que funcionará perfeitamente ou que estará livre de erros.

**Ao fazer o download ou usar este script, você concorda que leu, entendeu e aceita os termos desta isenção de responsabilidade.**


## 📜 Sobre o Projeto

Este script foi desenvolvido para automatizar a verificação de múltiplas contas na plataforma Hotmart. Ele lê as credenciais de um arquivo de texto, tenta realizar o login e, em caso de sucesso, extrai informações públicas do perfil e a lista de cursos associados à conta. O projeto foi construído com um sistema de checkpoint para evitar reprocessamento e separa os resultados em diferentes arquivos de saída para facilitar a análise.

## 📋 Índice

- [⚠️ Aviso Legal e Isenção de Responsabilidade](#️-aviso-legal-e-isenção-de-responsabilidade)
- [Funcionalidades](#-funcionalidades)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Como Usar](#-como-usar)
- [Entendendo os Arquivos de Saída](#-entendendo-os-arquivos-de-saída)
- [🐛 Problemas Conhecidos](#-problemas-conhecidos)
- [Como Contribuir](#-como-contribuir)
- [Licença](#-licença)

## ✨ Funcionalidades

-   **Login Automatizado:** Utiliza Playwright para simular o acesso humano à página de login da Hotmart.
-   **Processamento em Lote:** Lê múltiplas credenciais (email:senha) a partir de um arquivo `clientes.txt`.
-   **Extração de Dados:** Coleta dados do perfil (ID, nome, país) e a lista de cursos (pagos e gratuitos).
-   **Sistema de Checkpoint:** Salva o progresso no arquivo `sucessos_e_checkpoint.json` e pula automaticamente as contas já processadas com sucesso em execuções futuras.
-   **Gerenciamento de Falhas:** Identifica e separa diferentes tipos de erros:
    -   Credenciais inválidas.
    -   Contas bloqueadas ou com verificação em duas etapas (2FA).
    -   Falhas de autenticação/rede (HTTP 401/403).
    -   Erros críticos inesperados durante a execução.
-   **Salvamento de Sessão:** Armazena o estado da sessão (cookies, local storage) para cada login bem-sucedido na pasta `cliente_states/`.

## 🔧 Pré-requisitos

-   Python 3.8 ou superior
-   `pip` (gerenciador de pacotes do Python)

## 🚀 Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/CillsGhost2/Hotmart-Account-Checker.git
    cd Hotmart-Account-Checker
    ```

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install playwright
    ```

4.  **Instale os navegadores para o Playwright:**
    Este comando fará o download dos navegadores necessários para a automação.
    ```bash
    playwright install
    ```
    obs: Se estiver no Windows 10 pelo PowerShell e a intalação do Playwright der erro, tente esse comando:
    ```
    python -m playwright install
    ```

## ⚙️ Como Usar

1.  **Prepare as Contas:**
    Crie um arquivo chamado `clientes.txt` na mesma pasta do script. Adicione as credenciais no formato `email:senha`, uma por linha.
    ```
    exemplo1@email.com:senha123
    exemplo2@email.com:senha456
    exemplo3@email.com:senha789
    ```

2.  **Execute o Script:**
    Abra seu terminal na pasta do projeto e execute o seguinte comando:
    ```bash
    python aopotencia.py
    ```
    O script começará a processar as contas uma a uma, exibindo o status de cada uma no console.

## 📁 Entendendo os Arquivos de Saída

O script gera vários arquivos para organizar os resultados:

-   `sucessos_e_checkpoint.json`:
    -   **Função:** Arquivo principal. Armazena os dados completos de todas as contas que tiveram **sucesso** no login.
    -   **Utilidade:** Serve como um "checkpoint". Em futuras execuções, as contas listadas aqui como "SUCESSO" serão ignoradas.

-   `falhas_criticas.json`:
    -   **Função:** Registra erros inesperados do script (ex: um elemento da página não foi encontrado, timeout do Playwright, etc.).
    -   **Utilidade:** Ajuda a depurar problemas no código ou mudanças inesperadas na estrutura do site da Hotmart.

-   `falhas_autenticacao_rede.txt`:
    -   **Função:** Lista apenas as credenciais (`email:senha`) que resultaram em um erro de autenticação a nível de rede (HTTP status 401/403).
    -   **Utilidade:** Isola rapidamente as contas que foram rejeitadas diretamente pelo servidor, o que pode indicar um bloqueio de IP ou de credencial.

-   **Pasta `cliente_states/`**:
    -   **Função:** Contém um arquivo `.json` para cada login bem-sucedido, salvando cookies e dados de sessão.
    -   **Utilidade:** Pode ser usado no futuro para restaurar uma sessão logada sem precisar de usuário e senha novamente.

## 🐛 Problemas Conhecidos

#### 1. Timeout na Navegação Pós-Login
-   **Sintoma:** O login é bem-sucedido, mas o script falha ao esperar o redirecionamento para a URL `**/consumer.hotmart.com/main**`.
-   **Causa:** A conta pode ser de um tipo diferente (Produtor, Afiliado) que redireciona para outra página, ou a Hotmart pode ter alterado o fluxo de login.
-   **Erro Gerado:**
    ```
    Exceção Crítica: Timeout 20000ms exceeded.
    =========================== logs ===========================
    waiting for navigation to "**/consumer.hotmart.com/main**" until 'load'
    ============================================================
    ```

#### 2. Timeout na Detecção de Texto Pós-Login
-   **Sintoma:** O script não consegue confirmar que o login foi bem-sucedido porque não encontra os textos de verificação.
-   **Causa:** A conta do usuário está em um idioma que não foi previsto no script (ex: francês, italiano), então os seletores de texto como "Minhas compras" ou "Manage my business" não são encontrados.
-   **Erro Gerado:**
    ```
    Exceção Crítica: Page.wait_for_selector: Timeout 10000ms exceeded.
    Call log:
      - waiting for locator("text=/Gerenciar meu negócio|Manage my business|Minhas compras|Mis compras/i") to be visible
    ```

#### 3. Bloqueio por IP (CloudFront) Após Alto Volume de Requisições
-   **Sintoma:** Após processar um grande número de contas (cerca de 1000), o script começa a falhar ao tentar encontrar o campo de login `username` no início do processo.
-   **Causa:** O CloudFront, sistema de proteção da Hotmart, identifica o alto volume de requisições como atividade suspeita e bloqueia temporariamente o seu endereço de IP.
-   **Recomendação:** Se você receber o erro abaixo, pare o script e abra a URL da variável `LOGIN_URL_PADRAO` em um navegador. Se a página exibir "Service Unavailable" ou um erro similar, seu IP foi bloqueado. O bloqueio pode durar de 30 segundos a várias horas.
-   **AVISO:** Ser bloqueado repetidamente pode resultar em um **bloqueio permanente** do seu IP.
-   **Erro Gerado:**
    ```
    Exceção Crítica: Page.wait_for_selector: Timeout 10000ms exceeded.
    Call log:
      - waiting for locator("input[name=\"username\"]") to be visible
    ```

## 🤝 Como Contribuir

Contribuições são bem-vindas! Se você tiver ideias para melhorar o script, sinta-se à vontade para seguir estes passos:

1.  Faça um **Fork** do projeto.
2.  Crie uma nova Branch (`git checkout -b feature/sua-feature`).
3.  Faça o commit das suas alterações (`git commit -m 'Adiciona sua-feature'`).
4.  Faça o Push para a Branch (`git push origin feature/sua-feature`).
5.  Abra um **Pull Request**.

## 📄 Licença

Este projeto está licenciado sob a **Licença MIT**. Veja o arquivo `LICENSE` para mais detalhes.
