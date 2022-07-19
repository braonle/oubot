# Introduction
The purpose of the bot is to track the amount of valuables (cash, time etc.) paid in advance and used later per Telegram group chat.
# Installation
The process consists of 2 parts: bot code deployment and Telegram deployment
## Telegram deployment
1. Talk to [BotFather](https://t.me/botfather) to obtain bot API key
1. Create a maintenance chat and add your bot there
1. Add the bot to any group chat and grant it admin privileges (required for text cleanup)
## Bot code deployment
1. Copy the most up-to-date code to the host
    ```shell
    $ https://github.com/braonle/oubot.git
    $ cd oubot
    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install pip --upgrade
    $ pip install -r requirements.txt
    ```
1. Fill out the necessary parameters in [engine/global_params.py](#bot-parameters)
1. Initialize SQLite3 DB file
    ```shell
    $ cd engine/sqlite
    $ sqlite3 oubot.sqlite3 < oubot.schema
    ```
1. Create systemd entry is you want automatic bot startup on system boot
    ```shell
    $ cat /etc/systemd/system/oubot.service 
    [Unit]
    Description=Telegram bot (oubot)
    After=multi-user.target
    
    [Service]
    Type=simple
    WorkingDirectory=<path to the bot>/oubot
    Restart=always
    ExecStart=<path to the bot>/oubot/venv/bin/python <path to the bot>/oubot/main.py
    
    [Install]
    WantedBy=multi-user.target
    ```
1. Enable oubot
    ```shell
    $ systemctl daemon-reload
    $ systemctl enable oubot
    $ systemctl start oubot
    ```

## Bot parameters
### Global
* **DEBUG**: disables notifying all chats on startup/shutdown events
* **POLLING_BASED**: toggles webhook or polling Telegram to retrieve messages
### Bot
* **TOKEN**: API token obtained from [BotFather](https://t.me/botfather)
* **MAINT_ID**: chat ID of maintenance chat, can be obtained from [RawDataBot](https://t.me/RawDataBot)
### SQLite3
* **DB_NAME**: path to SQLite DB file created from oubot.schema [in advance](#bot-code-deployment), relative to working directory
### Polling
* **POLL_INTERVAL**: how often bot polls Telegram, seconds
### Webhook
* **PUBLIC_IP**: public IP or URL that can be used for webhook callback (e.g. public NAT IP)  
* **LISTEN_IP**: physical IP address to start listener on (e.g. private NAT IP), can be *0.0.0.0*  
* **PORT**: TCP port listener acquires from OS  
* **PRIVATE_KEY**: path to certificate private key, relative to working directory  
* **CERTIFICATE**: path to certificate, relative to working directory

# Usage
Initially no group is allowed to utilize the bot. Maintenance chat is used to authorize new groups via chat ID.
1. Call /help command in the group (other commands are ignored)
2. Bot will report a new group in maintenance chat
3. Call /authz_group <chat_id> in maintenance chat
4. Group is now authorized and all commands are available. Call /start for button menu or issue commands directly

## Caveats
1. If using inline keyboard, only a single instance per chat is allowed at a time. Invoking several 
keyboards in a single chat might result in session data corruption and loss of data input.
1. Creating a new keyboard does not render the previous one inactive. Thus it is recommended to finish 
conversation as soon as keyboard is not needed.

# Commands
All commands are available directly, although using inline button keyboard is recommended
* **/start**: invoke inline keyboard menu
* **/help**: list available commands and their description
* **/get_balance**: prints available resource amount
* **/add_balance \<amount\>**: adds the input amount to the currently available
* **/use_balance \<hours\> \<rent\>**: utilizes the resources, *hours* \* *hour_fee* + *rent*
* **/set_hour_fee \<hour_fee\>**: sets the multiplier (1200 by default), available to chat admins only


