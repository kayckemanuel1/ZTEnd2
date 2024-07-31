import os
import psutil
import platform
import subprocess
from playwright.sync_api import sync_playwright
import time
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

def descobrir_gateways():
    sistema = platform.system()
    
    if sistema == "Windows":
        comando = "route print 0.0.0.0"
    else:  # Supondo que seja um sistema Linux
        comando = "ip route show default"

    gateways = []

    try:
        resultado = subprocess.check_output(comando, shell=True, text=True)
        if sistema == "Windows":
            for linha in resultado.split('\n'):
                if "0.0.0.0" in linha:
                    partes = linha.split()
                    gateway = partes[2]
                    interface = partes[3]
                    custo = int(partes[-1])
                    gateways.append((gateway, interface, custo))
        else:
            for linha in resultado.split('\n'):
                if "default" in linha:
                    partes = linha.split()
                    gateway = partes[2]
                    interface = partes[4]
                    custo = int(partes[-1])
                    gateways.append((gateway, interface, custo))
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o comando: {e}")

    return gateways

def verificar_conexao_ethernet(interface_name):
    interfaces = psutil.net_if_stats()
    
    if interface_name in interfaces:
        # Verificar se a interface está operando
        if interfaces[interface_name].isup:
            return True
        else:
            return False
    else:
        raise ValueError(f"A interface {interface_name} não foi encontrada. Por favor verifique se você inseriu corretamente o nome da interface de rede, lembre-se de respeitar as letras maiusculas e minusculas e os espaços.")

def algoritimo_upload(interface_rede, file_path, gateway, headless):
    try:
        if not verificar_conexao_ethernet(interface_name=interface_rede):
            messagebox.showerror('Erro', 'Rede desconectada, verifique as conexões e o status da rede.')
            return
        
        # Dados
        url = 'http://' + gateway
        user_pass = 'multipro'

        messagebox.showinfo('Informação', f'Rede conectada!\nGateway: {gateway}')
        
        # Configurações navegador
        with sync_playwright() as p:
            browser_type = p.chromium
            if headless:
                browser = browser_type.launch(headless=True)
            else:
                browser = browser_type.launch(headless=False)

            context = browser.new_context()
            page = context.new_page()
            
            # Acessa o roteador
            page.goto(url)

            # Espera até que o formulário de login esteja visível
            page.wait_for_selector('xpath=//*[@id="Frm_Username"]')

            # Login
            page.fill('xpath=//*[@id="Frm_Username"]', user_pass)
            page.fill('xpath=//*[@id="Frm_Password"]', user_pass)
            page.locator('xpath=//*[@id="Frm_ShowPrivacy"]').click()
            
            # Adiciona uma espera explícita
            page.wait_for_selector('xpath=//*[@id="LoginId"]')
            page.locator('xpath=//*[@id="LoginId"]').click()
            time.sleep(0.3)

            # Chegando à aba de upload
            page.wait_for_selector('xpath=//*[@id="Btn_Close"]')
            page.locator('xpath=//*[@id="Btn_Close"]').click()
            time.sleep(0.3)
            page.wait_for_selector('xpath=//*[@id="mgrAndDiag"]')
            page.locator('xpath=//*[@id="mgrAndDiag"]').click()
            time.sleep(0.3)
            page.wait_for_selector('xpath=//*[@id="devMgr"]')
            page.locator('xpath=//*[@id="devMgr"]').click()
            time.sleep(0.3)
            page.wait_for_selector('xpath=//*[@id="defCfgMgr"]')
            page.locator('xpath=//*[@id="defCfgMgr"]').click()
            time.sleep(0.3)

            # Localizar o campo de upload e enviar o arquivo
            page.wait_for_selector('xpath=//*[@id="DefConfUploadBar"]')
            page.locator('xpath=//*[@id="DefConfUploadBar"]').click()
            page.wait_for_selector('xpath=//*[@id="defConfigUpload"]')
            page.set_input_files('xpath=//*[@id="defConfigUpload"]', file_path)
            page.wait_for_selector('xpath=//*[@id="Btn_Upload"]')
            page.locator('xpath=//*[@id="Btn_Upload"]').click()
            page.wait_for_selector('xpath=//*[@id="confirmOK"]')
            page.locator('xpath=//*[@id="confirmOK"]').click()

            # Verificação resultado do upload
            time.sleep(1)
            confirm_msg = page.text_content('xpath=//*[@id="confirmMsg"]/p')
            if "processing, please wait" in confirm_msg.lower() or "Are you sure to restore user configuration?" in confirm_msg.lower():
                messagebox.showinfo('Informação', "Fazendo upload do arquivo, por favor aguarde.")
                time.sleep(2)
                confirm_msg = page.text_content('xpath=//*[@id="confirmMsg"]/p')
                if "integrity check failed" in confirm_msg.lower():
                    messagebox.showerror('Erro', 'Erro de integridade, Verifique se você selecionou o arquivo correto e se o arquivo não está corrompido.')
                else:
                    messagebox.showinfo('Sucesso no upload!', 'Upload feito com sucesso. Desligue e ligue o roteador manualmente pelo botão power.')
            else:
                messagebox.showerror('Erro', f"Erro ao realizar upload: {confirm_msg}")

    except Exception as e:
        messagebox.showerror('Erro', str(e))

def selecionar_arquivo():
    file_path = filedialog.askopenfilename()
    file_path_entry.delete(0, tk.END)
    file_path_entry.insert(0, file_path)

# Interface gráfica
root = tk.Tk()
root.title("ZTEnd, Agile Preset ZTE H198")

tk.Label(root, text="Nome da Interface de Rede:").grid(row=0, column=0, padx=10, pady=10)
interface_rede = tk.Entry(root)
interface_rede.grid(row=0, column=1, padx=10, pady=10)

tk.Label(root, text="Caminho para o Arquivo de Configuração:").grid(row=1, column=0, padx=10, pady=10)
file_path_entry = tk.Entry(root)
file_path_entry.grid(row=1, column=1, padx=10, pady=10)

btn_selecionar_arquivo = tk.Button(root, text="Selecionar Arquivo", command=selecionar_arquivo)
btn_selecionar_arquivo.grid(row=1, column=2, padx=10, pady=10)

tk.Label(root, text="Selecione a Rota:").grid(row=2, column=0, padx=10, pady=10)
rota_combobox = ttk.Combobox(root, state="readonly")
rota_combobox.grid(row=2, column=1, padx=10, pady=10)

def atualizar_rotas():
    gateways = descobrir_gateways()
    rotas = [f"{gateway[1]} - {gateway[0]} (Custo: {gateway[2]})" for gateway in gateways]
    rota_combobox['values'] = rotas
    if rotas:
        rota_combobox.current(0)

btn_atualizar_rotas = tk.Button(root, text="Atualizar Rotas", command=atualizar_rotas)
btn_atualizar_rotas.grid(row=2, column=2, padx=10, pady=10)

headless_var = tk.BooleanVar(value=True)  # Faz o script ser executado de forma oculta
check_headless = tk.Checkbutton(root, text="Modo Headless", variable=headless_var)
check_headless.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

def executar_algoritmo():
    try:
        rota_selecionada = rota_combobox.get()
        if not rota_selecionada:
            messagebox.showerror('Erro', 'Por favor, selecione uma rota.')
            return
        gateway = rota_selecionada.split(' - ')[1].split(' (')[0]
        algoritimo_upload(interface_rede.get(), file_path_entry.get(), gateway, headless_var.get())
    except Exception as e:
        messagebox.showerror('Erro', str(e))

btn_executar = tk.Button(root, text="Preset", command=executar_algoritmo)
btn_executar.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

root.mainloop()
