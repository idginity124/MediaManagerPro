import sys
import os
import glob
import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QTextEdit, 
    QComboBox, QTabWidget, QMessageBox, QSplitter, QStatusBar
)
from PySide6.QtCore import Qt, QSettings 
from PySide6.QtGui import QAction, QShortcut, QDragEnterEvent, QDropEvent, QKeySequence,QIcon

from workers import AnalyzerWorker, OrganizerWorker, CleanerWorker, ConverterWorker, PrivacyWorker, InpaintWorker
from components import (
    StatCard, SmartProgressBar, EnhancedDropArea, QuickFilterBar, 
    FileTreeView, BatchRenameDialog, RecentFoldersMenu, PluginManagerDialog
)
from components import PreviewWidget
from theme import ThemeManager
from plugin_host import PluginHost
from utils import BatchRenamer
from languages import LANGUAGES, language_signal
import traceback 

class LanguageManager:
    def __init__(self):
        self.settings = QSettings("MediaManager", "Pro")
        self.current_language = self.settings.value('language', 'EN')
        if self.current_language not in LANGUAGES:
            self.current_language = 'EN'
    
    def set_language(self, lang):
        if lang in LANGUAGES:
            self.current_language = lang
            self.settings.setValue('language', lang)
            language_signal.language_changed.emit(lang)
    
    def get(self, key):
        return LANGUAGES[self.current_language].get(key, key)

class SettingsManager:
    def __init__(self):
        self.settings = QSettings("MediaManager", "Pro")
    
    def save_setting(self, key, value):
        self.settings.setValue(key, value)
    
    def load_setting(self, key, default=None):
        return self.settings.value(key, default)

class ShortcutManager:
    def setup_shortcuts(self, window):
        QShortcut(QKeySequence("Ctrl+O"), window, window.select_folder)
        QShortcut(QKeySequence("F5"), window, lambda: window.load_folder(window.current_folder))
        QShortcut(QKeySequence("Ctrl+Q"), window, window.close)

class MainWindow(QMainWindow):
    def __init__(self):
        
        super().__init__()

        self.APP_DIR = Path(__file__).resolve().parent
      
        icon_path = self.APP_DIR / "assets" / "app_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.APP_DIR = Path(__file__).resolve().parent
        self.lang_manager = LanguageManager()
        self.setWindowTitle(self.lang_manager.get('app_title'))
        self.resize(1200, 800)
        self.setAcceptDrops(True)
        
        self.settings = SettingsManager()
        self.plugin_host = PluginHost(self)
        self.theme_manager = ThemeManager()
        self.recent_menu = RecentFoldersMenu(self, self.lang_manager)
        self.current_folder = None
        self.worker = None
        self.analyzer = None
        
        self.setup_ui()
        self.setup_menu_bar()
        self.reload_plugins()
        self.setup_shortcuts()
        self.load_settings()
        saved_theme = self.settings.load_setting('theme', 'dark')
        self.theme_manager.apply_theme(self, saved_theme)
        
        language_signal.language_changed.connect(self.on_language_changed)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        self.file_tree = FileTreeView()
        self.file_tree.clicked.connect(self.on_tree_clicked)
        splitter.addWidget(self.file_tree)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        dash_layout = QHBoxLayout()
        self.card_total = StatCard(self.lang_manager.get('total'), 'fa5s.folder', '#007ACC')
        self.card_img = StatCard(self.lang_manager.get('images'), 'fa5s.image', '#28A745')
        self.card_vid = StatCard(self.lang_manager.get('videos'), 'fa5s.video', '#FFC107')
        self.card_size = StatCard(self.lang_manager.get('size'), 'fa5s.hdd', '#DC3545')
        dash_layout.addWidget(self.card_total)
        dash_layout.addWidget(self.card_img)
        dash_layout.addWidget(self.card_vid)
        dash_layout.addWidget(self.card_size)
        right_layout.addLayout(dash_layout)
        
        self.preview_widget = PreviewWidget(self.lang_manager)
        right_layout.addWidget(self.preview_widget)

        self.filter_bar = QuickFilterBar(self.lang_manager)
        self.filter_bar.btn_filter.clicked.connect(self.apply_filters)
        right_layout.addWidget(self.filter_bar)

        drop_layout = QHBoxLayout()
        self.lbl_folder = QLabel(self.lang_manager.get('select_folder'))
        self.lbl_folder.setStyleSheet("font-size: 14px; color: #AAA; font-style: italic; padding: 10px;")
        drop_layout.addWidget(self.lbl_folder, stretch=1)
        self.drop_area = EnhancedDropArea(self.lang_manager)
        drop_layout.addWidget(self.drop_area, stretch=1)
        right_layout.addLayout(drop_layout)

        self.tabs = QTabWidget()
        self.tabs.setEnabled(False)
        self.setup_tabs()
        right_layout.addWidget(self.tabs)

        self.progress = SmartProgressBar()
        right_layout.addWidget(self.progress)
        self.txt_log = QTextEdit()
        self.txt_log.setMaximumHeight(120)
        right_layout.addWidget(self.txt_log)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])
        main_layout.addWidget(splitter)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def setup_tabs(self):
        def create_conflict_combo():
            combo = QComboBox()
            combo.addItem(self.lang_manager.get('copy'), 'copy')
            combo.addItem(self.lang_manager.get('overwrite'), 'overwrite')
            combo.addItem(self.lang_manager.get('skip'), 'skip')
            return combo
        
        tab_org = QWidget()
        l_org = QVBoxLayout(tab_org)
        l_org.setAlignment(Qt.AlignTop)
        self.lbl_org_desc = QLabel(self.lang_manager.get('organize_desc'))
        l_org.addWidget(self.lbl_org_desc)
        h_sort = QHBoxLayout()
        self.lbl_mode = QLabel(self.lang_manager.get('mode'))
        h_sort.addWidget(self.lbl_mode)
        self.combo_org = QComboBox()
        self.combo_org.addItem(self.lang_manager.get('by_day'), 'by_day')
        self.combo_org.addItem(self.lang_manager.get('by_month'), 'by_month')
        self.combo_org.addItem(self.lang_manager.get('by_year'), 'by_year')
        h_sort.addWidget(self.combo_org)
        l_org.addLayout(h_sort)
        h_conflict = QHBoxLayout()
        self.lbl_conf_org = QLabel(self.lang_manager.get('conflict'))
        h_conflict.addWidget(self.lbl_conf_org)
        self.combo_conf_org = create_conflict_combo()
        h_conflict.addWidget(self.combo_conf_org)
        l_org.addLayout(h_conflict)
        self.btn_run_org = QPushButton(self.lang_manager.get('start_organize'))
        self.btn_run_org.clicked.connect(self.run_organizer)
        l_org.addWidget(self.btn_run_org)
        self.tabs.addTab(tab_org, self.lang_manager.get('organize'))
        
        tab_clean = QWidget()
        l_clean = QVBoxLayout(tab_clean)
        l_clean.setAlignment(Qt.AlignTop)
        self.lbl_clean_desc = QLabel(self.lang_manager.get('clean_desc'))
        l_clean.addWidget(self.lbl_clean_desc)
        h_conf_clean = QHBoxLayout()
        self.lbl_conf_clean = QLabel(self.lang_manager.get('conflict'))
        h_conf_clean.addWidget(self.lbl_conf_clean)
        self.combo_conf_clean = create_conflict_combo()
        h_conf_clean.addWidget(self.combo_conf_clean)
        l_clean.addLayout(h_conf_clean)
        self.btn_clean = QPushButton(self.lang_manager.get('clean_duplicates'))
        self.btn_clean.setStyleSheet("background-color: #D32F2F;")
        self.btn_clean.clicked.connect(self.run_cleaner)
        l_clean.addWidget(self.btn_clean)
        self.tabs.addTab(tab_clean, self.lang_manager.get('clean'))
        
        tab_conv = QWidget()
        l_conv = QVBoxLayout(tab_conv)
        l_conv.setAlignment(Qt.AlignTop)
        self.lbl_conv_desc = QLabel(self.lang_manager.get('convert_desc'))
        l_conv.addWidget(self.lbl_conv_desc)
        h_conv = QHBoxLayout()
        self.lbl_target = QLabel(self.lang_manager.get('target'))
        h_conv.addWidget(self.lbl_target)
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems([".jpg", ".png", ".webp", ".bmp"])
        h_conv.addWidget(self.combo_fmt)
        l_conv.addLayout(h_conv)
        h_conf_conv = QHBoxLayout()
        self.lbl_conf_conv = QLabel(self.lang_manager.get('conflict'))
        h_conf_conv.addWidget(self.lbl_conf_conv)
        self.combo_conf_conv = create_conflict_combo()
        h_conf_conv.addWidget(self.combo_conf_conv)
        l_conv.addLayout(h_conf_conv)
        self.btn_conv = QPushButton(self.lang_manager.get('convert_btn'))
        self.btn_conv.setStyleSheet("background-color: #E67E22;")
        self.btn_conv.clicked.connect(self.run_converter)
        l_conv.addWidget(self.btn_conv)
        self.tabs.addTab(tab_conv, self.lang_manager.get('convert'))
        
        tab_priv = QWidget()
        l_priv = QVBoxLayout(tab_priv)
        l_priv.setAlignment(Qt.AlignTop)
        self.lbl_priv_desc = QLabel(self.lang_manager.get('privacy_desc'))
        l_priv.addWidget(self.lbl_priv_desc)
        h_conf_priv = QHBoxLayout()
        self.lbl_conf_priv = QLabel(self.lang_manager.get('conflict'))
        h_conf_priv.addWidget(self.lbl_conf_priv)
        self.combo_conf_priv = create_conflict_combo()
        h_conf_priv.addWidget(self.combo_conf_priv)
        l_priv.addLayout(h_conf_priv)
        self.btn_priv = QPushButton(self.lang_manager.get('privacy_btn'))
        self.btn_priv.setStyleSheet("background-color: #6c757d;")
        self.btn_priv.clicked.connect(self.run_privacy)
        l_priv.addWidget(self.btn_priv)
        self.tabs.addTab(tab_priv, self.lang_manager.get('privacy'))
        
        tab_fix = QWidget()
        l_fix = QVBoxLayout(tab_fix)
        l_fix.setAlignment(Qt.AlignTop)
        self.lbl_fix_desc = QLabel(self.lang_manager.get('repair_desc'))
        l_fix.addWidget(self.lbl_fix_desc)
        h_conf_fix = QHBoxLayout()
        self.lbl_conf_fix = QLabel(self.lang_manager.get('conflict'))
        h_conf_fix.addWidget(self.lbl_conf_fix)
        self.combo_conf_fix = create_conflict_combo()
        h_conf_fix.addWidget(self.combo_conf_fix)
        l_fix.addLayout(h_conf_fix)
        self.btn_fix = QPushButton(self.lang_manager.get('repair_btn'))
        self.btn_fix.clicked.connect(self.run_repair)
        l_fix.addWidget(self.btn_fix)
        self.tabs.addTab(tab_fix, self.lang_manager.get('repair'))

    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        self.file_menu = menubar.addMenu(self.lang_manager.get('file'))
        self.open_action = QAction(self.lang_manager.get('open_folder'), self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.select_folder)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addMenu(self.recent_menu)
        self.exit_action = QAction(self.lang_manager.get('exit'), self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)
        
        self.tools_menu = menubar.addMenu(self.lang_manager.get('tools'))
        self.plugins_menu_action = self.tools_menu.addMenu(self.lang_manager.get('plugins'))
        self.rename_action = QAction(self.lang_manager.get('batch_rename'), self)
        self.rename_action.triggered.connect(self.open_batch_rename)
        self.tools_menu.addAction(self.rename_action)
        self.plugin_action = QAction(self.lang_manager.get('plugin_manager'), self)
        self.plugin_action.triggered.connect(self.open_plugin_manager)
        self.tools_menu.addAction(self.plugin_action)
        
        self.view_menu = menubar.addMenu(self.lang_manager.get('view'))
        self.theme_menu = self.view_menu.addMenu(self.lang_manager.get('themes'))
        self.action_dark = QAction(self.lang_manager.get('dark_theme'), self)
        self.action_dark.triggered.connect(lambda: self.set_theme('dark'))
        self.theme_menu.addAction(self.action_dark)
        self.action_light = QAction(self.lang_manager.get('light_theme'), self)
        self.action_light.triggered.connect(lambda: self.set_theme('light'))
        self.theme_menu.addAction(self.action_light)
        
        self.lang_menu = self.view_menu.addMenu(self.lang_manager.get('language'))
        self.action_tr = QAction("Türkçe", self)
        self.action_tr.triggered.connect(lambda: self.change_language('TR'))
        self.lang_menu.addAction(self.action_tr)
        self.action_en = QAction("English", self)
        self.action_en.triggered.connect(lambda: self.change_language('EN'))
        self.lang_menu.addAction(self.action_en)

    def change_language(self, lang):
        self.lang_manager.set_language(lang)

    def on_language_changed(self, lang):
        self.update_ui_language()

    def set_theme(self, theme_name):
        self.settings.save_setting('theme', theme_name)
        self.theme_manager.apply_theme(self, theme_name)

    def reload_plugins(self):
        disabled = self.settings.load_setting('disabled_plugins', [])
        if disabled is None:
            disabled = []
        if isinstance(disabled, str):
            disabled = [disabled]
        try:
            disabled = list(disabled)
        except Exception:
            disabled = []

        self.plugin_host.unload_all()
        self.plugin_host.load(disabled_filenames=disabled)
        try:
            self.plugin_host.build_menu(self.plugins_menu_action)
        except Exception:
            pass

    def update_ui_language(self):
        self.setWindowTitle(self.lang_manager.get('app_title'))
        
        self.lbl_folder.setText(self.lang_manager.get('select_folder'))
        self.card_total.lbl_title.setText(self.lang_manager.get('total'))
        self.card_img.lbl_title.setText(self.lang_manager.get('images'))
        self.card_vid.lbl_title.setText(self.lang_manager.get('videos'))
        self.card_size.lbl_title.setText(self.lang_manager.get('size'))
        
        self.file_menu.setTitle(self.lang_manager.get('file'))
        self.open_action.setText(self.lang_manager.get('open_folder'))
        self.exit_action.setText(self.lang_manager.get('exit'))
        
        self.tools_menu.setTitle(self.lang_manager.get('tools'))
        self.rename_action.setText(self.lang_manager.get('batch_rename'))
        self.plugin_action.setText(self.lang_manager.get('plugin_manager'))
        if hasattr(self, 'plugins_menu_action'):
            self.plugins_menu_action.setTitle(self.lang_manager.get('plugins'))
        
        self.view_menu.setTitle(self.lang_manager.get('view'))
        self.theme_menu.setTitle(self.lang_manager.get('themes'))
        self.action_dark.setText(self.lang_manager.get('dark_theme'))
        self.action_light.setText(self.lang_manager.get('light_theme'))
        self.lang_menu.setTitle(self.lang_manager.get('language'))
        
        self.lbl_org_desc.setText(self.lang_manager.get('organize_desc'))
        self.lbl_mode.setText(self.lang_manager.get('mode'))
        self.lbl_conf_org.setText(self.lang_manager.get('conflict'))
        self.btn_run_org.setText(self.lang_manager.get('start_organize'))
        self.tabs.setTabText(0, self.lang_manager.get('organize'))
        
        self.lbl_clean_desc.setText(self.lang_manager.get('clean_desc'))
        self.lbl_conf_clean.setText(self.lang_manager.get('conflict'))
        self.btn_clean.setText(self.lang_manager.get('clean_duplicates'))
        self.tabs.setTabText(1, self.lang_manager.get('clean'))
        
        self.lbl_conv_desc.setText(self.lang_manager.get('convert_desc'))
        self.lbl_target.setText(self.lang_manager.get('target'))
        self.lbl_conf_conv.setText(self.lang_manager.get('conflict'))
        self.btn_conv.setText(self.lang_manager.get('convert_btn'))
        self.tabs.setTabText(2, self.lang_manager.get('convert'))
        
        self.lbl_priv_desc.setText(self.lang_manager.get('privacy_desc'))
        self.lbl_conf_priv.setText(self.lang_manager.get('conflict'))
        self.btn_priv.setText(self.lang_manager.get('privacy_btn'))
        self.tabs.setTabText(3, self.lang_manager.get('privacy'))
        
        self.lbl_fix_desc.setText(self.lang_manager.get('repair_desc'))
        self.lbl_conf_fix.setText(self.lang_manager.get('conflict'))
        self.btn_fix.setText(self.lang_manager.get('repair_btn'))
        self.tabs.setTabText(4, self.lang_manager.get('repair'))
        
        self.filter_bar.update_language(self.lang_manager)
        self.recent_menu.update_language(self.lang_manager)

    # Yardımcı fonksiyon: Seçili veriyi (userData) koruyarak içeriği yeniler
        def update_combo_items(combo, keys):
            current_data = combo.currentData()
            combo.clear()
            for key in keys:
                combo.addItem(self.lang_manager.get(key), key)
            if current_data is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == current_data:
                        combo.setCurrentIndex(i)
                        break

        # 1. Çakışma (Conflict) ComboBox'ları için anahtarlar
        conflict_keys = ['copy', 'overwrite', 'skip']
        
        # Tüm sekmelerdeki conflict kutularını güncelle
        update_combo_items(self.combo_conf_org, conflict_keys)
        update_combo_items(self.combo_conf_clean, conflict_keys)
        update_combo_items(self.combo_conf_conv, conflict_keys)
        update_combo_items(self.combo_conf_priv, conflict_keys)
        update_combo_items(self.combo_conf_fix, conflict_keys)

        # 2. Düzenleme Modu (Organize Mode) ComboBox'ı
        org_mode_keys = ['by_day', 'by_month', 'by_year']
        update_combo_items(self.combo_org, org_mode_keys)
    
    def on_tree_clicked(self, index):
        path = self.file_tree.model.filePath(index)
        
        # Eğer klasörse, klasörü yükle (eski mantık)
        if os.path.isdir(path):
            self.load_folder(path)
            self.preview_widget.reset_preview() # Klasör seçilince önizlemeyi temizle
        
        # Eğer dosyaysa, önizlemeyi göster (YENİ)
        elif os.path.isfile(path):
            self.preview_widget.show_image(path)
            
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.lang_manager.get('select_folder_dialog'))
        if folder: self.load_folder(folder)
    
    def load_folder(self, folder):
        if self.analyzer is not None and self.analyzer.isRunning():
            self.analyzer.requestInterruption()
            self.analyzer.wait()

        self.current_folder = folder
        self.lbl_folder.setText(self.lang_manager.get('selected').format(folder))
        self.tabs.setEnabled(True)
        self.log(self.lang_manager.get('folder_loaded').format(folder))
        self.recent_menu.add_folder(folder)

        idx = self.file_tree.model.index(folder)
        self.file_tree.setCurrentIndex(idx)
        self.file_tree.expand(idx)

        self.analyzer = AnalyzerWorker(folder)
        self.analyzer.finished_signal.connect(self.update_dashboard)
        self.analyzer.start()
    
    def refresh_folder(self):
        if self.current_folder: self.load_folder(self.current_folder)

    def open_batch_rename(self):
        if not self.current_folder:
            QMessageBox.warning(self, self.lang_manager.get('warning'), 
                              self.lang_manager.get('select_first'))
            return
        files = [Path(f) for f in glob.glob(os.path.join(self.current_folder, "*.*"))]
        dialog = BatchRenameDialog(self, files, self.lang_manager)
        if dialog.exec_():
            renamer = BatchRenamer()
            pattern = dialog.get_current_pattern()
            if not pattern:
                QMessageBox.warning(self, self.lang_manager.get('error'), 
                                  self.lang_manager.get('invalid_pattern'))
                return
            try:
                renamer.rename_files(files, pattern)
                self.log(self.lang_manager.get('batch_completed').format(pattern))
                self.refresh_folder()
            except Exception as e:
                self.log(self.lang_manager.get('rename_error').format(e))

    def apply_filters(self):
        f_type = self.filter_bar.type_filter.currentText()
        f_size = self.filter_bar.size_filter.currentText()
        self.log(self.lang_manager.get('filters_applied').format(f_type, f_size))

    def open_plugin_manager(self):
        dialog = PluginManagerDialog(self, plugin_dir=str(self.APP_DIR / "plugins"), lang_manager=self.lang_manager)
        dialog.exec_()

    def connect_worker(self, worker):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, self.lang_manager.get('busy'), 
                              self.lang_manager.get('operation_progress'))
            return
        self.worker = worker
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.progress.setValue(0)
        self.txt_log.clear()
        self.worker.start()

    def run_organizer(self):
        self.connect_worker(OrganizerWorker(self.current_folder, self.combo_org.currentData() or self.combo_org.currentText(), self.combo_conf_org.currentData() or self.combo_conf_org.currentText(), self.lang_manager))
    
    def run_cleaner(self):
        self.connect_worker(CleanerWorker(self.current_folder, self.combo_conf_clean.currentData() or self.combo_conf_clean.currentText(), self.lang_manager))
    
    def run_converter(self):
        self.connect_worker(ConverterWorker(self.current_folder, self.combo_fmt.currentText(), self.combo_conf_conv.currentData() or self.combo_conf_conv.currentText(), self.lang_manager))
    
    def run_privacy(self):
        self.connect_worker(PrivacyWorker(self.current_folder, self.combo_conf_priv.currentData() or self.combo_conf_priv.currentText(), self.lang_manager))
    
    def run_repair(self):
        out_folder = QFileDialog.getExistingDirectory(self, self.lang_manager.get('save_location'))
        if out_folder: self.connect_worker(InpaintWorker(self.current_folder, out_folder, self.combo_conf_fix.currentData() or self.combo_conf_fix.currentText(), self.lang_manager))

    def on_worker_finished(self):
        QMessageBox.information(self, self.lang_manager.get('completed'), 
                              self.lang_manager.get('success'))
        if self.worker: self.worker.deleteLater(); self.worker = None
        self.refresh_folder()
    
    def log(self, msg):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')

        color = "#E0E0E0"
        if "❌" in msg or "Error" in msg or "Hata" in msg:
            color = "#FF5252"
        elif "✅" in msg or "Success" in msg or "Tamamlandı" in msg or "Başarılı" in msg:
            color = "#69F0AE"
        elif "⚠️" in msg or "Skipped" in msg or "Duplicate" in msg or "Atlandı" in msg or "Kopya" in msg:
            color = "#FFD740"
        elif "🚀" in msg or "Started" in msg or "Başladı" in msg:
            color = "#448AFF"

        formatted_msg = f'<span style="color:#888;">[{timestamp}]</span> <span style="color:{color};">{msg}</span>'
        self.txt_log.append(formatted_msg)

        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())
    
    def update_dashboard(self, stats):
        self.card_total.set_value(stats["images"] + stats["videos"] + stats["others"])
        self.card_img.set_value(stats["images"])
        self.card_vid.set_value(stats["videos"])
        self.card_size.set_value(f"{stats['size_mb']} MB")
        self.log(self.lang_manager.get('analysis_updated'))
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()
    
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files and os.path.isdir(files[0]): self.load_folder(files[0])
   
    def setup_shortcuts(self):
        self.shortcut_manager = ShortcutManager()
        self.shortcut_manager.setup_shortcuts(self)
   
    def load_settings(self):
        geo = self.settings.load_setting('window_geometry')
        if geo: self.restoreGeometry(geo)
        last = self.settings.load_setting('last_used_folder')
        if last and os.path.isdir(last): self.load_folder(last)
    
    def closeEvent(self, event):
        self.settings.save_setting('window_geometry', self.saveGeometry())
        if self.current_folder: self.settings.save_setting('last_used_folder', self.current_folder)
        event.accept()

def global_exception_handler(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("Unexpected Error:", error_msg)
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Unexpected Error Occurred")
    msg.setText("An unexpected error occurred while running the application.")
    msg.setInformativeText("Please report this error to the developer.")
    msg.setDetailedText(error_msg)
    msg.exec()

if __name__ == "__main__":
    sys.excepthook = global_exception_handler

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())