# PR Review API - Assignment for potpieai

This is a FastAPI application. Follow the steps below to set up and run the application.

## Requirements

- Docker, Docker-compose
- Ollama (including llama3.2)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/anirudhp26/pr-reviewer

    cd pr-reviewer
    ```

2. Start the ollama server:
    ```bash
    ollama serve
    ```

3. Start llama3.2 model:
    ```bash
    # if model not there pull it
    ollama pull llama3.2

    # otherwise start the model
    ollama run llama3.2
    ```

3. Start docker and run the following commands:

    ```bash
    docker-compose build

    docker-compose up
    ```

## License

This project is licensed under the MIT License.