# Shopcarts REST API

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)

A RESTful shopping cart management service developed for **CSCI-GA 2820: DevOps and Agile Methodologies** at New York University.

## Overview

The Shopcarts REST API allows customers to manage shopping carts and the products stored in them.

The service supports:

- Creating shopping carts for users
- Retrieving, updating, listing, and deleting shopping carts
- Adding products to shopping carts
- Retrieving, updating, listing, and deleting individual cart items
- Persisting shopping carts and items in PostgreSQL

Each shopcart belongs to a user and can contain multiple items. Each item stores a product ID, name, quantity, and price.

## Technology Stack

- **Python 3.12** — Programming language
- **Flask** — REST API framework
- **Flask-SQLAlchemy** — Database models and persistence
- **PostgreSQL** — Relational database
- **Pytest and pytest-cov** — Automated testing and coverage
- **Flake8 and Pylint** — Code quality checks
- **Docker and VS Code Dev Containers** — Repeatable development environment

## Getting Started

### Prerequisites

- Git
- Docker
- Visual Studio Code
- VS Code Dev Containers extension

### 1. Clone the repository

```bash
git clone https://github.com/CSCI-GA-2820-FA26-001/shopcarts.git
cd shopcarts
```

### 2. Open the development container

Open the repository in Visual Studio Code.

Use the Command Palette and select **Dev Containers: Reopen in Container**.

The development environment includes the application container and a PostgreSQL database container configured through `.devcontainer/docker-compose.yml`.

### 3. Run the service

From the VS Code Dev Container terminal, run:

```bash
make run
```

The Flask service runs on port **8080**.

Open:

http://localhost:8080/

The root endpoint returns JSON containing the service name, version, and Shopcarts collection URL.

## REST API Endpoints

The service provides the following endpoints.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Return service information |
| POST | `/shopcarts` | Create a shopping cart |
| GET | `/shopcarts` | List all shopping carts |
| GET | `/shopcarts/{shopcart_id}` | Retrieve a shopping cart |
| PUT | `/shopcarts/{shopcart_id}` | Update a shopping cart |
| DELETE | `/shopcarts/{shopcart_id}` | Delete a shopping cart |
| POST | `/shopcarts/{shopcart_id}/items` | Add an item to a shopping cart |
| GET | `/shopcarts/{shopcart_id}/items` | List items in a shopping cart |
| GET | `/shopcarts/{shopcart_id}/items/{item_id}` | Retrieve a specific item from a shopping cart |
| PUT | `/shopcarts/{shopcart_id}/items/{item_id}` | Update an existing item in a shopping cart |
| DELETE | `/shopcarts/{shopcart_id}/items/{item_id}` | Delete an item from a shopping cart |

### Shopcart Data Model

A shopcart contains:

- `id` — Unique shopcart identifier
- `user_id` — Identifier of the customer
- `status` — `OPEN` or `CHECKED_OUT`. New shopcarts start `OPEN`. The server manages this field, so a `status` sent in a POST or PUT body is ignored
- `created_at` — Creation timestamp
- `last_updated` — Last modification timestamp
- `items` — List of items in the shopcart

### Item Data Model

An item contains:

- `id` — Unique item identifier
- `shopcart_id` — Identifier of its parent shopping cart
- `product_id` — Product identifier
- `name` — Product name
- `quantity` — Number of units
- `price` — Unit price

### Validation and Error Responses

- Shopcart `user_id` must be an integer (not a boolean).
- Item `product_id` must be an integer, and `name` must be a non-empty string.
- Item `quantity` must be a positive integer (`quantity > 0`).
- Item `price` must be a finite, non-negative number (`price >= 0`).
- The service assigns resource IDs; an item cannot be moved to another shopcart by specifying `shopcart_id` in its request body.
- `400 Bad Request` is returned for invalid resource data.
- `404 Not Found` is returned when a requested shopcart or item does not exist, or when an item does not belong to the specified shopcart.
- `405 Method Not Allowed` is returned for unsupported HTTP methods; `415 Unsupported Media Type` is returned for unsupported request media types.

## API Usage Examples

These examples assume that the application is running on `localhost:8080`.

### Create a Shopping Cart

```bash
curl -X POST http://localhost:8080/shopcarts \
  -H "Content-Type: application/json" \
  -d '{"user_id": 101}'
```

A successful request returns `201 Created` with the new shopcart.

### List Shopping Carts

```bash
curl http://localhost:8080/shopcarts
```

A successful request returns `200 OK` with a JSON array of shopcarts.

### Retrieve a Shopping Cart

```bash
curl http://localhost:8080/shopcarts/1
```

Replace `1` with an existing shopcart ID.

### Add an Item to a Shopping Cart

```bash
curl -X POST http://localhost:8080/shopcarts/1/items \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1001,
    "name": "Notebook",
    "quantity": 2,
    "price": 12.99
  }'
```

A successful request returns `201 Created` with the created item.

### List Items in a Shopping Cart

```bash
curl http://localhost:8080/shopcarts/1/items
```

### Retrieve a Specific Item

```bash
curl http://localhost:8080/shopcarts/1/items/1
```

Replace both IDs with an existing shopcart and an item belonging to that shopcart. A successful request returns `200 OK` with the item's JSON representation.

### Update an Item

```bash
curl -X PUT http://localhost:8080/shopcarts/1/items/1 \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1001,
    "name": "Large notebook",
    "quantity": 5,
    "price": 9.99
  }'
```

Replace both IDs with an existing shopcart and an item belonging to it. Send all four fields (`product_id`, `name`, `quantity`, and `price`) in the PUT request. A successful update returns `200 OK` with the updated item. The item ID and its parent shopcart stay unchanged; `id` and `shopcart_id` in the request body are ignored. Invalid item data returns `400 Bad Request`, and a missing shopcart, missing item, or item belonging to a different shopcart returns `404 Not Found`.

### Delete an Item

```bash
curl -X DELETE http://localhost:8080/shopcarts/1/items/1
```

A successful deletion returns `204 No Content`.

## Testing and Code Quality

### Run Automated Tests

```bash
make test
```

The test suite uses Pytest and enforces a minimum of **95% code coverage**.

### Run Code Quality Checks

```bash
make lint
```

This command runs Flake8 and Pylint against the application and test code.

### Available Development Commands

| Command | Purpose |
|---|---|
| `make help` | Display available commands |
| `make install` | Install Python dependencies |
| `make run` | Start the application |
| `make test` | Run tests with coverage |
| `make lint` | Run Flake8 and Pylint |

## Project Structure

```text
shopcarts/
├── .devcontainer/          # VS Code development environment
├── service/
│   ├── __init__.py         # Flask application initialization
│   ├── config.py           # Application configuration
│   ├── models.py           # Shopcart and Item models
│   ├── routes.py           # REST API routes
│   └── common/             # Error handling, logging, utilities
├── tests/
│   ├── factories.py        # Test data factories
│   ├── test_cli_commands.py
│   ├── test_models.py
│   └── test_routes.py
├── wsgi.py                 # Application entry point
├── Procfile                # Application process configuration
├── Pipfile                 # Python dependencies
├── Makefile                # Development commands
└── README.md               # Project documentation
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

This repository was developed for **CSCI-GA.2820-001: DevOps and Agile Methodologies** at New York University, taught by [John Rofrano](https://cs.nyu.edu/~rofrano/).

The project is based on the NYU DevOps project template, which includes original material copyrighted by John Rofrano.
