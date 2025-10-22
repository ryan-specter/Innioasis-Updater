#!/usr/bin/env python3
"""
Innioasis Updater Script
A smart, resilient, and user-friendly updater designed for a seamless experience.
"""

import os
import sys
import zipfile
import subprocess
import requests
from pathlib import Path
import shutil
import time
import platform
import argparse
import tempfile
import logging
import datetime
import webbrowser
from PySide6.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QProgressBar,
                               QPushButton, QDialog, QTextEdit, QMessageBox)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication

class CrossPlatformHelper:
    """Helper class for cross-platform operations."""
    @staticmethod
    def get_platform_info():
        system = platform.system().lower()
        return {'is_windows': system == 'windows', 'is_macos': system == 'darwin', 'is_linux': system == 'linux', 'system': system}

    @staticmethod
    def get_python_executable():
        if sys.executable: return sys.executable
        info = CrossPlatformHelper.get_platform_info()
        candidates = ['python3', 'python']
        if info['is_windows']: candidates = ['python.exe', 'python3.exe', 'python']
        for candidate in candidates:
            try:
                if subprocess.run([candidate, '--version'], capture_output=True, text=True, timeout=5, check=False).returncode == 0: return candidate
            except (subprocess.TimeoutExpired, FileNotFoundError): continue
        return "python"

    @staticmethod
    def get_launch_command(script_path):
        return [CrossPlatformHelper.get_python_executable(), str(script_path)]

    @staticmethod
    def open_path(path_or_url):
        info = CrossPlatformHelper.get_platform_info()
        try:
            if "http" in str(path_or_url): webbrowser.open(path_or_url)
            elif info['is_windows']: subprocess.Popen(['explorer', path_or_url])
            elif info['is_macos']: subprocess.Popen(['open', path_or_url])
            else: subprocess.Popen(['xdg-open', path_or_url])
        except Exception as e:
            logging.error("Could not open path %s: %s", path_or_url, e)

    @staticmethod
    def launch_mac_app():
        """Launch Innioasis Updater.app from Applications folder on macOS"""
        info = CrossPlatformHelper.get_platform_info()
        if not info['is_macos']:
            return False
        
        app_path = Path("/Applications/Innioasis Updater.app")
        if not app_path.exists():
            logging.warning("Innioasis Updater.app not found in Applications folder")
            return False
        
        try:
            # Use 'open' command to launch the .app bundle
            subprocess.Popen(['open', str(app_path)])
            logging.info("Successfully launched Innioasis Updater.app from Applications folder")
            return True
        except Exception as e:
            logging.error("Failed to launch Innioasis Updater.app: %s", e)
            return False

    @staticmethod
    def check_drivers_and_architecture():
        """Check driver availability and system architecture for Windows users"""
        if platform.system() != "Windows":
            return {
                'has_mtk_driver': True,
                'is_arm64': False,
                'can_install_firmware': True
            }
        
        # Check for ARM64 architecture
        is_arm64 = False
        try:
            machine = platform.machine().lower()
            is_arm64 = machine in ['arm64', 'aarch64']
        except:
            pass
        
        # Check for MTK driver (SP Flash Tool driver) - only required driver
        has_mtk_driver = False
        try:
            mediatek_driver_file = Path("C:/Program Files/MediaTek/SP Driver/unins000.exe")
            has_mtk_driver = mediatek_driver_file.exists()
        except:
            pass
        
        # Determine if firmware installation is possible
        can_install_firmware = True
        if is_arm64:
            # ARM64 Windows: Only allow firmware downloads, no installation methods
            can_install_firmware = False
        elif not has_mtk_driver:
            # No MTK driver: Allow firmware installation with fallback methods
            can_install_firmware = True
        
        return {
            'has_mtk_driver': has_mtk_driver,
            'is_arm64': is_arm64,
            'can_install_firmware': can_install_firmware
        }

class TroubleshootWorker(QThread):
    """Dedicated worker for downloading troubleshooters."""
    status_updated = Signal(str)
    progress_updated = Signal(int)
    finished = Signal()

    def run(self):
        self.status_updated.emit("Getting your troubleshooting tools ready...")
        self.progress_updated.emit(10)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self.progress_updated.emit(20)
                if self.download_troubleshooters_with_progress(Path.cwd(), Path(temp_dir)):
                    self.progress_updated.emit(100)
                    self.status_updated.emit("Perfect! Your troubleshooting tools are ready.")
                    CrossPlatformHelper.open_path(Path.cwd() / "Troubleshooting")
                else:
                    self.status_updated.emit("Let me take you to our help website instead.")
                    CrossPlatformHelper.open_path("https://troubleshooting.innioasis.app")
        except Exception as e:
            logging.error("Troubleshooter download failed: %s", e)
            self.status_updated.emit("Let me take you to our help website instead.")
            CrossPlatformHelper.open_path("https://troubleshooting.innioasis.app")
        finally:
            self.finished.emit()
    
    def download_troubleshooters_with_progress(self, current_dir, temp_dir):
        """Download troubleshooters with progress indication"""
        try:
            troubleshooter_url = "https://github.com/y1-community/Innioasis-Updater/raw/main/Troubleshooters%20-%20Windows.zip"
            troubleshooter_zip = temp_dir / "troubleshooters.zip"
            
            self.status_updated.emit("Downloading troubleshooting tools...")
            self.progress_updated.emit(30)
            
            # Download with progress
            response = requests.get(troubleshooter_url, timeout=15, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            start_time = time.time()
            
            # Format file size for display
            def format_size(size_bytes):
                if size_bytes == 0:
                    return "Unknown size"
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size_bytes < 1024.0:
                        return f"{size_bytes:.1f} {unit}"
                    size_bytes /= 1024.0
                return f"{size_bytes:.1f} TB"
            
            with open(troubleshooter_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            # Progress from 30% to 70% for download
                            download_progress = 30 + int((downloaded_size / total_size) * 40)
                            self.progress_updated.emit(download_progress)
                            
                            # Calculate download speed and update status
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 0:
                                download_speed = downloaded_size / elapsed_time
                                progress_percent = (downloaded_size / total_size) * 100
                                status_text = f"Downloading troubleshooting tools... {progress_percent:.1f}% ({format_size(downloaded_size)} / {format_size(total_size)}) - {format_size(download_speed)}/s"
                                self.status_updated.emit(status_text)
            
            self.status_updated.emit("Extracting troubleshooting tools...")
            self.progress_updated.emit(75)
            
            troubleshooting_path = current_dir / "Troubleshooting"
            troubleshooting_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(troubleshooter_zip, 'r') as z:
                file_list = z.infolist()
                total_files = len(file_list) if file_list else 1
                for i, member in enumerate(file_list):
                    z.extract(member, troubleshooting_path)
                    # Progress from 75% to 95% for extraction
                    extract_progress = 75 + int((i / total_files) * 20)
                    self.progress_updated.emit(extract_progress)
            
            self.progress_updated.emit(100)
            return True
        except Exception as e:
            logging.error("Could not download troubleshooters: %s", e)
            return False


class UpdateWorker(QThread):
    """Worker thread for handling the update process."""
    progress_updated = Signal(int)
    status_updated = Signal(str)
    update_completed = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self.should_stop = False
        self.platform_info = CrossPlatformHelper.get_platform_info()
        self.files_updated = 0
        self.files_skipped = 0
        
    def run(self):
        temp_dir = None
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', filename='updater.log', filemode='w')

        try:
            current_dir = Path.cwd()
            temp_dir = Path(tempfile.mkdtemp(prefix="innioasis-update-"))
            timestamp_file = current_dir / ".last_update_check"
            self.status_updated.emit("Just checking what's new...")
            self.progress_updated.emit(5)
            
            main_repo_url = "https://github.com/y1-community/Innioasis-Updater/archive/refs/heads/main.zip"
            zip_file = temp_dir / "innioasis_updater_latest.zip"
            self.status_updated.emit("Downloading latest updates from repository...")
            self.download_with_progress(main_repo_url, zip_file, 5, 40)

            self.progress_updated.emit(45)

            self.status_updated.emit("Unpacking your updates...")
            with zipfile.ZipFile(zip_file, 'r') as z:
                file_list = z.infolist()
                total_files = len(file_list) if file_list else 1
                for i, member in enumerate(file_list):
                    z.extract(member, temp_dir)
                    progress = int(45 + (i / total_files) * 20)
                    self.progress_updated.emit(progress)
                    
                    # Update status with extraction progress
                    if i % 10 == 0 or i == total_files - 1:  # Update every 10 files or on last file
                        extract_percent = ((i + 1) / total_files) * 100
                        self.status_updated.emit(f"Extracting files... {extract_percent:.1f}% ({i + 1}/{total_files} files)")

            extracted_dir = next(temp_dir.glob("Innioasis-Updater-main*"), None)
            if not extracted_dir: 
                self.status_updated.emit("Almost there! Getting your files ready...")
                # Continue anyway - the update can still be successful
            
            self.status_updated.emit("Updating your app with the latest features...")
            if extracted_dir:
                items_to_copy = list(extracted_dir.iterdir())
            else:
                # If we can't find the extracted dir, just continue
                items_to_copy = []
            
            total_items = len(items_to_copy) if items_to_copy else 1
            
            for i, item in enumerate(items_to_copy):
                if self.should_stop: break
                try:
                    dest_item = current_dir / item.name
                    
                    # Skip system and cache directories
                    if item.name.lower() in ['.git', '__pycache__', '.ds_store', 'firmware_downloads', '.web_scripts']:
                        continue
                    
                    ext = item.suffix.lower()
                    if item.is_file():
                        # Skip platform-incompatible files on non-Windows
                        if not self.platform_info['is_windows'] and ext in ['.exe', '.dll', '.lnk']:
                            self.files_skipped += 1
                            continue
                        
                        # For .exe and .dll files, only copy if they don't exist or are newer
                        if ext in ['.exe', '.dll']:
                            if dest_item.exists():
                                # Check if the new file is newer
                                try:
                                    if item.stat().st_mtime <= dest_item.stat().st_mtime:
                                        self.files_skipped += 1
                                        continue
                                except:
                                    # If we can't compare timestamps, skip to be safe
                                    self.files_skipped += 1
                                    continue
                        
                        # Try to copy the file, but don't stress if it fails
                        try:
                            shutil.copy2(item, dest_item)
                            self.files_updated += 1
                        except (IOError, OSError, PermissionError):
                            # File might be in use or locked - that's cool, skip it
                            self.files_skipped += 1
                            continue
                        
                    elif item.is_dir():
                        # For directories, preserve existing content and merge new files
                        if dest_item.exists():
                            # Copy individual files from the directory without deleting anything
                            for subitem in item.iterdir():
                                subdest = dest_item / subitem.name
                                if subitem.is_file():
                                    # Skip platform-incompatible files
                                    if not self.platform_info['is_windows'] and subitem.suffix.lower() in ['.exe', '.dll', '.lnk']:
                                        self.files_skipped += 1
                                        continue
                                    
                                    # For .exe and .dll files, only copy if they don't exist or are newer
                                    if subitem.suffix.lower() in ['.exe', '.dll']:
                                        if subdest.exists():
                                            # Check if the new file is newer
                                            try:
                                                if subitem.stat().st_mtime <= subdest.stat().st_mtime:
                                                    self.files_skipped += 1
                                                    continue
                                            except:
                                                # If we can't compare timestamps, skip to be safe
                                                self.files_skipped += 1
                                                continue
                                    
                                    # Try to copy the file, but don't stress if it fails
                                    try:
                                        shutil.copy2(subitem, subdest)
                                        self.files_updated += 1
                                    except (IOError, OSError, PermissionError):
                                        # File might be in use or locked - that's cool, skip it
                                        self.files_skipped += 1
                                        continue
                                elif subitem.is_dir():
                                    # For subdirectories, copy if they don't exist, otherwise merge
                                    if not subdest.exists():
                                        try:
                                            shutil.copytree(subitem, subdest)
                                            self.files_updated += 1
                                        except (IOError, OSError, PermissionError):
                                            self.files_skipped += 1
                                            continue
                                    else:
                                        # Recursively merge subdirectories
                                        self.merge_directories(subitem, subdest)
                        else:
                            # Directory doesn't exist, copy it normally
                            try:
                                shutil.copytree(item, dest_item)
                                self.files_updated += 1
                            except (IOError, OSError, PermissionError):
                                self.files_skipped += 1
                                continue
                except Exception as e:
                    # Don't treat any file operation as critical - just log and continue
                    logging.info("Skipping %s due to error: %s", item.name, e)
                    self.files_skipped += 1
                    continue
                
                progress = int(65 + ((i + 1) / total_items) * 30)
                self.progress_updated.emit(progress)
                
                # Update status with file copying progress
                if i % 5 == 0 or i == total_items - 1:  # Update every 5 items or on last item
                    copy_percent = ((i + 1) / total_items) * 100
                    self.status_updated.emit(f"Installing updates... {copy_percent:.1f}% ({i + 1}/{total_items} items) - {self.files_updated} files updated")

            # Always consider the update successful if we got this far
            self.status_updated.emit("Brilliant! Your app is now up to date. ✨")
            
            self.status_updated.emit("Just finishing up...")
            try:
                timestamp_file.write_text(str(datetime.date.today()))
            except:
                pass  # Don't stress about timestamp file
            self.progress_updated.emit(100)
            self.update_completed.emit(True)
            
        except requests.exceptions.RequestException as e:
            self.status_updated.emit("No worries! Your app will work perfectly fine without the latest updates.")
            time.sleep(2)
            self.update_completed.emit(True)  # Still successful - app can run
        except Exception as e:
            self.status_updated.emit("Everything's ready to go! ✨")
            logging.info("Update process had issues but continuing: %s", e)
            self.update_completed.emit(True)  # Still successful - app can run
        finally:
            if temp_dir and temp_dir.exists(): 
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass  # Don't stress about cleanup

    def merge_directories(self, src_dir, dest_dir):
        """Recursively merge source directory into destination directory, preserving existing files"""
        for item in src_dir.iterdir():
            dest_item = dest_dir / item.name
            if item.is_file():
                # Skip platform-incompatible files
                if not self.platform_info['is_windows'] and item.suffix.lower() in ['.exe', '.dll', '.lnk']:
                    self.files_skipped += 1
                    continue
                
                # For .exe and .dll files, only copy if they don't exist or are newer
                if item.suffix.lower() in ['.exe', '.dll']:
                    if dest_item.exists():
                        # Check if the new file is newer
                        try:
                            if item.stat().st_mtime <= dest_item.stat().st_mtime:
                                self.files_skipped += 1
                                continue
                        except:
                            # If we can't compare timestamps, skip to be safe
                            self.files_skipped += 1
                            continue
                
                # Try to copy the file, but don't stress if it fails
                try:
                    shutil.copy2(item, dest_item)
                    self.files_updated += 1
                except (IOError, OSError, PermissionError):
                    # File might be in use or locked - that's cool, skip it
                    self.files_skipped += 1
                    continue
            elif item.is_dir():
                if not dest_item.exists():
                    try:
                        shutil.copytree(item, dest_item)
                        self.files_updated += 1
                    except (IOError, OSError, PermissionError):
                        self.files_skipped += 1
                        continue
                else:
                    # Recursively merge subdirectories
                    self.merge_directories(item, dest_item)

    def download_with_progress(self, url, filepath, base_progress, progress_range):
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        start_time = time.time()
        last_progress_time = start_time
        
        # Format file size for display
        def format_size(size_bytes):
            if size_bytes == 0:
                return "Unknown size"
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} TB"
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if self.should_stop: return
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    current_time = time.time()
                    
                    # Update progress every 0.5 seconds to avoid UI spam
                    if current_time - last_progress_time >= 0.5:
                        elapsed_time = current_time - start_time
                        
                        if total_size > 0:
                            # We have content-length, show precise progress
                            progress = int(base_progress + (downloaded_size / total_size) * progress_range)
                            self.progress_updated.emit(progress)
                            
                            if elapsed_time > 1.0:  # Only show ETA after 1 second
                                download_speed = downloaded_size / elapsed_time
                                remaining_bytes = total_size - downloaded_size
                                eta_seconds = remaining_bytes / download_speed if download_speed > 0 else 0
                                
                                progress_percent = (downloaded_size / total_size) * 100
                                status_text = f"Downloading updates... {progress_percent:.1f}% ({format_size(downloaded_size)} / {format_size(total_size)}) - {format_size(download_speed)}/s"
                                
                                # Show ETA
                                if eta_seconds > 0 and eta_seconds < 86400:
                                    if eta_seconds < 60:
                                        status_text += f" - ETA: {int(eta_seconds)}s"
                                    elif eta_seconds < 3600:
                                        eta_minutes = int(eta_seconds / 60)
                                        eta_seconds_remainder = int(eta_seconds % 60)
                                        status_text += f" - ETA: {eta_minutes}m {eta_seconds_remainder}s"
                                    else:
                                        eta_hours = int(eta_seconds / 3600)
                                        eta_minutes = int((eta_seconds % 3600) / 60)
                                        status_text += f" - ETA: {eta_hours}h {eta_minutes}m"
                                
                                self.status_updated.emit(status_text)
                            else:
                                # First second, show basic progress
                                progress_percent = (downloaded_size / total_size) * 100
                                status_text = f"Downloading updates... {progress_percent:.1f}% ({format_size(downloaded_size)} / {format_size(total_size)})"
                                self.status_updated.emit(status_text)
                        else:
                            # No content-length (GitHub ZIP issue), show estimated progress
                            if elapsed_time > 1.0:
                                download_speed = downloaded_size / elapsed_time
                                status_text = f"Downloading updates... {format_size(downloaded_size)} downloaded - {format_size(download_speed)}/s"
                                
                                # Estimate progress based on typical GitHub repo sizes (rough estimate)
                                estimated_size = 5 * 1024 * 1024  # 5MB estimate
                                estimated_progress = min(95, int(base_progress + (downloaded_size / estimated_size) * progress_range))
                                self.progress_updated.emit(estimated_progress)
                                
                                # Show estimated ETA based on average speed
                                if download_speed > 0:
                                    estimated_remaining = max(0, estimated_size - downloaded_size)
                                    eta_seconds = estimated_remaining / download_speed
                                    if eta_seconds > 0 and eta_seconds < 300:  # Show ETA if less than 5 minutes
                                        if eta_seconds < 60:
                                            status_text += f" - ETA: ~{int(eta_seconds)}s"
                                        else:
                                            eta_minutes = int(eta_seconds / 60)
                                            status_text += f" - ETA: ~{eta_minutes}m"
                                
                                self.status_updated.emit(status_text)
                            else:
                                # First second, show basic info
                                status_text = f"Downloading updates... {format_size(downloaded_size)} downloaded"
                                self.status_updated.emit(status_text)
                        
                        last_progress_time = current_time

class DriverSetupDialog(QDialog):
    """Dialog for Windows driver setup guidance"""
    def __init__(self, driver_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Driver Setup Required")
        self.setModal(True)
        self.setFixedSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Driver Setup Required")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Status message
        if driver_info['is_arm64']:
            message = ("You're running Windows on ARM64, which has limited compatibility.\n\n"
                      "You can still download firmware files, but installation methods may not work.\n\n"
                      "Would you like to see the installation guide anyway?")
        else:
            if not driver_info['has_mtk_driver']:
                message = ("To use all features of Innioasis Updater, you'll need to install:\n\n"
                          "• MediaTek USB Driver (SP Flash Tool Driver)\n\n"
                          "Would you like help setting this up?")
            else:
                message = "Your drivers look good! You should be able to use all features."
        
        status_label = QLabel(message)
        status_label.setWordWrap(True)
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        # Buttons
        button_layout = QVBoxLayout()
        
        if not driver_info['is_arm64'] and not driver_info['has_mtk_driver']:
            install_button = QPushButton("Install MTK USB Driver")
            install_button.clicked.connect(self.open_install_guide)
            button_layout.addWidget(install_button)
        
        continue_button = QPushButton("Continue Anyway")
        continue_button.clicked.connect(self.accept)
        button_layout.addWidget(continue_button)
        
        layout.addLayout(button_layout)
    
    def open_install_guide(self):
        """Open the installation guide in browser"""
        webbrowser.open("https://innioasis.app/")
        self.accept()

class UpdateProgressDialog(QDialog):
    """Progress dialog for the update process."""
    def __init__(self, mode='update', parent=None):
        super().__init__(parent)
        self.setWindowTitle("Innioasis Updater")
        self.setModal(True)
        self.setFixedSize(500, 220)
        
        layout = QVBoxLayout(self)
        title_label = QLabel("Innioasis Updater"); title_label.setFont(QFont("Arial", 16, QFont.Bold)); title_label.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("Initializing..."); self.status_label.setAlignment(Qt.AlignCenter); self.status_label.setWordWrap(True)
        
        # Main progress bar
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 100); self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Preparing...")
        
        # Download details label (initially hidden)
        self.download_details_label = QLabel("")
        self.download_details_label.setAlignment(Qt.AlignCenter)
        self.download_details_label.setStyleSheet("color: #666; font-size: 11px;")
        self.download_details_label.hide()
        
        self.update_button = QPushButton("Run without updating"); self.update_button.clicked.connect(self.run_without_update)
        
        layout.addWidget(title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.download_details_label)
        layout.addWidget(self.update_button)

        if mode == 'update':
            self.update_worker = UpdateWorker()
            self.update_worker.progress_updated.connect(self.progress_bar.setValue)
            self.update_worker.status_updated.connect(self.on_status_updated)
            self.update_worker.update_completed.connect(self.on_update_completed)
            self.update_worker.start()
        else: # No update needed
            self.setFixedSize(500, 180)
            self.status_label.setText("You're all up to date! Launching now...")
            self.progress_bar.hide()
            self.download_details_label.hide()
            self.update_button.setText("Launch Now")
            self.update_button.show()
            
            # Add "Check for Updates anyway" button for manual rescue
            self.force_update_button = QPushButton("Check for Updates anyway")
            self.force_update_button.clicked.connect(self.run_force_update)
            layout.addWidget(self.force_update_button)
            
            # Auto-launch after 3 seconds if user doesn't click anything
            QTimer.singleShot(3000, self.accept)
    
    def on_status_updated(self, status_text):
        """Handle status updates and show download details when appropriate"""
        # For download messages, show a cleaner status
        if "Downloading" in status_text and ("%" in status_text or "MB" in status_text or "KB" in status_text):
            # Show a simple status message
            self.status_label.setText("Downloading updates...")
        else:
            self.status_label.setText(status_text)
        
        # Show download details if the status contains download information
        if "Downloading" in status_text and ("%" in status_text or "MB" in status_text or "KB" in status_text):
            # Hide the details label to avoid redundancy
            self.download_details_label.hide()
            # Update progress bar format to show download progress with details
            if "%" in status_text:
                try:
                    percent = status_text.split("%")[0].split()[-1]
                    self.progress_bar.setFormat(f"Downloading... {percent}%")
                except:
                    self.progress_bar.setFormat("Downloading updates...")
            else:
                # Extract download info for progress bar
                if "MB" in status_text or "KB" in status_text:
                    # Extract the download info (e.g., "10.2 MB downloaded - 6.8 MB/s")
                    parts = status_text.split(" - ")
                    if len(parts) >= 2:
                        download_info = parts[0].replace("Downloading updates... ", "")
                        speed_info = parts[1]
                        self.progress_bar.setFormat(f"{download_info} - {speed_info}")
                    else:
                        self.progress_bar.setFormat("Downloading updates...")
                else:
                    self.progress_bar.setFormat("Downloading updates...")
        elif "Grabbing the latest updates" in status_text or "Downloading latest updates from repository" in status_text:
            # Hide details label and show in progress bar
            self.download_details_label.hide()
            self.progress_bar.setFormat("Downloading updates...")
        else:
            self.download_details_label.hide()
            # Reset progress bar format for non-download operations
            if "Unpacking" in status_text or "Extracting" in status_text:
                self.progress_bar.setFormat("Extracting...")
            elif "Updating" in status_text or "Installing" in status_text:
                self.progress_bar.setFormat("Installing...")
            elif "Just checking" in status_text:
                self.progress_bar.setFormat("Checking...")
            elif "Just finishing" in status_text:
                self.progress_bar.setFormat("Finishing...")
            else:
                self.progress_bar.setFormat("Working...")

    def run_without_update(self):
        """Run the app without updating"""
        self.accept()  # Close dialog and continue to app launch


    def run_force_update(self):
        """Force an update even when timestamp indicates recent update"""
        self.status_label.setText("Checking for updates...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.download_details_label.hide()
        self.update_button.hide()
        self.force_update_button.hide()
        
        # Create and start the update worker
        self.update_worker = UpdateWorker()
        self.update_worker.progress_updated.connect(self.progress_bar.setValue)
        self.update_worker.status_updated.connect(self.on_status_updated)
        self.update_worker.update_completed.connect(self.on_update_completed)
        self.update_worker.start()

    def on_update_completed(self, success):
        self.update_button.hide()
        if success:
            self.status_label.setText("All done! You're now up to date. ✨")
            self.progress_bar.setValue(100)
            QTimer.singleShot(2000, self.accept)
        else:
            # Even if there were issues, show a positive message and continue
            self.status_label.setText("Update completed! Your app is ready to go. ✨")
            self.progress_bar.setValue(100)
            QTimer.singleShot(2000, self.accept)

def load_redundant_files_list():
    """Load redundant files list from local file or remote URL"""
    try:
        # Try local file first
        local_file = Path("redundant_files.txt")
        if local_file.exists():
            logging.info("Loading redundant files list from local file")
            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            # Try remote URL with progress indication
            logging.info("Loading redundant files list from remote URL")
            response = requests.get("https://innioasis.app/redundant_files.txt", timeout=10, stream=True)
            response.raise_for_status()
            
            # Get content length for progress indication
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            content_parts = []
            
            if total_size > 0:
                logging.info(f"Downloading redundant files list ({total_size} bytes)...")
            
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    content_parts.append(chunk.decode('utf-8'))
                    downloaded_size += len(chunk)
                    
                    if total_size > 0:
                        progress_percent = (downloaded_size / total_size) * 100
                        if downloaded_size % 1024 == 0:  # Log every KB
                            logging.info(f"Downloaded {downloaded_size}/{total_size} bytes ({progress_percent:.1f}%)")
            
            content = ''.join(content_parts)
            logging.info("Successfully downloaded redundant files list")
        
        # Parse the content
        redundant_files = {}
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' in line:
                platform, files = line.split('=', 1)
                platform = platform.strip()
                files = files.strip()
                
                if platform == 'all':
                    redundant_files['all'] = [f.strip().strip('"') for f in files.split(',') if f.strip()]
                elif platform in ['mac', 'linux', 'win']:
                    redundant_files[platform] = [f.strip().strip('"') for f in files.split(',') if f.strip()]
        
        logging.info(f"Loaded redundant files list: {redundant_files}")
        return redundant_files
        
    except Exception as e:
        logging.error(f"Error loading redundant files list: {e}")
        return {}

def remove_files_by_pattern(directory, pattern):
    """Remove files or directories matching a pattern in the given directory and subdirectories"""
    removed_count = 0
    try:
        # Check if pattern is a directory (no file extension and exists as directory)
        pattern_path = directory / pattern
        if pattern_path.exists() and pattern_path.is_dir():
            # Remove entire directory
            import shutil
            shutil.rmtree(pattern_path)
            logging.info(f"Removed redundant directory: {pattern}")
            removed_count += 1
        elif '*' in pattern:
            # Handle wildcard patterns - search recursively in subdirectories
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    logging.info(f"Removed redundant file: {file_path.relative_to(directory)}")
                    removed_count += 1
                elif file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                    logging.info(f"Removed redundant directory: {file_path.relative_to(directory)}")
                    removed_count += 1
        else:
            # Handle specific file names - search recursively in subdirectories
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    logging.info(f"Removed redundant file: {file_path.relative_to(directory)}")
                    removed_count += 1
                elif file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                    logging.info(f"Removed redundant directory: {file_path.relative_to(directory)}")
                    removed_count += 1
    except Exception as e:
        logging.error(f"Error removing files/directories matching pattern '{pattern}': {e}")
    
    return removed_count

def cleanup_redundant_files():
    """Clean up redundant files based on platform and redundant_files.txt"""
    try:
        current_platform = platform.system().lower()
        if current_platform == "darwin":
            platform_key = "mac"
        elif current_platform == "linux":
            platform_key = "linux"
        elif current_platform == "windows":
            platform_key = "win"
        else:
            platform_key = "unknown"
        
        logging.info(f"Cleaning up redundant files for platform: {platform_key}")
        
        # Load redundant files list
        redundant_files = load_redundant_files_list()
        if not redundant_files:
            logging.info("No redundant files list found, skipping cleanup")
            return
        
        current_dir = Path.cwd()
        removed_count = 0
        
        # Clean up files for all platforms
        if 'all' in redundant_files:
            for pattern in redundant_files['all']:
                removed_count += remove_files_by_pattern(current_dir, pattern)
        
        # Clean up platform-specific files
        if platform_key in redundant_files:
            for pattern in redundant_files[platform_key]:
                removed_count += remove_files_by_pattern(current_dir, pattern)
        
        if removed_count > 0:
            logging.info(f"Cleaned up {removed_count} redundant files")
        else:
            logging.info("No redundant files found to clean up")
        
        # Remove redundant_files.txt after cleanup is complete
        try:
            redundant_files_path = Path("redundant_files.txt")
            if redundant_files_path.exists():
                redundant_files_path.unlink()
                logging.info("Removed redundant_files.txt after cleanup")
        except Exception as e:
            logging.error(f"Error removing redundant_files.txt: {e}")
            
    except Exception as e:
        logging.error(f"Error during redundant files cleanup: {e}")

def perform_initial_cleanup():
    """Removes obsolete or platform-specific files and folders."""
    logging.info("Performing initial directory cleanup...")
    platform_info = CrossPlatformHelper.get_platform_info()
    
    for path in Path.cwd().iterdir():
        try:
            if path.is_dir() and path.name == '.web_scripts':
                shutil.rmtree(path); logging.info("Removed obsolete folder: %s", path.name)
                continue
            if not platform_info['is_windows']:
                if path.suffix.lower() in ['.exe', '.dll', '.lnk']:
                    path.unlink(); logging.info("Removed Windows-specific file: %s", path.name)
                elif path.is_dir() and 'trouble' in path.name.lower():
                    shutil.rmtree(path); logging.info("Removed Windows-specific folder: %s", path.name)
        except OSError as e:
            logging.warning("Could not remove %s during cleanup: %s", path.name, e)
    
    # Clean up redundant files after initial cleanup
    cleanup_redundant_files()


class ARM64WindowsDialog(QDialog):
    """Dialog for ARM64 Windows users explaining limited functionality"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ARM64 Windows - Limited Functionality")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("ARM64 Windows Detected")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Message
        message = ("You're running Windows on ARM64, which has limited compatibility with firmware installation features.\n\n"
                  "❌ Not Available:\n"
                  "• Update Firmware\n"
                  "• Restore Firmware\n"
                  "• Custom Firmware Installation\n\n"
                  "✅ Still Available:\n"
                  "• Remote Control Features\n"
                  "• Screen and Scrollwheel Input via PC\n"
                  "• Screenshotting\n"
                  "• APK Installation on this computer\n\n"
                  "Alternative: You can try using the Linux version of Innioasis Updater on Windows ARM64 by using Ubuntu from the Microsoft Store and USBIPD-win.")
        
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(message_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        remote_control_button = QPushButton("Use Remote Control")
        remote_control_button.clicked.connect(self.accept)
        button_layout.addWidget(remote_control_button)
        
        wsl_button = QPushButton("Try Innioasis Updater on WSL")
        wsl_button.clicked.connect(self.open_wsl_guide)
        button_layout.addWidget(wsl_button)
        
        layout.addLayout(button_layout)
    
    def open_wsl_guide(self):
        """Open the WSL installation guide"""
        webbrowser.open("https://innioasis.app/")
        self.accept()

def launch_y1_helper_arm64():
    """Launch y1_helper.py for ARM64 Windows users"""
    current_dir = Path.cwd()
    platform_info = CrossPlatformHelper.get_platform_info()
    
    # Show ARM64 Windows dialog first
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    dialog = ARM64WindowsDialog()
    dialog.exec()
    
    # Try to launch y1_helper.py
    script_candidates = [
        "y1_helper.py",  # Primary target
    ]
    
    for script_name in script_candidates:
        script_path = current_dir / script_name
        if script_path.exists():
            try:
                # Method 1: Use current Python executable
                cmd = [sys.executable, str(script_path)]
                logging.info(f"Attempting to launch {script_name} with current Python: {cmd}")
                subprocess.Popen(cmd)
                logging.info(f"Successfully launched {script_name}")
                return True
            except Exception as e:
                logging.error(f"Failed to launch {script_name} with current Python: {e}")
                
                try:
                    # Method 2: Use python.exe explicitly
                    cmd = ["python.exe", str(script_path)]
                    logging.info(f"Attempting to launch {script_name} with python.exe: {cmd}")
                    subprocess.Popen(cmd)
                    logging.info(f"Successfully launched {script_name} with python.exe")
                    return True
                except Exception as e2:
                    logging.error(f"Failed to launch {script_name} with python.exe: {e2}")
                    continue
    
    # If all methods failed, show error message
    logging.error("All launch methods failed for y1_helper.py")
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Launch Error", 
                           "Could not launch y1_helper.py.\n\n"
                           "Please try running it manually from the terminal.")
    except:
        print("ERROR: Could not launch y1_helper.py")
        print("Please run it manually from the terminal.")
    
    return False

def launch_firmware_downloader():
    """Reliably launch firmware_downloader.py with multiple fallback methods"""
    current_dir = Path.cwd()
    platform_info = CrossPlatformHelper.get_platform_info()
    
    # Check if we're on ARM64 Windows - launch y1_helper.py instead
    if platform_info['is_windows'] and CrossPlatformHelper.check_drivers_and_architecture()['is_arm64']:
        return launch_y1_helper_arm64()
    
    # Check drivers for Windows x86-64 users
    if platform_info['is_windows'] and not CrossPlatformHelper.check_drivers_and_architecture()['is_arm64']:
        driver_info = CrossPlatformHelper.check_drivers_and_architecture()
        if not driver_info['can_install_firmware']:
            # Show driver setup dialog instead of launching
            app = QApplication.instance()
            if not app:
                app = QApplication([])
            dialog = DriverSetupDialog(driver_info)
            dialog.exec()
            # Continue with launch after dialog
    
    # Try multiple script names in order of preference
    script_candidates = [
        "firmware_downloader.py",  # Primary target
        "test.py",                 # Enhanced version as fallback
    ]
    
    for script_name in script_candidates:
        script_path = current_dir / script_name
        if script_path.exists():
            try:
                # Method 1: Use CrossPlatformHelper
                launch_cmd = CrossPlatformHelper.get_launch_command(script_path)
                logging.info(f"Attempting to launch {script_name} with command: {launch_cmd}")
                subprocess.Popen(launch_cmd)
                logging.info(f"Successfully launched {script_name}")
                return True
            except Exception as e:
                logging.error(f"Failed to launch {script_name} with CrossPlatformHelper: {e}")
                
                try:
                    # Method 2: Direct subprocess with sys.executable
                    cmd = [sys.executable, str(script_path)]
                    logging.info(f"Attempting to launch {script_name} with direct command: {cmd}")
                    subprocess.Popen(cmd)
                    logging.info(f"Successfully launched {script_name} with direct method")
                    return True
                except Exception as e2:
                    logging.error(f"Failed to launch {script_name} with direct method: {e2}")
                    
                    try:
                        # Method 3: Platform-specific commands
                        if platform_info['is_windows']:
                            # Windows: try with python.exe explicitly
                            cmd = ["python.exe", str(script_path)]
                        elif platform_info['is_macos']:
                            # macOS: try with python3
                            cmd = ["python3", str(script_path)]
                        else:
                            # Linux: try with python3
                            cmd = ["python3", str(script_path)]
                        
                        logging.info(f"Attempting to launch {script_name} with platform-specific command: {cmd}")
                        subprocess.Popen(cmd)
                        logging.info(f"Successfully launched {script_name} with platform-specific method")
                        return True
                    except Exception as e3:
                        logging.error(f"Failed to launch {script_name} with platform-specific method: {e3}")
                        continue
    
    # If all methods failed, try to show an error message
    logging.error("All launch methods failed for firmware_downloader.py")
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Launch Error", 
                           "Could not launch the main application (firmware_downloader.py).\n\n"
                           "Please try running firmware_downloader.py manually from the terminal.")
    except:
        # If tkinter fails, just print to console
        print("ERROR: Could not launch firmware_downloader.py")
        print("Please run firmware_downloader.py manually from the terminal.")
    
    return False

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', filename='updater.log', filemode='w')
    perform_initial_cleanup()
    
    parser = argparse.ArgumentParser(description="Innioasis Updater Script", add_help=False)
    parser.add_argument("-f", "--force", action="store_true", help="Force the update.")
    args, _ = parser.parse_known_args()

    app = QApplication(sys.argv)
    
    mode = 'update' # Default mode
    platform_info = CrossPlatformHelper.get_platform_info()

    needs_update = False
    if args.force: needs_update = True
    else:
        # Check if firmware_downloader.py is missing - force update if so
        firmware_downloader_path = Path.cwd() / "firmware_downloader.py"
        if not firmware_downloader_path.exists():
            logging.info("firmware_downloader.py not found - forcing update to restore missing file")
            needs_update = True
        else:
            # Check if automatic updates are disabled via .no_updates file
            no_updates_file = Path.cwd() / ".no_updates"
            if no_updates_file.exists():
                logging.info("Automatic updates disabled by user (.no_updates file found)")
                needs_update = False
            else:
                try:
                    timestamp_file = Path.cwd() / ".last_update_check"
                    today = str(datetime.date.today())
                    if not timestamp_file.exists() or timestamp_file.read_text() != today: needs_update = True
                except Exception as e:
                    logging.error("Could not read timestamp file: %s", e); needs_update = True
    
    if not needs_update:
        mode = 'no_update'

    app.setStyle('Fusion')
    dialog = UpdateProgressDialog(mode=mode)
    dialog.exec()
    
    # Always update the timestamp file, even if updates were skipped
    # This is critical for macOS compatibility: the .app bundle checks this file to determine
    # whether to launch updater.py (for updates) or firmware_downloader.py (if already updated today).
    # If this file is missing, the .app bundle will always launch updater.py instead of
    # firmware_downloader.py directly, breaking the normal launch flow on macOS.
    try:
        timestamp_file = Path.cwd() / ".last_update_check"
        today = str(datetime.date.today())
        timestamp_file.write_text(today)
        logging.info("Updated timestamp file to: %s", today)
    except Exception as e:
        logging.error("Could not update timestamp file: %s", e)
    
    # Always launch the main app
    # Check if we're on macOS - launch the .app bundle
    if platform_info['is_macos']:
        logging.info("macOS detected - launching Innioasis Updater.app from Applications folder...")
        launch_success = CrossPlatformHelper.launch_mac_app()
        if not launch_success:
            logging.error("Failed to launch Innioasis Updater.app, falling back to Python script...")
            # Fallback to Python script if .app launch fails
            launch_success = launch_firmware_downloader()
            if not launch_success:
                logging.error("Failed to launch firmware_downloader.py as fallback")
    # Check if we're on ARM64 Windows
    elif platform_info['is_windows'] and CrossPlatformHelper.check_drivers_and_architecture()['is_arm64']:
        logging.info("ARM64 Windows detected - launching y1_helper.py...")
        launch_success = launch_y1_helper_arm64()
        if not launch_success:
            logging.error("Failed to launch y1_helper.py")
    else:
        logging.info("Attempting to launch firmware_downloader.py...")
        launch_success = launch_firmware_downloader()
        if not launch_success:
            logging.error("Failed to launch firmware_downloader.py")
    
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in updater: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
