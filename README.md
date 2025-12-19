# 🎓 MauryaHub - Academic Resource Portal

[![Flask](https://img.shields.io/badge/Flask-2.3.3-blue)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow)](https://python.org)
[![License](https://img.shields.io/badge/License-Educational-orange)](LICENSE)

A comprehensive web portal for managing academic resources like PYQs, notes, and assignments, built for educational institutions.

> ### 🚀 [**View Live Demo**](https://mauryahub.onrender.com/) 🚀
> *Check out the live version of the portal hosted on Render.*

---

## ✨ Core Features

#### For Students
- **Course Dashboard**: Clean, card-based view of all available courses.
- **Resource Access**: Easily view PYQs, notes, assignments, and videos.
- **YouTube Integration**: Embedded videos with watch count tracking.
- **Fully Responsive**: Mobile-friendly interface for learning on any device.

#### For Admins & Security
- **Full CRUD Operations**: Manage courses and all associated resources.
- **Automatic DB Backups**: Database is backed up on critical operations.
- **Delete Confirmations**: Safety dialogs prevent accidental deletions.
- **Secure Admin Login**: Simple and secure session-based authentication.

---

## 💻 Tech Stack

-   **Backend**: **Flask**, **Python 3.11+**
-   **Database**: **SQLite**
-   **Frontend**: **HTML5**, **CSS3**, **Jinja2**
-   **Deployment**: **Gunicorn**, **Render.com**

---

## 🚀 Quick Start (Local Setup)

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/22f3000982/MauryaHub.git](https://github.com/22f3000982/MauryaHub.git)
    cd MauryaHub
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application**
    ```bash
    python app.py
    ```
    -   Access the portal at `http://localhost:5000`.
    -   Admin login is available on any course detail page. 

---


## 🎯 Roadmap & Contributing

We have a lot planned for the future!

-   [ ] User roles (Editors, Viewers)
-   [ ] Direct file uploads
-   [ ] Full-text search across all resources
-   [ ] Advanced analytics dashboard

Contributions are welcome! Please fork the repo, create a feature branch, and open a pull request.

---

## 📄 License

This project is created for educational purposes. Please use it responsibly and in accordance with your institution's policies.

**Built with ❤️ for education.**

Copy-Item "last.db" -Destination "database.db" -Force
