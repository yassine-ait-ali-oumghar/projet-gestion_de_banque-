# NovaBank - Django Banking Application

This project implements the specifications outlined in the technical document `CAHIER DE CHARGE (PYTHON).docx` using purely **Python**, **Django**, and **Bootstrap (HTML/CSS/JS)**. The unauthorized React frontend has been permanently deleted, and the UI layout and aesthetic features have been natively migrated to Django `templates/` and `static/`.

## Folder Structure Mapping

The architecture perfectly mimics the mandated design:

```text
bank_project/
  |-- accounts/         # Authentication and user profiles
  |-- banking/          # Core transaction and account models
  |-- dashboard/        # Views tracking internal metrics via Chart.js
  |-- notifications/    # System alerts
  |-- cards/            # Credit cards linkage algorithms
  |-- templates/        # Natively integrated HTML (Bootstrap format)
  |-- static/           # Core layout styling and Vanilla JS GSAP Animations
```

## How to Launch the Application

The environment is cleanly organized. Follow these exact steps to start the web application:

1. **Open your Terminal (Powershell / Command Prompt)**
2. Navigate into the main Django project directory:
   ```bash
   cd "bank_project" bank_project
   
   ```
3. To test the integrity of the system before running:
   ```bash
   python manage.py check
   ```
4. Finally, **Start the server**:
   ```bash
   python manage.py runserver
   ```
5. **Open your browser** and navigate to [http://localhost:8000/](http://localhost:8000/). You will see the natively rendered home landing page featuring scroll animations running under plain HTML and Bootstrap!
    'username': 'admin',
    'email': 'admin@novabank.local',
    'password': 'NovaBank-Admin-2026!',