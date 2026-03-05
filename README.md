# FoodFlow Agent

FoodFlow is an intelligent nutrition control system powered by OpenAI agents. It helps you manage your pantry, fridge, and diet plans through a simple Telegram interface.

## Features

- **Agent-based Data Analysis**: Automatically extracts information from your messages (e.g., "I bought milk") to update its databases.
- **Inventory Management**: Tracks Fridge, Pantry, and Freezer items with expiry dates.
- **Dietary & Health Profile**: Remembers family allergies, health issues, and goals.
- **Meal Planning & Shopping Lists**: Generates plans based on what you have and what you like.
- **Image Recognition**: Can analyze photos of your fridge or groceries (via GPT-4o Vision).

## Setup

1. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Rename `.env.example` to `.env` and fill in your keys:
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `TELEGRAM_TOKEN`: Your Telegram Bot Token (from @BotFather).

3. **Run the Application**
   - **Backend**:
     ```bash
     python src/server.py
     ```
   - **Frontend**:
     ```bash
     cd frontend
     npm run dev
     ```

## Usage

- **Web Interface**:
  - Open http://localhost:5173
  - **Chat**: Talk to the bot, upload images of your food/fridge.
  - **Data**: View and edit your inventory and preferences in the Data tab.
  - **Settings**: Change language in the sidebar.

- **Telegram**:
  - Just talk to the bot.
  - "I bought 2kg of chicken breast and a dozen eggs."
  - "My son is allergic to peanuts."
  - "What can I cook with what I have in the fridge?"
- **Images**: Send a photo of your groceries or fridge to automatically catalog items (functionality depends on specific prompt tuning).

## Project Structure

- `src/`: Source code
  - `agent.py`: Core logic interacting with OpenAI.
  - `data_manager.py`: Handles CSV database operations.
  - `main.py`: Telegram bot interface.
- `data/`: CSV files (generated automatically).

## License
Open Source.
