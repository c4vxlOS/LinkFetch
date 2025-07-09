import re
import base64
import os
import requests
import mimetypes

def get_content(path: str):
    if path.startswith("http://") or path.startswith("https://"):
        response = requests.get(path, headers={ "User-Agent": "Mozilla/5.0" })
        return response.content if response.status_code == 200 else None
    elif path.startswith("data:"):
        return base64.b64decode(path.split(";base64,")[1])
    else:
        with open(path, "rb") as f:
            return f.read()
        
    return None

def as_b64(path):
    try:
        print(path)
        return f"data:{mimetypes.guess_type(path)[0]};base64,{base64.b64encode(get_content(path)).decode('utf-8')}"
    except:
        return None

def bundle_imported_file(source: str, pattern: str, replace_pattern: str):
    tags = re.findall(pattern.replace('*', '([^"]+)').format(r'([^"]+)'), source)
    total = """"""
    for i, src in enumerate(tags):
        r = None
        if type(src) is tuple:
            r = src[:-1]
            src = src[-1:][0]

        content = open(src.strip(), "r").read()
        total += content + "\n"

        p = pattern.format(src)
        if r != None:
            for x in r: p = p.replace("*", x, 1)
        
        if i == len(tags) - 1:
            source = source.replace(p, replace_pattern.format(total))
        else:
            source = re.sub(p, "", source)
    
    return source

def bundle_css(html):
    return re.sub(r'@import url\([^\)]+\);', '', bundle_imported_file(html, '<link rel="stylesheet" href="{}">', "<style>\n{}\n</style>"))

def bundle_js(html):
    return bundle_imported_file(html, '<script*src="{}"></script>', "<script>\n{}\n</script>")

def bundle_images(html):
    def h(match):
        return as_b64(match.group(0))
    
    return re.sub(r"assets/resources(?:/[^ \n\r\t\"\'<>]*)?", h, html)


def compress_js(html):
    scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    for script in scripts:
        html = html.replace(script, re.sub(r'\n}\n', r'\n};\n', script))
    return html

def parse_variable(src, key, name = None, n = 1):
    if name == None:
        name = "{" + key.replace("--", "").replace("let ", "").replace("const ", "").removeprefix("<").removesuffix(">").replace("-", "_") + "}"

    if "*" in key:
        return re.sub(key, name, src, n)
    
    return re.sub(rf"({re.escape(key)}\s*[:=]\s*)([^;]*)(;?)", rf"\1{name}\3", src, count=n)

def build_template(content: str, skip_vars: bool = False) -> str:
    print(">> Building src")

    print("  | Bundling css")
    content = bundle_css(content)

    print("  | Bundling js")
    content = bundle_js(content)

    print("  | Bundling img")
    content = bundle_images(content)

    content = compress_js(content)

    print("  | Compressing src")
    content = re.sub(r" //.*", "", content)
    content = re.sub(r"/\*\*([\s\S]*?)\*/", "", content)
    # content = content.replace("\\n", "\\\\n")
    content = re.sub(r"^\s+", "", content, flags=re.MULTILINE)
    content = re.sub(r">\s+<", "><", content)
    content = re.sub(r"\s+", " ", content).strip()

    return content

def file_to_template(file, skip_vars: bool = False):
    src = open(file, "r").read()
    return build_template(src, skip_vars)

def template_to_file(tmp, file):
    open(file, "w").write(tmp)

def replace_temp(file, src):
    file = file
    new = re.sub(r'return """.*?"""', 'return """--source--"""', open(file, "r").read(), re.DOTALL).replace("--source--", src)
    open(file, "w").write(new)

os.chdir("src")
template_to_file(file_to_template("index.html"), "../index.template")