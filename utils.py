import os
import shutil
import datetime
import hashlib
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.tiff'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv'}

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False


def resolve_conflict(target_path, mode, lang_manager=None):
    """Handle file conflicts when target path already exists.

    Supports stable mode codes:
      - 'overwrite'
      - 'skip'
      - 'copy'

    Backward compatible: also accepts localized UI texts (e.g. 'Üstüne Yaz', 'Overwrite').
    """
    if not target_path.exists():
        return target_path, False

    mode_code = None
    if isinstance(mode, str):
        m = mode.strip()
        ml = m.lower()
        if m in ('overwrite', 'skip', 'copy'):
            mode_code = m
        elif 'overwrite' in ml or 'üstüne yaz' in ml:
            mode_code = 'overwrite'
        elif 'skip' in ml or 'atla' in ml:
            mode_code = 'skip'
        else:
            # treat anything else as copy
            mode_code = 'copy'

    # Last resort: if LangManager provided and mode matches one of its translated labels
    if mode_code is None and lang_manager is not None and isinstance(mode, str):
        try:
            if mode == lang_manager.get('overwrite'):
                mode_code = 'overwrite'
            elif mode == lang_manager.get('skip'):
                mode_code = 'skip'
            elif mode == lang_manager.get('copy'):
                mode_code = 'copy'
        except Exception:
            pass

    mode_code = mode_code or 'copy'

    if mode_code == 'overwrite':
        try:
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)
            return target_path, False
        except Exception:
            return None, True

    if mode_code == 'skip':
        return None, True

    # copy: create a new name with a timestamp suffix
    ts = datetime.datetime.now().strftime("%H%M%S")
    new_name = f"{target_path.stem}_{ts}{target_path.suffix}"
    return target_path.parent / new_name, False


def get_date_from_file(file_path):
    """Extract date information from file EXIF or modification time."""
    str_date = None
    if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.heic']:
        try:
            img = Image.open(file_path)
            exif = img._getexif()
            if exif:
                for tag, val in exif.items():
                    if TAGS.get(tag) == 'DateTimeOriginal':
                        str_date = val.split(' ')[0].replace(':', '-')
                        break
        except:
            pass
    
    if not str_date:
        try:
            ts = os.path.getmtime(file_path)
            str_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except:
            pass
    return str_date

def get_hash(file_path):
    """Calculate MD5 hash of file."""
    h = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except:
        return None

class BatchRenamer:
    def rename_files(self, files, pattern, start_counter=1):
        for i, file in enumerate(files):
            new_name = self.apply_pattern(file, pattern, i + start_counter)
            try:
                new_path = file.parent / new_name
                file.rename(new_path)
            except Exception: 
                pass
            
    def apply_pattern(self, file, pattern, counter):
        date = get_date_from_file(file) or datetime.datetime.now().strftime('%Y%m%d')
        return pattern.format(
            date=date,
            name=file.stem,
            ext=file.suffix,
            counter=counter,
            time=datetime.datetime.now().strftime('%H%M%S')
        )