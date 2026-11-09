#!/usr/bin/env python3
"""Draw current portrait figures from regenerated CSV, then render HTML to vector PDF."""
from pathlib import Path
import csv,io,json,shutil,os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/figs'
LABEL={'adress_dementia':'ADReSS','coperia':'COPERIA','coswara':'Coswara','neurovoz_vowels':'NeuroVoz','parcz_vowels':'PARCZ','visia':'VISIA'}
BACK={'hubert_base':'HuBERT','wav2vec2_base':'wav2vec2','whisper_base':'Whisper'}
COLORS={'adress_dementia':'#315f9e','coperia':'#cf8428','coswara':'#499d75','neurovoz_vowels':'#9164bd','parcz_vowels':'#be5b7b','visia':'#647d8e'}

def csv_rows(name):
    with (OUT/name).open(newline='') as f:return list(csv.DictReader(f))

def html_figure(name,fig):
    buf=io.StringIO();fig.savefig(buf,format='svg',metadata={'Date':None});plt.close(fig)
    svg=buf.getvalue();svg=svg[svg.index('<svg'):]
    width,height=512,round(512*fig.get_figheight()/fig.get_figwidth())
    content=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>{name}</title><style>*{{box-sizing:border-box}}html,body{{margin:0;background:white}}.figure{{width:{width}px;height:{height}px}}svg{{display:block;width:100%;height:100%}}@page{{size:{width}px {height}px;margin:0}}</style><div class="figure">{svg}</div></html>'''
    (OUT/f'{name}.html').write_text(content)

def draw():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.linewidth':.6,'svg.fonttype':'path','svg.hashsalt':'clinical-speech-repro-v1'})
    rows=csv_rows('fig_blocks_data.csv')
    for endpoint,suffix in [('speaker_auroc','auroc'),('speaker_macro_f1','macrof')]:
        fig,axes=plt.subplots(2,1,figsize=(6.6,9.2),gridspec_kw={'height_ratios':[18,12]})
        fig.subplots_adjust(left=.30,right=.98,top=.96,bottom=.125,hspace=.32)
        for ax,stage in zip(axes,['extension_stage','screening_stage']):
            data=[r for r in rows if r['stage']==stage and r['endpoint']==endpoint]
            blocks=sorted({r['block'] for r in data});methods=sorted({r['method'] for r in data});ys={b:len(blocks)-i-1 for i,b in enumerate(blocks)}
            lo=min(float(r['partition_min_pp']) for r in data)-2;hi=max(float(r['partition_max_pp']) for r in data)+2
            ax.axvspan(0,max(hi,0),color='#315f9e',alpha=.06);ax.axvline(0,color='#505866',lw=.7)
            for r in data:
                method=r['method'];j=methods.index(method);y=ys[r['block']]+(j-(len(methods)-1)/2)*.22
                color=COLORS[r['block'].split('/')[0]];marker={'lora':'o','dora':'o','adalora_peft':'s','ia3':'^','hira':'D'}[method]
                ax.plot([float(r['partition_min_pp']),float(r['partition_max_pp'])],[y,y],color=color,lw=1,alpha=.7)
                ax.plot(float(r['delta_pp']),y,marker,ms=5,mfc='white' if method=='dora' else color,mec=color,mew=1)
            labels=[LABEL[b.split('/')[0]]+' / '+BACK[b.split('/')[1]] for b in blocks]
            ax.set_yticks([ys[b] for b in blocks],labels=labels,fontsize=8.5);ax.set_xlim(lo,hi);ax.set_ylim(-.8,len(blocks)-.2)
            ax.set_title(('AUROC' if suffix=='auroc' else 'Macro-F1')+' — '+stage.replace('_',' '),loc='left',fontsize=11)
            ax.set_xlabel('DFA − method (percentage points)');ax.grid(axis='x',color='#e1e5eb',lw=.5);ax.set_axisbelow(True)
            for sp in ['top','right']:ax.spines[sp].set_visible(False)
        fig.text(.5,.02,'Extension: ● LoRA · ○ DoRA     Screening: ■ AdaLoRA · ▲ IA³ · ◆ HiRA\nLines: range across the three partitions.',ha='center',fontsize=8)
        html_figure('fig_blocks_'+suffix,fig)
    rows=csv_rows('fig_rank_curve_data.csv')
    # The CSV schema is validated below instead of inferring an undocumented mapping.
    required={'series','rank','endpoint','median','q25','q75'}
    if not required.issubset(rows[0]):raise ValueError('Unexpected rank-curve schema: '+str(list(rows[0])))
    fig,axes=plt.subplots(2,1,figsize=(6,6.8));fig.subplots_adjust(left=.15,right=.97,top=.95,bottom=.16,hspace=.36)
    for ax,endpoint in zip(axes,['Auroc','MacroF']):
        data=[r for r in rows if r['endpoint']==endpoint]
        for arm,color in [('lora','#cf8428'),('dora','#9164bd')]:
            selected=sorted([r for r in data if r['series']==arm],key=lambda r:int(r['rank']));x=list(range(len(selected)));med=[float(r['median']) for r in selected]
            ax.errorbar(x,med,yerr=[[m-float(r['q25']) for r,m in zip(selected,med)],[float(r['q75'])-m for r,m in zip(selected,med)]],marker='o',color=color,capsize=3,label=arm.upper())
            ax.set_xticks(x,[r['rank'] for r in selected])
        for arm,style,color in [('dfa','-','#315f9e'),('full_ft','--','#7f8793')]:
            r=next(r for r in data if r['series']==arm);ax.axhline(float(r['median']),ls=style,color=color,label={'dfa':'DFA','full_ft':'Full FT'}[arm])
        ax.set_title('Speaker '+('AUROC' if endpoint=='Auroc' else 'macro-F1'),loc='left',fontsize=11);ax.set_xlabel('Adapter rank');ax.grid(color='#e1e5eb',lw=.5)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.015),ncol=4,fontsize=9)
    fig.text(.5,.005,'Error bars: interquartile range across blocks.',ha='center',fontsize=8)
    html_figure('fig_rank_readable',fig)
    source=ROOT/'paper/figs/source/fig_families_readable.html';(OUT/source.name).write_bytes(source.read_bytes())

def render():
    names=['fig_families_readable','fig_blocks_auroc','fig_blocks_macrof','fig_rank_readable']
    binary=os.environ.get('CHROME_BIN') or next((shutil.which(n) for n in ['google-chrome','chromium','chromium-browser'] if shutil.which(n)),None)
    with sync_playwright() as p:
        options={'headless':True}
        if binary:options['executable_path']=binary
        browser=p.chromium.launch(**options)
        for name in names:
            page=browser.new_page(viewport={'width':600,'height':1300},device_scale_factor=2)
            page.goto((OUT/f'{name}.html').as_uri());page.evaluate('document.fonts.ready');page.emulate_media(media='print')
            box=page.locator('.figure').bounding_box()
            bad=page.locator('.card,.node,.description').evaluate_all('(els)=>els.filter(e=>e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1).length')
            if bad:raise ValueError(f'{name}: clipped diagram text')
            page.pdf(path=str(OUT/f'{name}.pdf'),width=str(math_ceil(box['width']))+'px',height=str(math_ceil(box['height']))+'px',margin={k:'0' for k in ['top','bottom','left','right']},print_background=True)
            pdf_path=OUT/f'{name}.pdf'
            writer=PdfWriter(clone_from=pdf_path);writer.metadata=None;writer.add_metadata({'/Creator':'dfa-paper-results'})
            with pdf_path.open('wb') as stream:writer.write(stream)
            page.locator('.figure').screenshot(path=str(OUT/f'{name}.png'));page.close()
            if len(PdfReader(OUT/f'{name}.pdf').pages)!=1:raise ValueError(f'{name}: expected one page')
        browser.close()
    print('Rendered four current-layout figures from local HTML; numeric panels read generated CSV.')

def math_ceil(value):
    import math
    return math.ceil(value)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT/'outputs');args=parser.parse_args()
    OUT=args.root/'figs';draw();render()
