"""Inventory literal runtime UI keys in the built 5D3 core and its 19 modules.

This supplements catalog-key parity with binary-backed source/metadata checks.
Computed messages and raster documentation are outside this static inventory.
"""
from pathlib import Path
import ast,re,json
V=Path(__file__).resolve().parents[2];ROOT=V
STRING=r'"(?:\\.|[^"\\])*"';GROUP=r'(?:'+STRING+r'\s*)+'
FIELD=re.compile(r'\.(name|help|help2)\s*=\s*('+GROUP+r')',re.S)
MODULES='raw_video/mlv_lite raw_video/mlv_play raw_video/mlv_snd file_man pic_view ettr dual_iso silent dot_tune autoexpo arkanoid deflick img_name lua bench selftest adv_int crop_rec dev_tools/edmac'.split()

def decode(group):return ''.join(ast.literal_eval(s) for s in re.findall(STRING,group))
def words(s):
    s=re.sub(r'%[-+ #0]*[0-9]*(?:\.[0-9]*)?(?:hh|ll|[hljztL])?[diouxXfFeEgGaAcsp%]','',s)
    return bool(re.search(r'[A-Za-z]{2}',s))
def between_calls(text,pattern):
    for m in re.finditer(pattern,text):
        start=m.end();depth=1;i=start;quoted=False;escape=False
        while i<len(text) and depth:
            c=text[i]
            if quoted:
                if escape:escape=False
                elif c=='\\':escape=True
                elif c=='"':quoted=False
            elif c=='"':quoted=True
            elif c=='(':depth+=1
            elif c==')':depth-=1
            i+=1
        yield m.start(),text[start:i-1]

def inventory(build='build-lang4-r4'):
    keys={};metadata=[]
    def add(s,role,path,binary=None):
        if not s or '\0' in s or not words(s):return
        if binary is not None and s.encode()+b'\0' not in binary:return
        item=keys.setdefault(s,dict(source=s,roles=[],origins=[]))
        if role not in item['roles']:item['roles'].append(role)
        if path not in item['origins']:item['origins'].append(path)
    def scan(folder,binary):
        for p in sorted(folder.rglob('*')):
            if p.suffix not in ('.c','.h') or any(t=='build' or t.startswith('build-') for t in p.relative_to(folder).parts):continue
            text=p.read_text('utf-8',errors='replace');origin=p.relative_to(V).as_posix()
            for m in FIELD.finditer(text):
                try:s=decode(m[2])
                except (ValueError,SyntaxError):continue
                add(s,m[1],origin,binary)
                if m[1] in ('help','help2') and s.encode()+b'\0' in binary:
                    for line in s.split('\n'):add(line,'selected-help-line',origin)
            for pos,call in between_calls(text,r'\b(?:MENU_SET_(?:NAME|VALUE|SHORT_NAME|SHORT_VALUE|RINFO|HELP|WARNING)|CHOICES)\s*\('):
                for group in re.finditer(GROUP,call):
                    try:s=decode(group[0])
                    except (ValueError,SyntaxError):continue
                    add(s,'menu-update-or-choice',origin,binary)
            for m in re.finditer(r'\.choices\s*=\s*\(const\s+char\s*\*\s*\[\s*\]\s*\)\s*\{([^}]*)\}',text,re.S):
                for group in re.finditer(GROUP,m[1]):
                    try:s=decode(group[0])
                    except (ValueError,SyntaxError):continue
                    add(s,'choice',origin,binary)
    scan(V/'src',(V/('platform/5D3.123/'+build+'/magiclantern.bin')).read_bytes())
    for mod in MODULES:
        binary=(V/('modules/build/'+Path(mod).name+'.mo')).read_bytes()
        scan(V/('modules/'+mod),binary)
        header=V/('modules/'+mod+'/build/module_strings.h')
        fields={}
        for m in re.finditer(r'static char __module_string_(\w+)_(name|value)\s*\[\][^=]*=\s*('+GROUP+r');',header.read_text('utf-8'),re.S):
            fields.setdefault(m[1],{})[m[2]]=decode(m[3])
        for pair in fields.values():
            name,value=pair['name'],pair['value']
            assert value.encode()+b'\0' in binary,(mod,name)
            if name in ('Name','Summary','Description') or name.startswith('Help page'):
                add(value,'module-'+name,header.relative_to(V).as_posix(),binary)
                metadata.append(dict(module=Path(mod).name,field=name,source=value))
            add(name,'module-field-label',header.relative_to(V).as_posix(),binary)
    # Displayed by the module info renderer; identifiers and credits stay intact.
    for s in ['Information:','Properties:','Properties (no support):','Callbacks:','More info after you load this module.']:
        add(s,'module-info-label','src/module.c')
    catalogs={c:{r['source']:r['translation'] for r in json.loads((V/('data/localization/'+c+'.json')).read_text('utf-8'))['messages']} for c in ['zh_cn','de','pl']}
    result=dict(build=build,static_scope='Built core and selected 19 modules: fields, choices, menu update literals, selected help lines and exact metadata strings',candidate_keys=len(keys),modules=len(MODULES),metadata=metadata,keys=sorted(keys.values(),key=lambda r:r['source']),missing={c:[r for s,r in sorted(keys.items()) if not catalogs[c].get(s)] for c in catalogs})
    return result

if __name__=='__main__':
    import sys
    result=inventory(sys.argv[1] if len(sys.argv)>1 else 'build-lang4-r4')
    target=Path(sys.argv[2]) if len(sys.argv)>2 else Path('runtime-ui-inventory.json');target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Candidates',result['candidate_keys'],'missing',{c:len(v) for c,v in result['missing'].items()})
    for c in ['de']:
        print('\n'.join(json.dumps(dict(source=r['source'],roles=r['roles']),ensure_ascii=False) for r in result['missing'][c]))
