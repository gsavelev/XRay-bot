**Язык / Language:** [Русский](../README.md) **|** <ins>English</ins>

<div id="header" align="center"><h1>XRay VPN Bot [Telegram]</h1></div>

## Project Description

This project is a Telegram bot for managing VPN subscriptions via the 3X-UI control panel. The bot allows users to issue VPN subscriptions, create and manage their profiles, and enables administrators to manage users and track statistics.

Key Features:

- User registration
- Creation and deletion of VPN profiles (VLESS) in the 3X-UI panel
- Administrative menu for user management and broadcast messages
- Traffic usage statistics

## Installation and Setup

### Prerequisites

- Python 3.10+
- 3X-UI control panel
   - An inbound created with the security set to `Reality`
- A Telegram bot (created via `@BotFather`)

### Installation Steps

1. Clone the repository:

```bash
git clone https://github.com/gsavelev/XRay-bot
cd XRay-bot
```

2. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp src/.env.example src/.env
# Edit the .env file with your values
```

4. Create a directory for database storage:

```bash
mkdir -p ./app/data
```

5. Run the bot:

```bash
python3 src/app.py
```

### Environment Variables Configuration

Mandatory parameters in `.env`:

- `BOT_TOKEN` - Your Telegram bot token from @BotFather
- `ADMINS` - Administrator IDs, comma-separated
- `CHAT_ID` - Chat/group ID with users
- `XUI_API_URL` - 3X-UI panel URL (e.g., http://ip:54321)
- `XUI_USERNAME` and `XUI_PASSWORD` - Panel credentials
- `INBOUND_ID` - Inbound ID in the 3X-UI panel
- Reality parameters (public key, fingerprint, SNI, etc.)

## Technical Architecture

### File Structure

```
./
├── src
│   ├── .env.example        # Example configuration file
│   ├── app.py              # Main application file
│   ├── config.py           # Application configuration
│   ├── database.py         # Database models and functions
│   ├── functions.py        # Functions for 3X-UI API interaction
│   └── handlers.py         # Command and callback handlers
├── docs                    # Documentation in other languages
│   └── README.en_US        # Documentation in English
├── app
│   └── data
│       └── users.db        # SQLite database file. Created on first bot run
├── Dockerfile              # Container configuration
├── README.md               # Documentation in Russian
└── requirements.txt        # Project dependencies
```

### Database

The project uses `SQLite` with `SQLAlchemy ORM`. Main tables:

1. **`users`** - User information:
   - `telegram_id` - User's Telegram ID
   - `vless_profile_data` - VPN profile data in JSON
   - `chat_member` - Chat/group membership flag
   - `is_admin` - Administrator flag
2. **`static_profiles`** - Static VPN profiles:
   - `name` - Profile name
   - `vless_url` - VLESS URL

### Core Components

#### 1. `app.py`
Main application file:
- Initializes the database
- Starts the background profile revision task
- Starts polling for the bot

#### 2. `config.py`
Loads and validates configuration using `Pydantic`. Includes:
- 3X-UI panel connection settings
- Reality protocol parameters

#### 3. `database.py`
Database models and functions:
- `User` model for users
- `StaticProfile` model for static profiles
- Functions for profile management

#### 4. `functions.py`
`XUIAPI` class for interaction with 3X-UI panel:
- Panel authentication
- Creating and deleting clients
- Retrieving usage statistics
- VLESS URL generation

#### 5. `handlers.py`
Command and callback handlers:
- `/start` and `/menu` commands
- Administrative functions
- Profile management

## Administrative Functions

Administrators have access to a special menu:
- View the user list
- Network usage statistics
- Broadcast messages to users
- Manage static profiles

## Integration with **3X-UI**
Bot interacts with the **3X-UI** panel via its API:
1. Authentication via login/password
2. Retrieving inbound data
3. Adding clients to inbound settings
4. Updating inbound configuration

## VLESS URL Generation
VLESS URL format for Reality:
```
vless://{client_id}@{host}:{port}?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}&sni={sni}&sid={short_id}&spx={spider_x}#{remark}
```

## Monitoring and Notifications
The bot runs periodic (hourly by default) checks and:
- Deletes users' profiles if they are no longer a chat/group member

## Security
- All sensitive data is stored in environment variables
- Pydantic used for configuration validation
- Limited access to administrative functions

## Potential Issues and Solutions
1. **3X-UI connection errors** - Check the URL and credentials
2. **Database errors** - Check directory write permissions
3. **Notifications not working** - Check time/timezone settings

---

*For more information, see the [aiogram](https://docs.aiogram.dev/en/latest/) and [3X-UI](https://github.com/MHSanaei/3x-ui/wiki) documentation.*