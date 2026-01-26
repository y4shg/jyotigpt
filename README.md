![GitHub stars](https://img.shields.io/github/stars/y4shg/jyotigpt?style=social)
![GitHub forks](https://img.shields.io/github/forks/y4shg/jyotigpt?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/y4shg/jyotigpt?style=social)

![Offline First](https://img.shields.io/badge/Offline--First-Yes-79C83D)
![Privacy](https://img.shields.io/badge/Data-Local%20Only-4CAF50)
![Purpose](https://img.shields.io/badge/Purpose-Meditation%20AI-8E44AD)
![License](https://img.shields.io/github/license/y4shg/jyotigpt)

---

# 🌸 JyotiGPT

**JyotiGPT is a meditation-focused AI designed to support inner clarity, calm thinking, and conscious self-reflection.**

It combines **guided reflective dialogue** with a **fully local, offline AI system**, allowing users to practice meditation and self-inquiry without cloud dependence, distractions, or data sharing.

---

## 🧘 What JyotiGPT Is

JyotiGPT is an AI companion for:

* 🌿 Meditation support
* 🌿 Inner dialogue and self-reflection
* 🌿 Conscious, value-aligned thinking
* 🌿 Quiet, intentional interaction with AI

Rather than encouraging fast answers or endless conversation, JyotiGPT is designed to **slow the interaction**, helping users pause, observe, and return to awareness.

---

## 🌼 How JyotiGPT Helps

### 🧠 Guided Reflection

JyotiGPT gently guides users to look at their thoughts and feelings without judgment, offering prompts that encourage awareness rather than reaction.

### 🌬️ Meditation Preparation & Integration

JyotiGPT can help:

* Set the mental state before meditation
* Ground attention with simple focus cues
* Reflect after meditation to integrate clarity

### 💬 Conscious Conversation

Conversations are designed to be:

* Calm
* Non-reactive
* Supportive, not directive

The goal is **inner stability**, not stimulation.

### 🌱 Support Without Dependency

JyotiGPT does not position itself as a teacher, authority, or replacement for personal effort.
It is a **tool to support self-realization**, not to replace it.

---

## ✨ What Makes JyotiGPT Different

* 🚫 Not entertainment-focused
* 🚫 Not cloud-dependent
* 🚫 Not data-harvesting
* 🚫 Not emotionally manipulative

Instead, JyotiGPT prioritizes:

* 🕊️ Simplicity
* 🔐 Privacy
* 🧘 Stillness
* 🌍 Ethical, local AI use

---

## ⚙️ The Technology Behind JyotiGPT

While JyotiGPT is meditation-oriented in purpose, it is built on a **powerful and flexible AI platform**.

### 🔧 Core Technical Features

* 🖥️ **Offline-First & Self-Hosted**

  * Runs entirely on your own hardware
  * No mandatory internet connection
  * Full data ownership

* 🤖 **LLM Support**

  * Ollama (local models)
  * OpenAI-compatible APIs (optional)

* 📚 **Local RAG (Retrieval-Augmented Generation)**

  * Load local documents (notes, study material, Murli text, PDFs)
  * Ask questions directly against your own files

* 👥 **Multi-User Support with RBAC**

  * Role-based access control
  * Suitable for centers, families, or shared systems

* 🧩 **Extensible by Design**

  * Plugin & pipeline support
  * Python function calling
  * Custom meditation flows or logic

* 📱 **Responsive Web UI + PWA**

  * Works on desktop, tablet, and mobile
  * Installable as a Progressive Web App

---

## 🚀 Getting Started

### 🐍 Install with Python (Simple & Native)

> **Requires Python 3.11**

```bash
pip install jyotigpt
jyotigpt serve
```

Access JyotiGPT at:
👉 [http://localhost:8080](http://localhost:8080)

---

### 🐳 Install with Docker (Recommended)

#### Basic Installation

```bash
docker run -d -p 3000:8080 \
  -v jyotigpt:/app/backend/data \
  --name jyotigpt \
  --restart always \
  ghcr.io/y4shg/jyotigpt:main
```

#### With NVIDIA GPU

```bash
docker run -d -p 3000:8080 \
  --gpus all \
  -v jyotigpt:/app/backend/data \
  --name jyotigpt \
  --restart always \
  ghcr.io/y4shg/jyotigpt:cuda
```

#### Bundled with Ollama (All-in-One)

```bash
docker run -d -p 3000:8080 \
  -v ollama:/root/.ollama \
  -v jyotigpt:/app/backend/data \
  --name jyotigpt \
  --restart always \
  ghcr.io/y4shg/jyotigpt:ollama
```

Access at:
👉 [http://localhost:3000](http://localhost:3000)

---

## 🌙 Offline & Quiet Mode

For fully offline environments:

```bash
export HF_HUB_OFFLINE=1
```

This prevents JyotiGPT from attempting any external downloads.

---

## 🧭 Intended Use

JyotiGPT is suitable for:

* Daily meditation support
* Quiet self-reflection
* Study and contemplation
* Brahma Kumaris centers
* Personal offline AI systems
* Ethical, intentional AI use

---

## ⚠️ Important Note

JyotiGPT is **not**:

* A therapist
* A guru
* A medical or psychological authority

It does not diagnose, prescribe, or replace professional guidance.

---

## 📜 License

Released under the **BSD-3-Clause License**.
You are free to use, modify, and distribute JyotiGPT responsibly.

---

## 🌸 Attribution

**JyotiGPT**
Made by **Yash**

*A conscious approach to artificial intelligence.*

---

If you want next, I can:

* add a **“Daily Meditation Flow using JyotiGPT”** section
* tune language to be **even more BK-institutional**
* or split this into **README + philosophy doc**

Just say 🌼
