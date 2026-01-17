import sys
import os
import importlib.util
import qtawesome as qta
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QProgressBar, QWidget, QHBoxLayout,
    QComboBox, QPushButton, QTreeView, QFileSystemModel, QDialog,
    QLineEdit, QListWidget, QDialogButtonBox, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction,QPixmap


from utils import BatchRenamer
from languages import language_signal


try:
    from plugin_interface import PluginInterface
except ImportError:
    PluginInterface = None

class StatCard(QFrame):
    def __init__(self, title, icon_name, color):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #2D2D30;
                border-radius: 10px;
                border: 1px solid #3E3E42;
            }}
            QLabel {{ border: none; background: transparent; font-family: 'Segoe UI'; }}
        """)
        
        layout = QVBoxLayout(self)
        
        # --- Üst Kısım: İkon ve Başlık ---
        header_layout = QHBoxLayout()
        
        # İkon (Sol Üst)
        self.icon_label = QLabel()
        try:
            # Eğer qtawesome yüklü değilse hata vermesin diye try-except
            icon_pixmap = qta.icon(icon_name, color=color).pixmap(24, 24)
            self.icon_label.setPixmap(icon_pixmap)
        except:
            self.icon_label.setText("▪") # Fallback
            self.icon_label.setStyleSheet(f"color: {color}; font-size: 20px;")
        
        # Başlık (İkonun Yanı) - BURASI DÜZELDİ: self.lbl_title yapıldı
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: #CCCCCC; font-weight: 600; font-size: 12px;")
        
        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # --- Alt Kısım: Değer ---
        self.lbl_value = QLabel("-")
        self.lbl_value.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        self.lbl_value.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_value)
        
    def set_value(self, value):
        self.lbl_value.setText(str(value))

class SmartProgressBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444;
                border-radius: 10px;
                text-align: center;
                background-color: #252526;
                color: white;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007ACC, stop:0.5 #68217A, stop:1 #D32F2F
                );
                border-radius: 10px;
            }
        """)

class EnhancedDropArea(QFrame):
    def __init__(self, lang_manager=None):
        super().__init__()
        self.lang_manager = lang_manager
        self.setAcceptDrops(True)
        self.setup_ui()
        language_signal.language_changed.connect(self.update_language)
        
    def setup_ui(self):
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #555;
                border-radius: 10px;
                background-color: rgba(45, 45, 48, 0.5);
            }
            QFrame:hover {
                border-color: #007ACC;
                background-color: rgba(0, 122, 204, 0.1);
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        drag_text = self.lang_manager.get('drag_files') if self.lang_manager else '📂 Drag Files Here'
        self.text = QLabel(drag_text)
        self.text.setStyleSheet("color: #AAA; font-weight: bold; font-size: 14px; border: none;")
        layout.addWidget(self.text)
    
    def update_language(self):
        if self.lang_manager:
            self.text.setText(self.lang_manager.get('drag_files'))

class QuickFilterBar(QWidget):
    def __init__(self, lang_manager=None, parent=None):
        super().__init__(parent)
        self.lang_manager = lang_manager
        self.setup_ui()
        language_signal.language_changed.connect(self.on_language_changed)
    
    def on_language_changed(self):
        self.update_language()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        
        self.type_filter = QComboBox()
        type_items = [
            self.lang_manager.get('all') if self.lang_manager else 'All',
            self.lang_manager.get('pictures') if self.lang_manager else 'Pictures',
            self.lang_manager.get('video_label') if self.lang_manager else 'Videos',
            self.lang_manager.get('other') if self.lang_manager else 'Other',
        ]
        self.type_filter.addItems(type_items)
        self.lbl_type = QLabel(self.lang_manager.get('type') if self.lang_manager else 'Type:')
        layout.addWidget(self.lbl_type)
        layout.addWidget(self.type_filter)
        
        self.size_filter = QComboBox()
        size_items = [
            self.lang_manager.get('all') if self.lang_manager else 'All',
            self.lang_manager.get('small') if self.lang_manager else 'Small (<1MB)',
            self.lang_manager.get('medium') if self.lang_manager else 'Medium (1-10MB)',
            self.lang_manager.get('large') if self.lang_manager else 'Large (>10MB)',
        ]
        self.size_filter.addItems(size_items)
        self.lbl_size = QLabel(self.lang_manager.get('size_label') if self.lang_manager else 'Size:')
        layout.addWidget(self.lbl_size)
        layout.addWidget(self.size_filter)
        
        filter_text = self.lang_manager.get('filter') if self.lang_manager else '🔍 Filter'
        self.btn_filter = QPushButton(filter_text)
        self.btn_filter.setStyleSheet("background-color: #333; padding: 5px 10px;")
        layout.addWidget(self.btn_filter)

    def update_language(self, lang_manager=None):
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        type_items = [
            self.lang_manager.get('all'),
            self.lang_manager.get('pictures'),
            self.lang_manager.get('video_label'),
            self.lang_manager.get('other'),
        ]
        current_type = self.type_filter.currentIndex()
        self.type_filter.clear()
        self.type_filter.addItems(type_items)
        self.type_filter.setCurrentIndex(max(0, current_type))
        
        size_items = [
            self.lang_manager.get('all'),
            self.lang_manager.get('small'),
            self.lang_manager.get('medium'),
            self.lang_manager.get('large'),
        ]
        current_size = self.size_filter.currentIndex()
        self.size_filter.clear()
        self.size_filter.addItems(size_items)
        self.size_filter.setCurrentIndex(max(0, current_size))
        
        self.lbl_type.setText(self.lang_manager.get('type'))
        self.lbl_size.setText(self.lang_manager.get('size_label'))
        self.btn_filter.setText(self.lang_manager.get('filter'))

class FileTreeView(QTreeView):
    def __init__(self):
        super().__init__()
        self.model = QFileSystemModel()
        self.model.setRootPath("") 
        self.setModel(self.model)
        self.setColumnWidth(0, 250)
        self.hideColumn(1) 
        self.hideColumn(2) 
        self.hideColumn(3) 
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setHeaderHidden(True)

class BatchRenameDialog(QDialog):
    def __init__(self, parent=None, files=[], lang_manager=None):
        super().__init__(parent)
        self.files = files
        self.lang_manager = lang_manager
        self.setup_ui()
        language_signal.language_changed.connect(self.update_language)
        
    def setup_ui(self):
        title = self.lang_manager.get('batch_rename_title') if self.lang_manager else 'Batch Rename'
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        
        pattern_label = self.lang_manager.get('pattern') if self.lang_manager else 'Pattern:'
        layout.addWidget(QLabel(pattern_label))
        self.pattern_combo = QComboBox()
        pattern_items = [
            self.lang_manager.get('original_name') if self.lang_manager else 'Original Name',
            self.lang_manager.get('date_sequence') if self.lang_manager else 'Date_Sequence (e.g: 20240101_001)',
            self.lang_manager.get('sequence_name') if self.lang_manager else 'Sequence_Name (e.g: 001_photo)',
            self.lang_manager.get('name_date') if self.lang_manager else 'Name_Date (e.g: photo_20240101)',
            self.lang_manager.get('custom_pattern') if self.lang_manager else 'Custom Pattern',
        ]
        self.pattern_combo.addItems(pattern_items)
        layout.addWidget(self.pattern_combo)
        
        custom_label = self.lang_manager.get('custom_pattern_label') if self.lang_manager else 'Custom Pattern (e.g: {name}_{date}_{counter}):'
        layout.addWidget(QLabel(custom_label))
        self.custom_pattern = QLineEdit()
        self.custom_pattern.setPlaceholderText("{name}_{date}_{counter}{ext}")
        layout.addWidget(self.custom_pattern)
        
        preview_label = self.lang_manager.get('preview') if self.lang_manager else 'Preview:'
        layout.addWidget(QLabel(preview_label))
        self.preview_list = QListWidget()
        layout.addWidget(self.preview_list)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.pattern_combo.currentIndexChanged.connect(self.update_preview)
        self.custom_pattern.textChanged.connect(self.update_preview)
        self.update_preview()
    
    def update_language(self):
        if not self.lang_manager:
            return

    def update_preview(self):
        self.preview_list.clear()
        pattern = self.get_current_pattern()
        if not pattern: return
        
        renamer = BatchRenamer()
        for i, file in enumerate(self.files[:5]): 
            try:
                new_name = renamer.apply_pattern(file, pattern, i+1)
                self.preview_list.addItem(f"{file.name} → {new_name}")
            except: pass

    def get_current_pattern(self):
        index = self.pattern_combo.currentIndex()
        if index == 4:
            return self.custom_pattern.text() + "{ext}"
        elif index == 1:
            return "{date}_{counter:03d}{ext}"
        elif index == 2:
            return "{counter:03d}_{name}{ext}"
        elif index == 3:
            return "{name}_{date}{ext}"
        else:
            return "{name}{ext}"

class RecentFoldersMenu(QMenu):
    def __init__(self, parent=None, lang_manager=None):
        super().__init__(self._get_title(lang_manager), parent)
        self.lang_manager = lang_manager
        self.max_recent = 10
        self.recent_folders = []
        self.load_recent_folders()
        language_signal.language_changed.connect(self.on_language_changed)
        
    def _get_title(self, lang_manager):
        return lang_manager.get('recent') if lang_manager else 'Recent Folders'
        
    def on_language_changed(self):
        if self.lang_manager:
            self.setTitle(self.lang_manager.get('recent'))
    
    def load_recent_folders(self):
        settings = QSettings("MediaManager", "Pro")
        self.recent_folders = settings.value("recent_folders", [])
        self.update_menu()
        
    def save_recent_folders(self):
        settings = QSettings("MediaManager", "Pro")
        settings.setValue("recent_folders", self.recent_folders[:self.max_recent])
        
    def add_folder(self, folder):
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        self.recent_folders = self.recent_folders[:self.max_recent]
        self.save_recent_folders()
        self.update_menu()
        
    def update_menu(self):
        self.clear()
        for folder in self.recent_folders:
            action = QAction(folder, self)
            action.triggered.connect(lambda checked, f=folder: self.parent().load_folder(f))
            self.addAction(action)
    
    def update_language(self, lang_manager):
        self.lang_manager = lang_manager
        if self.lang_manager:
            self.setTitle(self.lang_manager.get('recent'))


class PluginManagerDialog(QDialog):
    """Manage plugins: enable/disable + run.

    This dialog is intentionally simple: it stores disabled plugins in QSettings
    under the key `disabled_plugins`.
    """

    def __init__(self, main_window, plugin_dir="plugins", lang_manager=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.plugin_dir = plugin_dir
        self.lang_manager = lang_manager
        self.loaded_plugins = {}  # filename -> plugin instance
        self.load_errors = {}     # filename -> error string

        self.settings = QSettings("MediaManager", "Pro")

        title = self._t('plugin_manager_title', 'Plugin Manager')
        self.setWindowTitle(title)
        self.resize(560, 420)

        self.setup_ui()
        self.load_plugins()
        language_signal.language_changed.connect(self.update_language)

    def _t(self, key, fallback):
        return self.lang_manager.get(key) if self.lang_manager else fallback

    def setup_ui(self):
        layout = QVBoxLayout(self)

        plugin_label = self._t('detected_plugins', '📂 Detected Plugins:')
        layout.addWidget(QLabel(plugin_label))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        desc_text = self._t('description_label', 'Description:')
        self.lbl_desc = QLabel(f"{desc_text} -")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.lbl_desc)

        btn_layout = QHBoxLayout()

        self.btn_apply = QPushButton(self._t('apply', '✅ Apply'))
        self.btn_apply.clicked.connect(self.apply_changes)
        btn_layout.addWidget(self.btn_apply)

        self.btn_run = QPushButton(self._t('run_plugin', '▶️ Run Selected'))
        self.btn_run.clicked.connect(self.run_selected_plugin)
        btn_layout.addWidget(self.btn_run)

        self.btn_refresh = QPushButton(self._t('refresh', '🔄 Refresh'))
        self.btn_refresh.clicked.connect(self.reload_plugins)
        btn_layout.addWidget(self.btn_refresh)

        layout.addLayout(btn_layout)

        self.list_widget.currentRowChanged.connect(self.update_description)

    def update_language(self):
        if not self.lang_manager:
            return

        self.setWindowTitle(self._t('plugin_manager_title', 'Plugin Manager'))
        self.btn_run.setText(self._t('run_plugin', '▶️ Run Selected'))
        self.btn_refresh.setText(self._t('refresh', '🔄 Refresh'))
        self.btn_apply.setText(self._t('apply', '✅ Apply'))

        # Refresh list texts (keep checks)
        self.reload_plugins()

    def disabled_list(self):
        v = self.settings.value('disabled_plugins', [])
        if v is None:
            return []
        if isinstance(v, str):
            # QSettings sometimes stores as a single string
            return [v]
        return list(v)

    def load_plugins(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem
        import importlib.util

        self.list_widget.clear()
        self.loaded_plugins = {}
        self.load_errors = {}

        os.makedirs(self.plugin_dir, exist_ok=True)

        disabled = set(self.disabled_list())

        for filename in sorted(os.listdir(self.plugin_dir)):
            if not filename.endswith('.py') or filename == '__init__.py':
                continue

            item = QListWidgetItem(filename)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked if filename in disabled else Qt.Checked)
            item.setData(Qt.UserRole, filename)

            # Try import to read metadata (name/version/description)
            path = os.path.join(self.plugin_dir, filename)
            module_name = f"pm_{filename[:-3]}"
            plugin_obj = None
            err = None
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    raise ImportError('Could not create import spec')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if not hasattr(module, 'Plugin'):
                    raise AttributeError("Missing 'Plugin' class")
                plugin_obj = module.Plugin()
            except Exception as e:
                err = str(e)

            if plugin_obj is not None:
                name = getattr(plugin_obj, 'name', filename[:-3])
                version = getattr(plugin_obj, 'version', '1.0')
                item.setText(f"{name} (v{version})")
                self.loaded_plugins[filename] = plugin_obj
            else:
                item.setText(f"{filename} (⚠️ load error)")
                self.load_errors[filename] = err or 'Unknown error'

            self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def update_description(self, index):
        from PySide6.QtCore import Qt

        if index < 0:
            desc_label = self._t('description_label', 'Description:')
            self.lbl_desc.setText(f"{desc_label} -")
            return

        item = self.list_widget.item(index)
        filename = item.data(Qt.UserRole)

        desc_label = self._t('description_label', 'Description:')

        if filename in self.load_errors:
            self.lbl_desc.setText(f"{desc_label} ⚠️ {self.load_errors[filename]}")
            return

        plugin = self.loaded_plugins.get(filename)
        desc = getattr(plugin, 'description', self._t('no_description', 'No description.'))
        self.lbl_desc.setText(f"{desc_label} {desc}")

    def apply_changes(self):
        from PySide6.QtCore import Qt

        disabled = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            filename = item.data(Qt.UserRole)
            if item.checkState() != Qt.Checked:
                disabled.append(filename)

        self.settings.setValue('disabled_plugins', disabled)

        # Let main window rebuild plugin menu
        if hasattr(self.main_window, 'reload_plugins'):
            try:
                self.main_window.reload_plugins()
            except Exception:
                pass

        try:
            self.main_window.log(self._t('plugin_reloaded', '🔌 Plugins reloaded.'))
        except Exception:
            pass

    def run_selected_plugin(self):
        from PySide6.QtCore import Qt

        idx = self.list_widget.currentRow()
        if idx < 0:
            QMessageBox.warning(self, self._t('warning', 'Warning'), self._t('select_plugin', 'Please select a plugin.'))
            return

        item = self.list_widget.item(idx)
        filename = item.data(Qt.UserRole)

        if filename in self.load_errors:
            QMessageBox.critical(self, self._t('error', 'Error'), f"{self._t('plugin_error', 'Plugin error:')} {self.load_errors[filename]}")
            return

        # Respect enabled state
        if item.checkState() != Qt.Checked:
            QMessageBox.information(self, self._t('warning', 'Warning'), self._t('plugin_disabled', 'This plugin is disabled. Enable it first.'))
            return

        plugin = self.loaded_plugins.get(filename)
        if not plugin:
            QMessageBox.critical(self, self._t('error', 'Error'), self._t('plugin_error', 'Plugin error:') + ' missing plugin object')
            return

        try:
            plugin.run(self.main_window)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, self._t('error', 'Error'), f"{self._t('plugin_error', 'Plugin error:')} {e}")

    def reload_plugins(self):
        self.load_plugins()


class PreviewWidget(QLabel):
    def __init__(self, lang_manager=None):
        super().__init__()
        self.lang_manager = lang_manager
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #1E1E1E;
                border: 2px dashed #444;
                border-radius: 8px;
                color: #666;
            }
        """)
        self.setMinimumHeight(200)
        self.setText("👁️ Önizleme Yok / No Preview")
    
    def show_image(self, path):
        if not path or not os.path.exists(path):
            return
            
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # Resmi orantılı olarak yeniden boyutlandır (maksimum yükseklik 250px)
                scaled_pixmap = pixmap.scaled(
                    self.width(), 250, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
                self.setStyleSheet("background-color: #1E1E1E; border: 1px solid #333;")
            else:
                self.reset_preview()
        else:
            self.setText(f"📁 {os.path.basename(path)}\n(Önizleme Yok)")
            self.setStyleSheet("background-color: #1E1E1E; border: 2px dashed #444; color: #AAA;")

    def reset_preview(self):
        self.clear() # Önce temizle
        # Dilden metni al, yoksa varsayılanı kullan
        msg = "Resim Seçilmedi"
        if self.lang_manager:
            # languages.py'ye 'no_preview' anahtarı ekleyebilirsin
            msg = self.lang_manager.get('no_preview', "Resim Seçilmedi")
            
        self.setText(msg)
        self.setStyleSheet("""
            QLabel {
                background-color: #1E1E1E;
                border: 2px dashed #444;
                border-radius: 8px;
                color: #666;
            }
        """)