"""main.py - PJ-AG2 运行入口 (python main.py)"""
import subprocess, sys, os
script_dir = os.path.dirname(os.path.abspath(__file__))
run_script = os.path.join(script_dir, "run.py")
subprocess.run([sys.executable, run_script] + sys.argv[1:])