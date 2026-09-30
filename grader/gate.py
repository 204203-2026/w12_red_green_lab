import json
import sys

report = json.load(open("results/report.json"))
sys.exit(0 if report["score"] == report["total"] else 1)
