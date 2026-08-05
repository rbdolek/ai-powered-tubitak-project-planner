# AI-Powered TÜBİTAK Project Planning Assistant

<p align="center">
  <img src="imagine/banner.png" width="100%">
</p>

<p align="center">
  <strong>Graduation Project • Artificial Intelligence • Django • LSTM • OpenAI • Project Planning</strong>
</p>

---

# Executive Summary

The AI-Powered TÜBİTAK Project Planning Assistant is an intelligent web platform developed as a Computer Engineering graduation project.

The system assists researchers and university students in preparing long-term project plans for TÜBİTAK research programs. Based on the selected funding program, project topic, and official project duration, the platform automatically generates a personalized monthly project roadmap.

Unlike traditional planning tools, the system supports two different artificial intelligence approaches:

- OpenAI-based intelligent planning
- A custom-trained LSTM sequence generation model

The generated plans can be viewed as a project calendar, downloaded as PDF reports, and managed through a personalized user profile.

---

# Project Motivation

Preparing a TÜBİTAK research project requires careful planning over several months.

Researchers often struggle with:

- Creating realistic project timelines
- Dividing work into monthly milestones
- Managing project documentation
- Tracking progress
- Organizing research activities

This project aims to automate this planning process using artificial intelligence.

---

# Key Features

- AI-powered project planning
- TÜBİTAK program selection
- Automatic timeline generation
- Personalized monthly work plans
- OpenAI integration
- Custom-trained LSTM model
- User authentication
- Project history
- Chat history
- Calendar integration
- PDF export
- User profile management

---

# System Workflow

```text
User Login
      │
      ▼
Select TÜBİTAK Program
      │
      ▼
Enter Project Topic
      │
      ▼
Choose AI Model
(OpenAI / LSTM)
      │
      ▼
AI Generates Project Plan
      │
      ▼
Monthly Timeline
      │
      ▼
Calendar Integration
      │
      ▼
Project Storage
      │
      ▼
PDF Export
```

---

# Artificial Intelligence Models

## OpenAI Model

The OpenAI model generates project plans based on the selected TÜBİTAK funding program and user-defined project topic.

This model provides intelligent planning using large language model capabilities.

---

## Custom LSTM Model

A custom LSTM-based sequence generation model was developed and trained as part of this project.

Training data was prepared from project planning examples, allowing the model to learn project planning structures and generate planning recommendations without relying solely on external AI services.

The LSTM model was integrated directly into the Django application and can be selected as an alternative planning engine.

---

# Project Architecture

```text
                    User
                      │
                      ▼
             Django Web Application
                      │
      ┌───────────────┴───────────────┐
      │                               │
      ▼                               ▼
OpenAI API                  Custom LSTM Model
      │                               │
      └───────────────┬───────────────┘
                      ▼
            Project Planning Engine
                      ▼
              Calendar Generator
                      ▼
            PDF Report Generator
                      ▼
             SQLite Database
```

---

# Screenshots

## AI Chat Interface

<img src="images/chat-interface.png" width="900">

---

## Project Calendar

<img src="images/calendar.png" width="900">

---

## User Profile

<img src="images/profile.png" width="900">

---

# Technologies Used

| Category | Technology |
|-----------|------------|
| Backend | Django |
| API | Django REST Framework |
| AI | TensorFlow |
| Deep Learning | LSTM |
| NLP | NLTK |
| Dataset Processing | Pandas |
| Numerical Computing | NumPy |
| Machine Learning | Scikit-Learn |
| Visualization | Matplotlib |
| Database | SQLite |
| Report Generation | ReportLab |
| AI API | OpenAI |
| Frontend | HTML, CSS, JavaScript |

---

# Dataset

The project includes custom datasets prepared for training the LSTM sequence generation model.

Examples include:

- Project planning data
- Question-answer pairs
- Extended planning datasets

These datasets were preprocessed before model training.

---

# Model Training

The project includes multiple experimental training pipelines including:

- LSTM
- Sequence-to-Sequence LSTM
- T5 Transformer experiments

Model checkpoints and training logs were generated throughout the development process.

---

# Main Modules

- User Management
- AI Planning Engine
- LSTM Training Module
- OpenAI Integration
- Calendar Management
- Project Repository
- Chat History
- PDF Generator
- User Profiles

---

# Skills Demonstrated

- Artificial Intelligence
- Deep Learning
- LSTM
- Natural Language Processing
- Django
- REST API Development
- Python
- TensorFlow
- Database Design
- Software Architecture
- Full Stack Development
- Machine Learning

---

# Future Improvements

Potential future enhancements include:

- Transformer-based planning models
- Retrieval-Augmented Generation (RAG)
- Multi-language support
- Team collaboration
- Mobile application
- Cloud deployment

---

# Repository Structure

```text
ai-powered-tubitak-project-planner

│
├── agent_ai/
├── agent_ai2/
├── agent_memory/
├── chat/
├── project_planning/
├── users/
├── templates/
├── media/
├── model_checkpoints/
├── nltk_data/
├── manage.py
├── requirements.txt
└── README.md
```

---

# Disclaimer

This repository has been prepared for educational and portfolio purposes.

Sensitive API keys, configuration files, and private credentials have been removed before publication.
