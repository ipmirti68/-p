name: MIRTI68 Voleybol Güncelleme
on:
  workflow_dispatch:
  schedule:
    - cron: "*/20 * * * *"
permissions:
  contents: write
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Paketleri kur
        run: pip install -U yt-dlp requests beautifulsoup4 lxml
      - name: YouTube tara (Cookiesiz - Android mod)
        run: |
          python voleybol_youtube.py
          ls -lh mirti68.m3u voleybol_youtube.json || true
      - name: Kaydet
        if: always()
        run: |
          git config user.name "MIRTI68 Bot"
          git config user.email "bot@users.noreply.github.com"
          git add -f mirti68.m3u voleybol_youtube.json 2>/dev/null || true
          git diff --cached --quiet || (git commit -m "MIRTI68 güncellendi" && git pull --rebase origin main && git push)rmalize_text(i['name']) or 'sultanlar' in normalize_text(i['name'])])} tekrar")

def main():
    print("MIRTI68 VOLEYBOL HLS BOT")
    items=scan_channel()
    if not items: print("Video yok, boş JSON yazılıyor"); items=[]
    save_files(items)
    print("BİTTİ")

if __name__=="__main__": main()
