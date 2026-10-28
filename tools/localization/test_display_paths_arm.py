"""Execute the production menu-key recovery and module prose helpers on ARM.

Uses the real language/catalog/font code with mocked card I/O. This checks
display-path inputs, including selected help lines, rather than catalog parity.
"""
from pathlib import Path
import sys,runpy,subprocess,json,re
from audit_runtime_ui import inventory,V,ROOT
sys.path.insert(0,str(V/'tools/localization'))
scope=runpy.run_path(str(V/'tools/localization/test_startup_arm.py'))
Machine=scope['Machine'];check=scope['check'];fnv1a=scope['fnv1a']
out=scope['OUT'];arm=scope['ARM'];suffix=scope['TOOL_SUFFIX']

def function(path,name):
    text=path.read_text('utf-8');match=re.search(r'^static [^\n]*\b'+name+r'\(',text,re.M)
    assert match,name
    end=text.index('\n}',match.start())+2
    return text[match.start():end]

harness=out/'display-paths.c'
harness.write_text('''#include "menu.h"
#include "language.h"
#include "string.h"
#define MIN(a,b) ((a)<(b)?(a):(b))
int strncmp(const char *a,const char *b,unsigned n){while(n--){unsigned x=(unsigned char)*a++,y=(unsigned char)*b++;if(x!=y)return x-y;if(!x)return 0;}return 0;}
static int startswith(const char *s,const char *p){while(*p)if(*s++!=*p++)return 0;return 1;}
'''+function(V/'src/menu.c','menu_display_text')+'\n'+
function(V/'src/menu.c','menu_help_get_line')+'\n'+
function(V/'src/module.c','module_display_string_value')+'''
const char *test_menu_name(const char *current,const char *original){return menu_display_text(current,original,MENU_MAX_NAME_LEN);}
const char *test_menu_value(const char *current,const char *original){return menu_display_text(current,original,MENU_MAX_VALUE_LEN);}
const char *test_help_line(const char *source,int index){static char buf[MENU_MAX_HELP_LEN];return menu_translate(menu_help_get_line(source,index,buf));}
const char *test_module_value(const char *field,const char *value){return module_display_string_value(field,value);}
int test_name_capacity(void){return MENU_MAX_NAME_LEN;}
int test_value_capacity(void){return MENU_MAX_VALUE_LEN;}
''',encoding='utf-8')
obj=out/'display-paths.o'
p=subprocess.run([str(arm/('arm-none-eabi-gcc'+suffix)),*scope['flags'],'-c',str(harness),'-o',str(obj)],capture_output=True)
assert p.returncode==0,p.stderr.decode(errors='replace')
elf=out/'display.elf';raw=out/'display.bin'
exports=['test_menu_name','test_menu_value','test_help_line','test_module_value','test_name_capacity','test_value_capacity','language_translate','language_select','test_selector_is_action']
subprocess.run([str(arm/('arm-none-eabi-gcc'+suffix)),'-march=armv5te','-marm','-nostdlib','-Wl,--gc-sections','-Wl,-Ttext=0x10000','-Wl,-Tdata=0x20000','-Wl,-e,language_init',*['-Wl,-u,'+x for x in exports],*map(str,scope['objects']),str(obj),'-lgcc','-o',str(elf)],check=True)
subprocess.run([str(arm/('arm-none-eabi-objcopy'+suffix)),'-O','binary',str(elf),str(raw)],check=True)
syms={s[2]:int(s[0],16) for line in subprocess.check_output([str(arm/('arm-none-eabi-nm'+suffix)),str(elf)],text=True).splitlines() if len(s:=line.split())==3}
Machine.__init__.__globals__.update(raw=raw,syms=syms)
files={'ML/LANG/INDEX.TXT':(V/'data/lang/INDEX.TXT').read_bytes()}
for code in ('zh_cn','de','pl'):files['ML/LANG/'+code+'.lng']=(V/('data/lang/'+code+'.lng')).read_bytes()
for font in ('zh_cn','lat_ext'):files['ML/FONTS/'+font+'.bfn']=(V/('data/fonts/'+font+'.bfn')).read_bytes()
inv=inventory(sys.argv[2] if len(sys.argv)>2 else 'build-lang4-r4');cases=dict(truncated_keys=0,selected_help_lines=0,module_prose=0,preserved_metadata=0)
assert all(not v for v in inv['missing'].values())
for code in ('zh_cn','de','pl'):
    m=Machine(files,fnv1a(code)&0x7fffffff);m.call('language_init')
    catalog={r['source']:r['translation'] for r in json.loads((V/('data/localization/'+code+'.json')).read_text('utf-8'))['messages']}
    def put(addr,text):m.uc.mem_write(addr,text.encode()+b'\0');return addr
    for item in inv['keys']:
        s=item['source'];roles=set(item['roles'])
        for role,wrapper,capacity in [('name','test_menu_name','test_name_capacity'),('choice','test_menu_value','test_value_capacity')]:
            n=m.call(capacity)
            if (role in roles or 'menu-update-or-choice' in roles) and len(s.encode())>=n and '\n' not in s:
                current=s.encode()[:n-1].decode('ascii')
                got=m.string(m.call(wrapper,put(0x30000,current),put(0x34000,s)))
                check(got==catalog[s],code+' truncated '+s);cases['truncated_keys']+=1
        if roles&{'help','help2'} and '\n' in s:
            for i,line in enumerate(s.split('\n')):
                if not line or line not in catalog:continue
                got=m.string(m.call('test_help_line',put(0x30000,s),i))
                check(got==catalog[line],code+' selected line '+repr(line));cases['selected_help_lines']+=1
    for row in inv['metadata']:
        got=m.string(m.call('test_module_value',put(0x30000,row['field']),put(0x34000,row['source'])))
        check(got==catalog[row['source']],code+' module '+row['module']+' '+row['field']);cases['module_prose']+=1
    for field in ('Author','License','Forum','URL','Version','Build date'):
        value='Original credit / GPL / https://example.invalid/ 1.2.3'
        check(m.string(m.call('test_module_value',put(0x30000,field),put(0x34000,value)))==value,'metadata intact');cases['preserved_metadata']+=1
    # An unrelated custom value with the same length must not be replaced by
    # the translation belonging to the original menu entry.
    n=m.call('test_name_capacity');current='Q'*(n-1)
    check(m.string(m.call('test_menu_name',put(0x30000,current),put(0x34000,'Different original label')))==current,'custom text retained')
check(all(cases.values()),'all intended regression categories exercised')
report=dict(result='PASS',execution='Production C display helpers executed as ARM with real catalogs/font loader and mocked card I/O',languages=['zh_cn','de','pl'],cases=cases,static_inventory_keys=inv['candidate_keys'],modules=19,missing_static_inventory_keys={c:len(v) for c,v in inv['missing'].items()},hardware_test=False,limitation='Does not emulate camera drawing, computed messages, raster help pages or every camera state.')
(out/'runtime-ui-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
