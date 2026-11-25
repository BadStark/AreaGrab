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
