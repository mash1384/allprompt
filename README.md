# allprompt

A desktop application for easily generating code snippets for LLM prompts.

## Introduction

This application allows you to select a code folder and include only the necessary files, converting them into a format suitable for LLM prompts. With an intuitive interface, you can check the token count in real-time while efficiently excluding unnecessary files using `.gitignore` rules.

## Key Features

- 📁 **Folder Structure Visualization** - Navigate the file system with a tree view
- ✅ **Selective Inclusion/Exclusion** - Apply checkboxes and `.gitignore` rules
- 🔢 **Real-time Token Calculation** - Display token count of selected content
- 📋 **Standardized Output** - `<file_map>` and `<file_contents>` format
- 🔍 **Automatic File Processing** - Text/binary file detection and support for various encodings

## Download and Installation

### Released Version (General Users)

Download from [GitHub Releases](https://github.com/mash1384/allprompt/releases):
- **macOS**: Download and extract `allprompt.app.zip`
- **Windows**: not yet

> **Note**: When first running on macOS, you may see an "unidentified developer" warning. Please allow it in System Preferences > Security & Privacy.

### Install from Source (Developers)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/allprompt.git
cd allprompt

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python -m src.main
```

## How to Use

1. Launch the application
2. Click the **Open Folder** button to select a code folder
3. Check files/folders to include in the tree view
4. Check the real-time token count
5. Click the **Copy to Clipboard** button
6. Paste into ChatGPT, Claude, or other LLM prompts

## Technical Notes

This project was developed using the Vibe coding approach. Vibe coding focuses on rapid prototyping and development, so some features or error handling may not be perfect. If you encounter issues during use, please register an issue.



## License

[MIT License](LICENSE)