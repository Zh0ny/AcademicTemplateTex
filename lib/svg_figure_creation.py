# image_creation.py

import re
import sys
import shutil
import psutil
import os
import subprocess
import urllib.request
import py7zr

def pathSanitize(path):
    if path is None or not str(path).strip():
        return "figura_sem_nome"
    path = str(path).strip()
    if len(path) < 2:
        return "figura_sem_nome"
    result = re.match(r'^[\[\{\("\']?(.*?)[\]\}\)"\']?$', path, flags=re.S)
    if not result: 
        return "figura_sem_nome"
    for group in result.groups():
        if group is not None:
            svg_name = group.strip()
            break
    if not svg_name or not re.search(r'[A-Za-z0-9]', svg_name):
        return "figura_sem_nome"
    return svg_name

def checkIfProgramIsRunning(process_name):
    for process in psutil.process_iter(['name']):
        if process.info['name'] == process_name:
            print(f"figure_creation: {process_name} está em execução (PID: {process.pid})")
            return True
    return False

def openInkscape(inkscape_path,svg_name, reuse=None):
    if reuse:
        svg_for_actions = svg_name.replace("\\", "/")
        subprocess.run([inkscape_path, "--with-gui", "-q", "--actions", "export-overwrite;export-do;window-close"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        subprocess.Popen([inkscape_path, "--with-gui", f"{svg_for_actions}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        print("trying to reuse")
    else:
        subprocess.Popen([inkscape_path, "--with-gui", svg_name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

def findOrDownloadInkscape(portable_path):

    try:
        print("figure_creation: Verificando Inkscape...")
        ##result = subprocess.run(["inkscape", "-V"], capture_output=True, text=True)
        ##if result.returncode == 0:
        ##    print(f"figure_creation: Inkscape encontrado via variável do ambiente: {result.stdout.strip()}")
        ##    return "inkscape"
    except Exception as e:
        print(f"figure_creation: Inkscape do sistema não encontrado ({e}).")

    inkscape_exe = os.path.normpath(os.path.join(portable_path, "inkscape", "bin", "inkscape.exe"))

    if not os.path.isfile(inkscape_exe):
        print("figure_creation: Inkscape não encontrado. Baixando versão portátil...")
        url = "https://inkscape.org/gallery/item/56342/inkscape-1.4.2_2025-05-13_f4327f4-x64.7z"
        download_path = os.path.join(portable_path, "inkscape")
        
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        
        local_path, response_headers = urllib.request.urlretrieve(url, download_path)

        print(f"figure_creation: Arquivo salvo em: {local_path}")

        with py7zr.SevenZipFile(local_path, mode='r') as inkscape_7zip_file:
            inkscape_7zip_file.extractall(path=portable_path)
    else:
        print(f"figure_creation: Inkscape encontrado em: {inkscape_exe}")
    return inkscape_exe

def openSvgOnInkscape(svg_name, figures_path, inkscape_path, template_path = None):
    if not os.path.isfile(svg_name):
        print(f"figure_creation: Arquivo SVG não encontrado: {svg_name}")
        if template_path and os.path.isfile(template_path):
            print(f"figure_creation: Criando o arquivo usando template SVG: {template_path}")
            shutil.copyfile(template_path, svg_name)
        else:
            print("figure_creation: Template SVG não fornecido ou não encontrado. Criando arquivo SVG vazio.")
            with open(svg_name, 'w') as svg_file:
                svg_file.write("")
                svg_file.close()
        try:
            if checkIfProgramIsRunning("inkscape.exe"):
                openInkscape(inkscape_path, svg_name, True)
            else:
                openInkscape(inkscape_path, svg_name, False)
        except Exception as e:
            print(f"figure_creation: Erro ao abrir o arquivo SVG no Inkscape: {e}")
    else:
        print(f"figure_creation: Abrindo arquivo SVG existente: {svg_name}")
        try:
            if checkIfProgramIsRunning("inkscape.exe"):
                openInkscape(inkscape_path, svg_name, True)
            else:
                openInkscape(inkscape_path, svg_name, False)
        except Exception as e:
            print(f"figure_creation: Erro ao abrir o arquivo SVG no Inkscape: {e}")
    return

def main():
    if len(sys.argv) > 1:
        print(f"figure_creation: Argumento recebido: {sys.argv[1]}")
        root_path = os.path.dirname(os.path.abspath(sys.argv[0]))

        basename = os.path.splitext(pathSanitize(sys.argv[1]))
        user_arg = os.path.basename(basename[0])

        figures_path = os.path.normpath(os.path.join(os.path.dirname(root_path), "figuras"))
        template_path = os.path.normpath(os.path.join(root_path, "template_figuras.svg"))
        
        extension_type = "" if user_arg.lower().endswith(".svg") else ".svg"
        svg_path = os.path.normpath(os.path.join(figures_path, user_arg + extension_type))
        
        inkscape_path = findOrDownloadInkscape(root_path)
        ##checkIfProgramIsRunning("inkscape.exe")
        openSvgOnInkscape(svg_path, figures_path, inkscape_path, template_path)
    else:
        print("figure_creation: Nenhum argumento recebido.")
    print("figure_creation: Image creation module initialized.")

if __name__ == "__main__":
    main()