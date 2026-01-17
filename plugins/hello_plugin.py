from PySide6.QtWidgets import QMessageBox



class Plugin:
    name = "Merhaba Eklentisi"
    version = "1.2"
    description = "Ekrana basit bir mesaj kutusu çıkarır."

    def get_actions(self, main_window):

        from dataclasses import dataclass
        from typing import Optional, Callable, Any

        @dataclass
        class SimpleAction:
            text: str
            callback: Callable
            shortcut: Optional[str] = None
            status_tip: Optional[str] = None

        return [
            SimpleAction(
                text="Merhaba de", 
                callback=self.run
            ),
            SimpleAction(
                text="Hakkında",
                callback=lambda mw: QMessageBox.information(
                    mw,
                    "Merhaba Eklentisi",
                    "Bu örnek bir eklentidir.\n'plugins/' klasörüne eklenmiştir."
                )
            ),
        ]

    def run(self, main_window):
        if hasattr(main_window, 'log'):
            main_window.log("🔌 Merhaba Eklentisi çalıştı!")
            
        QMessageBox.information(main_window, "Plugin", "Merhaba! Ben eklenti tarafından oluşturuldum.")