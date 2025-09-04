import os
import sys
import json
import svg2tikz as s2t
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

EXIT_OK = 0
EXIT_USAGE = 64    
EXIT_FAIL_CONVERT = 65

def convertSvgToTikz(svg_file):
    tikz_path = os.path.splitext(svg_file)[0]+".tikz"
    try:
        s2t.convert_file(svg_file, no_output=False, returnstring=False, output=tikz_path)
        return True
    except Exception as e:
        print(f"auto_svg2tikz: Error converting {svg_file} to {tikz_path}: {e}")
        print(traceback.format_exc())
    return False

def loadJson(json_path):
    try: 
        with open(json_path, 'r', encoding='utf-8') as json_file:
            json_data = json.load(json_file)
        return json_data
    except FileNotFoundError:
        print(f"auto_svg2tikz: Arquivo não encontrado: {json_path}")
        sys.exit(EXIT_USAGE)
    except json.JSONDecodeError as e:
        print(f"auto_svg2tikz: JSON inválido ({e}) em {json_path}")
        sys.exit(EXIT_USAGE)

def main(argv):

    if len(argv) < 2:
        print("auto_svg2tikz: Usage: python auto_svg2tikz.py <input_json_file_path>")
        return EXIT_USAGE
    input_json_file_path = argv[1]
    
    json_data = loadJson(input_json_file_path)
    if not isinstance(json_data, dict):
        print("auto_svg2tikz: Formato JSON inesperado.")
        sys.exit(1)
    
    for svg_path, info in json_data.items():
        tc = info.get("to_convert")
        td = info.get("to_delete")
        print(f"DEBUG: {svg_path} to_convert={tc!r} ({type(tc).__name__}) to_delete={td!r} ({type(td).__name__})")

    tasks = [
        svg_path
        for svg_path, info in json_data.items()
        if info.get("to_convert", 0) == 1 and info.get("to_delete",0) == 0
    ]
    print(tasks)
    if tasks:
        success = fail = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(convertSvgToTikz, svg_path): svg_path for svg_path in tasks}
            for future in as_completed(futures):
                svg = futures[future]
                try:
                    ok = future.result()
                except Exception as e: 
                    print(f"auto_svg2tikz: Exceçao inesperada na conversão do arquivo {svg}: {e}")
                    ok = False
                if ok:
                    json_data[svg]["to_convert"] = 0
                    success += 1
                else:
                    fail +=1
        print("auto_svg2tikz: Arquivo cache atualizado com sucesso.")
    else:

        print("auto_svg2tikz: Nenhum arquivo SVG para ser convertido.")
        return EXIT_OK
    
    with open(input_json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)
    
    print(f"auto_svg2tikz: Sucessos={success}, Falhas={fail}.")
    return EXIT_OK if fail == 0 else EXIT_FAIL_CONVERT

if __name__ == "__main__":
    sys.exit(main(sys.argv))
