import subprocess
import requests
import os
import pyautogui
import pytesseract
import time
from PIL import Image
from bs4 import BeautifulSoup
import uuid
import json
import google.generativeai as genai
import shutil

class Tools:
    def run_python(self, code=None, filepath=None) -> str:
        """Execute Python code or run a Python file."""
        if filepath:
            if not os.path.isfile(filepath):
                return f"[PY ERROR] File not found: {filepath}"
            cmd = ["python", filepath]
        else:
            if not code:
                return "[PY ERROR] No code provided"
            fname = f"tmp_{uuid.uuid4().hex[:8]}.py"
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(code)
                cmd = ["python", fname]
            except Exception as e:
                return f"[PY ERROR] Failed to create temp file: {e}"
        
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            # Clean up temp file
            if not filepath and 'fname' in locals():
                try:
                    os.remove(fname)
                except:
                    pass
            
            if cp.returncode == 0:
                return cp.stdout.strip() or "[PY SUCCESS] No output"
            else:
                return f"[PY ERROR]\nStderr: {cp.stderr.strip()}\nStdout: {cp.stdout.strip()}"
        except subprocess.TimeoutExpired:
            return "[PY ERROR] Script timed out after 60 seconds"
        except Exception as e:
            return f"[PY EXCEPTION] {e}"

    def run_shell(self, command: str) -> str:
        """Execute Windows shell command."""
        if not command:
            return "[SHELL ERROR] No command provided"
        
        try:
            print(f"terminal command- {command}")
            cp = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            
            if cp.returncode == 0:
                return cp.stdout.strip() or "[SHELL SUCCESS] Command completed"
            else:
                return f"[SHELL ERROR]\nReturn code: {cp.returncode}\nStderr: {cp.stderr.strip()}\nStdout: {cp.stdout.strip()}"
        except subprocess.TimeoutExpired:
            return "[SHELL ERROR] Command timed out after 60 seconds"
        except Exception as e:
            return f"[SHELL EXCEPTION] {e}"

    def scrape_web(self, query: str) -> str:
        """Search and scrape web content using DuckDuckGo."""
        if not query:
            return "[SCRAPE ERROR] No query provided"
        
        try:
            print(f"🔍 Searching web for: {query}")
            resp = requests.post("https://html.duckduckgo.com/html/", 
                               data={"q": query}, 
                               timeout=10,
                               headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract results
            results = []
            for result in soup.select('.result')[:5]:  # Get top 5 results
                title_elem = result.select_one('.result__title')
                snippet_elem = result.select_one('.result__snippet')
                url_elem = result.select_one('.result__url')
                
                title = title_elem.get_text(strip=True) if title_elem else "No title"
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else "No snippet"
                url = url_elem.get_text(strip=True) if url_elem else "No URL"
                
                results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {url}\n")
            print(results)
            return "\n".join(results) or "[SCRAPE ERROR] No results found"
            
        except Exception as e:
            return f"[SCRAPE EXCEPTION] {e}"

    def ocr_screenshot(self) -> str:
        """Take a screenshot and extract text using OCR."""
        try:
            print("📸 Taking screenshot for OCR...")
            img = pyautogui.screenshot()
            text = pytesseract.image_to_string(img)
            return text.strip() or "[OCR] No text detected on screen"
        except Exception as e:
            return f"[OCR EXCEPTION] {e}"

    def edit_file(self, path=None, edits=None, filepath=None, content=None) -> str:
        """Edit existing files with find/replace or content replacement."""
        target = filepath or path
        if not target:
            return "[EDIT ERROR] No filepath provided"
        
        # If content is provided, overwrite the file
        if content is not None:
            try:
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"[EDIT SUCCESS] Overwrote {target} with new content"
            except Exception as e:
                return f"[EDIT EXCEPTION] {e}"
        
        # Check if file exists
        if not os.path.isfile(target):
            return f"[EDIT ERROR] File not found: {target}"
        
        try:
            with open(target, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            # Find and replace operation
            if isinstance(edits, dict) and 'find' in edits and 'replace' in edits:
                new_content = old_content.replace(edits['find'], edits['replace'])
                if new_content == old_content:
                    return f"[EDIT WARNING] No changes made - text '{edits['find']}' not found in {target}"
                
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return f"[EDIT SUCCESS] Replaced '{edits['find']}' with '{edits['replace']}' in {target}"
            
            # Append operation
            else:
                with open(target, 'a', encoding='utf-8') as f:
                    f.write("\n" + str(edits))
                return f"[EDIT SUCCESS] Appended content to {target}"
                
        except Exception as e:
            return f"[EDIT EXCEPTION] {e}"

    def make_file(self, filepath=None, content="", directory=None) -> str:
        """Create new files with specified content."""
        if not filepath:
            return "[MAKE_FILE ERROR] No filepath provided"
        
        try:
            # Create directory if it doesn't exist
            dir_path = directory or os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
                print(f"📁 Created directory: {dir_path}")
            
            # Create the file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = os.path.getsize(filepath)
            return f"[MAKE_FILE SUCCESS] Created {filepath} ({file_size} bytes)"
            
        except Exception as e:
            return f"[MAKE_FILE EXCEPTION] {e}"

    def delete_file(self, filepath=None, dirpath=None) -> str:
        """Delete files or directories."""
        target = filepath or dirpath
        if not target:
            return "[DELETE ERROR] No filepath or dirpath provided"
        
        try:
            if not os.path.exists(target):
                return f"[DELETE ERROR] Path not found: {target}"
            
            if os.path.isfile(target):
                os.remove(target)
                return f"[DELETE SUCCESS] Deleted file: {target}"
            elif os.path.isdir(target):
                shutil.rmtree(target)
                return f"[DELETE SUCCESS] Deleted directory: {target}"
            else:
                return f"[DELETE ERROR] Unknown file type: {target}"
                
        except Exception as e:
            return f"[DELETE EXCEPTION] {e}"
        
# not working tho
 
    def run_openscad(self, scad_code: str, output_path="out.stl") -> str:
        with open("newfile.scad", "w") as f:
            f.write(scad_code)

    def plan_shell_sequence(self, prompt: str) -> str:
        """Plan and execute multiple shell commands in sequence."""
        planning_prompt = f"""You are a Windows Command Planner. Convert the user's request into a Python list of Windows CMD commands.

User Request: {prompt}

Rules:
1. Return only a Python list of strings (valid CMD commands)
2. Each command should be a complete, executable Windows command
3. Use Windows-specific commands (dir, mkdir, copy, etc.)
4. Be specific and avoid ambiguous commands
5. Consider command dependencies and order

Example format: ["mkdir new_folder", "dir", "echo Task completed"]

Response:"""

        try:
            response = model.generate_content(planning_prompt)
            commands_str = response.text.strip()
            
            # Remove code fences if present
            if commands_str.startswith("```"):
                lines = commands_str.splitlines()
                commands_str = "\n".join(lines[1:-1]).strip()
            
            # Parse the command list
            commands = eval(commands_str)
            if not isinstance(commands, list):
                return "[SHELL_PLAN ERROR] Response is not a list of commands"
            
            results = []
            for i, cmd in enumerate(commands, 1):
                print(f"🔧 Shell command {i}/{len(commands)}: {cmd}")
                result = self.run_shell(cmd)
                results.append(f"Command {i}: {cmd}\nResult: {result}\n")
                time.sleep(0.5)  # Small delay between commands
            
            return "\n".join(results)
            
        except Exception as e:
            return f"[SHELL_PLAN EXCEPTION] {e}"

    def dispatch(self, task: dict) -> str:
        """Dispatch tasks to appropriate tool methods."""
        intent = task.get('intent', '')
        args = task.get('args', {})
        
        method_map = {
            'run_python': self.run_python,
            'run_shell': self.run_shell,
            'scrape_web': self.scrape_web,
            'ocr_screenshot': self.ocr_screenshot,
            'edit_file': self.edit_file,
            'make_file': self.make_file,
            'delete_file': self.delete_file,
            'run_openscad': self.run_openscad,
            'plan_shell_sequence': self.plan_shell_sequence,
        }
        
        if intent in method_map:
            print("$$$$$$$$$$$$$$$$$$$$$$$$$",method_map[intent](**args))
            return method_map[intent](**args)
        else:
            return f"[DISPATCH ERROR] Unknown intent: {intent}"
