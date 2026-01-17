import os
import shutil
import datetime
import glob

# Optional deps (keep the app usable even without the repair stack)
try:
    import cv2  # type: ignore
    CV2_AVAILABLE = True
except Exception:
    cv2 = None
    CV2_AVAILABLE = False

try:
    import numpy as np  # type: ignore
    NUMPY_AVAILABLE = True
except Exception:
    np = None
    NUMPY_AVAILABLE = False

try:
    from skimage import measure  # type: ignore
    SKIMAGE_AVAILABLE = True
except Exception:
    measure = None
    SKIMAGE_AVAILABLE = False
from pathlib import Path
from PIL import Image, UnidentifiedImageError 
from PySide6.QtCore import QThread, Signal

from utils import IMAGE_EXTS, VIDEO_EXTS
from utils import resolve_conflict, get_date_from_file, get_hash

class AnalyzerWorker(QThread):
    finished_signal = Signal(dict)
    
    def __init__(self, folder):
        super().__init__()
        self.folder = Path(folder)

    def run(self):
        stats = {"images": 0, "videos": 0, "others": 0, "size": 0}
        
        try:
            for file in self.folder.rglob("*.*"):
                if self.isInterruptionRequested():
                    return 

                if file.is_file():
                    ext = file.suffix.lower()
                    try: 
                        stats["size"] += file.stat().st_size
                    except PermissionError:
                        pass 
                    except: 
                        pass
                    
                    if ext in IMAGE_EXTS: stats["images"] += 1
                    elif ext in VIDEO_EXTS: stats["videos"] += 1
                    else: stats["others"] += 1
        except Exception: pass
        
        if not self.isInterruptionRequested():
            stats["size_mb"] = round(stats["size"] / (1024 * 1024), 2)
            self.finished_signal.emit(stats)

class OrganizerWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()
    
    def __init__(self, folder, mode, conflict, lang_manager=None):
        super().__init__()
        self.folder = Path(folder)
        self.mode = mode
        self.conflict = conflict
        self.lang_manager = lang_manager

    def run(self):
        files = list(self.folder.rglob("*.*"))
        total = len(files)
        if total == 0: self.finished_signal.emit(); return
        
        msg = self.lang_manager.get('start_organizing') if self.lang_manager else "🚀 Organizing Started..."
        self.log_signal.emit(msg)
        
        for i, file in enumerate(files):

            if self.isInterruptionRequested(): 
                msg = self.lang_manager.get('process_stopped') if self.lang_manager else "🛑 Process stopped by user."
                self.log_signal.emit(msg)
                self.finished_signal.emit()
                return 
            
            if not file.is_file(): continue
            
            date_str = get_date_from_file(file)
            if date_str:
                try:
                    dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    folder_name = date_str
                    if self.mode in ('by_year', 'year') or (isinstance(self.mode, str) and ('Year' in self.mode or 'Yıla' in self.mode)): 
                        folder_name = dt.strftime('%Y')
                    elif self.mode in ('by_month', 'month') or (isinstance(self.mode, str) and ('Month' in self.mode or 'Aya' in self.mode)): 
                        folder_name = dt.strftime('%Y-%m')
                    
                    target_dir = self.folder / folder_name
                    target_dir.mkdir(exist_ok=True)
                    
                    final_path, skip = resolve_conflict(target_dir / file.name, self.conflict, self.lang_manager)
                    
                    if not skip and final_path != file:
                        shutil.move(str(file), str(final_path))
                        msg = self.lang_manager.get('moved').format(file.name) if self.lang_manager else f"✅ Moved: {file.name}"
                        self.log_signal.emit(msg)
                    elif skip:
                        msg = self.lang_manager.get('skipped').format(file.name) if self.lang_manager else f"⏩ Skipped: {file.name}"
                        self.log_signal.emit(msg)
                
                except PermissionError:
                    msg = self.lang_manager.get('access_denied').format(file.name) if self.lang_manager else f"❌ Access Denied: {file.name}"
                    self.log_signal.emit(msg)
                except OSError as e:
                    msg = self.lang_manager.get('disk_error').format(file.name, e) if self.lang_manager else f"❌ Disk/File Error: {file.name} ({e})"
                    self.log_signal.emit(msg)
                except Exception as e: 
                    msg = self.lang_manager.get('unexpected_error_file').format(file.name, e) if self.lang_manager else f"❌ Unexpected Error: {file.name} ({e})"
                    self.log_signal.emit(msg)
                    
            self.progress_signal.emit(int((i + 1) / total * 100))
        self.finished_signal.emit()


class CleanerWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()

    def __init__(self, folder, conflict, lang_manager=None):
        super().__init__()
        self.folder = Path(folder)
        self.conflict = conflict
        self.lang_manager = lang_manager

    def run(self):
        files = [f for f in self.folder.rglob("*.*") if f.is_file()]
        total = len(files) or 1

        msg = self.lang_manager.get('scan_start') if self.lang_manager else "🔍 Duplicate scan started..."
        self.log_signal.emit(msg)

        # Optimization: group by size first. Different sizes can't be duplicates.
        size_map = {}
        for i, f in enumerate(files):
            if self.isInterruptionRequested():
                msg = self.lang_manager.get('process_stopped') if self.lang_manager else "🛑 Process stopped by user."
                self.log_signal.emit(msg)
                self.finished_signal.emit()
                return

            try:
                sz = f.stat().st_size
            except PermissionError:
                read_msg = self.lang_manager.get('read_error').format(f.name) if self.lang_manager else f"❌ Read Permission Denied: {f.name}"
                self.log_signal.emit(read_msg)
                continue
            except Exception:
                continue

            size_map.setdefault(sz, []).append(f)
            # first half of progress bar = scanning sizes
            self.progress_signal.emit(int((i + 1) / total * 50))

        hashes = {}
        duplicates = []

        # Second phase: hash only candidates with same size
        candidates = [grp for grp in size_map.values() if len(grp) > 1]
        cand_total = sum(len(g) for g in candidates) or 1
        done = 0

        for grp in candidates:
            for f in grp:
                if self.isInterruptionRequested():
                    msg = self.lang_manager.get('process_stopped') if self.lang_manager else "🛑 Process stopped by user."
                    self.log_signal.emit(msg)
                    self.finished_signal.emit()
                    return

                try:
                    f_hash = get_hash(f)
                    if not f_hash:
                        continue
                    if f_hash in hashes:
                        duplicates.append(f)
                        dup_msg = self.lang_manager.get('duplicate_found').format(f.name) if self.lang_manager else f"⚠️ Duplicate Found: {f.name}"
                        self.log_signal.emit(dup_msg)
                    else:
                        hashes[f_hash] = f
                except PermissionError:
                    read_msg = self.lang_manager.get('read_error').format(f.name) if self.lang_manager else f"❌ Read Permission Denied: {f.name}"
                    self.log_signal.emit(read_msg)
                except Exception:
                    pass

                done += 1
                self.progress_signal.emit(50 + int(done / cand_total * 25))

        # Move duplicates into a folder
        if duplicates:
            dup_folder = self.lang_manager.get('duplicate_folder') if self.lang_manager else "Duplicate_Files"
            target_dir = self.folder / dup_folder
            target_dir.mkdir(exist_ok=True)

            for i, dup in enumerate(duplicates):
                if self.isInterruptionRequested():
                    msg = self.lang_manager.get('process_stopped') if self.lang_manager else "🛑 Process stopped by user."
                    self.log_signal.emit(msg)
                    self.finished_signal.emit()
                    return

                try:
                    final_path, skip = resolve_conflict(target_dir / dup.name, self.conflict, self.lang_manager)
                    if not skip:
                        shutil.move(str(dup), str(final_path))
                        dup_msg = self.lang_manager.get('moved_to_duplicates').format(dup.name) if self.lang_manager else f"🗑️ Moved: {dup.name}"
                        self.log_signal.emit(dup_msg)
                    else:
                        skip_msg = self.lang_manager.get('skipped').format(dup.name) if self.lang_manager else f"⏩ Skipped: {dup.name}"
                        self.log_signal.emit(skip_msg)

                except PermissionError:
                    deny_msg = self.lang_manager.get('access_denied').format(dup.name) if self.lang_manager else f"❌ Access Denied: {dup.name}"
                    self.log_signal.emit(deny_msg)
                except OSError as e:
                    move_msg = self.lang_manager.get('move_error').format(dup.name, e) if self.lang_manager else f"❌ Move Error: {dup.name} ({e})"
                    self.log_signal.emit(move_msg)
                except Exception as e:
                    err_msg = self.lang_manager.get('error_file').format(dup.name, e) if self.lang_manager else f"❌ Error: {dup.name} ({e})"
                    self.log_signal.emit(err_msg)

                self.progress_signal.emit(75 + int((i + 1) / len(duplicates) * 25))

        self.progress_signal.emit(100)
        self.finished_signal.emit()


class ConverterWorker(QThread):

    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()
    
    def __init__(self, folder, target_format, conflict, lang_manager=None):
        super().__init__()
        self.folder = Path(folder)
        self.target_format = target_format.lower()
        self.conflict = conflict
        self.lang_manager = lang_manager

    def run(self):
        valid_exts = IMAGE_EXTS  
        files = [f for f in self.folder.rglob("*.*") if f.suffix.lower() in valid_exts]
        total = len(files)
        
        output_dir = self.folder / "Donusturulenler"
        output_dir.mkdir(exist_ok=True)
        
        conv_msg = self.lang_manager.get('converting').format(self.target_format) if self.lang_manager else f"🔄 Converting -> {self.target_format}"
        self.log_signal.emit(conv_msg)
        
        for i, file in enumerate(files):
            if self.isInterruptionRequested(): 
                msg = self.lang_manager.get('process_stopped') if self.lang_manager else "🛑 Process stopped by user."
                self.log_signal.emit(msg)
                self.finished_signal.emit()
                return 
            
            if file.suffix.lower() == self.target_format: continue
            
            try:
                img = Image.open(file)
                if self.target_format in ['.jpg', '.jpeg'] and img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                target_file = output_dir / (file.stem + self.target_format)
                final_path, skip = resolve_conflict(target_file, self.conflict, self.lang_manager)
                
                if not skip:
                    img.save(final_path, quality=95)
                    conv_done_msg = self.lang_manager.get('converted').format(file.name) if self.lang_manager else f"✅ Converted: {file.name}"
                    self.log_signal.emit(conv_done_msg)
                else:
                    skip_msg = self.lang_manager.get('skipped').format(file.name) if self.lang_manager else f"⏩ Skipped: {file.name}"
                    self.log_signal.emit(skip_msg)
            
            except UnidentifiedImageError:
                corrupt_msg = self.lang_manager.get('corrupt_image').format(file.name) if self.lang_manager else f"❌ Corrupt/Unknown Image: {file.name}"
                self.log_signal.emit(corrupt_msg)
            except PermissionError:
                deny_msg = self.lang_manager.get('access_denied').format(file.name) if self.lang_manager else f"❌ Access Denied: {file.name}"
                self.log_signal.emit(deny_msg)
            except OSError as e:
                save_msg = self.lang_manager.get('save_error').format(file.name, e) if self.lang_manager else f"❌ Save Error: {file.name} ({e})"
                self.log_signal.emit(save_msg)
            except Exception as e: 
                unk_msg = self.lang_manager.get('unknown_error').format(file.name, e) if self.lang_manager else f"❌ Unknown Error ({file.name}): {e}"
                self.log_signal.emit(unk_msg)
            
            self.progress_signal.emit(int((i + 1) / total * 100))
        self.finished_signal.emit()

class PrivacyWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()
    
    def __init__(self, folder, conflict, lang_manager=None):
        super().__init__()
        self.folder = Path(folder)
        self.conflict = conflict
        self.lang_manager = lang_manager

    def run(self):
        valid_exts = ['.jpg', '.jpeg', '.png', '.webp', '.tiff']
        files = [f for f in self.folder.rglob("*.*") if f.suffix.lower() in valid_exts]
        total = len(files)
        
        output_dir = self.folder / "Guvenli_Fotograflar"
        overwrite_mode = "Üstüne Yaz" in self.conflict or "Overwrite" in self.conflict
        
        if not overwrite_mode:
            output_dir.mkdir(exist_ok=True)
        
        clean_msg = self.lang_manager.get('cleaning_metadata') if self.lang_manager else "🛡️ Cleaning metadata..."
        self.log_signal.emit(clean_msg)
        
        for i, file in enumerate(files):
            if self.isInterruptionRequested(): 
                msg = self.lang_manager.get('process_stopped') if self.lang_manager else "🛑 Process stopped by user."
                self.log_signal.emit(msg)
                self.finished_signal.emit()
                return 

            try:
                img = Image.open(file)
                img.load()  
                
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(list(img.getdata()))
                
                img.close() 

                if overwrite_mode:
                    target_path = file 
                else:
                    target_path = output_dir / file.name

                final_path, skip = resolve_conflict(target_path, self.conflict, self.lang_manager)
                
                if not skip:
                    clean_img.save(final_path)
                    if target_path == file:
                        inplace_msg = self.lang_manager.get('cleaned_inplace').format(file.name) if self.lang_manager else f"🔒 Cleaned in place: {file.name}"
                        self.log_signal.emit(inplace_msg)
                    else:
                        folder_msg = self.lang_manager.get('saved_to_folder').format(file.name) if self.lang_manager else f"🔒 Saved to folder: {file.name}"
                        self.log_signal.emit(folder_msg)
                else:
                    skip_msg = self.lang_manager.get('skipped').format(file.name) if self.lang_manager else f"⏩ Skipped: {file.name}"
                    self.log_signal.emit(skip_msg)
                    
            except UnidentifiedImageError:
                corrupt_msg = self.lang_manager.get('corrupt_image').format(file.name) if self.lang_manager else f"❌ Corrupt Image: {file.name}"
                self.log_signal.emit(corrupt_msg)
            except PermissionError:
                deny_msg = self.lang_manager.get('access_denied').format(file.name) if self.lang_manager else f"❌ Access Denied: {file.name}"
                self.log_signal.emit(deny_msg)
            except Exception as e: 
                proc_msg = self.lang_manager.get('error_file').format(file.name, e) if self.lang_manager else f"❌ Error: {file.name} ({e})"
                self.log_signal.emit(proc_msg)
            
            self.progress_signal.emit(int((i + 1) / total * 100))
            
        self.finished_signal.emit()

class InpaintWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()
    
    def __init__(self, in_folder, out_folder, conflict, lang_manager=None):
        super().__init__()
        self.in_folder = in_folder
        self.out_folder = out_folder
        self.conflict = conflict
        self.lang_manager = lang_manager

    def run(self):
        # Bağımlılık kontrolü
        if not (CV2_AVAILABLE and NUMPY_AVAILABLE and SKIMAGE_AVAILABLE):
            msg = self.lang_manager.get('opencv_missing') if self.lang_manager else "❌ Repair feature requires opencv-python, numpy and scikit-image."
            self.log_signal.emit(msg)
            self.finished_signal.emit()
            return

        # Resimleri listele
        images = glob.glob(os.path.join(self.in_folder, '*.*'))
        total = len(images)
        
        repair_msg = self.lang_manager.get('repair_start') if self.lang_manager else "🔧 Repair started (Telea Algorithm)..."
        self.log_signal.emit(repair_msg)

        if total == 0:
            self.finished_signal.emit()
            return

        for i, path in enumerate(images):
            # İptal isteği kontrolü
            if self.isInterruptionRequested(): 
                msg = self.lang_manager.get('process_stopped') if self.lang_manager else "🛑 Process stopped by user."
                self.log_signal.emit(msg)
                self.finished_signal.emit()
                return 
            
            try:
                # Görüntü okuma
                img = cv2.imread(path)
                if img is None:
                    # CV2 okuyamazsa atla
                    continue

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(blurred, 100, 200)
                contours = measure.find_contours(edges, 0.8)
                mask = np.zeros(img.shape[:2], dtype=np.uint8)
                for c in contours:
                    c = np.array(c, dtype=np.int32)
                    cv2.fillPoly(mask, [c], 255)
                
                restored = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
                name = os.path.basename(path)
                output_path = os.path.join(self.out_folder, name)
                target_path = Path(output_path)
                
                # Çakışma kontrolü
                final_path, skip = resolve_conflict(target_path, self.conflict, self.lang_manager)
                
                if not skip:
                    # Klasör yoksa oluştur (Garanti olsun)
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    
                    success = cv2.imwrite(str(final_path), restored)
                    if success:
                        rep_msg = self.lang_manager.get('repaired').format(name) if self.lang_manager else f"✨ Repaired: {name}"
                        self.log_signal.emit(rep_msg)
                    else:
                        raise OSError("Could not write file to disk.")
                else:
                    skip_msg = self.lang_manager.get('skipped').format(name) if self.lang_manager else f"⏩ Skipped: {name}"
                    self.log_signal.emit(skip_msg)
            
            except Exception as e: 
                # Genel hata yakalama (cv2.error dahil)
                err_msg = self.lang_manager.get('error_file').format(os.path.basename(path), e) if self.lang_manager else f"❌ Error: {os.path.basename(path)} - {e}"
                self.log_signal.emit(err_msg)
                
            self.progress_signal.emit(int((i + 1) / total * 100))
        
        self.finished_signal.emit()