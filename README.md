# FlaskArtisan

FlaskArtisan is a command-line tool inspired by Laravel Artisan,
designed to streamline development workflows in Flask applications. It
provides a convenient CLI interface to generate controllers, manage
project structure, automate repetitive tasks, and improve overall
developer productivity.

## 🚀 Features

-   Artisan-like CLI commands for Flask
-   Generate controllers, models, and boilerplate code
-   Integrates with SQLAlchemy
-   Git automation powered by GitPython
-   Easy to extend and customize
-   Python 3.10+ support

## 📦 Installation

Install FlaskArtisan using `pip`:

``` bash
pip install flaskartisan
```

Or install directly from the source:

``` bash
git clone https://github.com/yourusername/flaskartisan.git
cd flaskartisan
pip install -e .
```

## 🛠 Requirements

-   Python ≥ 3.10\
-   Flask\
-   SQLAlchemy\
-   Click\
-   GitPython

These dependencies are automatically installed when using `pip`.

## 🧰 Usage

FlaskArtisan provides a `flasktool` command, similar to Laravel's
`artisan`.

### View all available commands:

``` bash
flasktool --help
```

### Example: Generate a controller

``` bash
flasktool make:controller UserController --type api
```

### Example: Generate a fullstack module

``` bash
flasktool make:controller Blog --type fullstack
```

## 📁 Project Structure Example

Using FlaskArtisan may generate structures like:

    project_name/
    ├── app/
    │   ├── __init__.py
    │   ├── routes.py
    │   ├── controller/
    │   │   ├── feature/
    │   │   ├   ├──*Controller.py
    │   ├── model/
    │   │   ├── __init__.py
    │   │   ├── *model.py
    │   ├── service/
    │   │   ├── feature
    │   │   ├   ├── *_service.py
    │   ├── static/
    │   │   ├── assets
    │   │   ├   ├── CSS/img/js/etc
    │   ├── templates/
    │   │   ├   ├── base.html
    │   │   ├   ├── 404.html
    │   │   ├   ├── page/
    │   │   ├── assets
    ├── utils/
    │   ├── __init__.py
    │   ├── *.py
    ├── build/ # Dockerfile for dev and production
    ├── config.py
    ├── server.py
    ├── requirements.txt
    ├── .gitignore
    ├── .dockerignore
    ├── setup.sh
    ├── Makefile
    ├── .env.example
    ├── docker-compose.yml
    └── README.md


## ⚙ Configuration

`flasktool` is registered as a script under:

    flasktool = "flasktool.cli:cli"

Meaning you can run CLI commands anywhere inside your project.

## 🤝 Contributing

Contributions are welcome!\
Feel free to submit issues, feature requests, or pull requests.

## 📄 License

This project is licensed under the MIT License.
