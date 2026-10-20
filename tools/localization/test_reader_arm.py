from pathlib import Path
import subprocess, sys, json, struct, random
import os, tempfile
ROOT=Path(__file__).resolve().parents[2]; V=ROOT
OUT=Path(tempfile.mkdtemp(prefix='ml-language-test-'))
arm_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('ARM_BINPATH')
if not arm_path:
    raise SystemExit('Provide the ARM toolchain bin directory as the first argument or ARM_BINPATH.')
ARM=Path(arm_path)
TOOL_SUFFIX='.exe' if os.name == 'nt' else ''
from catalog import compile_catalog, fnv1a
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UcError
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
from catalog import compile_catalog, fnv1a
elf=OUT/'language_file.elf'; binary=OUT/'language_file.bin'
subprocess.run([str(ARM/('arm-none-eabi-gcc'+TOOL_SUFFIX)),'-march=armv5te','-marm','-Os','-ffreestanding','-fno-builtin','-nostdlib','-Wall','-Wextra','-Werror','-Wl,-Ttext=0x10000','-Wl,-e,language_file_validate',str(V/'src/language_file.c'),'-o',str(elf)],check=True)
subprocess.run([str(ARM/('arm-none-eabi-objcopy'+TOOL_SUFFIX)),'-O','binary',str(elf),str(binary)],check=True)
syms={line.split()[2]:int(line.split()[0],16) for line in subprocess.check_output([str(ARM/('arm-none-eabi-nm'+TOOL_SUFFIX)),str(elf)],text=True).splitlines() if len(line.split())==3}
uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
uc.mem_map(0x10000,0x10000);uc.mem_write(0x10000,binary.read_bytes())
uc.mem_map(0x400000,0x100000);uc.mem_map(0x600000,0x20000);uc.mem_map(0x900000,0x10000)
STOP=0x1fff0
def call(name,a,b):
    uc.reg_write(UC_ARM_REG_R0,a);uc.reg_write(UC_ARM_REG_R1,b)
    uc.reg_write(UC_ARM_REG_SP,0x90fff0);uc.reg_write(UC_ARM_REG_LR,STOP)
    uc.emu_start(syms[name],STOP,count=100000000)
    if uc.reg_read(UC_ARM_REG_PC) != STOP: raise AssertionError('instruction limit: ' + name)
    return uc.reg_read(UC_ARM_REG_R0)
def validate(data,size=None):
    # The end of each input is immediately followed by unmapped memory.
    p=0x500000-len(data);uc.mem_write(p,data)
    return call('language_file_validate',p,len(data) if size is None else size)
def lookup(data,text):
    p=0x500000-len(data);uc.mem_write(p,data);uc.mem_write(0x600000,text.encode()+b'\0')
    q=call('language_file_lookup',p,0x600000);out=bytearray()
    while True:
        c=uc.mem_read(q,1)[0];q+=1
        if not c: return out.decode()
        out.append(c)
def check(cond,label):
    if not cond: raise AssertionError(label)
rows=[dict(source='ISO %d',translation='感光度 %d'),dict(source='Menu',translation='Menü')]
sample=compile_catalog(dict(messages=rows))
check(validate(sample)==1,'valid multilingual input')
for i in range(len(sample)): check(validate(sample[:i])==0,'truncated input '+str(i))
for pos,value in [(0,0),(4,1),(8,0xffffffff),(12,0xffffffff),(16,0xffffffff),(20,0),(24,0xffffffff),(28,0xffffffff)]:
    data=bytearray(sample);struct.pack_into('<I',data,pos,value)
    check(validate(bytes(data))==0,'invalid field '+str(pos))
for value in (b'\xc0\x80', b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xe4\x80'):
    data=bytearray(compile_catalog(dict(messages=[dict(source='A',translation='aaaaa')])));pool=32
    data[pool+2:pool+2+len(value)]=value
    check(validate(bytes(data))==0,'invalid UTF8')
for language in ('中文','Deutsch','Polski'):
    data=compile_catalog(dict(messages=[dict(source='Menu',translation=language)]))
    check(validate(data)==1,'valid language '+language)
    check(lookup(data,'Menu')==language,'lookup '+language)
    check(lookup(data,'Missing')=='Missing','English fallback')
# Two distinct source strings with the same FNV-1a hash must remain distinct.
check(fnv1a('costarring')==fnv1a('liquid'),'collision fixture')
data=compile_catalog(dict(messages=[dict(source='costarring',translation='first'),dict(source='liquid',translation='second')]))
check(validate(data)==1,'collision catalog validates')
check(lookup(data,'costarring')=='first' and lookup(data,'liquid')=='second','full-key collision lookup')
for a,b,expected in [('ISO %d','感光度 %d',1),('%s %d','%d %s',0),('%02d','%n',0),('%d','%1$d',0),('%*d','%*d',0),('100%%','百分之百%%',1),('A','B',1),('%s','',0),('','',1)]:
    uc.mem_write(0x600000,a.encode()+b'\0');uc.mem_write(0x610000,b.encode()+b'\0')
    check(call('language_format_compatible',0x600000,0x610000)==expected,'format '+repr((a,b)))
catalog=json.loads((V/'data/localization/zh_cn.json').read_text('utf-8'))
actual=(V/'data/lang/zh_cn.lng').read_bytes();check(validate(actual)==1,'Chinese catalog validates')
for row in catalog['messages']:check(lookup(actual,row['source'])==row['translation'],'Chinese lookup '+row['source'])
randomizer=random.Random(20261020)
for _ in range(500):
    data=bytearray(sample)
    for _ in range(randomizer.randrange(1,5)):
        data[randomizer.randrange(len(data))]=randomizer.randrange(256)
    validate(bytes(data))  # malformed files must not read outside declared input
report=dict(arm_gcc='12.2.1-1.1',execution='ARMv5 instructions under Unicorn 2.1.4',catalog_entries=len(catalog['messages']),truncations=len(sample),mutations=500,result='PASS',hardware_test=False)
(OUT/'reader-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
