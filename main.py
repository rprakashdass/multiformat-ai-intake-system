import os
import sys
from agents.classifier_agents import main

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

main()