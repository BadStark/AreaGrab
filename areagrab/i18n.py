"""Offline interface locale selection."""
import ctypes
import locale

LANGUAGES = {
    "auto": "System language",
    "ru": "Русский", "en": "English",
    "zh-CN": "简体中文", "zh-TW": "繁體中文",
    "es": "Español", "pt-BR": "Português (Brasil)",
    "de": "Deutsch", "fr": "Français", "ja": "日本語",
    "ko": "한국어", "tr": "Türkçe", "it": "Italiano", "pl": "Polski",
}

def resolve_language(value="auto", system_locale=None):
    if value != "auto":
        return value if value in LANGUAGES else "en"
    if system_locale is None:
        try:
            system_locale = locale.windows_locale.get(
                ctypes.windll.kernel32.GetUserDefaultUILanguage(), "en")
        except (AttributeError, OSError):
            system_locale = "en"
    tag = system_locale.replace("_", "-").lower()
    base = tag.split("-")[0]
    if base == "zh":
        return "zh-TW" if any(x in tag.split("-") for x in ("tw", "hk", "mo", "hant")) else "zh-CN"
    if base == "pt":
        return "pt-BR"
    return base if base in LANGUAGES and base != "auto" else "en"

# Common UI vocabulary, in registry order (excluding automatic mode).
_CODES = tuple(k for k in LANGUAGES if k != "auto")
_ROWS = {
    "Настройки": ["Настройки","Settings","设置","設定","Configuración","Configurações","Einstellungen","Paramètres","設定","설정","Ayarlar","Impostazioni","Ustawienia"],
    "Общие": ["Общие","General","常规","一般","General","Geral","Allgemein","Général","一般","일반","Genel","Generali","Ogólne"],
    "Применить": ["Применить","Apply","应用","套用","Aplicar","Aplicar","Übernehmen","Appliquer","適用","적용","Uygula","Applica","Zastosuj"],
    "Закрыть": ["Закрыть","Close","关闭","關閉","Cerrar","Fechar","Schließen","Fermer","閉じる","닫기","Kapat","Chiudi","Zamknij"],
    "Захват": ["Захват","Capture","截图","擷取","Captura","Captura","Aufnahme","Capture","キャプチャ","캡처","Yakalama","Cattura","Przechwytywanie"],
    "Сохранение": ["Сохранение","Saving","保存","儲存","Guardado","Salvamento","Speichern","Enregistrement","保存","저장","Kaydetme","Salvataggio","Zapisywanie"],
    "Буфер": ["Буфер","Clipboard","剪贴板","剪貼簿","Portapapeles","Área de transferência","Zwischenablage","Presse-papiers","クリップボード","클립보드","Pano","Appunti","Schowek"],
    "Уведомления": ["Уведомления","Notifications","通知","通知","Notificaciones","Notificações","Benachrichtigungen","Notifications","通知","알림","Bildirimler","Notifiche","Powiadomienia"],
    "О программе": ["О программе","About","关于","關於","Acerca de","Sobre","Über","À propos","バージョン情報","정보","Hakkında","Informazioni","O programie"],
    "Выход": ["Выход","Exit","退出","結束","Salir","Sair","Beenden","Quitter","終了","종료","Çıkış","Esci","Wyjście"],
    "Язык / Language": ["Язык / Language","Interface language","界面语言","介面語言","Idioma","Idioma","Anzeigesprache","Langue","表示言語","표시 언어","Arayüz dili","Lingua","Język interfejsu"],
    "Настройки…": ["Настройки…","Settings…","设置…","設定…","Configuración…","Configurações…","Einstellungen…","Paramètres…","設定…","설정…","Ayarlar…","Impostazioni…","Ustawienia…"],
    "Открыть папку": ["Открыть папку","Open folder","打开文件夹","開啟資料夾","Abrir carpeta","Abrir pasta","Ordner öffnen","Ouvrir le dossier","フォルダーを開く","폴더 열기","Klasörü aç","Apri cartella","Otwórz folder"],
    "Последние снимки": ["Последние снимки","Recent screenshots","最近截图","最近截圖","Capturas recientes","Capturas recentes","Letzte Screenshots","Captures récentes","最近のスクリーンショット","최근 스크린샷","Son ekran görüntüleri","Screenshot recenti","Ostatnie zrzuty ekranu"],
}

def translate(text, language="auto"):
    code = resolve_language(language)
    row = _ROWS.get(text)
    return row[_CODES.index(code)] if row else text

_ROWS.update({
"Сделать снимок": ["Сделать снимок","Take screenshot","截图","截圖","Capturar pantalla","Capturar tela","Screenshot erstellen","Faire une capture","スクリーンショットを撮る","스크린샷 찍기","Ekran görüntüsü al","Cattura schermata","Zrób zrzut ekranu"],
"Весь экран": ["Весь экран","Full screen","全屏","全螢幕","Pantalla completa","Tela inteira","Vollbild","Plein écran","全画面","전체 화면","Tam ekran","Schermo intero","Cały ekran"],
"Нет снимков": ["Нет снимков","No screenshots","无截图","無截圖","Sin capturas","Sem capturas","Keine Screenshots","Aucune capture","画像なし","스크린샷 없음","Görüntü yok","Nessuna cattura","Brak zrzutów"],
"Более старые →": ["Более старые →","Older →","更早 →","更早 →","Anteriores →","Anteriores →","Ältere →","Plus anciennes →","以前の画像 →","이전 항목 →","Daha eski →","Precedenti →","Starsze →"],
"Горячая клавиша": ["Горячая клавиша","Hotkey","快捷键","快速鍵","Atajo","Atalho","Tastenkürzel","Raccourci","ホットキー","단축키","Kısayol","Scorciatoia","Skrót klawiszowy"],
"Папка": ["Папка","Folder","文件夹","資料夾","Carpeta","Pasta","Ordner","Dossier","フォルダー","폴더","Klasör","Cartella","Folder"],
"Формат": ["Формат","Format","格式","格式","Formato","Formato","Format","Format","形式","형식","Biçim","Formato","Format"],
"Открыть": ["Открыть","Open","打开","開啟","Abrir","Abrir","Öffnen","Ouvrir","開く","열기","Aç","Apri","Otwórz"],
"Обзор…": ["Обзор…","Browse…","浏览…","瀏覽…","Examinar…","Procurar…","Durchsuchen…","Parcourir…","参照…","찾아보기…","Gözat…","Sfoglia…","Przeglądaj…"],
"Сохранено": ["Сохранено","Saved","已保存","已儲存","Guardado","Salvo","Gespeichert","Enregistré","保存済み","저장됨","Kaydedildi","Salvato","Zapisano"],
"Ошибка": ["Ошибка","Error","错误","錯誤","Error","Erro","Fehler","Erreur","エラー","오류","Hata","Errore","Błąd"],
"Записать…": ["Записать…","Record…","录制…","錄製…","Grabar…","Gravar…","Aufzeichnen…","Enregistrer…","記録…","기록…","Kaydet…","Registra…","Nagraj…"],
"Качество JPG": ["Качество JPG","JPG quality","JPG 质量","JPG 品質","Calidad JPG","Qualidade JPG","JPG-Qualität","Qualité JPG","JPG 品質","JPG 품질","JPG kalitesi","Qualità JPG","Jakość JPG"],
"Шаблон имени": ["Шаблон имени","Filename template","文件名模板","檔名範本","Plantilla de nombre","Modelo de nome","Dateinamenvorlage","Modèle de nom","ファイル名テンプレート","파일 이름 템플릿","Dosya adı şablonu","Modello nome file","Szablon nazwy"],
"Длительность": ["Длительность","Duration","持续时间","持續時間","Duración","Duração","Dauer","Durée","表示時間","표시 시간","Süre","Durata","Czas trwania"],
"Показывать миниатюру": ["Показывать миниатюру","Show thumbnail","显示缩略图","顯示縮圖","Mostrar miniatura","Mostrar miniatura","Miniatur anzeigen","Afficher la miniature","サムネイルを表示","미리 보기 표시","Küçük resmi göster","Mostra miniatura","Pokaż miniaturę"],
"Сохранять снимки в папку": ["Сохранять снимки в папку","Save screenshots to folder","保存截图到文件夹","儲存截圖至資料夾","Guardar capturas en carpeta","Salvar capturas na pasta","Screenshots im Ordner speichern","Enregistrer les captures dans un dossier","画像をフォルダーに保存","스크린샷을 폴더에 저장","Görüntüleri klasöre kaydet","Salva catture nella cartella","Zapisuj zrzuty w folderze"]
})
