from pathlib import Path
from pypdf import PdfReader
for name in ['SRS_RE_1.pdf', 'PROJEC_1.PDF']:
    path = Path(name)
    print('===== ' + name + ' =====')
    try:
        reader = PdfReader(str(path))
        text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        print(text[:30000])
    except Exception as e:
        print('ERROR', e)
    print('\n---END---\n')
