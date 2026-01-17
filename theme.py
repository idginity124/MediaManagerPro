class ThemeManager:
    # Color Palettes (Güncellenmiş Renkler)
    PALETTES = {
        "dark": {
            "primary": "#E50914",          # Netflix Kırmızısı (Canlı)
            "background": "#181818",       # Tam siyah yerine çok koyu gri (Göz yormaz)
            "surface": "#2B2B2B",          # Kartlar ve paneller için
            "text": "#EEEEEE",             # Okunabilir beyaz
            "secondary_text": "#AAAAAA",   # Yan metinler
            "border": "#404040",           # İnce, belirgin çerçeveler
            "hover": "#3A3A3A",            # Üzerine gelince
            "scrollbar_bg": "#181818",
            "scrollbar_handle": "#555555",
            "selection": "#E5091444"       # Seçim rengi (Transparan kırmızı)
        },
        "light": {
            "primary": "#D32F2F",          # Biraz daha koyu kırmızı (Beyaz üstünde okunurluk için)
            "background": "#F4F6F8",       # Hafif gri-mavi tonlu beyaz
            "surface": "#FFFFFF",          # Tam beyaz kartlar
            "text": "#202124",             # Tam siyah yerine koyu gri
            "secondary_text": "#5F6368",
            "border": "#D1D5DB",           # Modern gri çerçeve
            "hover": "#E0E0E0",
            "scrollbar_bg": "#F4F6F8",
            "scrollbar_handle": "#A0A0A0",
            "selection": "#D32F2F33"       # Seçim rengi (Transparan kırmızı)
        }
    }

    def apply_theme(self, widget, theme_name="dark"):
        # Tema ismini kontrol et, yoksa varsayılanı al
        palette = self.PALETTES.get(theme_name, self.PALETTES["dark"])
        stylesheet = self._generate_qss(palette)
        widget.setStyleSheet(stylesheet)

    def _generate_qss(self, p):
        return f"""
            /* --- Genel Ayarlar --- */
            QMainWindow, QWidget {{
                background-color: {p['background']};
                color: {p['text']};
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
                font-size: 14px;
            }}

            QWidget:disabled {{
                color: {p['secondary_text']};
            }}

            /* --- Menü Çubuğu --- */
            QMenuBar {{
                background-color: {p['surface']};
                border-bottom: 1px solid {p['border']};
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 10px 15px;
                color: {p['text']};
            }}
            QMenuBar::item:selected {{
                background-color: {p['hover']};
                border-radius: 4px;
            }}
            QMenu {{
                background-color: {p['surface']};
                border: 1px solid {p['border']};
                padding: 5px 0px;
                border-radius: 6px;
            }}
            QMenu::item {{
                padding: 8px 30px 8px 20px;
            }}
            QMenu::item:selected {{
                background-color: {p['primary']};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background: {p['border']};
                margin: 5px 10px;
            }}

            /* --- Dosya Ağacı / Listeler / Tablolar --- */
            QTreeView, QListWidget, QTableView {{
                background-color: {p['surface']};
                alternate-background-color: {p['background']};
                color: {p['text']};
                border: 1px solid {p['border']};
                border-radius: 8px; /* Modern köşe */
                outline: none;
                selection-background-color: {p['selection']};
                selection-color: {p['text']};
                padding: 5px;
            }}

            QTreeView:focus, QListWidget:focus, QTableView:focus {{
                border: 1px solid {p['primary']};
            }}

            QTreeView::item, QListWidget::item {{
                padding: 6px;
                border-radius: 4px;
                border: none;
            }}

            QTreeView::item:hover, QListWidget::item:hover {{
                background-color: {p['hover']};
            }}

            QTreeView::item:selected, QListWidget::item:selected {{
                background-color: {p['selection']};
                color: {p['text']};
                border: 1px solid {p['primary']}; /* Seçili öğe etrafında ince çizgi */
            }}

            /* Tablo Başlıkları */
            QHeaderView {{
                background-color: transparent;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {p['background']};
                color: {p['secondary_text']};
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid {p['border']};
                font-weight: 600;
                text-transform: uppercase;
                font-size: 12px;
            }}
            
            /* --- Girdi Alanları (Input Fields) --- */
            QLineEdit, QComboBox, QTextEdit {{
                background-color: {p['surface']};
                color: {p['text']};
                border: 1px solid {p['border']};
                border-radius: 6px;
                padding: 8px 12px; /* Daha geniş iç boşluk */
                selection-background-color: {p['primary']};
                selection-color: white;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid {p['primary']};
                background-color: {p['background']};
            }}

            /* Read Only Durumu */
            QLineEdit[readOnly="true"], QTextEdit[readOnly="true"] {{
                background-color: {p['background']};
                color: {p['secondary_text']};
                border: 1px solid {p['border']};
            }}

            /* ComboBox Ok İşareti */
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
                image: none; /* Varsayılan oku kaldırıp CSS ile üçgen çizebiliriz ama renk yeterli */
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {p['secondary_text']};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {p['surface']};
                border: 1px solid {p['border']};
                border-radius: 6px;
                padding: 5px;
                outline: none;
            }}

            /* --- Butonlar --- */
            QPushButton {{
                background-color: {p['surface']};
                color: {p['text']};
                border: 1px solid {p['border']};
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                border-color: {p['primary']};
                color: {p['primary']};
                background-color: {p['hover']};
            }}
            QPushButton:pressed {{
                background-color: {p['primary']};
                color: white;
                border-color: {p['primary']};
            }}
            QPushButton:disabled {{
                background-color: {p['background']};
                color: {p['secondary_text']};
                border-color: {p['border']};
            }}

            /* --- Sekmeler (Tab Widget) --- */
            QTabWidget::pane {{
                border: 1px solid {p['border']};
                background: {p['surface']};
                border-radius: 8px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: {p['background']};
                color: {p['secondary_text']};
                padding: 10px 20px;
                border: 1px solid transparent;
                margin-right: 5px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background: {p['surface']};
                color: {p['primary']};
                border: 1px solid {p['border']};
                border-bottom: 2px solid {p['surface']}; /* İçeriğe birleşik görünüm */
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background: {p['hover']};
                color: {p['text']};
            }}

            /* --- Durum Çubuğu (Status Bar) --- */
            QStatusBar {{
                background-color: {p['surface']};
                color: {p['secondary_text']};
                border-top: 1px solid {p['border']};
            }}

            /* --- Kaydırma Çubukları (Modern & İnce) --- */
            QScrollBar:vertical {{
                border: none;
                background: {p['scrollbar_bg']};
                width: 8px; /* Daha ince */
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {p['scrollbar_handle']};
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {p['primary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                border: none;
                background: {p['scrollbar_bg']};
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {p['scrollbar_handle']};
                min-width: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {p['primary']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
            
            /* --- ToolTip (İpucu Kutusu) --- */
            QToolTip {{
                background-color: {p['primary']};
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
                opacity: 200;
            }}
        """