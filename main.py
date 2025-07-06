import real_tools
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

# ---------------- CONFIGURE GEMINI ----------------
genai.configure(api_key="AIzaSyAT891OKC8Aj3lst8ges1g4Dt_doR2aLaM")  # replace with your key
model = genai.GenerativeModel('gemini-1.5-flash')

# ---------------------- AGENT ----------------------
class Agent:
    def __init__(self, llm_client, tools):
        self.llm = llm_client
        self.tools = tools
        self.history = []

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        Extract the first JSON array or object from text by locating matching brackets.
        Returns the JSON substring, or original text if not found.
        """
        # Remove code fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        
        # Attempt to extract array
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        # Attempt to extract object
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return text

    def plan(self, user_prompt: str) -> list:
        system_prompt = """You are an intelligent WINDOWS CLI agent. Your job is to understand the user's raw instruction and break it down into a list of executable tasks in JSON format.

AVAILABLE INTENTS:
- "run_python": Execute Python code or run a Python file
- "run_shell": Execute Windows command line commands
- "scrape_web": Search and scrape web content using DuckDuckGo
- "ocr_screenshot": Take a screenshot and extract text using OCR
- "edit_file": Modify existing files (find/replace or append)
- "make_file": Create new files with specified content
- "delete_file": Delete files or directories
- "run_openscad": Generate 3D models using OpenSCAD
- "plan_shell_sequence": Execute multiple shell commands in sequence

RESPONSE FORMAT:
- Output ONLY a valid JSON array of objects
- NO explanations, comments, or extra text
- Each object must have: {"intent": "...", "args": {...}}

ARGS STRUCTURE EXAMPLES:
- run_python: {"code": "print('hello')"} OR {"filepath": "script.py"}
- run_shell: {"command": "dir"}
- scrape_web: {"query": "python tutorials"}
- ocr_screenshot: {} (no args needed)
- edit_file: {"filepath": "test.txt", "edits": {"find": "old", "replace": "new"}} OR {"filepath": "test.txt", "content": "new content"}
- make_file: {"filepath": "new.txt", "content": "file content"}
- delete_file: {"filepath": "file.txt"} OR {"dirpath": "folder"}
- run_openscad: {"scad_code": "cube([1,1,1]);", "output_path": "model.stl"}
- plan_shell_sequence: {"prompt": "user request for multiple commands"}

PLANNING GUIDELINES:
1. Break complex tasks into logical steps
2. Use appropriate tools for each subtask
3. Consider dependencies between steps
4. Be specific with file paths and commands
5. For web research, use descriptive search queries
6. For Python tasks, write complete, working code

EXAMPLES:
User: "Create a Python script that prints hello world"
Response: [{"intent": "make_file", "args": {"filepath": "hello.py", "content": "print('Hello, World!')"}}]

User: "Search for Python tutorials and save the results to a file"
Response: [
    {"intent": "scrape_web", "args": {"query": "Python programming tutorials beginner"}},
    {"intent": "make_file", "args": {"filepath": "search_results.txt", "content": "Python tutorial search results will be saved here"}}
]

User: "Delete the old backup folder and create a new one"
Response: [
    {"intent": "delete_file", "args": {"dirpath": "backup_old"}},
    {"intent": "run_shell", "args": {"command": "mkdir backup_new"}}
]

User: "Make a dragon in openscad."
Response: [

  {
    "intent": "run_openscad",
    "args": {
      "scad_code": "union() {\n  // Body\n  translate([0,0,0]) sphere(5);\n  // Neck\n  translate([0,5,0]) cylinder(h=5, r1=2, r2=1);\n  // Head\n  translate([0,10,0]) sphere(2);\n  // Wings\n  translate([-8,0,0]) rotate([0,0,45]) cube([2, 10, 0.5]);\n  translate([6,0,0]) rotate([0,0,-45]) cube([2, 10, 0.5]);\n  // Tail\n  translate([0,-6,0]) rotate([0,0,0]) cylinder(h=6, r1=1, r2=0.2);\n}",
      
      "output_path": "dragon_like_shape.stl"
    }
  }
]



]"""

        prompt = f"{system_prompt}\n\nUSER REQUEST: {user_prompt}"
        
        try:
            response = self.llm.generate_content(prompt)
            text = response.text.strip()
            
            # Extract JSON from response
            json_str = self._extract_json(text)
            plan = json.loads(json_str)
            
            if not isinstance(plan, list):
                plan = [plan]
                
            print(f"🎯 Generated plan: {len(plan)} steps")
            for i, step in enumerate(plan, 1):
                print(f"  {i}. {step.get('intent', 'unknown')} - {step.get('args', {})}")
                
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing error: {e}")
            # Fallback to shell planning
            plan = [{"intent": "plan_shell_sequence", "args": {"prompt": user_prompt}}]
        except Exception as e:
            print(f"⚠️ Planning error: {e}")
            plan = [{"intent": "run_shell", "args": {"command": "echo Failed to plan task"}}]
        
        self.history.extend([
            {"from": "user", "text": user_prompt},
            {"from": "agent", "text": plan}
        ])
        print(self.history)
        return plan

    def execute(self, action: dict) -> dict:
        print(f"🔧 Executing: {action.get('intent')} with args: {action.get('args', {})}")
        result = self.tools.dispatch(action)
        # print("##################",result)
        obs = {"action": action.get("intent"), "result": result}
        self.history.append({"from": "tool", "text": obs})
        # print("###########################", obs)
        return obs

    def reflect(self, observation: dict) -> str:
        reflection_prompt = f"""TASK REFLECTION:
Previous action: {observation.get('action')}
Result: {observation.get('result')}

INSTRUCTIONS:
1. Analyze if the task completed successfully
2. If successful and no more steps needed, respond with exactly: DONE
3. If failed or incomplete, provide exactly ONE JSON object with next action

AVAILABLE INTENTS: run_python, run_shell, scrape_web, ocr_screenshot, edit_file, make_file, delete_file, run_openscad, plan_shell_sequence

Response format: {{"intent": "...", "args": {{...}}}}

What should happen next?"""

        try:
            response = self.llm.generate_content(reflection_prompt)
            text = response.text.strip()
            
            if text.upper() in ("DONE", "FINISHED", "COMPLETE"):
                return "DONE"
                
            return self._extract_json(text)
        except Exception as e:
            print(f"⚠️ Reflection error: {e}")
            return "DONE"

    def run(self, user_prompt: str):
        print(f"🚀 Starting task: {user_prompt}")
        actions = self.plan(user_prompt)
        
        for i, action in enumerate(actions, 1):
            print(f"\n📍 Step {i}/{len(actions)}")
            obs = self.execute(action)
            
            # Follow-up reflection loop
            for attempt in range(3):  # Reduced from 10 to 3 to prevent infinite loops
                next_step = self.reflect(obs)
                
                if not next_step or next_step.upper() in ("DONE", "FINISHED", "COMPLETE"):
                    print("✅ Step completed successfully")
                    break
                    
                # Try to parse next action
                next_json = self._extract_json(next_step)
                try:
                    next_action = json.loads(next_json)
                    print(f"🔄 Follow-up action needed (attempt {attempt + 1})")
                    obs = self.execute(next_action)
                except json.JSONDecodeError:
                    with open("raw_response.txt", "w", encoding="utf-8") as f:
                        f.write(next_step)
                    print("⚠️ Unable to parse follow-up JSON; see raw_response.txt")
                    break
            else:
                print("⚠️ Maximum follow-up attempts reached")
        
        print("\n🎉 All tasks completed!")


if __name__ == '__main__':
    print("🤖 Enhanced AI Agent Starting...")
    print("Available intents: run_python, run_shell, scrape_web, ocr_screenshot, edit_file, make_file, delete_file, run_openscad, plan_shell_sequence")
    print("Type 'quit' or 'exit' to stop\n")
    
    tools = real_tools.Tools()
    agent = Agent(llm_client=model, tools=tools)
    
    while True:
        try:
            ui = input("💬 What do you want to do? > ")
            if ui.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            if ui.strip():
                agent.run(ui)
            print("\n" + "="*50 + "\n")
        except KeyboardInterrupt:
            print("\n Goodbye!")
            break
        # except Exception as e:
        #     print(f"Unexpected error: {e}")
        #     print("Continuing...\n")


### work on openscad function