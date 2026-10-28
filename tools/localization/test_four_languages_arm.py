"""Exercise the supplied four-language card data with the actual ARM switcher."""
from pathlib import Path
import runpy,json

scope=runpy.run_path(str(Path(__file__).with_name('test_startup_arm.py')))
Machine=scope['Machine'];check=scope['check'];fnv1a=scope['fnv1a'];syms=scope['syms'];root=scope['V']
files={'ML/LANG/INDEX.TXT':(root/'data/lang/INDEX.TXT').read_bytes()}
for code in ('zh_cn','de','pl'):files['ML/LANG/'+code+'.lng']=(root/('data/lang/'+code+'.lng')).read_bytes()
for font in ('zh_cn','lat_ext'):files['ML/FONTS/'+font+'.bfn']=(root/('data/fonts/'+font+'.bfn')).read_bytes()
machine=Machine(files,0);machine.call('language_init')
check(machine.translate('Language')=='Language','supplied card starts in original English')
check(machine.reads==['ML/LANG/INDEX.TXT'],'English startup needs no translation/font allocation')
expected={'zh_cn':'语言','de':'Sprache','pl':'Język'}
lookups=0
chinese_sources={r['source'] for r in json.loads((root/'data/localization/zh_cn.json').read_text('utf-8'))['messages']}
for code in ('zh_cn','de','pl'):
    check(machine.call('language_select',fnv1a(code)&0x7fffffff)==1,'select supplied '+code)
    check(machine.translate('Language')==expected[code],'supplied selector label '+code)
    catalog=json.loads((root/('data/localization/'+code+'.json')).read_text('utf-8'))
    if code in ('de','pl'):
        check(chinese_sources <= {r['source'] for r in catalog['messages']},'all original Chinese keys are supplied in '+code)
    for row in catalog['messages']:
        check(machine.translate(row['source'])==row['translation'],'supplied translation '+code+' '+row['source'])
        lookups+=1
machine.call('language_select',0)
reads=len(machine.reads);allocated=machine.next
for _ in range(25):
    for code in ('zh_cn','de','pl'):
        machine.call('select_language',0,1)
        check(machine.translate('Language')==expected[code],'repeated supplied switch')
    machine.call('select_language',0,1);check(machine.translate('Language')=='Language','English')
check(machine.next==allocated and len(machine.reads)==reads,'supplied languages do not reallocate on repeated switching')
check(machine.reads.count('ML/FONTS/lat_ext.bfn')==1,'German and Polish share one Latin font')
for code,expected_label in [('zh_cn','语言'),('de','Sprache'),('pl','Język')]:
    machine.call('language_select',fnv1a(code)&0x7fffffff)
    saved=machine.u32(syms['selected_language'])
    restarted=Machine(files,saved);restarted.call('language_init')
    check(restarted.translate('Language')==expected_label,'saved selection restored on restart: '+code)
    check(restarted.translate('Untranslated test key')=='Untranslated test key','unknown source falls back to English')
report=dict(result='PASS',languages=['English','Simplified Chinese','Deutsch','Polski'],english_default=True,chinese_catalog_keys=len(chinese_sources),de_pl_missing_chinese_keys=0,actual_catalog_lookups=lookups,repeated_set_key_switches=100,saved_selection_restored=True,shared_latin_font=True,hardware_test=False)
print(json.dumps(report))
(scope['OUT']/'four-language-results.json').write_text(json.dumps(report,indent=2)+'\n')
print('Test report:',scope['OUT']/'four-language-results.json')
