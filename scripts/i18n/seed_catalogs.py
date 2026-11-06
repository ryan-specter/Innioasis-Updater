#!/usr/bin/env python3
"""
Hand-reviewed translations for the launch languages.

These are the strings a visitor sees first: the shell, the home page calls to
action, the picker itself, and the region note. They are written by a person
(or an editor) rather than a machine, they merge into i18n/catalogs/<lc>.json
without disturbing anything else, and translate.py will not overwrite them
unless --force is used.

    python scripts/i18n/seed_catalogs.py
    python scripts/i18n/seed_catalogs.py --list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

# English source -> {locale: reviewed translation}
REVIEWED: dict[str, dict[str, str]] = {
    "Skip to content": {
        "de": "Zum Inhalt springen",
        "fr": "Aller au contenu",
        "es": "Ir al contenido",
        "pt-BR": "Ir para o conteúdo",
        "ja": "本文へスキップ",
        "zh-CN": "跳到主要内容",
    },
    "Software Updates and Firmware": {
        "de": "Software-Updates und Firmware",
        "fr": "Mises à jour logicielles et firmware",
        "es": "Actualizaciones de software y firmware",
        "pt-BR": "Atualizações de software e firmware",
        "ja": "ソフトウェア更新とファームウェア",
        "zh-CN": "软件更新与固件",
    },
    "Browse firmware": {
        "de": "Firmware durchsuchen",
        "fr": "Parcourir les firmwares",
        "es": "Explorar el firmware",
        "pt-BR": "Explorar o firmware",
        "ja": "ファームウェアを見る",
        "zh-CN": "浏览固件",
    },
    "Help me choose": {
        "de": "Bei der Auswahl helfen",
        "fr": "M'aider à choisir",
        "es": "Ayúdame a elegir",
        "pt-BR": "Ajude-me a escolher",
        "ja": "選び方を確認",
        "zh-CN": "帮我选择",
    },
    "See what you can install.": {
        "de": "Sehen Sie, was Sie installieren können.",
        "fr": "Voyez ce que vous pouvez installer.",
        "es": "Mira lo que puedes instalar.",
        "pt-BR": "Veja o que você pode instalar.",
        "ja": "インストールできるものを確認しましょう。",
        "zh-CN": "看看可以安装哪些软件。",
    },
    "Get Updater CE": {
        "de": "Updater CE holen",
        "fr": "Obtenir Updater CE",
        "es": "Obtener Updater CE",
        "pt-BR": "Obter o Updater CE",
        "ja": "Updater CE を入手",
        "zh-CN": "获取 Updater CE",
    },
    "Get this in Updater CE": {
        "de": "In Updater CE erhalten",
        "fr": "Disponible dans Updater CE",
        "es": "Obtener en Updater CE",
        "pt-BR": "Obter no Updater CE",
        "ja": "Updater CE で入手",
        "zh-CN": "在 Updater CE 中获取",
    },
    "Install / Restore": {
        "de": "Installieren / Wiederherstellen",
        "fr": "Installer / Restaurer",
        "es": "Instalar / Restaurar",
        "pt-BR": "Instalar / Restaurar",
        "ja": "インストール / 復元",
        "zh-CN": "安装 / 恢复",
    },
    "Device Model": {
        "de": "Gerätemodell",
        "fr": "Modèle d'appareil",
        "es": "Modelo de dispositivo",
        "pt-BR": "Modelo do dispositivo",
        "ja": "デバイスモデル",
        "zh-CN": "设备型号",
    },
    "Original Software": {
        "de": "Original-Software",
        "fr": "Logiciel d'origine",
        "es": "Software original",
        "pt-BR": "Software original",
        "ja": "純正ソフトウェア",
        "zh-CN": "原厂固件",
    },
    "Software": {
        "de": "Software",
        "fr": "Logiciel",
        "es": "Software",
        "pt-BR": "Software",
        "ja": "ソフトウェア",
        "zh-CN": "软件",
    },
    "Troubleshooting": {
        "de": "Fehlerbehebung",
        "fr": "Dépannage",
        "es": "Solución de problemas",
        "pt-BR": "Solução de problemas",
        "ja": "トラブルシューティング",
        "zh-CN": "故障排除",
    },
    "FAQs": {
        "de": "FAQ",
        "fr": "FAQ",
        "es": "Preguntas frecuentes",
        "pt-BR": "Perguntas frequentes",
        "ja": "よくある質問",
        "zh-CN": "常见问题",
    },
    "Innioasis Community": {
        "de": "Innioasis-Community",
        "fr": "Communauté Innioasis",
        "es": "Comunidad Innioasis",
        "pt-BR": "Comunidade Innioasis",
        "ja": "Innioasis コミュニティ",
        "zh-CN": "Innioasis 社区",
    },
    "Innioasis player": {
        "de": "Innioasis-Player",
        "fr": "lecteur Innioasis",
        "es": "reproductor Innioasis",
        "pt-BR": "player Innioasis",
        "ja": "Innioasis プレーヤー",
        "zh-CN": "Innioasis 播放器",
    },
    "The safe way back": {
        "de": "Der sichere Rückweg",
        "fr": "Le retour en toute sécurité",
        "es": "El camino seguro de vuelta",
        "pt-BR": "O caminho seguro de volta",
        "ja": "安全に戻る方法",
        "zh-CN": "恢复原厂固件",
    },
    "Download ZIP": {
        "de": "ZIP herunterladen",
        "fr": "Télécharger le ZIP",
        "es": "Descargar ZIP",
        "pt-BR": "Baixar ZIP",
        "ja": "ZIP をダウンロード",
        "zh-CN": "下载刷机包 ZIP",
    },
    "Show nightly builds": {
        "de": "Nightly-Builds anzeigen",
        "fr": "Afficher les builds nightly",
        "es": "Mostrar compilaciones nocturnas",
        "pt-BR": "Mostrar builds noturnos",
        "ja": "ナイトビルドを表示",
        "zh-CN": "显示预览/每日构建",
    },
    "Updater connection instructions": {
        "de": "Anweisungen zum Verbinden mit Updater",
        "fr": "Instructions de connexion à Updater",
        "es": "Instrucciones de conexión con Updater",
        "pt-BR": "Instruções de conexão com o Updater",
        "ja": "Updater への接続手順",
        "zh-CN": "Updater 连接说明",
    },
    "Connect only at the live prompt.": {
        "de": "Erst verbinden, wenn die Aufforderung erscheint.",
        "fr": "Ne connectez qu'au moment de l'invite.",
        "es": "Conecta solo cuando aparezca el aviso.",
        "pt-BR": "Conecte apenas quando o aviso aparecer.",
        "ja": "案内が表示されてから接続してください。",
        "zh-CN": "仅在提示时连接。",
    },
    "Set Device Model to Y1.": {
        "de": "Gerätemodell auf Y1 setzen.",
        "fr": "Réglez le modèle d'appareil sur Y1.",
        "es": "Selecciona el modelo de dispositivo Y1.",
        "pt-BR": "Defina o modelo do dispositivo como Y1.",
        "ja": "デバイスモデルを Y1 に設定します。",
        "zh-CN": "将设备型号设为 Y1。",
    },
    "Support Updater and the Themes Gallery.": {
        "de": "Unterstützen Sie Updater und die Themen-Galerie.",
        "fr": "Soutenez Updater et la galerie de thèmes.",
        "es": "Apoya Updater y la galería de temas.",
        "pt-BR": "Apoie o Updater e a galeria de temas.",
        "ja": "Updater とテーマギャラリーを支援してください。",
        "zh-CN": "支持固件档案与主题画廊。",
    },
    # The picker's own interface.
    "Language": {
        "de": "Sprache",
        "fr": "Langue",
        "es": "Idioma",
        "pt-BR": "Idioma",
        "ja": "言語",
        "zh-CN": "语言",
    },
    "Edition": {
        "de": "Edition",
        "fr": "Édition",
        "es": "Edición",
        "pt-BR": "Edição",
        "ja": "エディション",
        "zh-CN": "版本",
    },
    "Search languages": {
        "de": "Sprachen suchen",
        "fr": "Rechercher une langue",
        "es": "Buscar idiomas",
        "pt-BR": "Pesquisar idiomas",
        "ja": "言語を検索",
        "zh-CN": "搜索语言",
    },
    "Close": {
        "de": "Schließen",
        "fr": "Fermer",
        "es": "Cerrar",
        "pt-BR": "Fechar",
        "ja": "閉じる",
        "zh-CN": "关闭",
    },
    "All languages": {
        "de": "Alle Sprachen",
        "fr": "Toutes les langues",
        "es": "Todos los idiomas",
        "pt-BR": "Todos os idiomas",
        "ja": "すべての言語",
        "zh-CN": "所有语言",
    },
    "The edition changes what this site offers, not just the language.": {
        "de": "Die Edition ändert, was diese Seite anbietet – nicht nur die Sprache.",
        "fr": "L'édition change ce que le site propose, pas seulement la langue.",
        "es": "La edición cambia lo que ofrece el sitio, no solo el idioma.",
        "pt-BR": "A edição muda o que o site oferece, não apenas o idioma.",
        "ja": "エディションは言語だけでなく、提供内容も変わります。",
        "zh-CN": "版本改变的是本站提供的内容，而不只是语言。",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="Print the reviewed pairs and exit")
    args = parser.parse_args()

    if args.list:
        for source, by_locale in REVIEWED.items():
            print(f"{source}\n  " + "\n  ".join(f"{code}: {text}" for code, text in by_locale.items()))
        return 0

    locales_path = os.path.join(ROOT, "i18n", "locales.json")
    with open(locales_path, "r", encoding="utf-8") as handle:
        registry = json.load(handle)
    meta = {entry["code"]: entry for entry in registry["locales"] + registry.get("variants", [])}

    languages = sorted({code for by_locale in REVIEWED.values() for code in by_locale})
    catalog_dir = os.path.join(ROOT, "i18n", "catalogs")
    os.makedirs(catalog_dir, exist_ok=True)

    for code in languages:
        path = os.path.join(catalog_dir, code + ".json")
        catalog = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                catalog = json.load(handle)
        strings = catalog.get("strings", {})
        added = 0
        for source, by_locale in REVIEWED.items():
            value = by_locale.get(code)
            if not value or strings.get(source) == value:
                continue
            strings[source] = value
            added += 1

        entry = meta.get(code, {"code": code, "name": code, "native": code, "dir": "ltr"})
        output = {
            "locale": code,
            "name": entry.get("name", code),
            "native": entry.get("native", code),
            "dir": entry.get("dir", "ltr"),
            "source": "en",
            "provider": catalog.get("provider", "reviewed"),
            "reviewed": True,
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(strings),
            "strings": dict(sorted(strings.items())),
        }
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(output, handle, ensure_ascii=False, indent=1)
            handle.write("\n")
        print(f"{code:<8} {len(strings):>4} entries ({added} reviewed)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
