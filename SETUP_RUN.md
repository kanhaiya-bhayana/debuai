# DebugAI - Setup & Run Guide

This guide helps you set up and run DebugAI locally.

---

## 🛠 Prerequisites

- Python 3.9+
- pip (Python package manager)

Optional (for AI features):
- NVIDIA API key (or any configured LLM provider)

---

## 📦 Clone the Repository

```bash
git clone https://github.com/kanhaiya-bhayana/debuai.git
cd debuai
```

---

## ⚙️ Install the Project

Install in editable mode:

```bash
pip install -e .
```

This allows you to make changes and use the CLI without reinstalling.

---

## 🔑 Setup API Key (For AI Mode)

Set your API key as an environment variable.

### macOS / Linux

```bash
export NVIDIA_API_KEY="your_api_key_here"
```

To persist it:

```bash
echo 'export NVIDIA_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

---

## 🚀 Run the Tool

### 1️⃣ Using a File

```bash
debuai examples/python_error.log
```

### 2️⃣ With AI Analysis

```bash
debuai examples/python_error.log --ai
```

---

## 🔄 Using STDIN (Recommended)

### From a file

```bash
cat examples/python_error.log | debuai
```

### With AI

```bash
cat examples/python_error.log | debuai --ai
```

---

## ✏️ Direct Input

```bash
debuai "NullReferenceException at OrderService.CalculateTotal()"
```

---

## 📋 Clipboard Support (macOS)

```bash
pbpaste | debuai --ai
```

---

## 🧪 Example Input

You can test using:

```
examples/python_error.log
```

Example content:

```
System.NullReferenceException
at OrderService.CalculateTotal()
at CartService.Checkout()
at CheckoutController.PlaceOrder()
```

---

## 🧠 What the Tool Does

DebugAI will:

* Extract exception type
* Identify failure origin
* Reconstruct execution chain
* Optionally use AI for:

  * Root cause analysis
  * Suggested fixes
  * Prevention strategies

---

## ❗ Troubleshooting

### Command not found: debuai

Add Python scripts to PATH:

```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

---

### API Key Not Found

```bash
echo $NVIDIA_API_KEY
```

If empty, set it again.

---

### AI Not Working

* Ensure API key is valid
* Check internet connectivity
* Verify model configuration

---

## ✅ Verify Installation

Run:

```bash
debuai --help
```

If this works, setup is complete 🎉
