"""Execute the real ARM language startup and BFNT loader with mocked card I/O."""
from pathlib import Path
import subprocess,sys,json,struct
import os, tempfile
ROOT=Path(__file__).resolve().parents[2]; V=ROOT
OUT=Path(tempfile.mkdtemp(prefix='ml-language-test-'))
arm_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('ARM_BINPATH')
if not arm_path:
    raise SystemExit('Provide the ARM toolchain bin directory as the first argument or ARM_BINPATH.')
ARM=Path(arm_path)
TOOL_SUFFIX='.exe' if os.name == 'nt' else ''
from catalog import compile_catalog,fnv1a
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
shim=OUT/'io-shim.c'
shim.write_text('''#include <stdint.h>
#include "rbf_font.h"
int FIO_GetFileSize(const char *p,uint32_t *s){return 0;}
uint8_t *read_entire_file_persistent(const char *p,int *s){return 0;}
void __mem_free(void *p){}
int snprintf(char *p,unsigned n,const char *fmt,...){return 0;}
int menu_snprintf(char *p,int n,const char *fmt,...){return 0;}
unsigned strlen(const char *p){return 0;}
char *strchr(const char *p,int c){return 0;}
void menu_add(const char *name,void *entries,int count){}
void *memset(void *p,int value,unsigned size){unsigned char *q=p;while(size--)*q++=value;return p;}
int bfnt_char_get_width_scaled(int c,int height){return 1;}
int test_text_width(const char *s){
    font f={0};
    for(int i=0;i<256;i++)f.wTable[i]=1;
    f.cTable=f.wTable; f.hdr.height=20;
    return rbf_str_width(&f,s);
}
''')
flags=['-march=armv5te','-marm','-Os','-ffreestanding','-fno-builtin','-ffunction-sections','-fdata-sections','-nostdlib','-std=gnu99','-D__ARM__','-DCONFIG_MAGICLANTERN=1','-DCONFIG_DEBUGMSG=0','-DCONFIG_CONSOLE','-DCONFIG_TCC','-DCONFIG_MODULES','-DCONFIG_5D3=1','-DCONFIG_5D3_123=1','-DRESTARTSTART=0x69500','-DMAIN_FIRMWARE_ADDR=0xFF0C0000','-DCONFIG_FW_VERSION=123','-I'+str(V/'include'),'-I'+str(V/'src'),'-I'+str(V/'platform/5D3.123'),'-I'+str(V/'platform/5D3.123/include')]
objects=[]
for source in [V/'src/language.c',V/'src/language_file.c',V/'src/rbf_font.c',shim]:
    obj=OUT/(source.stem+'-startup.o');objects.append(obj)
    p=subprocess.run([str(ARM/('arm-none-eabi-gcc'+TOOL_SUFFIX)),*flags,'-c',str(source),'-o',str(obj)],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
elf=OUT/'startup.elf';raw=OUT/'startup.bin'
subprocess.run([str(ARM/('arm-none-eabi-gcc'+TOOL_SUFFIX)),'-march=armv5te','-marm','-nostdlib','-Wl,--gc-sections','-Wl,-Ttext=0x10000','-Wl,-Tdata=0x20000','-Wl,-e,language_init','-Wl,-u,language_translate','-Wl,-u,test_text_width',*map(str,objects),'-lgcc','-o',str(elf)],check=True)
subprocess.run([str(ARM/('arm-none-eabi-objcopy'+TOOL_SUFFIX)),'-O','binary',str(elf),str(raw)],check=True)
syms={s[2]:int(s[0],16) for line in subprocess.check_output([str(ARM/('arm-none-eabi-nm'+TOOL_SUFFIX)),str(elf)],text=True).splitlines() if len(s:=line.split())==3}
STOP=0xf0000
def check(value,message):
    if not value:raise AssertionError(message)
class Machine:
    def __init__(self,files,selected=0):
        self.files=files;self.reads=[];self.freed=[];self.next=0x400000
        self.uc=uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        uc.mem_map(0x10000,0x100000);uc.mem_write(0x10000,raw.read_bytes())
        uc.mem_map(0x400000,0x800000);uc.mem_map(0x2000000,0x10000)
        self.u32write(syms['selected_language'],selected)
        hooks={syms[name]:name for name in ['FIO_GetFileSize','read_entire_file_persistent','__mem_free','snprintf','menu_snprintf','strlen','strchr','menu_add']}
        def intercept(uc,address,size,user):
            if address not in hooks:return
            name=hooks[address];args=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
            result=0
            if name=='FIO_GetFileSize':
                path=self.string(args[0]);result=0 if path in self.files else 0xffffffff
                if path in self.files:self.u32write(args[1],len(self.files[path]))
            elif name=='read_entire_file_persistent':
                path=self.string(args[0]);self.reads.append(path)
                data=self.files[path]+b'\0';result=self.next;self.next+=(len(data)+4095)&~4095
                uc.mem_write(result,data);self.u32write(args[1],len(data)-1)
            elif name=='__mem_free':self.freed.append(args[0])
            elif name in ('snprintf','menu_snprintf'):
                fmt=self.string(args[2]);value=fmt.replace('%s',self.string(args[3])) if '%s' in fmt else fmt
                encoded=value.encode();result=len(encoded)
                if args[1]:uc.mem_write(args[0],encoded[:args[1]-1]+b'\0')
            elif name=='strlen':result=len(self.bytes(args[0]))
            elif name=='strchr':
                data=self.bytes(args[0])+b'\0';index=data.find(bytes([args[1]&255]));result=args[0]+index if index>=0 else 0
            uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,intercept)
    def bytes(self,p):
        out=bytearray()
        while self.uc.mem_read(p,1)[0]:out+=self.uc.mem_read(p,1);p+=1
        return bytes(out)
    def string(self,p):return self.bytes(p).decode()
    def u32write(self,p,n):self.uc.mem_write(p,struct.pack('<I',n&0xffffffff))
    def u32(self,p):return struct.unpack('<I',self.uc.mem_read(p,4))[0]
    def call(self,name,a=0,b=0):
        uc=self.uc;uc.reg_write(UC_ARM_REG_R0,a);uc.reg_write(UC_ARM_REG_R1,b)
        uc.reg_write(UC_ARM_REG_SP,0x200fff0);uc.reg_write(UC_ARM_REG_LR,STOP)
        uc.emu_start(syms[name],STOP,count=100000000)
        check(uc.reg_read(UC_ARM_REG_PC)==STOP,'execution limit '+name)
        return uc.reg_read(UC_ARM_REG_R0)
    def translate(self,text):
        self.uc.mem_write(0x30000,text.encode()+b'\0');return self.string(self.call('language_translate',0x30000))

manifest=b'zh_cn\tSimplified Chinese\tzh_cn\nde\tDeutsch\t\n'
files={'ML/LANG/INDEX.TXT':manifest,'ML/LANG/zh_cn.lng':(V/'data/lang/zh_cn.lng').read_bytes(),'ML/FONTS/zh_cn.bfn':(V/'data/fonts/zh_cn.bfn').read_bytes(),'ML/LANG/de.lng':compile_catalog(dict(messages=[dict(source='Language',translation='Sprache')]))}
english=Machine(files);english.call('language_init');check(english.translate('Language')=='Language','English default')
check(english.reads==['ML/LANG/INDEX.TXT'],'English does not allocate catalog or font')
english.call('select_language',0,1);check(english.translate('Language')=='Language','selection deferred until restart')
check(english.u32(syms['selected_language'])==fnv1a('zh_cn')&0x7fffffff,'stable saved language identifier')
chinese=Machine(files,fnv1a('zh_cn')&0x7fffffff);chinese.call('language_init')
check(chinese.translate('Language')=='语言','Chinese startup')
check(chinese.u32(syms['BFNT_ALT_FONT'])!=0,'Chinese font loaded')
check(len(chinese.freed)==1,'only index freed; selected resources remain resident')
check(chinese.translate('Untranslated label')=='Untranslated label','English fallback')
german=Machine(files,fnv1a('de')&0x7fffffff);german.call('language_init')
check(german.translate('Language')=='Sprache','second language without new C code')
check(german.u32(syms['BFNT_ALT_FONT'])==0,'second language reuses built-in fonts')
for missing in ('ML/FONTS/zh_cn.bfn','ML/LANG/zh_cn.lng'):
    bad=dict(files);bad.pop(missing);m=Machine(bad,fnv1a('zh_cn')&0x7fffffff);m.call('language_init')
    check(m.translate('Language')=='Language','missing resource fallback '+missing)
bad=dict(files);bad['ML/FONTS/zh_cn.bfn']=b'invalid font';m=Machine(bad,fnv1a('zh_cn')&0x7fffffff);m.call('language_init');check(m.translate('Language')=='Language','bad font fallback')
# A corrupt glyph offset must fail before the renderer can dereference it.
bad=dict(files);f=bytearray(files['ML/FONTS/zh_cn.bfn']);off,count=struct.unpack_from('<2I',f,8);struct.pack_into('<I',f,off+count,0xffffffff);bad['ML/FONTS/zh_cn.bfn']=bytes(f)
m=Machine(bad,fnv1a('zh_cn')&0x7fffffff);m.call('language_init');check(m.translate('Language')=='Language','bad glyph offset fallback')
for index in (b'../bad\tBad\t\n',b'xx\tNon ASCII \xff\t\n',b'x'*2049):
    m=Machine({'ML/LANG/INDEX.TXT':index},1);m.call('language_init');check(m.translate('Language')=='Language','invalid index fallback')
for text,count in [(b'ABC',3),('中文'.encode(),2),('Menü'.encode(),4),(b'A\xe4',2),(b'\xb0',1),('A😀B'.encode(),3)]:
    chinese.uc.mem_write(0x30000,text+b'\0');check(chinese.call('test_text_width',0x30000)==count,'UTF8/legacy glyph boundary '+repr(text))
report=dict(result='PASS',execution='Real ARM startup/catalog/font functions with mocked card I/O',cases=['English default','save/restart selection','Chinese with font','second language without font','missing catalog','missing font','malformed font','corrupt glyph offset','invalid index'],hardware_test=False)
(OUT/'startup-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
