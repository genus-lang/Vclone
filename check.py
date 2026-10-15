import re

with open('frontend/js/app.js', encoding='utf-8') as f:
    js = f.read()
with open('frontend/index.html', encoding='utf-8') as f:
    html = f.read()

ids = set(re.findall(r'getElementById\([\"\']([a-zA-Z0-9_\-]+)[\"\']\)', js))
missing = []
for i in ids:
    if f'id="{i}"' not in html and f"id='{i}'" not in html:
        missing.append(i)
        
print("Missing IDs:", missing)
print("All IDs:", sorted(list(ids)))