#!/bin/bash

# Setup script for Gym Reminder Bot

echo "🏋️ Gym Reminder Bot Setup 🏋️"
echo "================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.8 or higher first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed!"
    echo "Please install pip3 first."
    exit 1
fi

echo "✅ pip3 found"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
else
    echo "❌ Failed to install dependencies!"
    exit 1
fi

echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created!"
    echo ""
    echo "⚠️  IMPORTANT: Please edit the .env file and add your Telegram bot token!"
    echo "   You can get a token from @BotFather on Telegram."
    echo ""
    echo "   Steps to get a bot token:"
    echo "   1. Open Telegram and search for @BotFather"
    echo "   2. Send /newbot command"
    echo "   3. Follow the instructions to create your bot"
    echo "   4. Copy the token and paste it in the .env file"
    echo ""
else
    echo "ℹ️  .env file already exists"
    echo ""
fi

echo "================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your bot token"
echo "2. Run: python3 bot.py"
echo ""
echo "For more information, see README.md"
echo "================================"
