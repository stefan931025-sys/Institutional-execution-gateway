import os
import re

def clean_markdown_artifacts(directory="."):
    pattern = re.compile(r"span_\d+span_\d+")
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Check if pattern exists in file
                if pattern.search(content):
                    cleaned_content = pattern.sub("", content)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(cleaned_content)
                    print(f"Cleaned artifacts from: {filepath}")

if __name__ == "__main__":
    clean_markdown_artifacts()
    print("Artifact cleanup complete!")
