import os
import logging
from pathlib import Path
from uuid import uuid4

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vaultai_bot")

API_BASE = "http://localhost:8000"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to VaultAI Bot!\n\n"
        "Commands:\n"
        "/register <email> <password> - Create account\n"
        "/login <email> <password> - Get your token\n"
        "/jobs - List your processing jobs\n"
        "/vaults - List your podcasts\n"
        "/ask <podcast_id> <question> - Ask about a podcast\n\n"
        "Or just send an audio file to upload!"
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /register <email> <password>")
        return
    import httpx
    email, password = context.args[0], context.args[1]
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/auth/register", json={"email": email, "password": password})
        if resp.status_code == 201:
            await update.message.reply_text("Account created! Login with /login")
        else:
            await update.message.reply_text(f"Error: {resp.json().get('detail', resp.text)}")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /login <email> <password>")
        return
    import httpx
    email, password = context.args[0], context.args[1]
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            context.user_data["token"] = token
            await update.message.reply_text(f"Logged in! Token saved for this chat.")
        else:
            await update.message.reply_text(f"Error: {resp.json().get('detail', resp.text)}")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("token")
    if not token:
        await update.message.reply_text("Please /login first")
        return
    import httpx
    file = await update.message.effective_attachment.get_file()
    local_path = f"/tmp/{uuid4()}.ogg"
    await file.download_to_drive(local_path)
    async with httpx.AsyncClient() as client:
        with open(local_path, "rb") as f:
            resp = await client.post(
                f"{API_BASE}/upload/audio",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (file.file_path.split("/")[-1], f, "audio/ogg")},
            )
    os.remove(local_path)
    if resp.status_code == 200:
        data = resp.json()
        await update.message.reply_text(
            f"Uploaded! Job ID: {data['job_id']}\nPodcast ID: {data['podcast_id']}"
        )
    else:
        await update.message.reply_text(f"Upload failed: {resp.text}")

async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("token")
    if not token:
        await update.message.reply_text("Please /login first")
        return
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/ingest/jobs", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            jobs = resp.json().get("jobs", [])
            if not jobs:
                await update.message.reply_text("No jobs found.")
            else:
                msg = "\n".join(f"• {j['job_id'][:8]}... - {j['status']}" for j in jobs[:10])
                await update.message.reply_text(f"Jobs:\n{msg}")
        else:
            await update.message.reply_text(f"Error: {resp.text}")

async def list_vaults(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("token")
    if not token:
        await update.message.reply_text("Please /login first")
        return
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/vaults", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            vaults = resp.json().get("vaults", [])
            if not vaults:
                await update.message.reply_text("No podcasts yet.")
            else:
                msg = "\n".join(f"• {v['podcast_id']} - {v['title'][:40]}" for v in vaults[:10])
                await update.message.reply_text(f"Vaults:\n{msg}")
        else:
            await update.message.reply_text(f"Error: {resp.text}")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("token")
    if not token:
        await update.message.reply_text("Please /login first")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /ask <podcast_id> <question>")
        return
    podcast_id = context.args[0]
    question = " ".join(context.args[1:])
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/query/ask",
            headers={"Authorization": f"Bearer {token}"},
            json={"podcast_id": podcast_id, "question": question},
        )
        if resp.status_code == 200:
            await update.message.reply_text(resp.json()["answer"][:4000])
        else:
            await update.message.reply_text(f"Error: {resp.text}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("jobs", list_jobs))
    app.add_handler(CommandHandler("vaults", list_vaults))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    logger.info("Bot started. Polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
