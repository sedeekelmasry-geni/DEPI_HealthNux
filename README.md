# 🏥 HealthNux

### A Data-Driven Electronic Medical Record (EMR) and Clinic Management Platform

HealthNux is a healthcare management platform developed to support the digital transformation of clinics and polyclinics by replacing traditional paper-based workflows with a centralized Electronic Medical Record (EMR) system.

The platform enables healthcare providers to manage:

* Patient Profiles
* Appointment Scheduling
* Clinical Visits
* Vital Signs
* ICD-10 Diagnoses
* Prescriptions
* Laboratory Results
* Radiology Findings
* Physician Scheduling
* Billing & Payments

In addition to healthcare management functionalities, HealthNux applies modern Data Engineering concepts through PostgreSQL, Google BigQuery, ETL synchronization pipelines, healthcare reference datasets, and analytics-ready architecture.

Developed as part of the **Digital Egypt Pioneers Initiative (DEPI)**.

---

# 🚀 Key Features

* Centralized Electronic Medical Records (EMR)
* Patient History Management
* Appointment Scheduling
* Doctor Timetable Management
* ICD-10 Integration
* Chronic Disease Classification
* Prescription Management
* Laboratory Result Tracking
* Radiology Result Tracking
* Billing & Payment Tracking
* Google Calendar Holiday Integration
* Drug Reference Integration
* PostgreSQL Operational Database
* Google BigQuery Data Warehouse
* ETL Synchronization Pipelines
* Analytics-Ready Architecture

---

# 🏗️ System Architecture

```text
NiceGUI Frontend
        │
        ▼
Python Backend
        │
        ▼
PostgreSQL (Operational Database)
        │
        ▼
ETL Synchronization Layer
        │
        ▼
Google BigQuery (Data Warehouse)
        │
        ▼
Analytics & Reporting
```

---

# 👥 Contributors

| Team Member        | Role                                         |
| ------------------ | -------------------------------------------- |
| **Sedeek Ashraf** | Technical Lead & Data Engineering Lead       |
| **Nermeen Diaa**   | System Analysis & Architecture Documentation |
| **Ghada Fathy**    | Database Development Support                 |
| **Ahmed Magdy**    | Presentation & Project Communication         |

---

## Contribution Summary

### Sedeek Ashraf 
GitHub: @sedeekelmasry-geni
* System Analysis
* Database Architecture
* PostgreSQL Implementation
* BigQuery Integration
* ETL Pipeline Development
* ICD-10 Processing
* AI-Assisted Translation Workflow
* Chronic Disease Classification
* Google Calendar Integration
* Drug Database Integration
* Backend Development
* Healthcare Data Engineering
* System Integration
* Technical Leadership

### Nermeen Diaa
GitHub: @NerminDiaa
* ERD Design
* Data Pipeline Design
* System Architecture Documentation
* Technical Diagrams

### Ghada Fathy
GitHub: @drghadaali
* Doctors Table Development
* Vitals Table Development
* Database Support & Validation

### Ahmed Magdy
GitHub: @ahmaddiaa949-alt
* Presentation Design
* Project Demonstration Support
* Project Communication Materials

---

# 🛠️ Technologies & Libraries

## Frontend

* NiceGUI

## Backend

* Python

## Databases

* PostgreSQL
* Google BigQuery

## Python Libraries

```python
nicegui
pandas
sqlalchemy
datetime
sys
psycopg2
ast
fpdf
pathlib
google.cloud
google.oauth2
bs4
requests
urllib3
bcrypt
shutil
tkinter
lxml
googleapiclient.discovery
```

---

# 📂 Project Setup

## Prerequisites

Before starting the setup process, make sure you have the following:

### 1. PostgreSQL Database

You will need:

* PostgreSQL Server Installed
* PostgreSQL Database URL
* PostgreSQL Username
* PostgreSQL Password

The setup process will request the PostgreSQL connection URL and credentials required to initialize the operational database.

---

### 2. Google BigQuery

You will need:

* Google Cloud Project
* BigQuery Dataset
* Service Account Credentials JSON File

The setup process requires a valid Google Service Account Key in JSON format.

Example:

```text
project-key.json
```

This file is used to authenticate with BigQuery and perform:

* Dataset creation
* Table creation
* Data synchronization
* Data warehouse operations

---

### 3. Google Calendar API

You will need:

* Google Calendar API Key

This key is used to retrieve official holidays and automatically exclude holidays from doctor schedules and available visits generation.

---

# 📁 Required Resource Files

Before running the database setup process, make sure the following files are completed and placed inside the Resources folder:

```text
Dr_List.xlsx
Labs_Ref.xlsx
Scans_Ref.xlsx
```

### Dr_List.xlsx

Contains:

* Doctor Information
* Specialties
* Consultation Fees
* Scheduling Information

### Labs_Ref.xlsx

Contains:

* Laboratory Test Reference Data

### Scans_Ref.xlsx

Contains:

* Radiology and Imaging Reference Data

These files are loaded during the database initialization process.

---

# ⚠️ Important Configuration Note

This repository was originally configured using the development team's Google Cloud environment.

Before running the project, testers and reviewers must update all references related to:

```text
Google Cloud Project ID
BigQuery Project ID
BigQuery Dataset Name
BigQuery Credentials Path
```

inside the project files.

Failure to replace these values with your own Google Cloud configuration may result in authentication or synchronization errors.

---

# 🗄️ Database Setup

Navigate to:

```text
database_setup/
```

The setup process is organized as a sequence of Jupyter Notebooks.

Run the notebooks in the following order:

```text
0
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
```

---

## Notebook 0

Notebook 0 is responsible for environment initialization.

It will prompt the user to provide:

### Required Inputs

* BigQuery Service Account JSON File
* PostgreSQL Database URL
* PostgreSQL Login Credentials
* Google Calendar API Key

After completion, the notebook automatically:

* Creates local configuration files
* Creates the required key folder
* Stores credentials securely for the remaining setup notebooks
* Initializes project configuration

Once Notebook 0 is completed successfully, continue executing the remaining notebooks sequentially.

---

# ▶️ Running the Application

After completing all setup notebooks:

Navigate to the GUI directory and run:

```bash
python index.py
```

or

```bash
python index_GUI.py
```

(depending on the project version)

The application will automatically launch in your default web browser.

---

# 🗄️ Core Database Modules

* Users
* Patients
* Doctors
* Doctor Timetable
* Available Visits
* Booked Visits
* Vitals
* Payments
* ICD Codes
* Labs
* Scans
* Lab References
* Scan References
* RX Medications
* Holidays

---

# 🔄 Data Engineering Components

## Operational Database

* PostgreSQL

## Data Warehouse

* Google BigQuery

## ETL Processes

* Data Extraction
* Data Transformation
* Data Validation
* Data Synchronization
* Data Warehousing

## External Integrations

### WHO ICD-10 Dataset

Used for diagnosis standardization and chronic disease classification.

### Google Calendar API

Used for holiday management and schedule optimization.

### Drug Reference Database

Integrated through web scraping to provide medication lookup functionality.

---

# 📊 Future Enhancements

* Patient Portal
* Multi-Clinic Support
* Cloud Deployment
* Power BI Integration
* Looker Studio Dashboards
* Advanced Healthcare Analytics
* Predictive Healthcare Insights

---

# 📖 Documentation

Documentation Link:

```text
https://drive.google.com/file/d/1qtkdV94bzPvdNTSMmPGcw1Mh0GVPgA3I/view?usp=sharing
```

---

# 🎥 Demo

Demo Video Link:

```text
https://drive.google.com/file/d/1t2y69PEZ6flOh1fPJTYc6LvFzLCsVCO2/view?usp=sharing
```

---

# 🌐 Project Brochure / Website

Project Website:

```text
https://claude.ai/public/artifacts/87e6d925-40e5-4595-b107-00222e6fe79f
```

---

# 📜 License

This project was developed as part of the Digital Egypt Pioneers Initiative (DEPI) for educational, research, and demonstration purposes.

All healthcare data used during development and testing should comply with applicable privacy and security regulations.
