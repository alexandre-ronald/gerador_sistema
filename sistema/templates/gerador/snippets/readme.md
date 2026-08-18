# {{ sistema.nome }}

{{ sistema.descricao }}

## Instalação

```bash
python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Linux/macOS

```bash
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Configuração

As configurações sensíveis podem ser definidas por variáveis de ambiente, incluindo `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` e `DJANGO_ALLOWED_HOSTS`.

## Banco de dados

O projeto é gerado com a configuração selecionada na especificação. Para PostgreSQL, configure `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e `POSTGRES_PORT`.
